おはようございます！ぐっすり眠れましたか？ ファイル一式、確認しました。index.html にCSSが内包されているスタイルですね。構造は非常に綺麗です！

原因が判明しました。 ボタンが反応しない・表示されない原因は、UI（HTML/CSS）ではなく、「サーバー（脳みそ）側の設定不足」 です。

ピンクのボタン（能動会話）:

server.py の HeadlessApi クラスに、force_talk という機能の実装が入っていません。そのため、ボタンを押しても裏でエラーになっているか、無視されています。

黄色のボタン（返答提案）:

このボタンは「AIから『次の候補(suggestions)』が送られてきた時だけ表示される」仕組みですが、サーバー側のAIに「JSON形式で返答候補も作って！」という指示（プロンプト）が渡っていません。

そのため、AIは普通のテキストだけを返し、ボタンはずっと非表示のままになっています。

サーバー側のコード server.py を修正して、脳みそを「マルチタスク対応（会話＋候補生成）」にアップグレードしましょう。

🛠️ 修正 1: server.py のアップグレード
この修正で、AIが「JSONモード」で思考するようになり、ピンクボタンの処理も追加されます。 既存の server.py の HeadlessApi クラスを以下のように書き換えてください。

変更点:

_configure_ai メソッドで、「JSONで返してね」という強力なシステムプロンプト を注入するようにしました。

force_talk メソッドを追加し、「話しかけて！」ボタンの処理 を実装しました。

Python

# server.py の HeadlessApi クラス部分を修正

class HeadlessApi(ChatApiMixin, SettingsApiMixin, BaseApiMixin):
    def __init__(self):
        # ... (既存の初期化コードはそのまま) ...
        self._window = None 
        self.config_manager = ConfigManager()
        self.ai_engine = AIEngine()
        self.calendar_manager = CalendarManager()
        self.memory_manager = MemoryManager()
        
        from src.services.persona_manager import PersonaManager
        self.persona_manager = PersonaManager()
        
        self.active_engine = None 
        
        # Init TTS
        base_dir = os.getcwd()
        try:
            self.tts_engine = TTSEngine(key_path="google-credentials.json")
            logger.info("TTS Engine initialized.")
        except Exception as e:
            logger.error(f"TTS Init Failed: {e}")
            self.tts_engine = None

        # Configure AI
        settings = self.config_manager.get_all()
        self._configure_ai(settings)

    def _configure_ai(self, settings):
        """AIの設定と、JSONモード用プロンプトの注入"""
        api_key = settings.get('api_key')
        model = settings.get('model_name', 'gemini-2.5-flash-lite')
        
        if self.ai_engine:
            # ★重要: ここで「JSONモード」のプロンプトを作成
            # これがないと黄色のボタン(suggestions)が出ません
            system_instruction = """
You are SoulMate, a helpful and active AI partner.
Response Format: JSON
You MUST respond in the following JSON format:
{
    "response": "Your spoken response text here.",
    "suggestions": ["Short reply option 1", "Option 2", "Option 3"]
}
Note:
- "response": Natural conversation text.
- "suggestions": 3 short, context-aware phrases the user might want to say next.
"""
            # PersonaManagerから設定があればそれをベースにする処理も本来は必要ですが、
            # まずは機能させるためにJSON強制プロンプトをセットします。
            self.ai_engine.configure(
                api_key=api_key, 
                model_name=model, 
                system_instruction=system_instruction
            )
            logger.info(f"AI Configured: {model} with JSON System Prompt")

    def force_talk(self):
        """★追加: ピンクボタン(話しかけて)の処理"""
        logger.info("[HeadlessApi] Processing Force Talk...")
        
        # AIに「能動的に話しかけて」と指示する隠しコマンドを送る
        prompt = "（ユーザーは無言でこちらを見ています。何か話題を提供したり、気遣う言葉をかけてください）"
        
        # 通常のチャットとして処理（JSONが返ってくるはず）
        return self.chat(prompt)
🛠️ 修正 2: index.ts の微調整
スマホのタップ操作を確実に拾うために、touchstart イベントの挙動を少し調整します。 現状のコードでも概ねOKですが、念のため確認してください。

index.ts の forceTalkBtn と suggestionToggleBtn の部分です。 （提供いただいたコードではすでに touchstart が入っているので、そのままで動く可能性が高いですが、もし反応が悪い場合は e.preventDefault() を外してみてください）

TypeScript

// index.ts の修正案 (反応が悪い場合のみ)

if (forceTalkBtn) {
    const trigger = (e: Event) => {
        // e.preventDefault(); // ★もしタップが反応しない場合は、この行をコメントアウトしてみてください
        logToServer("Force Talk Button Pressed");
        triggerForceTalk();
    };
    // ...
}
🛠️ 修正 3: index.html のCSS調整（念のため）
スマホモードの時、ボタンが「チャットパネル」に隠れてしまわないよう、z-index を最強にしておきます。 index.html の <style> 内にある .mobile-mode セクションを確認してください。

CSS

/* index.html 内の style */

.mobile-mode #force-talk-btn {
    /* ... 既存の設定 ... */
    z-index: 9999 !important; /* 最前面へ */
    pointer-events: auto;     /* クリックを確実に受け付ける */
}

.mobile-mode #suggestion-toggle-btn {
    /* ... 既存の設定 ... */
    z-index: 9999 !important;
    pointer-events: auto;
}