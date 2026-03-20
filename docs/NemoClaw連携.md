SoulMate × NVIDIA NemoClaw 連携仕様書 (v1.1)

1. 目的

本ドキュメントは、AIアプリケーション「SoulMate」にNVIDIAの「NemoClaw」を統合し、高度なPC操作（GUI操作、ファイル操作、マルチアプリ連携）を実現するための設計指針を定義する。

2. システムアーキテクチャ

SoulMateを「意思決定（脳）」、NemoClawを「実行（手足）」として分離する疎結合アーキテクチャを採用する。

レイヤー

コンポーネント

役割

UI / Interaction

SoulMate (Desktop App)

ユーザーとの対話、人格（キャラクター）の表現、/do コマンドの受付

Reasoning Engine

Gemini 3.1 / Nemotron

自然言語の解釈、実行プランの生成（推論）

Agent Layer

NemoClaw (NVIDIA)

推論結果を具体的なPC操作手順（Pythonスクリプト/APIコール）に変換

Execution Layer

OpenShell (Sandbox)

Windows OS上での安全な操作実行、画面キャプチャの取得

3. 主要機能

3.1 インテリジェント /do コマンドの拡張

従来のコマンドベースの操作から、VLM（視覚言語モデル）を活用した動的な操作へ拡張する。

画面認識: アクティブウィンドウのボタンやテキストを認識し、座標を特定。

逐次実行: 「ブラウザを開く」→「ログインする」→「データを取得する」といったステップバイステップの実行。

3.2 連携フロー

指示受付: ユーザーが「/do YouTubeでジャズを流して」と入力。

プランニング: SoulMate（Gemini 3.1）が操作手順を生成。

ハンドオフ: NemoClaw SDKを通じてOpenShellに操作コマンドを送信。

実行・フィードバック: NemoClawが画面変化を監視しながら操作を実行し、完了をSoulMateに通知。

4. 実装要件 (Python)

4.1 必要なライブラリ

nvidia-nemoclaw-sdk (v2026.3以降)

openshell-runtime

soulmate-core-v3

4.2 セキュリティ・ガードレール

承認フロー: システム設定の変更やファイル削除など、高リスクな操作には必ず「ユーザーの最終承認」を挟む。

サンドボックス化: OpenShell内で実行し、メインシステムへの致命的な影響を防止する。

5. 今後の拡張予定

マルチモーダル・フィードバック: NemoClawがエラーを検知した際、SoulMateが「あらあら、ボタンが見つからないみたいです」と人格を持ってユーザーに助けを求める機能。

メモリ共有: 過去の操作ログを学習し、ユーザーの好みの操作手順を最適化する。

© 2026 SoulMate Project / Developed by