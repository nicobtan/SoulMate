# Active Talk (能動的発話) Specification

## Overview
ユーザーからの入力を待つだけでなく、AI（SoulMate）側から能動的に話しかける機能。
ユーザーは「話しかけられたい」時にボタンを押すか、放置しているとAIが話題を振ってくる。

## 1. Manual Trigger (強制発話ボタン)
ユーザーが「今すぐ何か話してほしい」と思った時に押すボタン。

### UI Specification
- **位置**: メイン画面（キャラクター表示領域）。チャットトグルボタン（吹き出しアイコン）の**真上**に配置。
- **デザイン**: 
    - アイコン: ✨ (Sparkles) または 🗣️ (Speaking Head) ? 
    - 色: ピンク/オレンジ系（注意を引くが、警告色ではない）。
    - 形状: 円形（チャットボタンと同じサイズか少し小さめ）。
- **挙動**:
    - クリックすると、AIが即座にプロアクティブなメッセージを生成する。
    - 生成中、「考え中...」のエフェクトを表示。
    - 生成されたメッセージは、チャットログに追加され、音声（TTS）があれば再生される。
    - チャットパネルが閉じている場合は、自動的に開く（または通知バブルを出す？今回はシンプルにパネルオープン）。

## 2. Auto Timer (自動発話タイマー) - *Future/Configurable*
設定された時間（例: 60分）放置されると、自動的に話しかける。

### Logic
- **Idle Detection**: 最後のユーザー入力（またはAI発話）からの経過時間を計測。
- **Condition**: 
    - 設定時間が経過していること。
    - ユーザーが集中モード（DND）でないこと（将来拡張）。
- **Action**: Manual Triggerと同じく、プロアクティブメッセージを生成して通知。

## 3. AI Proactive Logic
AIは何を話すべきか？

### Context Data
- **Current Time**: 「もうお昼ですね」「深夜ですが起きてますか？」
- **News**: 最新のニュース（RSS）からトピックを拾う（Phase 9連携）。
- **Calendar**: 「次の予定まであと○分です」
- **Random Topic**: 「そういえば、好きな映画って何ですか？」

### Prompt Strategy
- System Promptに `generate_proactive_message()` 用の指示を追加、または専用メソッドを使用。
- "User didn't say anything, but wants you to start a conversation. Pick a topic relevant to the time or just a casual question."
