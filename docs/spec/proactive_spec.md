# SoulMate Proactive Mode Specification (Full Edition)

## 1. コンセプト (Concept)
SoulMateを「指示待ちの受動的AI」から、ユーザーの状況を自律的に察知し、癒やしや助言を差し出す「能動的（Proactive）な理解者」へと進化させる。

## 2. モード定義 (Operation States)

| 状態 (State) | 説明 | Vision (画面認識) | 挙動の性質 |
| :--- | :--- | :--- | :--- |
| **IDLE** | 待機中。リソース消費を最小化。 | OFF | ユーザーからの呼びかけのみに反応。 |
| **ACTIVE** | 通常会話モード。 | 手動/リクエスト時 | 会話文脈に応じてYouTubeや画面を解析。 |
| **PROACTIVE** | **能動的守護モード。** | **定期実行 (1-60分)** | 状況を自律的に判断し、自ら発話・行動。 |

## 3. 設定とインターフェース (Settings UI)

### Settings Tab (Proactive)
`src/settings.html` に追加された専用タブで以下の制御が可能。

1.  **Interval Slider**:
    *   スキャン間隔を **1分〜60分** の範囲で調整可能 (デフォルト: 3分)。 Since user activity varies.
2.  **Silent Mode**:
    *   **ON**: 音声フィードバック(TTS)を抑制し、ログ出力と表情変化のみ行う（オフィス/深夜作業用）。
    *   **OFF**: 通常通り音声で話しかける。
3.  **Target Scopes**:
    *   監視対象カテゴリを選択可能 (`Work`, `Media`, `Social`, `Health`)。
    *   例: "Work"のみONにすれば、YouTubeを見ていてもツッコミを入れない。

## 4. 解析・行動ロジック (Logic Flow)

1.  **Vision Sampling (L1 - Local):**
    *   **PaliGemma 3B (Running on RTX 5060 Ti / sm_120)** が高速に画面キャプションを生成 (e.g., "A code editor with Python code...").
    *   GPUアクセラレーションにより低負荷で実行。
2.  **Situation Analysis (L2 - Cloud):**
    *   **Gemini 3 Flash Preview** にキャプションを送信。
    *   **Japanese Constraint**: 入力が英語キャプションであっても、**強制的に日本語で思考・応答**するようプロンプトで厳格に制御。
3.  **Action Decision:**
    *   カテゴリ分類 (Coding, Media, Health...)
    *   介入判断 (Interrupt logic)
4.  **Proactive Action:**
    *   `[Vision]` ログへの出力。
    *   TTSによる音声発話（Silent Mode OFF時）。
    *   Live2Dモーション同期 (Eye Contact)。

## 5. ログ出力仕様 (Enhanced Logging)
* **[Vision]**: 認識した要素（IDE, YouTube, Browser等）と視覚的印象の要約。
* **[Mind]**: キャラクターとしての主観的な推論プロセス。
    * 例: `[Mind] Category: health. 深夜2時を回っているわ。そろそろ寝なさいって言わないと…`

## 6. 技術的ロードマップ (Hybrid Architecture)

* **L1 (Local): PaliGemma 3B [Implemented]**
    * **Status**: ✅ **Done (RTX 50 Support)**
    * PyTorch 2.7 / CUDA 12.8 (sm_120) 環境で動作。
    * 高速なキャプション生成を担当。

* **L2 (Cloud): Gemini 3 Flash Preview [Implemented]**
    * **Status**: ✅ **Done**
    * 高度な文脈理解とキャラクター性の付与。
    * `ResponseParser` による思考漏れ防止と堅牢なJSON出力。