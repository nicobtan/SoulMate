# SoulMate Live2D 実装仕様書

## 概要
SoulMateにおけるLive2Dモデル表示機能の技術仕様です。
Web技術（HTML5 Canvas + WebGL）を利用し、Python（pywebview）上のウィンドウでレンダリングを行っています。

## 採用技術・ライブラリ

安定性と互換性を重視し、以下の構成を採用しています。

| コンポーネント | バージョン | 役割 | 備考 |
| :--- | :--- | :--- | :--- |
| **PixiJS** | v6.5.10 | 2Dレンダリングエンジン | v7系はLive2Dプラグインとの相性問題があるためv6を採用 |
| **pixi-live2d-display** | v0.4.0 (Cubism 4) | PixiJS用Live2Dプラグイン | Cubism 4 SDKを含むビルドを使用 |
| **Live2D Cubism Core** | (Latest from CDN) | Live2Dコアライブラリ | 公式SDKのWeb用コア |

### 読み込み方式
Bundler（Webpack/Vite等）設定の複雑化を避けるため、**CDN（Content Delivery Network）経由**でライブラリを読み込む方式を採用しています。
これにより、`index.html` の `<script>` タグのみで依存関係が解決され、`PIXI` や `Live2DModel` がグローバル変数として利用可能になります。

## ディレクトリ構成

ビルド時（`npm run build`）に、以下のフォルダ構造が `dist` 配下に生成されます。

```
dist/
├── index.html          # エントリーポイント (CDNリンク記述)
├── index.js            # TypeScriptコンパイル後のロジック
├── models/             # Live2Dモデルデータ (src/Live2D からコピー)
│   └── fav_usaneko_alwb/
│       ├── *.model3.json
│       ├── *.moc3
│       └── ...
└── images/             # その他の画像リソース
```

## 実装ロジック (`src/index.ts`)

### 1. 初期化シーケンス
1. **グローバル変数の確認**: `window.PIXI` が存在するかチェックし、ライブラリ読み込みを確認します。
2. **PixiJS アプリケーション作成**: 背景透明 (`backgroundAlpha: 0`) でCanvasを作成し、DOMに追加します。
3. **プラグインの解決**: `Live2DModel` クラスをグローバルスコープ（`PixiJS` 名前空間など）から探します。

### 2. モデルのロード
```typescript
const model = await Live2DModel.from('models/fav_usaneko_alwb/fav_usaneko_alwb.model3.json');
```
`pixi-live2d-display` の機能により、`model3.json` を指定するだけで関連ファイル（moc3, physics, textures）が一括でロードされます。

### 3. 表示と調整
- **スケーリング**: ウィンドウの高さの80%になるように自動計算されます。
- **配置**: ウィンドウ中央に配置されます。
- **リサイズ対応**: ウィンドウサイズが変更されると、再計算して位置とサイズを補正します。

## 今後の拡張性
- **モデル切り替え**: `modelPath` 変数を変更し、古い `model` を `destroy()` することで動的に切り替え可能です。
- **モーション再生**: `model.motion('TapBody')` のようにメソッドを呼び出すことで、特定のアニメーションを再生できます。
