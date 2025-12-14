# SoulMate Remote Access (Server Mode) 仕様書

## 1. 概要
本仕様書は、SoulMateをローカルネットワーク内のWebサーバーとして稼働させ、スマートフォン等の外部デバイスからブラウザ経由でアクセス可能にするための設計図である。

### 目的
* **スマホでの添い寝機能**: PCを母艦として稼働させ、ベッドサイドのスマホでキャラクターを表示・対話する。
* **マルチデバイス対応**: タブレットや古いスマホをサブディスプレイとして活用する。

### アプローチ
* **Backend**: `FastAPI` を導入し、既存の `pywebview` APIロジックをREST APIとしても公開する。
* **Frontend**: `pywebview` 環境と `Webブラウザ` 環境を自動判別し、通信方式（Native Bridge vs HTTP Fetch）を切り替えるアダプター層を導入する。

---

## 2. アーキテクチャ変更点

### A. Backend (Python)
既存の `main.py` とは別に、Webサーバー専用のエントリーポイント `server.py` を作成する。
ロジックの重複を防ぐため、AIエンジンやカレンダー管理などのコア機能は `src/` 以下のモジュールを共通利用する。

| 機能 | デスクトップ版 (`main.py`) | Webサーバー版 (`server.py`) |
| :--- | :--- | :--- |
| **UI表示** | `webview.create_window` | `StaticFiles` (HTML配信) |
| **API通信** | `window.pywebview.api` | REST API (`/api/...`) |
| **音声再生** | PCスピーカー (`pyaudio`) | **課題:** ブラウザでの再生が必要<br>※Phase 1ではPCから鳴らす簡易実装とする |

### B. Frontend (TypeScript)
直接 `window.pywebview.api` を叩くのをやめ、通信を抽象化する `ApiClient` クラスを経由する。

---

## 3. 実装ステップ

### Step 0: 依存ライブラリのインストール
```bash
pip install fastapi uvicorn python-multipart

Step 1: サーバープログラムの実装 (server.py)
プロジェクトルートに作成する。

Python

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os

# 既存モジュールのインポート
from src.ai_engine import AIEngine
from src.calendar_manager import CalendarManager

app = FastAPI()

# インスタンス化 (共通ロジック)
ai_engine = AIEngine()
calendar_manager = CalendarManager()

# --- Request Models ---
class ChatRequest(BaseModel):
    text: str

# --- API Endpoints ---
@app.post("/api/chat")
async def chat(req: ChatRequest):
    """チャット処理"""
    response_text = ai_engine.generate_response(req.text)
    # 必要に応じてJSON構造化や音声データのBase64化を行う
    return {"response": response_text}

@app.get("/api/calendar")
async def get_calendar():
    """カレンダー取得"""
    events = calendar_manager.get_upcoming_events()
    return {"events": events}

# --- Static Files (Frontend) ---
# ビルド済みの dist フォルダをルートとして配信
if os.path.exists("dist"):
    app.mount("/", StaticFiles(directory="dist", html=True), name="static")

if __name__ == "__main__":
    # 0.0.0.0 で公開することで、LAN内の他端末からアクセス可能に
    uvicorn.run(app, host="0.0.0.0", port=8000)
Step 2: フロントエンドの通信アダプター (src/api_client.ts)
環境に応じて通信方法を切り替えるクラスを作成。

TypeScript

// 型定義 (pywebviewがない環境用)
declare global {
    interface Window {
        pywebview?: any;
    }
}

export class ApiClient {
    private isDesktop: boolean;

    constructor() {
        this.isDesktop = !!window.pywebview;
        console.log(`Environment: ${this.isDesktop ? 'Desktop (pywebview)' : 'Web Browser'}`);
    }

    /**
     * AIとチャットする
     */
    async sendChat(text: string): Promise<any> {
        if (this.isDesktop) {
            // デスクトップ版: 既存のブリッジ呼び出し
            return await window.pywebview.api.process_message(text);
        } else {
            // Web版: Fetch APIでサーバーへPOST
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text })
            });
            return await res.json();
        }
    }

    /**
     * カレンダー取得
     */
    async getCalendar(): Promise<any> {
        if (this.isDesktop) {
            return await window.pywebview.api.get_calendar_events();
        } else {
            const res = await fetch('/api/calendar');
            return await res.json();
        }
    }
}

export const api = new ApiClient();
Step 3: フロントエンド呼び出し箇所の修正 (src/index.ts)
既存のコードで window.pywebview.api... と書かれている部分を、api インスタンス経由に書き換える。

TypeScript

import { api } from './api_client';

// 修正前: window.pywebview.api.process_message(input_text)
// 修正後:
api.sendChat(input_text).then(response => {
    // ...
});
4. 使い方 (Usage)
1. サーバーの起動
PC側で以下のコマンドを実行する。

Bash

python server.py
成功すると Uvicorn running on http://0.0.0.0:8000 と表示される。

2. IPアドレスの確認
PCのコマンドプロンプトで自分のIPアドレスを確認する。

Windows: ipconfig -> IPv4 Address を探す (例: 192.168.1.15)

Mac/Linux: ifconfig または ip a

3. スマホからのアクセス
スマホのChrome/Safariを開き、アドレスバーに入力する。 http://192.168.1.15:8000 (IPアドレスは上記で確認したもの)

→ SoulMateの画面が表示されれば成功！

5. 今後の課題 (For Step 2)
音声のスマホ再生:

現状の server.py 実装では、PC側で音声生成・再生処理が走るため、PCから音が鳴る。

スマホから音を出すには、/api/chat のレスポンスに音声データ（Base64 MP3等）を含め、TypeScript側で new Audio(...) を使って再生する処理が必要。

スリープ防止:

スマホブラウザ用の NoSleep.js を導入する。

HTTPS化:

マイク入力（音声認識）を使う場合、ブラウザのセキュリティ制限によりHTTPS必須となる場合がある。