あらあら、こだわり派のあなた、大好きよ！✨ 「音が鳴ったら口が開く（ON/OFF）」だけじゃ、なんだかロボットみたいで満足できない……その感覚、とっても大事です。

SoulMateちゃんが**「本当に喋っているように」見せるためには、ただ開くだけじゃなくて、「声の大きさ（音量）に合わせて、なめらかに口の開き具合を変化させる」**必要があるわ。

これを実現するための**「魔法のレシピ（Lip-sync v2.0）」**を提案するわね。

🔧 実装のポイント： 「音量解析」＋「慣性処理」
単に「口を開く」のではなく、以下の2つの工夫を加えます。

音量解析 (RMS): Python側で、音声の波形から「今の瞬間のエネルギー（音量）」を0.0〜1.0の数値で計算する。

スムージング (Smoothing): いきなり 0.0 → 1.0 に変えるのではなく、0.1 → 0.3 → 0.8 のように、**「筋肉が動くような遅延（慣性）」**をプログラムで再現する。

さあ、コードを書き換えましょう！

Step 1: Python側 (音声解析エンジン)
src/audio_player.py (または該当するファイル) を作成・修正します。 numpy と pyaudio を使って、再生しながらリアルタイムに数値を計算してフロントエンドに送ります。

必要なライブラリ: pip install pyaudio numpy

Python

import pyaudio
import wave
import numpy as np
import threading
import time

# PyWebViewのウィンドウオブジェクトを格納する変数（main.pyからセットしてね）
webview_window = None 

class AudioPlayer:
    def __init__(self):
        self.chunk = 1024
        self.p = pyaudio.PyAudio()

    def play_voice(self, file_path):
        """
        音声を再生しながら、リップシンク用のデータを送る
        """
        def _play():
            try:
                wf = wave.open(file_path, 'rb')
                stream = self.p.open(
                    format=self.p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True
                )

                data = wf.readframes(self.chunk)
                
                while data:
                    # 1. 音声を再生
                    stream.write(data)
                    
                    # 2. 音量を計算 (RMS: 二乗平均平方根)
                    # バイナリデータを整数配列に変換
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    # RMSを計算
                    rms = np.sqrt(np.mean(audio_data**2))
                    
                    # 3. Live2D用の0.0〜1.0の範囲に正規化
                    # ※ 3000くらいで割るとちょうどいい感度になるわ（調整してね）
                    mouth_value = min(rms / 3000.0, 1.0)
                    
                    # 4. フロントエンドへ送信 (JavaScriptの関数を呼ぶ)
                    if webview_window:
                        # ちらつき防止のため、小さすぎる値は0にする
                        if mouth_value < 0.1: mouth_value = 0
                        
                        webview_window.evaluate_js(f"window.updateLipSync({mouth_value});")

                    data = wf.readframes(self.chunk)

                stream.close()
                wf.close()
                
                # 再生終了後は口を閉じる
                if webview_window:
                    webview_window.evaluate_js("window.updateLipSync(0);")

            except Exception as e:
                print(f"Error playing audio: {e}")

        # UIを止めないように別スレッドで再生
        threading.Thread(target=_play).start()

audio_player = AudioPlayer()
Step 2: TypeScript側 (なめらかな動きの表現)
受け取った数値をそのままセットすると、口がガクガクしてしまいます。 ここで**「線形補間（Lerp）」**を使って、ヌルっと動くようにします。

src/index.ts (またはLive2D管理ファイル) に以下のロジックを追加してね。

TypeScript

// 現在の口の開き具合 (0.0 ~ 1.0)
let currentMouthY = 0.0;
// Pythonから送られてきた目標値
let targetMouthY = 0.0;

// ■ Pythonから呼ばれる関数 (globalに登録)
(window as any).updateLipSync = (value: number) => {
    targetMouthY = value;
};

// ■ Live2Dの描画ループ (Tick関数) 内で呼ぶ処理
function updateMouthMotion(model: any, deltaTime: number) {
    if (!model) return;

    // 【魔法の計算】 現在値を目標値に少しずつ近づける (補間)
    // 0.3 という係数が「追従スピード」。小さいほどゆっくり、大きいほどキビキビ。
    const smoothing = 0.3; 
    currentMouthY += (targetMouthY - currentMouthY) * smoothing;

    // パラメータを適用
    // ParamMouthOpenY は Cubism SDK の標準IDよ
    model.internalModel.coreModel.setParameterValueById('ParamMouthOpenY', currentMouthY);
}

// ※ 注意: この updateMouthMotion は、
// app.ticker.add(...) の中で毎フレーム実行させてね！
🎨 調整のコツ（開発パートナーからのアドバイス）
実装したら、以下の数値をいじって「一番可愛い動き」を探してみて！

感度調整 (Python側):

rms / 3000.0 の 3000 を小さくすると（例: 1500）、小声でも大きく口を開けます。

逆に大きくすると、叫ばないと口が開かなくなります。

なめらかさ調整 (TS側):

smoothing = 0.3 を 0.1 にすると、おっとりした口の動きになります。

0.8 にすると、ハキハキした動きになります。

これで、SoulMateちゃんの口が「パカパカ」ではなく、**「声に合わせて生き生きと」**動くようになるはずよ。 試してみて、動きがどう変わったか教えてね！✨