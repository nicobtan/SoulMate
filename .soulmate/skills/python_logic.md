# Python Logic - Best Practices (Python 3.12+)

このドキュメントは、SoulMateプロジェクトにおけるPython 3.12以上の環境を前提とした実装の定石・ベストプラクティスを定めます。エージェントがPythonコードを生成・修正する際はこのスキルに基づき行動してください。

## 1. 型ヒント (Type Hints) の徹底

安全性と可読性の向上のため、全ての関数・メソッドに対して引数・戻り値の型ヒントを義務付けます。

- **モダンな型構文の使用**
  - Python 3.10以降の `|` 演算子を使用したUnion型を記述します： `def process(data: str | None) -> int:`
  - 組み込み型のコレクション（`list`, `dict`, `tuple` など）を直接使用します。`typing.List` などは非推奨です： `def get_items() -> list[str]:`
- **Generics / TypeVar の活用**
  - 汎用的なクラスや関数では、`TypeVar` や、Python 3.12で導入された新しい型のパラメーター構文 (`type` ステートメントや `[T]` など) を適宜活用します。

## 2. 構造化データの扱い (Dataclasses / Pydantic)

データのやり取りには、辞書(`dict`)の代わりに `dataclasses.dataclass` または Pydanticモデル（設定管理やAPI通信などでバリデーションが必要な場合）を利用してください。

```python
from dataclasses import dataclass

@dataclass(kw_only=True)
class UserMemory:
    id: str
    content: str
    importance: int = 0
```
*(kwargs専用の `kw_only=True` を活用し、初期化の安全性を高めることを推奨します。)*

## 3. match-case 文の積極活用（パターンマッチング）

複雑な条件分岐（特にデータ構造の中身に応じた処理）には、`if-elif-else` の連続ではなく、Python 3.10以降の構造的パターンマッチングを利用してください。

```python
def handle_event(event: dict) -> None:
    match event:
        case {"type": "error", "code": code} if code > 500:
            logging.critical(f"Server error: {code}")
        case {"type": "message", "text": text}:
            logging.info(f"Received: {text}")
        case _:
            logging.warning("Unknown event format")
```

## 4. エラー処理と例外のチェイン

- カスタム例外を定義する場合は、`Exception` クラスを継承して適切な名前のクラスを作成してください。
- 他の例外を捕捉して新たな例外として再送出する際は、必ず `raise ... from e` を使用して元のスタックトレース（原因）を保持してください。

## 5. 新機能の活用 (Python 3.11 / 3.12+)

- **`asyncio.TaskGroup` の利用**: 複数の非同期処理を並行して実行し、安全に管理するために、`asyncio.gather` の代わりに Python 3.11で導入された、コンテキストマネージャーとしての `TaskGroup` を優先的に使用してください。
- **`try-except*` と `ExceptionGroup`**: 同時に複数発生しうる例外を個別に制御する必要がある場合は、`except*` を積極的に活用してください。
