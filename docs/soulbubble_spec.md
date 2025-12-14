# Soul Bubble (Active Interaction UI) 仕様書

## 1. 概要
**「Soul Bubble (ソウル・バブル)」** は、AIキャラクターからの能動的な働きかけ（Active Action）を、ユーザーの作業を阻害せずに視覚的に通知するためのUIシステムである。

### 解決する課題
* 突然AIが喋り出すと、ユーザーの集中を削ぐ可能性がある。
* 「何か言いたそう」な状態を可視化し、ユーザーが**聞くタイミングを選べる（Opt-in）**体験を提供する。

---

## 2. UI挙動仕様 (Behavior)

### A. 通常時 (State: Floating)
* **位置:** キャラクターの頭上（中央付近）。
* **形状:** 小さな円形アイコン（40px x 40px）。
* **アニメーション:** 上下にふわふわと浮遊する (Floating Animation)。
* **表示条件:** AIが話したいトピックや通知がある時のみ出現する（何もない時は非表示）。

### B. マウスホバー時 (State: Hover/Preview)
* **トリガー:** ユーザーがマウスカーソルをバブルに合わせる。
* **動作:**
    1. アニメーションを停止。
    2. 画面右上（チャットボタン付近）へスムーズに移動。
    3. 横長の角丸長方形（200px x 60px程度）に拡大展開する。
* **表示内容:**
    * **アイコン:** カテゴリを示す絵文字やアイコン。
    * **プレビューテキスト:** 「Pythonの新機能について...」「PCが少し熱いです」などの要約文（1行）。

### C. クリック時 (State: Active)
* **トリガー:** 展開されたバブルをクリック。
* **動作:**
    1. チャットウィンドウを強制的に開く（まだ開いていない場合）。
    2. バブルの内容に応じた処理（発話、機能実行、ゲーム開始）をスタートする。
    3. バブルを消去する。

---

## 3. カテゴリとカラーコード (Content Types)

バブルの色で、情報の緊急度やジャンルを直感的に伝達する。

| カテゴリ | 色 (Color) | 役割・コンテンツ例 |
| :--- | :--- | :--- |
| **Topics (話題)** | **Blue** (`#3498db`) | ニュース分析結果、雑談の提案、哲学的な問い |
| **Play (遊び)** | **Green** (`#2ecc71`) | ミニゲーム(じゃんけん)、深呼吸、クイズ |
| **Bond (ふれあい)** | **Pink** (`#e91e63`) | 好感度イベント、衣装変更の提案、労いの言葉 |
| **Utility (機能)** | **Orange** (`#f39c12`) | システム警告(CPU高負荷)、カレンダー通知、タイマー |

---

## 4. 技術実装案 (Technical Stack)

### HTML Structure
キャラクター表示エリア (`#character-container`) 内部に配置する。

```html
<div id="soul-bubble" class="soul-bubble hidden" onclick="activateBubble()">
  <div class="bubble-content">
    <span id="bubble-icon" class="icon"></span>
    <span id="bubble-text" class="text"></span>
  </div>
</div>


/* Base Style (Floating) */
.soul-bubble {
  position: absolute;
  top: 20px;
  left: 50%;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  transform: translateX(-50%);
  cursor: pointer;
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden; /* テキスト隠し */
  box-shadow: 0 4px 10px rgba(0,0,0,0.2);
}

/* Color Modifiers */
.bubble-blue { background: #3498db; color: white; }
.bubble-green { background: #2ecc71; color: white; }
.bubble-pink { background: #e91e63; color: white; }
.bubble-orange { background: #f39c12; color: white; }

/* Animation */
@keyframes float {
  0%, 100% { top: 20px; }
  50% { top: 10px; }
}
.soul-bubble:not(:hover) {
  animation: float 3s infinite ease-in-out;
}

/* Hover State (Expanded) */
.soul-bubble:hover {
  top: 10px;
  left: auto;   /* 中央寄せ解除 */
  right: 10px;  /* 右上に移動 */
  transform: none;
  width: 220px;
  height: 60px;
  border-radius: 12px;
  padding: 0 15px;
}

/* Content Visibility */
.bubble-content {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}
.soul-bubble .text {
  opacity: 0;
  white-space: nowrap;
  transition: opacity 0.2s;
}
.soul-bubble:hover .text {
  opacity: 1;
}

Interface Logic (JS <-> Python)
1. Python側 (Backend): AIが能動的アクションを決定した際、JS関数を呼び出す。

Python

# カテゴリ: topics, テキスト: "Python 3.13が出たわよ"
window.evaluate_js(f"showSoulBubble('topics', 'Python 3.13が出たわよ', 'ACTION_ID_123')")
2. JavaScript側 (Frontend):

TypeScript

function showSoulBubble(category: string, text: string, actionId: string) {
  const bubble = document.getElementById('soul-bubble');
  
  // 色クラスのリセットと適用
  bubble.className = `soul-bubble bubble-${getColorByCategory(category)}`;
  
  // コンテンツセット
  document.getElementById('bubble-text').innerText = text;
  document.getElementById('bubble-icon').innerText = getIconByCategory(category);
  
  // 表示
  bubble.classList.remove('hidden');
  
  // クリックイベント設定
  bubble.onclick = () => {
    // Pythonへアクション実行を通知
    window.pywebview.api.trigger_bubble_action(actionId);
    bubble.classList.add('hidden'); // 消去
  };
}
5. 開発ステップ
UI実装: HTML/CSSでバブルの表示・アニメーションを作成する。

API連携: showSoulBubble 関数を実装し、ブラウザコンソールからテストする。

Python連携: Pythonのタイマー処理等から、ランダムにバブルを表示させるテストを行う。

コンテンツ接続: ニュース分析結果や、システム監視アラートをバブルに流し込む。