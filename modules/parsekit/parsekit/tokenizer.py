import re
from typing import Callable, Iterable, Dict, Tuple, TypeAlias


# Represents a lexical token that also tracks its position (line and column) in the source text.
# Inherits from `str` so it behaves like a string while carrying extra metadata.
class Token(str):
	"""A lexical token that behaves like a string but stores its source position.

	Each Token object contains the original string value and its
	position (line and column) within the source text.
	"""
	def __new__(cls, value: str, line: int = 0, column: int = 0):
		"""Create a new Token instance.

		Args:
			value: The string value of the token.
			line: The line number where the token starts (1-based).
			column: The column number where the token starts (1-based).

		Returns:
			A new Token instance containing the given value and position.
		"""
		# Create a new immutable string instance
		obj = super().__new__(cls, value)
		# Attach positional metadata (line and column) as attributes
		object.__setattr__(obj, "line", line)
		object.__setattr__(obj, "column", column)
		return obj

	def __repr__(self):
		"""Return a developer-friendly representation including position info."""
		# Custom string representation that includes token position info
		line = self.__getattribute__("line")
		column = self.__getattribute__("column")
		return f"<{self.__class__.__name__} {super().__repr__()} @ {line}:{column}>"

	def __str__(self):
		"""Return the plain string value of the token."""
		# Return the plain string value
		return super().__str__()

# Type alias for a function that constructs a Token object
# (value: str, line: int, column: int) -> Token
TokenConstructor: TypeAlias = Callable[[str, int, int], Token]

# Tokenizes the input text according to the given token specifications.
# Each entry in `specs` maps a token name to a tuple (constructor, regex).
# Returns an iterable of Token objects in order of appearance.
def tokenize(
		text: str,
		specs: Dict[str, Tuple[TokenConstructor, str]]
) -> Iterable[Token]:
	r"""Generate tokens from input text according to the given token specifications.

	This function scans `text` using a composite regular expression built
	from `specs`, which defines named token types and their matching patterns.
	Each matched substring is passed to the associated TokenConstructor
	to create a Token object that includes its position in the source text.

	Args:
		text: The input text to be tokenized.
		specs: A mapping of token type names to tuples of
			(TokenConstructor, regex_pattern).  
			Example:  
			```
			specs = {
				"NUMBER": (NumberToken, r"\d+"),
				"PLUS": (OperatorToken, r"\+"),
				"WS": (lambda v, l, c: None, r"\s+"),
			}
			```

	Yields:
		Token objects in the order they appear in the source text.

	Raises:
		ValueError: If any portion of the input does not match a token pattern,
			or if a zero-length regex match is detected.

	Example:
		>>> specs = {
		...     "NUMBER": (Token, r"\d+"),
		...     "PLUS": (Token, r"\+"),
		...     "WS": (lambda v, l, c: None, r"\s+"),
		... }
		>>> list(tokenize("12 + 34", specs))
		[<Token '12' @ 1:1>, <Token '+' @ 1:4>, <Token '34' @ 1:6>]
	"""
	# Combine all token regex patterns into a single pattern with named groups
	parts = [f"(?P<{name}>{regex})" for name, (_, regex) in specs.items()]
	_re_pattern = re.compile("|".join(parts), re.DOTALL)

	# Initialize position tracking
	line = 1
	col = 1
	pos = 0

	# Iterate over all regex matches in the input text
	for m in _re_pattern.finditer(text):
		kind = m.lastgroup # The name of the matched token type
		value = m.group()  # The matched text

		# Detect unrecognized text between matches
		if m.start() != pos:
			snippet = text[pos:m.start()]
			raise ValueError(f"Unrecognized input at {line}:{col}: {snippet!r}")

		# Skip unnamed or invalid matches (should not normally occur)
		if not kind:
			pos = m.end()
			continue

		# Prevent infinite loops caused by zero-length regex matches
		if value == "":
			raise ValueError(f"Zero-length match for token '{kind}' at {line}:{col}")

		# Record the token's starting position before advancing
		start_line = line
		start_col = col

		# Update line and column counters based on the matched text
		newlines = value.count("\n")
		if newlines:
			line += newlines
			# Column resets to 1 + the length of text after the last newline
			tail = value.rsplit("\n", 1)[1]
			col = 1 + len(tail)
		else:
			col += len(value)

		# Construct and yield a Token instance using the appropriate constructor
		(new_func, _) = specs[kind]
		yield new_func(value, start_line, start_col)

		# Move the scanning position forward
		pos = m.end()

	# Detect leftover unrecognized text at the end of input
	if pos != len(text):
		snippet = text[pos:pos+20]
		raise ValueError(f"Unrecognized input at {line}:{col}: {snippet!r}")