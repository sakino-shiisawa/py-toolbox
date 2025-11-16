from typing import Any, Dict, List, Tuple, Optional
from dataclasses import dataclass ,field
import re


class RenderError(Exception): pass

@dataclass
class Node: pass

@dataclass
class TextNode(Node):
	text: str

@dataclass
class IfNode(Node):
	branches: List[Tuple[str, List[Node]]] = field(default_factory=list) # type: ignore
	else_block: Optional[List[Node]] = None

@dataclass
class ForNode(Node):
	target: str
	iterable_expr: str
	body: List[Node] = field(default_factory=list) # type: ignore

_SAFE_BUILTINS = {
	"len": len,
	"range": range,
	"str": str,
	"int": int,
	"float": float,
	"bool": bool,
	"list": list,
	"dict": dict,
	"tuple": tuple,
	"set": set,
	"sum": sum,
	"min": min,
	"max": max,
	"any": any,
	"all": all,
	"enumerate": enumerate,
	"zip": zip,
}

_DOLLAR_SENTINEL = "\0__ESC_DOLLAR_LBRACE__\0"
_AT_SENTINEL = "\0__ESC_AT_AT__\0"

def _eval_expr(expr: str, ctx: Dict[str, Any]) -> Any:
	local_ctx = dict(ctx)
	local_ctx["ctx"] = ctx
	try:
		return eval(expr, {"__builtins__": _SAFE_BUILTINS}, local_ctx)
	except Exception as e:
		raise RenderError(f"式の評価に失敗しました: {expr!r}: {e}") from e

def _render_if(node: IfNode, ctx: Dict[str, Any]) -> str:
	for (cond, block) in node.branches:
		value = _eval_expr(cond, ctx)
		if bool(value):
			return _render_block(block, ctx)
	if node.else_block is not None:
		return _render_block(node.else_block, ctx)
	return ""

def _render_for(node: ForNode, ctx: Dict[str, Any]) -> str:
	iterable = _eval_expr(node.iterable_expr, ctx)

	try:
		iterator = iter(iterable)
	except:
		raise RenderError(f"<expr> is not iterable in @for <var> in <expr>")
	
	var_names = [ v.strip() for v in node.target.split(",") if v.strip() ]
	if not var_names:
		raise RenderError(f"<var> is not defined in @for <var> in <expr>")
	
	result_parts: List[str] = []
	local_ctx: Dict[str, Tuple[bool, Any]] = {}

	for var in var_names:
		if var in ctx:
			local_ctx[var] = (True, ctx[var])
		else:
			local_ctx[var] = (False, None)
	
	for element in iterator:
		if len(var_names) == 1:
			ctx[var_names[0]] = element
		else:
			try:
				seq = list(element)
			except TypeError:
				raise RenderError("<expr> cannnot unpack @for <var> in <expr>")
			if len(seq) != len(var_names):
				raise RenderError("iterator count is mismatched")
			
			for name, value in zip(var_names, seq):
				ctx[name] = value
		result_parts.append(_render_block(node.body, ctx))
	
	for (var, (had_original, value)) in local_ctx.items():
		if had_original:
			ctx[var] = value
		else:
			ctx.pop(var, None)
	return "".join(result_parts)

def _render_block(nodes: List[Node], ctx: Dict[str, Any]) -> str:
	out_parts: List[str] = []
	for node in nodes:
		if isinstance(node, TextNode):
			out_parts.append(_substitute_placeholders(node.text, ctx))
		elif isinstance(node, IfNode):
			out_parts.append(_render_if(node, ctx))
		elif isinstance(node, ForNode):
			out_parts.append(_render_for(node, ctx))
		else:
			raise RuntimeError(f"unknown node type: f{type(node)}")
	return "\n".join(out_parts)

def _substitute_placeholders(text: str, ctx: Dict[str, Any]) -> str:

	s = text.replace("$${", _DOLLAR_SENTINEL)
	s = s.replace("@@", _AT_SENTINEL)

	pattern = re.compile(r"\$\{([^}]+)\}")

	def repl(m: re.Match) -> str: # type: ignore
		expr = m.group(1).strip()
		if not expr:
			raise RenderError("found empty placeholder")
		
		value = _resolve_placeholder(expr, ctx)
		try:
			return str(value)
		except Exception as e:
			raise RenderError(f"placeholder {expr!r} cannot be convert to string: {e}") from e
	s = pattern.sub(repl, s)

	s = s.replace(_DOLLAR_SENTINEL, "${")
	s = s.replace(_AT_SENTINEL, "@")

	return s

def _resolve_placeholder(expr: str, ctx: Dict[str, Any]) -> Any:
	parts = expr.split(".")
	key = parts[0]
	if key not in ctx:
		raise RenderError(f"not found value in context: {expr!r}")
	
	value: Any = ctx[key]

	for p in parts[1:]:
		if not hasattr(value, "__getitem__"):
			raise RenderError(f"placeholder {expr!r} is not dictionary: {value!r}")
		str_key = str(p)
		try:
			value = value[str_key]
		except Exception as e:
			raise RenderError(f"context has no placeholder {expr!r}: {e}") from e
	
	return value


class Template(str):
	def __new__(cls, value: str):
		obj = super().__new__(cls, value)
		return obj

	def _parse_template(self) -> List[Node]:
		lines = self.splitlines(keepends=True)

		root: List[Node] = []
		current_block: List[Node] = root
		block_stack: List[List[Node]] = []
		control_stack: List[Node] = []

		for line in lines:
			stripped = line.strip()

			if stripped.startswith("@if "):
				cond = stripped[len("@if "):].strip()
				if not cond:
					raise SyntaxError("@if should be condition expression")
				node = IfNode(branches=[(cond, [])])
				current_block.append(node)

				control_stack.append(node)
				block_stack.append(current_block)
				current_block = node.branches[0][1]
			elif stripped.startswith("@elif"):
				if not control_stack or not isinstance(control_stack[-1], IfNode):
					raise SyntaxError("@elif out of range between @if and @end")
				
				cond = stripped[len("@elif "):].strip()
				if not cond:
					raise SyntaxError("@if should be condition expression")
				if_node: IfNode = control_stack[-1]
				new_block: List[Node] = []
				if_node.branches.append((cond, new_block))
				current_block = new_block

			elif stripped == "@else":
				if not control_stack or not isinstance(control_stack[-1], IfNode):
					raise SyntaxError("@else out of range between @if and @end")
				
				if_node: IfNode = control_stack[-1]
				new_block: List[Node] = []
				if_node.else_block = new_block
				current_block = new_block
			elif stripped.startswith("@for "):
				rest = stripped[len("@for "):].strip()
				parts = rest.split(" in ", 1)
				if len(parts) != 2:
					raise RenderError("syntax error: @for <var> in <expr>")
				(target, iterable_expr) = (parts[0].strip(), parts[1].strip())
				if not target or not iterable_expr:
					raise SyntaxError("syntax error: @for <var> in <expr>")
				node = ForNode(target=target, iterable_expr=iterable_expr)
				current_block.append(node)

				control_stack.append(node)
				block_stack.append(current_block)
				current_block = node.body

			elif stripped == "@end":
				if not control_stack:
					raise SyntaxError("invalid @end keyword")
				control_stack.pop()
				if not block_stack:
					raise RuntimeError("block statck is broken")
				current_block = block_stack.pop()

			else:
				current_block.append(TextNode(line))
		if control_stack:
			raise SyntaxError("not found @end")
		return root

	def apply_template(self, params: Dict[str, Any]) -> str:
		ast_root = self._parse_template()
		ctx: Dict[str, Any] = dict(params)
		return _render_block(ast_root, ctx)