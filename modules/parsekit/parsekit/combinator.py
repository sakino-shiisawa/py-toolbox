from .tokenizer import Token
from typing import Self, Tuple, List, TypeAlias, Union, Callable

def _error_message(text: str, tok: Token|None, message: str) -> str: # type: ignore
	lines = text.splitlines()
	if not tok:
		return message
	
	line = tok.__getattribute__("line")
	column = tok.__getattribute__("column")

	line_content: str = ""
	
	if line < 1 or line > len(lines):
		line_content = ""
	else:
		line_content = lines[line - 1] # type: ignore

	pointer_line = " " * (column - 1) + "^" + message
	return f"\n{line_content}\n{pointer_line}"

class ParseError(SyntaxError):
	def __init__(self, tok: Token|None, message: str):
		super().__init__(f"{tok} - {message}")
		self.token = tok

class FatalParseError(ParseError):
	def __init__(self, tok: Token | None, message: str):
		super().__init__(tok, message)


ParseResult: TypeAlias = List[Union[Token, "ParseResult"]]

ParseReturn: TypeAlias = Tuple[ParseResult, List[Token]]

class Node:
	_token_type = None
	_expected_value = None
	_unexpected_value = None
	_gather = False
	_on_fail = None

	def __init__(self, token_type: type|None = None):
		self._token_type = token_type
		self._expected_value = None
		self._gather = False
		self._on_fail = None
	
	def expected(self, value: str) -> Self:
		self._expected_value = value
		return self
	
	def unexpected(self, value: str) -> Self:
		self._unexpected_value = value
		return self
	
	def pack(self) -> "PackNode":
		return PackNode(self)
	
	def gather(self, flag: bool = True) -> Self:
		self._gather = flag
		return self
	
	def on_fail(self, _on_fail: Callable[[Exception], None]) -> Self:
		self._on_fail = _on_fail
		return self
	
	def __add__(self, other: "Node") -> "SequenceNode":
		return SequenceNode(self, other)
	
	def __or__(self, other: "Node") -> "ChoiceNode":
		return ChoiceNode(self, other)

	def repeat(self, min_times: int, max_times: int|None = None) -> "RepeatNode":
		return RepeatNode(self, min_times, max_times)
	
	def parse(self, text: str, tokens: List[Token]) -> ParseReturn:
		if not tokens:
			e = ParseError(None, f"tokens is empty")
			if self._on_fail:
				self._on_fail(e)
				return ([], [])
			else:
				raise e
		if not self._token_type:
			e = ValueError(f"Token type is not set")
			if self._on_fail:
				self._on_fail(e)
				return ([], tokens)
			else:
				raise e
		
		# Check if the token type matches the expected type
		if not isinstance(tokens[0], self._token_type): # type: ignore
			e = ParseError(tokens[0], _error_message(text, tokens[0], f"Expected {self._token_type}"))
			if self._on_fail:
				self._on_fail(e)
				return ([], tokens)
			else:
				raise e
		# Match expected or unexpected value			
		head = tokens[0]
		tail = tokens[1:]
		val = str(head)

		if not self._expected_value and not self._unexpected_value:
			return ([head], tail)

		matched= False
		if self._expected_value is not None:
			matched = (val == self._expected_value)
		elif self._unexpected_value is not None:
			matched = (val != self._unexpected_value)
		else:
			matched = False

		if matched:
			if self._gather:
				return ([head], tail)
			else:
				return ([], tail)
		
		# Fail if the value does not match expectations
		e = ParseError(tokens[0], _error_message(text, tokens[0], f"Expected {self._expected_value}"))
		if self._on_fail:
			self._on_fail(e)
			return ([], tokens)
		else:
			raise e
		
		# not reachable
		return ([], tokens)


class PackNode(Node):
	_node: Node|None = None

	def __init__(self, node: Node):
		super().__init__()
		self._node = node

	def parse(self, text: str, tokens: List[Token]) -> ParseReturn:
		result: ParseResult = []
		try:
			if not self._node:
				e = ValueError(f"node is not set")
				if self._on_fail:
					self._on_fail(e)
					return ([], tokens)
				else:
					raise e
			(sub_result, tokens) = self._node.parse(text, tokens)
			if sub_result:
				result.append(sub_result)
		except FatalParseError:
			raise
		except ParseError as e:
			if self._on_fail:
				self._on_fail(e)
				return ([], tokens)
			raise e
		return (result, tokens)

class SequenceNode(Node):
	_lhs: Node|None = None
	_rhs: Node|None = None

	def __init__(self, lhs: Node, rhs: Node):
		super().__init__()
		self._lhs = lhs
		self._rhs = rhs

	def parse(self, text: str, tokens: List[Token]) -> ParseReturn:
		result: ParseResult = []
		new_tokens: List[Token] = []
		try:
			if not self._lhs:
				e = ValueError(f"lhs is not set")
				if self._on_fail:
					self._on_fail(e)
					return ([], tokens)
				else:
					raise e
			if not self._rhs:
				e = ValueError(f"rhs is not set")
				if self._on_fail:
					self._on_fail(e)
					return ([], tokens)
				else:
					raise e
			(sub_result, new_tokens) = self._lhs.parse(text, tokens)
			if sub_result:
				result.extend(sub_result)
			(sub_result, new_tokens) = self._rhs.parse(text, new_tokens)
			if sub_result:
				result.extend(sub_result)
		except FatalParseError:
			raise
		except ParseError as e:
			# Call failure handler if provided
			if self._on_fail:
				self._on_fail(e)
				return ([], tokens)
			raise
		return (result, new_tokens)

class RepeatNode(Node):
	_node: Node|None = None
	_min_times: int = 0
	_max_times: int|None = None

	def __init__(self, node: Node, min_times: int, max_times: int|None):
		super().__init__()
		self._node = node
		self._min_times = min_times
		self._max_times = max_times

	def parse(self, text: str, tokens: List[Token]) -> ParseReturn:
		count = 0
		result: ParseResult = []

		if self._max_times and (self._min_times > self._max_times):
			e = ValueError(f"min_times > max_times")
			if self._on_fail:
				self._on_fail(e)
				return ([], tokens)
			else:
				raise e
		if not self._node:
			e = ValueError(f"node is not set")
			if self._on_fail:
				self._on_fail(e)
				return ([], tokens)
			else:
				raise e

		while tokens:
			if self._max_times and count >= self._max_times:
				break
			try:
				(sub_result, tokens) = self._node.parse(text, tokens) # type: ignore
				if sub_result:
					result.extend(sub_result)
				count += 1
			except FatalParseError:
				raise
			except ParseError as e:
				# Fail if minimum repetitions not met
				if count < self._min_times:
					tok = tokens[0] if tokens else None
					line = tok.__getattribute__("line") if tok else -1
					col = tok.__getattribute__("column") if tok else -1
					e = ParseError(tok, _error_message(text, tok, f"Expected at least {self._min_times} matches at {line}:{col}"))
					if self._on_fail:
						self._on_fail(e)
						return ([], tokens)
					else:
						raise e
				else:
					break
		return (result, tokens)


class ChoiceNode(Node):
	_first: Node
	_second: Node

	def __init__(self, first: Node, second: Node):
		super().__init__()
		self._first = first
		self._second = second
	
	def gather(self, flag: bool = True) -> Self:
		self._first.gather()
		self._second.gather()
		return self
	
	def parse(self, text: str, tokens: List[Token]) -> ParseReturn:
		for node in [self._first, self._second]:
			try:
				return node.parse(text, tokens)
			except FatalParseError:
				raise
			except ParseError as e:
				if self._on_fail:
					self._on_fail(e)
		else:
			e = ParseError(tokens[0], _error_message(text, tokens[0], f"No OR match"))
			if self._on_fail:
				self._on_fail(e)
				return ([], tokens)
			else:
				raise e
		
		return ([], tokens)
	
class FatalNode(Node):
	_node: Node

	def __init__(self, node: Node):
		super().__init__()
		self._node = node

	def parse(self, text: str, tokens: List[Token]) -> ParseReturn:
		try:
			return self._node.parse(text, tokens)
		except FatalParseError:
			raise
		except ParseError as e:
			raise FatalParseError(e.token, str(e)) from e
		
def Fatal(node: Node) -> FatalNode:
	return FatalNode(node)