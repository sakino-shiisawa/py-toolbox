# tests/parsekit/test_combinator.py
import pytest

from typing import List
from parsekit.parsekit import *

# ヘルパ: 楽に Token を作る
def T(v: str, line: int = 1, col: int = 1) -> Token:
	return Token(v, line, col)

# -----------------------
# Node（単体）挙動
# -----------------------

def test_node_raises_when_tokens_empty():
	n = Node(token_type=Token).gather()  # gatherは結果を返すように
	with pytest.raises(ParseError) as e:
		n.parse("text", [])
	assert "tokens is empty" in str(e.value)


def test_node_raises_when_token_type_not_set():
	n = Node()  # token_type を渡さない
	with pytest.raises(ValueError) as e:
		n.parse("text", [T("x")])
	assert "Token type is not set" in str(e.value)


def test_node_type_mismatch_raises_parseerror_with_pointer():
	n2 = Node(token_type=Token)
	text = "xx\ny"
	# 最初のトークンは Token だが、期待値チェックは通す前に type は OK
	# 「型ミスマッチ」を作るには別型が必要だが、実装は isinstance なので Token でOK。
	# ここでは「期待値」にトリガを置かず、敢えて別クラスで検証する
	class OtherToken(Token): pass

	n2 = Node(token_type=OtherToken)
	with pytest.raises(ParseError) as e:
		n2.parse(text, [T("y", line=2, col=1)])
	s = str(e.value)
	assert "Expected" in s
	assert "^Expected" in s  # ポインタ付きメッセージ


def test_node_expected_match_gathers_when_flag_true():
	n = Node(token_type=Token).expected("X").gather(True)
	res, rest = n.parse("X", [T("X")])
	# gather=True なので最初のトークンが結果に入る
	assert rest == []
	assert res and isinstance(res[0], Token) and str(res[0]) == "X"


def test_node_expected_match_no_gather_returns_empty_result():
	n = Node(token_type=Token).expected("X")  # gather=False デフォルト
	res, rest = n.parse("X", [T("X")])
	assert res == []
	assert rest == []


def test_node_unexpected_blocks_specific_value_and_raises():
	n = Node(token_type=Token).unexpected("NG")  # これと等しい値は拒否
	with pytest.raises(ParseError) as e:
		n.parse("NG", [T("NG")])
	assert "Expected" in str(e.value)  # 実装上は Expected メッセージを返す


def test_node_unexpected_accepts_other_values():
	n = Node(token_type=Token).unexpected("NG").gather()
	res, rest = n.parse("OK", [T("OK")])
	assert [str(x) for x in res] == ["OK"]
	assert rest == []


# -----------------------
# PackNode
# -----------------------

def test_packnode_wraps_subresult_as_nested_list():
	base = Node(token_type=Token).expected("A").gather()
	p = PackNode(base)
	res, rest = p.parse("A", [T("A")])
	# Pack はサブ結果があれば [sub_result] としてネストする
	assert isinstance(res, list)
	assert len(res) == 1
	assert [str(x) for x in res[0]] == ["A"]
	assert rest == []


def test_packnode_propagates_parseerror_to_on_fail_or_raises():
	base = Node(token_type=Token).expected("A")  # gather=False
	p = PackNode(base)

	# on_fail を設定していると、例外を握りつぶして ([], tokens) を返す
	captured: List[Exception] = []
	def on_fail(e: Exception):
		captured.append(e)
	p.on_fail(on_fail)

	res, rest = p.parse("B", [T("B")])  # 期待と不一致→ParseError
	assert res == []
	assert rest == [T("B")]  # tokens は消費されない
	assert captured and isinstance(captured[0], ParseError)


# -----------------------
# SequenceNode
# -----------------------

def test_sequencenode_combines_two_nodes_and_concatenates_results():
	a = Node(token_type=Token).expected("A").gather()
	b = Node(token_type=Token).expected("B").gather()
	seq = SequenceNode(a, b)

	res, rest = seq.parse("A B", [T("A"), T("B"), T("C")])
	assert [str(x) for x in res] == ["A", "B"]
	assert [str(x) for x in rest] == ["C"]


def test_sequencenode_handles_failure_via_on_fail():
	a = Node(token_type=Token).expected("A")
	b = Node(token_type=Token).expected("B")
	seq = SequenceNode(a, b)

	captured: List[Exception] = []
	seq.on_fail(lambda e: captured.append(e))

	res, rest = seq.parse("A X", [T("A"), T("X")])
	# on_fail があるため空結果で tokens を返す
	assert res == []
	assert [str(x) for x in rest] == ["A", "X"]
	assert captured and isinstance(captured[0], ParseError)


# -----------------------
# RepeatNode
# -----------------------

def test_repeatnode_errors_when_min_greater_than_max():
	base = Node(token_type=Token).expected("A")
	with pytest.raises(ValueError) as e:
		RepeatNode(base, min_times=2, max_times=1).parse("A", [T("A")])
	assert "min_times > max_times" in str(e.value)


def test_repeatnode_repeats_within_bounds_and_gathers_results():
	base = Node(token_type=Token).expected("A").gather()
	rep = RepeatNode(base, min_times=1, max_times=3)

	res, rest = rep.parse("A A B", [T("A"), T("A"), T("B")])
	assert [str(x) for x in res] == ["A", "A"]
	assert [str(x) for x in rest] == ["B"]


def test_repeatnode_raises_if_min_not_met():
	base = Node(token_type=Token).expected("A").gather()
	rep = RepeatNode(base, min_times=2, max_times=5)

	with pytest.raises(ParseError) as e:
		# 先頭で "A" にマッチしないため 0 回で失敗 → min_times を満たさずエラー
		rep.parse("X ...", [T("X", line=1, col=2)])
	s = str(e.value)
	assert "Expected at least 2 matches" in s
	assert "^Expected at least 2 matches" in s


# -----------------------
# ChoiceNode
# -----------------------

def test_choicenode_picks_first_that_matches():
	a = Node(token_type=Token).expected("A").gather()
	b = Node(token_type=Token).expected("B").gather()
	ch = a | b

	res, rest = ch.parse("A|B", [T("A"), T("B")])
	assert [str(x) for x in res] == ["A"]
	assert [str(x) for x in rest] == ["B"]


def test_choicenode_picks_second_if_first_fails():
	a = Node(token_type=Token).expected("A").gather()
	b = Node(token_type=Token).expected("B").gather()
	ch = a | b

	res, rest = ch.parse("B only", [T("B"), T("C")])
	assert [str(x) for x in res] == ["B"]
	assert [str(x) for x in rest] == ["C"]


def test_choicenode_raises_if_both_fail():
	a = Node(token_type=Token).expected("A")
	b = Node(token_type=Token).expected("B")
	ch = a | b

	with pytest.raises(ParseError) as e:
		ch.parse("X", [T("X")])
	assert "No OR match" in str(e.value)


def test_choicenode_gather_sets_children_to_gather():
	a = Node(token_type=Token).expected("A")
	b = Node(token_type=Token).expected("B")
	ch = (a | b).gather()  # 子の gather() を有効化する設計

	res, rest = ch.parse("A or B", [T("A"), T("B")])
	assert [str(x) for x in res] == ["A"]
	assert [str(x) for x in rest] == ["B"]
