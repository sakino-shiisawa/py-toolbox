# parsekit

**parsekit** は Python 用の軽量パーサーコンビネータライブラリです。
レキサ（字句解析）とパーサ（構文解析）を宣言的に組み合わせて、DSL・設定ファイル・独自言語などを簡潔に解析できます。

---

## 主な特徴
### 1. 型付きトークン
用途ごとにトークンクラスを自由に定義できます。  
これにより、構文要素に意味（型）を持たせることができます。

```python
class Repeat(Token): pass
class Ident(Token): pass
class Skip(Token): pass
class Function(Token): pass
class Char(Token): pass
```

トークンの仕様は正規表現で定義し、トークンの粒度を柔軟に決められます。

```python
TOKEN_SPECS = {
	"IDENT":         (lambda v, l, c: Ident(v, l, c),    r"[A-Za-z_][\w\d]*"),
	"SKIP":          (lambda v, l, c: Skip(v, l, c),     r"[ \t\n]+"),
	"REPEAT":        (lambda v, l, c: Repeat(v, l, c),   r"\.\.\."),
	"CHAR":          (lambda v, l, c: Char(v, l, c),     r"\(\)\{\};"),
	"FUNCTION":      (lambda v, l, c: Function(v, l, c),   r"function"),
}
```

解析は簡単な呼び出しで実現できます。
```python
tokens = [ tok for tok in tokenize(content, TOKEN_SPECS) ]
```

### 2. EBNFライクな文法
演算子のオーバーロードによりEBNF形式で直感的に文法で記述できます。

```python
FirstArgumentNode = (Node(String) | Node(Repeat)).gather()
ArgumentNode = FirstArgumentNode \
    + (Node(Char).expected(",") + FirstArgumentNode).repeat(0)

FunctionNode = \
	Node(Function) + Node(Ident).gather() \
	+ Node(Char).expected("(") \
	+ Node(MetaData).gather().repeat(0, 1) \
	+ Node(Char).expected(")") + Node(Char).expected(";")
```

| 記法 | 意味 | 例 |
| --- | --- | --- |
| `A + B` | 順次 | `Node(Char).expected("(") + ArgumentNode + Node(Char).expected(")")` |
| `.repeat(min, max)` | 繰り返し | `.repeat(0)`（0回以上） |
| `.gather()` | 解析結果に含める | `Node(Indent).gather()` |
| `.pack()` | 解析結果を収集する際にtuple化 | `ArgumentNode.pack()` |
| `.expected("str")` | トークンの文字列を参照 | `.expected("function")` |


### 3. 入れ子構造の解析
ネストされた構造も簡潔に扱えます。

```
function hoge() {
	function fugo() {
	}
}
```

### 4. 宣言的な構文構築
文法は「トークンクラス」または「トークン文字列」によってパターンを宣言的に定義できます。

### 5. 詳細なエラーレポート
`.expected("...")`により「どのトークンを期待していたか」を明示的に指定でき、
エラー時に「line 3, column 15 で ) を期待」といった詳細なメッセージを生成します。

### 6. 文法の合成と再利用が容易
複雑な構文も、部分文法を切り出して組み合わせることで簡潔に構築できます。

Before

```python
FunctionNode = \
	Node(Function) + Node(Ident).gather() \
	+ Node(Char).expected("(") \
	+ ((Node(Ident) | Node(Repeat)).gather() + (Node(Char).expected(",") + (Node(Ident) | Node(Repeat)).gather()).repeat(0)).gather() \
	+ Node(Char).expected(")") + Node(Char).expected(";")
```

After

```python
FirstArgumentNode = (Node(Ident) | Node(Repeat)).gather()
ArgumentNode = FirstArgumentNode \
	+ (Node(Char).expected(",") + FirstArgumentNode).repeat(0)

FunctionNode = \
	Node(Function) + Node(Ident).gather() \
	+ Node(Char).expected("(") \
	+ ArgumentNode.gather() \
	+ Node(Char).expected(")") + Node(Char).expected(";")
```

---

## インストール

```bash
pip install "git+https://github.com/OWNER/py-toolbox.git@main#subdirectory=modules/parsekit"
```

## サンプルコード

以下の内容を解析してみます。
```
function hoge(a, b);
function fugo(...);
```

期待される出力は次の通りです。
```
[
	("hoge", "a, b"),
	("fugo", "...")
]
```

この挙動を満たす実装は次のようになります。
```python
from parsekit import Token, Node, tokenize
class Repeat(Token): pass
class Ident(Token): pass
class Skip(Token): pass
class Function(Token): pass
class Char(Token): pass

TOKEN_SPECS = {
	"IDENT":         (lambda v, l, c: Ident(v, l, c),    r"[A-Za-z_][\w\d]*"),
	"SKIP":          (lambda v, l, c: Skip(v, l, c),     r"[ \t\n]+"),
	"REPEAT":        (lambda v, l, c: Repeat(v, l, c),   r"\.\.\."),
	"CHAR":          (lambda v, l, c: Char(v, l, c),     r"\(\)\{\};"),
	"FUNCTION":      (lambda v, l, c: Function(v, l, c),   r"function"),
}

tokens = [ tok for tok in tokenize(data, TOKEN_SPECS) if not isinstance(tok, Skip) ]

FirstArgumentNode = (Node(Ident) | Node(Repeat)).gather()
ArgumentNode = FirstArgumentNode \
	+ (Node(Char).expected(",") + FirstArgumentNode).repeat(0)

FunctionNode = \
	Node(Function) + Node(Ident).gather() \
	+ Node(Char).expected("(") \
	+ ArgumentNode.gather() \
	+ Node(Char).expected(")") + Node(Char).expected(";")

Program = FunctionNode.pack().repeat(0)

(results, _) = Program.parse(data, tokens)

print(results)
```
