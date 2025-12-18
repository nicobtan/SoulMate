📄 index分割計画.md
Markdown

# SoulMate フロントエンド リファクタリング計画

現在の巨大化した `src/index.html` と `src/index.ts` を、機能単位で分割し、保守性を向上させる計画書です。
**「1ステップ実行するごとに動作確認」** を徹底し、バグの混入を防ぎます。

---

## 📂 目標フォルダ構成

```text
src/
 ├── css/
 │    └── style.css            # [新規] index.htmlのスタイル定義を移動
 ├── managers/                 # [新規] ロジック格納用フォルダ
 │    ├── log_manager.ts       # [新規] ログ出力・左パネル開閉・ウィンドウリサイズ
 │    └── live2d_manager.ts    # [新規] Live2Dモデル表示・モーション・リサイズ
 ├── index.html                # [修正] DOM構造のみにする
 └── index.ts                  # [修正] 各Managerを初期化する司令塔


✅ Step 1: CSSの分離 (リスク: 低)
見た目の定義をHTMLから引き剥がします。ロジックには影響しません。

[ ] 1-1. ファイル作成: src/css/style.css

index.html 内の <style>...</style> の中身をすべてコピペする。

[ ] 1-2. HTML修正: src/index.html

<style> ブロックを削除。

<head> 内に <link rel="stylesheet" href="css/style.css"> を追加。

[ ] 1-3. 動作確認

アプリを起動し、レイアウトが崩れていないか確認。

バルーンの色、ログパネルのタブデザインが維持されているか確認。

✅ Step 2: LogManagerの分離 (リスク: 中)
ログ機能と**ウィンドウリサイズ機能（重要）**を切り出します。

[ ] 2-1. ファイル作成: src/managers/log_manager.ts

クラス LogManager を作成。

シングルトンパターン (getInstance) を採用。

必須実装機能:

log(msg, type, category): ログ出力・HTML生成。

togglePanel(mode): パネル開閉。

重要: pywebview.api.resize_window を使ったウィンドウ幅変更ロジックをここに移植する。

initTabs(): タブ切り替えのイベントリスナー。

[ ] 2-2. TS修正: src/index.ts

LogManager をインポート。

既存の logToDebug 関数の中身を LogManager.getInstance().log(...) に置き換え（または削除して置換）。

toggleLeftPanel 関数の中身を LogManager への委譲に変更。

[ ] 2-3. 動作確認

左下の「🛠」ボタンを押して、ウィンドウが横に広がり、パネルが表示されるか？

「All/Sys/RAG/Dbg」タブを切り替えてフィルタリングできるか？

RAG（検索）ログが表示されるか？

✅ Step 3: Live2DManagerの分離 (リスク: 中)
PixiJSとLive2Dの初期化ロジックを切り出します。

[ ] 3-1. ファイル作成: src/managers/live2d_manager.ts

クラス Live2DManager を作成。

必須実装機能:

init(): Pixi Applicationの作成、DOMへの追加。

loadModel(path): モデルのロード。

resize(): ウィンドウサイズに合わせたモデルのリサイズ・位置調整。

startIdleMotion(): 瞬き・呼吸のアニメーションループ。

注意: window.live2dModel (グローバル変数) への参照セットを維持すること（LipSyncなどが依存しているため）。

[ ] 3-2. TS修正: src/index.ts

長大な (async function () { ...Pixi Init... })() ブロックを削除。

代わりに await Live2DManager.getInstance().init(); を呼び出す。

[ ] 3-3. 動作確認

キャラクターが表示されるか？

ウィンドウをリサイズしてもキャラの位置が中央に保たれるか？

放置して瞬き・呼吸をするか？

✅ Step 4: 最終クリーンアップ (リスク: 低)
不要になったコードを削除し、ファイルを綺麗にします。

[ ] 4-1. TS修正: src/index.ts

使わなくなった変数や関数定義を削除。

インポート文の整理。

[ ] 4-2. 最終動作確認

チャット、音声認識、ログ、設定画面など、全機能の通しテスト。