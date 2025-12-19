src/index.ts（現在1525行）を解体し、メンテナンスしやすい「きれいな設計」にするまでの全4ステップの改修計画を提示します。

ゴールは、index.ts を「単なる起動スイッチ（200行以下）」にし、機能ごとに専門のマネージャーファイルに任せることです。

🗺️ リファクタリング・ロードマップ
現在は Step 0（安定版到達） です。ここから以下の順序で進めます。

📦 Step 1: デザインとロジックの完全分離（今回やること）
目的: HTML内に散らばった <style> や、JSで無理やり書いているスタイル制御を style.css に一本化します。

効果: TSファイルから「見た目に関するコード」が消え、ロジックの移動中にレイアウト崩れが起きるリスクを極限まで下げます。

🖥️ Step 2: UI操作の分離 (UIManager)
目的: ボタンのクリックイベント、パネルの開閉、設定画面の制御などを src/managers/ui_manager.ts に移動します。

効果: index.ts から大量の addEventListener や document.getElementById が消え、コードの見通しが一気に良くなります。

🐱 Step 3: キャラクター制御の分離 (Live2DManager)
目的: 最も行数を食っている「PixiJSの初期化」「モデルの読み込み」「リサイズ計算」「リップシンク」を src/managers/live2d_manager.ts に移動します。

効果: index.ts に残るのは「アプリの初期化」だけになります。ここが最大の山場です。

🏁 Final Step: エントリーポイントの整理
目的: スカスカになった index.ts を整理し、「各マネージャーを起動するだけ」のきれいな形に整えます。

完了形: index.ts は以下のようになります。

TypeScript

// 理想の index.ts
import { UIManager } from './managers/ui_manager';
import { Live2DManager } from './managers/live2d_manager';
import { LogManager } from './managers/log_manager';

window.addEventListener('DOMContentLoaded', async () => {
    LogManager.getInstance().init();
    UIManager.getInstance().init();
    await Live2DManager.getInstance().init('character-area');
    console.log("SoulMate System All Green.");
});
この計画でよろしければ、まずは土台となる Step 1: CSSの分離 から始めましょう。 準備はできていますか？