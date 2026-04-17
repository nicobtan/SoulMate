# Session Log / Memories

このファイルは、エージェントが現在どのようなタスクに取り組み、プロジェクトがどの段階にあるかを自己記録・共有するための動的ファイル（Memory）です。
エージェント間で作業を引き継ぐ際や、過去の文脈を失わないために活用します。

## 記録フォーマット

新しいタスクや重要なフェーズの開始・終了時に、このファイルの下部に追記していくこと。

### テンプレート
```markdown
### [YYYY-MM-DD HH:MM] タスク名 / タイトル
- **Status:** [ Not Started | In Progress | Blocked | Completed ]
- **Context/Goal:** なぜこのタスクを行っているかの背景と目標
- **Working Files:** 編集・作成した主要ファイルパス
- **Next Action / Pending Questions:** 次のアクション、またはユーザーに確認すべき未定義事項
```

---

## Logs

### [2026-04-17 17:50] .soulmate ディレクトリ構成の構築
- **Status:** Completed
- **Context/Goal:** プロジェクト規模拡大に伴うバグ発生リスクを下げるため、プロジェクト独自の「魂」と「技術要件」をファイル化し、エージェントが自己完結的にプロジェクト方針を理解できるようにする。
- **Working Files:** `.soulmate/PROJECT_MAP.md`, `.soulmate/RULES.md`, `.soulmate/identity.yaml`, `.soulmate/skills/python_logic.md`, `.soulmate/skills/live2d_master.md`, `.soulmate/memories/session_log.md`
- **Next Action / Pending Questions:** この構成で不足しているルールや、他に追加したいSkillがある場合はユーザーにヒアリングを行い拡張する。
