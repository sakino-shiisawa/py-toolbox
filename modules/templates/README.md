# templates: シンプルでコード生成に最適なテンプレートエンジン

`templates` は、行頭ディレクティブ（`@for`, `@if`, `@end` など）と `${expr}` による式展開をサポートする、Python 向けの軽量テンプレートエンジンです。  
C++/Rust/Go などのコード生成、設定ファイル生成、ドキュメント生成などに向いています。

---

## 主な特徴

- `${expression}` による Python 変数・式の埋め込みが可能
- 行頭の `@for` / `@if` / `@elif` / `@else` / `@end` による制御構文
- テンプレートを一度コンパイルしてキャッシュし、高速にレンダリング
- 完全な Python ベースで依存関係が少なく、組み込みやすい
- コード生成に適したミニマルな構文設計

---

## インストール

```bash
python -m pip install "templates @ git+https://github.com/sakino-shiisawa/py-toolbox.git@main#subdirectory=modules/templates" --target ./script/modules --no-deps --upgrade
```

## サンプルコード

```python
from templates import Template

tmpl = Template(r'''
namespace v${version} {
@for c in classes
    class ${c.name} : public ${c.parent} {
    public:
        ${c.member_definitions}
    };
@end
}
''')

code = tmpl.render({
	"version": "1_0_0",
	"classes": [
        {
		    "name": "hoge",
            "parent": "test",
            "member_definitions": "int a;",
        },
        {
            "name": "fugo",
            "parent": "test1",
            "member_definitions": "int b;",
        },
	]
})

print(code)
```