# py-toolbox

**py-toolbox** は複数の独立した Python ユーティリティモジュールをまとめたモノレポです。
各モジュールは個別にインストール・利用でき、共通の設計方針（シンプル・型安全・テスト済み）に基づいています。

---

## 含まれるモジュール

| モジュール名 | 説明 | インストール例 |
|--------------|------|----------------|
| [`parsekit`](./modules/parsekit) | パーサーコンビネータによるテキスト解析ツールキット | `pip install "git+https://github.com/OWNER/py-toolbox.git@main#subdirectory=modules/parsekit"` |

---

## クイックスタート
次のコマンドでモジュールのインストールができます。

```bash
# 例: parsekit をインストール
pip install "git+https://github.com/OWNER/py-toolbox.git@main#subdirectory=modules/<モジュール名>"

# インポート
python -m parsekit
```
