
// src/constants.ts

// --- カテゴリ正規化マップ (揺らぎ吸収) ---
// バックエンドから来るカテゴリ名(キー)を、CSSクラス名(値)に変換します
export const categoryMapping: Record<string, string> = {
    'topics': 'topic',       // 青・吹き出し
    'bond': 'force_talk',    // ピンク・ハート
    'chat': 'topic',
    'general': 'topic',
    'utility': 'suggestion', // ★追加: ツール系はオレンジ
    'space': 'news',         // ★追加: 宇宙ニュースは緑
    'science': 'news',

    'tech': 'news',          // 緑・新聞
    'news': 'news',
    'game': 'fun',           // 紫・ゲーム
    'fun': 'fun',
    'weather': 'weather',    // 黄・天気
    'search': 'search',      // 青緑・虫眼鏡
    'love': 'love'           // Love Slot (Pink)
};

// --- アイコン辞書 ---
export const categoryIcons: Record<string, string> = {
    'topic': '💬',
    'news': '📰',
    'weather': '☀',
    'fun': '🎮',
    'health': '💊',
    'suggestion': '💡',
    'force_talk': '♥', // ピンクのハート (White Text)
    'search': '🔍',
    'love': '♥',        // Love Slot (White Text)
    'alert': '❗',
    // 復活: 詳細カテゴリアイコン
    'tech': '💻',
    'gadget': '📱',
    'science': '🔬',
    'space': '🚀',
    'food': '🍔',
    'travel': '✈️',
    'game': '🎮',
    'anime': '📺',
    'movie': '🎬',
    'music': '🎵',
    'art': '🎨'
};

// --- Emotion-Expression Map ---
export const emotions: { [key: string]: string } = {
    '[happy]': '01.blush',  // Smile/Blush
    '[angry]': '02.angry',  // Angry
    '[sad]': '03.cry',      // Cry
    '[pale]': '04.pale',    // Pale
    '[wink]': '06.wink_R',  // Wink
    '[surprise]': '13.surprised', // Surprised
    '[love]': 'fx_01_heart' // Heart FX
};

// UI State Definition
export const uiState = {
    charWidth: 500,
    chatWidth: 450, // width + margin
    logWidth: 410, // width 400 + margin 10
    isChatOpen: false,
    isLogOpen: false
};
