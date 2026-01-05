Markdown

# Character Changer Specification

**Phase:** 20 (Character Profile & Switching)
**Status:** Draft
**Last Updated:** 2026-01-05

## 1. 概要
Live2Dモデル、ペルソナ（性格設定）、TTS音声設定をひとまとめにした「キャラクタープロファイル」を定義し、ワンクリックでキャラクター全体（外見・中身・声）を切り替える機能を実装する。

## 2. データ構造

### 2.1 定義ファイル (`profiles/characters.json`)
キャラクターごとの設定をリスト形式で管理する。ハードコードを避け、将来的な拡張（ユーザーによる追加）を容易にする。

```json
[
  {
    "id": "lena_default",
    "name": "Lena (Default)",
    "description": "いつものパートナー。優しくて少しお世話焼き。",
    "model_id": "fav_usaneko_alwb",
    "persona_id": "lena",
    "voice": {
      "provider": "gemini-2.5-flash-preview-tts",
      "voice_name": "Aoede"
    }
  },
  {
    "id": "liiv4_cool",
    "name": "Liiv4 Model (Cool)",
    "description": "Liiv4さんから頂いた新しい姿。少しクールな性格。",
    "model_id": "liiv4_sample_v1", 
    "persona_id": "cool_assistant",
    "voice": {
      "provider": "voicevox",
      "voice_name": "2"
    }
  }
]
2.2 型定義 (src/static/ts/types/character.ts)
フロントエンド（TypeScript）で使用する型定義。

TypeScript

export interface VoiceConfig {
    provider: string;   // 例: "gemini-2.5-flash-preview-tts", "voicevox"
    voice_name: string; // 例: "Aoede", "3"
}

export interface CharacterProfile {
    id: string;
    name: string;
    description?: string;
    model_id: string;   // models/ 以下のフォルダ名と一致させる
    persona_id: string; // backendの persona_manager で管理されるID
    voice: VoiceConfig;
}
3. アーキテクチャ & フロー
3.1 切り替えフロー
Trigger: ユーザーが設定画面またはAPI経由で switch_character(profile_id) を実行。

Frontend (Live2D):

現在のモデルを destroy() してリソース解放。

新しい model_id に基づきパスを再構築し、loadModel() を実行。

Backend (Python):

CharacterService (新規作成) がリクエストを受信。

Config更新: current_character_id を保存。

Persona更新: PersonaManager を呼び出し、システムプロンプトを再設定。

Voice更新: VoiceService のデフォルト声を変更。

Notification: 完了後、「変身」した旨をチャットログにシステムメッセージとして表示。

4. 実装タスクリスト
Step 1: フロントエンド基盤 (TypeScript)
[ ] 型定義: src/static/ts/types/character.ts の作成。

[ ] Live2Dマネージャー改修: src/static/ts/managers/live2d_manager.ts に switchModel(modelDirName) メソッドを実装。

既存モデルのクリーンアップ処理（メモリリーク防止）を含むこと。

[ ] UI公開: コンソールから window.live2dManager.switchModel(...) でテストできるようにする。

Step 2: バックエンド基盤 (Python)
[ ] JSON作成: profiles/characters.json の配置。

[ ] サービス実装: src/services/character_service.py の作成。

プロファイルのロード機能。

apply_profile(profile_id) メソッドの実装（Persona, Voice, Configの一括更新）。

[ ] API実装: src/api/character_api.py の作成と main.py への統合。

Step 3: 設定画面 (UI)
[ ] タブ追加: settings.html に「Character」タブを追加。

[ ] リスト表示: characters.json から読み込んだプロファイルをカード形式で一覧表示。

[ ] 切り替えボタン: 「Activate」ボタンを押すと、Step 2のAPIを呼び出して反映させる。

5. Live2D Manager 実装詳細 (Reference)
TypeScript

// src/static/ts/managers/live2d_manager.ts への追加メソッド

public async switchModel(modelDirName: string): Promise<void> {
    console.log(`[Live2D] Switching to model: ${modelDirName}`);
    
    try {
        // 1. 既存モデルのクリーンアップ
        if (this.model) {
            if (this.app && this.app.stage) {
                this.app.stage.removeChild(this.model);
            }
            if (typeof this.model.destroy === 'function') {
                this.model.destroy();
            }
            this.model = null;
        }

        // 2. パスの更新
        this.resourcesPath = `models/${modelDirName}/`;
        this.definitionFileName = `${modelDirName}.model3.json`;
        
        // 3. 再ロード実行
        await this.loadModel(`${this.resourcesPath}${this.definitionFileName}`);
        
        console.log("[Live2D] Model switched successfully.");

    } catch (e) {
        console.error("[Live2D] Failed to switch model:", e);
        throw e;
    }
}