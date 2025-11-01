import pytest

from typing import Dict, Tuple


from parsekit import *


def test_token_str_and_repr():
	t = Token("abc", line=3, column=5)
	assert str(t) == "abc"
	# repr はクォート付きの値と位置が入る
	assert repr(t) == "<Token 'abc' @ 3:5>"

class SkipToken(Token): pass

def test_tokenize_basic_with_ws_skipped_by_returning_none():
	# WS は None を返すコンストラクタにして「見た目上スキップ」
	specs: Dict[str, Tuple[TokenConstructor, str]] = {
		"NUMBER": (Token, r"\d+"),
		"PLUS": (Token, r"\+"),
		"WS": (lambda v, l, c: SkipToken(v, l, c), r"\s+"),
	}
	text = "12 + 34"

	out = list(tokenize(text, specs))

	# 生成物には None も含まれる点に注意（tokenize はフィルタしない実装）
	nones = [ x for x in out if isinstance(x, SkipToken) ]
	toks = [ x for x in out if not isinstance(x, SkipToken) ]

	assert len(nones) == 2  # 空白2つ
	assert [str(t) for t in toks] == ["12", "+", "34"]

	# 位置も検証（1-based）
	assert (toks[0].__getattribute__("line"), toks[0].__getattribute__("column")) == (1, 1)  # "12"
	assert (toks[1].__getattribute__("line"), toks[1].__getattribute__("column")) == (1, 4)  # "+"
	assert (toks[2].__getattribute__("line"), toks[2].__getattribute__("column")) == (1, 6)  # "34"

def test_unrecognized_input_raises_value_error():
	# アルファベットが specs に無いので途中で未認識扱い
	specs: Dict[str, Tuple[TokenConstructor, str]] = {
		"NUMBER": (Token, r"\d+"),
		"WS": (lambda v, l, c: SkipToken(v, l, c), r"\s+"),
	}
	with pytest.raises(ValueError) as e:
		list(tokenize("1a", specs))
	msg = str(e.value)
	assert "Unrecognized input" in msg
	assert "1:2" in msg  # "1" の後ろ（col=2）で未認識 'a'

def test_zero_length_match_is_rejected():
	# 空文字にマッチする正規表現は実装で禁止されている
	specs: Dict[str, Tuple[TokenConstructor, str]]= {
		"EMPTY": (Token, r""),
	}
	with pytest.raises(ValueError) as e:
		list(tokenize("", specs))
	assert "Zero-length match for token 'EMPTY'" in str(e.value)

def test_position_updates_across_newlines():
	specs: Dict[str, Tuple[TokenConstructor, str]] = {
		"WORD": (Token, r"[a-z]+"),
		"NUMBER": (Token, r"\d+"),
		"WS": (lambda v, l, c: SkipToken(v, l, c), r"\s+"),  # 改行も含めてスキップ
	}
	text = "ab\n12\nc"
	out = [t for t in tokenize(text, specs) if not isinstance(t, SkipToken)]
	vals = [str(t) for t in out]
	poss = [(t.__getattribute__("line"), t.__getattribute__("column")) for t in out]

	assert vals == ["ab", "12", "c"]
	assert poss == [(1, 1), (2, 1), (3, 1)]  # 改行で列がリセット


def test_custom_constructor_is_used_and_positions_are_correct():
	class NumToken(Token):
		pass

	def make_num(v: str, line: int, col: int) -> Token:
		# たとえば数値は専用サブクラスで返す
		return NumToken(v, line, col)

	specs: Dict[str, Tuple[TokenConstructor, str]] = {
		"NUMBER": (make_num, r"\d+"),
		"WS": (lambda v, l, c: SkipToken(v, l, c), r"\s+"),
	}
	out = [t for t in tokenize("7 8", specs) if not isinstance(t, SkipToken)]

	assert all(isinstance(t, NumToken) for t in out)
	assert [str(t) for t in out] == ["7", "8"]
	assert (out[0].__getattribute__("line"), out[0].__getattribute__("column")) == (1, 1)
	assert (out[1].__getattribute__("line"), out[1].__getattribute__("column")) == (1, 3)