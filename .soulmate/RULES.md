📜 SoulMate: 開発・運用規約 (RULES.md)

このドキュメントは、本プロジェクトに関わるすべてのエージェントが遵守すべき絶対的な規約です。

1. コーディング規約 (Coding Standards)

Python 3.12+:

全ての関数・変数に型ヒント (Type Hinting) を必須とします。

mypy による静的解析をパスしないコードの提出を禁じます。

非同期処理 (Asynchronous):

原則として asyncio を使用し、メインUIスレッドをブロックする処理を記述してはいけません。

ロギング (Logging):

print() の使用を厳禁します。

logging モジュールを用い、debug, info, warning, error を文脈に応じて適切に使い分けてください。

2. エージェント運用ルール (Agent Operational Rules)

破壊的変更の禁止:

既存のコアロジックを大幅に変更する場合は、必ずバックアップの作成または別ブランチでの作業を提案し、ユーザーの承諾を得ること。

ドキュメントの同期:

ファイル構成を変更した際は、即座に .soulmate/PROJECT_MAP.md を更新すること。

3. 📝 ログ更新の絶対義務 (Strict Logging Policy)

エージェントのすべての活動は、以下の手順に従って記録されなければなりません。この手順の省略は、業務の未完了を意味します。

作業開始時 (Pre-process):

実際のコードを書き換える前に、必ず .soulmate/memories/session_log.md を読み込み、現在のタスクを [In Progress] に更新すること。

作業終了時 (Post-process):

変更内容の要約、実行したテストの結果、および「次にやるべき課題」を明記し、ステータスを [Completed] に更新すること。

継続的な思考の共有:

途中で問題が発生した場合は、速やかにログの Pending Questions セクションへ追記し、ユーザーの判断を仰ぐこと。

