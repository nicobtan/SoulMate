# SoulMate Proactive Mode Specification (Full Edition)

## 1. コンセプト (Concept)
SoulMateを「指示待ちの受動的AI」から、ユーザーの状況を自律的に察知し、癒やしや助言を差し出す「能動的（Proactive）な理解者」へと進化させる。

## 2. モード定義 (Operation States)

| 状態 (State) | 説明 | Vision (画面認識) | 挙動の性質 |
| :--- | :--- | :--- | :--- |
| **IDLE** | 待機中。リソース消費を最小化。 | OFF | ユーザーからの呼びかけのみに反応。 |
| **ACTIVE** | 通常会話モード。 | 手動/リクエスト時 | 会話文脈に応じてYouTubeや画面を解析。 |
| **PROACTIVE** | **能動的守護モード。** | **定期実行 (1-5分)** | 状況を自律的に判断し、自ら発話・行動。 |

## 3. ユーザーインターフェース (UI/UX)
* **切り替え:** キャラクター、またはクロック上の「Active」インジケーターを右クリックし、コンテキストメニューから `Proactive Mode` をON/OFF。
* **視覚演出:** * Live2Dモデルの瞳にハイライト（加算レイヤー）を追加し、「注視している」ことを表現。
    * システムトレイまたはUI端に「Watching...」等のステータスを表示。

## 4. 解析・行動ロジック (Logic Flow)

1.  **Vision Sampling:** タイマーに基づき、デスクトップ（またはアクティブウィンドウ）をキャプチャ。
2.  **Multimodal Analysis (Gemini 3 Flash Preview):**
    * 現在の作業内容、エラーの有無、ユーザーの疲労度を推論。
    * YouTube視聴時は、映像の内容と現在の時刻（深夜等）を統合して解析。
3.  **Mind Reasoning (思考の言語化):**
    * `[Mind]` ログに「なぜ今話しかけるのか」という葛藤や根拠を出力。
    * 例: `[Mind] 30分間同じエラーに苦しんでいる様子。少し強引にでも休憩を勧めるべきかしら。`
4.  **Proactive Action:**
    * ユーザーの入力を待たずにTTS（音声）とLive2D（モーション）で介入。

## 5. ログ出力仕様 (Enhanced Logging)
* **[Vision]**: 認識した要素（IDE, YouTube, Browser等）と視覚的印象の要約。
* **[Mind]**: キャラクターとしての主観的な推論プロセス。
* **[RAG]**: 過去の会話や知識から「何を思い出したか（Recall）」の履歴。
* **[Expression]**: 表情選択の理由。

## 6. 技術的ロードマップ (Hybrid Architecture)
コストとプライバシーの最適化のため、将来的に以下の二層構造を採用する。

* **L1 (Local): Gemma 2B/7B (Vision)**
    * 高頻度（15-30秒）で画面を監視。
    * 「変化の検知」および「重要度のフィルタリング」を担当。
* **L2 (Cloud): Gemini 3 Flash Preview**
    * L1が「介入が必要」と判断した際のみ起動。
    * 高度な情緒的対話と解決策の生成を担当。

---

## 7. CodeAssistAgent への実装指示プロンプト (Snippet)

以下のプロンプトをAntigravityのチャットに貼り付けて開発