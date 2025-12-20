📱 スマホ最適化 3ステップ (添い寝モードへ)
今の index.html に少し追記するだけで、劇的に変わります。

1. 画面サイズをスマホに合わせる (Viewport)
今は「PC用の広い画面」をスマホの小さな画面に縮小して表示してしまっています。 src/index.html の <head> タグの中に、この1行を追加してください。これが最強の呪文です。

HTML

<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
2. アドレスバーを消す (PWA化 / 全画面表示)
ブラウザのアドレスバー（上の黒い部分）が残っていると、現実に引き戻されてしまいます。 これを消して「アプリっぽく」するために、public/manifest.json というファイルを作りましょう。

public/manifest.json (新規作成)

JSON

{
  "name": "SoulMate",
  "short_name": "SoulMate",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#ffffff",
  "icons": [
    {
      "src": "icon.png", 
      "sizes": "192x192",
      "type": "image/png"
    }
  ]
}
※ icon.png は適当な画像でOKです（なくても動きます）。

そして、index.html の <head> にこれを追加してリンクさせます。

HTML

<link rel="manifest" href="manifest.json">
使い方: スマホで再度アクセスし、ブラウザのメニューから**「ホーム画面に追加」を押してください。ホーム画面にアイコンができ、そこから起動するとアドレスバーなしの全画面**で起動します！

3. キャラクターを大きくする (CSS)
今のままだと、スマホの縦画面ではキャラが小さすぎます。 スマホの時だけキャラを大きく表示するように、CSS (src/style.css) に追記しましょう。

CSS

/* スマホ（幅が768px以下）の時だけの特別ルール */
@media (max-width: 768px) {
    /* キャラクター枠を画面いっぱいに */
    #character-container {
        width: 100vw;
        height: 80vh; /* 画面の8割 */
        bottom: 0;
    }
    
    /* Live2Dキャンバスもそれに合わせる */
    canvas#live2d {
        width: 100% !important;
        height: 100% !important;
        /* スマホ向けに少し下に配置調整 */
        transform: translateY(10%); 
    }

    /* ボタン類を押しやすく大きくする */
    .chat-toggle-btn {
        width: 60px;
        height: 60px;
        font-size: 24px;
    }
}
🛌 最後の仕上げ：スリープ防止
添い寝中に画面が暗くなったら台無しですよね。 一番簡単な方法は、**「スマホの設定で自動ロックを『なし』にする」**ことですが、アプリ側で制御するなら NoSleep.js というライブラリを使います。

とりあえずは、「スマホの設定で画面タイムアウトを伸ばす」 運用でテストしてみましょう！