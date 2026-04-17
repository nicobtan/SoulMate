# Development Rules

このファイルは、SoulMateプロジェクトにおけるコーディングスタイル、エラーハンドリング、非同期処理の原則を定義します。常にこのルールに従って実装を行ってください。

## 1. 命名規則 (Naming Conventions)

- **Python**
  - 変数名 / 関数名: `snake_case` (例: `user_profile`, `get_memory_data()`)
  - クラス名: `PascalCase` (例: `AgentController`, `Live2dManager`)
  - 定数名: `UPPER_SNAKE_CASE` (例: `MAX_RETRIES`, `DEFAULT_TIMEOUT`)
  - プライベート変数・メソッド: 先頭にアンダースコア `_private_var`
- **TypeScript / JavaScript**
  - 変数名 / 関数名: `camelCase` (例: `userProfile`, `getMemoryData()`)
  - クラス名 / インターフェース名: `PascalCase` (例: `AgentController`, `IUserMemory`)
  - 定数名: `UPPER_SNAKE_CASE`
- **ファイル・ディレクトリ**
  - 原則として `snake_case`（Pythonの場合）または `kebab-case`（Webフロントエンドなどの場合）を用い、プロジェクトの一貫性を最優先とします。

## 2. エラーハンドリングの原則

- **例外の握りつぶし厳禁**
  - 空の `except:` や `except Exception as e: pass` は絶対に記述しないでください。
  - 予期せぬエラーを防ぐため、エラーは必ず `logging` モジュールを使用して記録してください。
- **Loggingモジュールの活用**
  - デバッグ用の `print()` は本番コードに残さず、`logging.debug()`, `logging.info()`, `logging.warning()`, `logging.error()`, `logging.critical()` を使い分けてください。
  - エラー時には `logging.error("エラーの文脈: %s", e, exc_info=True)` とし、スタックトレースを残すことが推奨されます。
- **フェイルセーフな設計**
  - 外部API(例: TTS, STT, LLM)の呼び出し時は必ずタイムアウトを設定し、失敗した場合はリトライロジックを挟むか、適切なフォールバック処理（例: エラーメッセージの読み上げ、Live2Dの固有モーション（＞＜など）の再生）を行ってください。

## 3. 非同期処理 (Async/Await) の原則

- **I/Oバウンドな処理の非同期化**
  - ファイルの読み書き、ネットワークリクエスト、データベースへのクエリなどは、原則として `asyncio` や `aiohttp`（Python）、`fetch` / `Promise`（TS）を用いて非同期化してください。
- **イベントループのブロッキング回避**
  - `time.sleep()` のような同期的なブロッキング処理は避け、`await asyncio.sleep()` を使用してください。
  - CPUバウンドの重い処理（画像処理、同期的なモデル推論など）は、`concurrent.futures.ThreadPoolExecutor` や `ProcessPoolExecutor` (`asyncio.to_thread` など)に逃がしてメインスレッドのブロッキングを防いでください。

以上、このルールブックを順守し、プロジェクトの品質と安定性を保つように努めてください。
