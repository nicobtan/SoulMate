# Python Logic

## ベストプラクティス

- **Robust Error Handling**: API通信やファイルI/Oには必ず `try-except` と指数バックオフを入れること。
- **Modular Design**: 1つの関数は1つの責任（Single Responsibility）を持つこと。
- **Docstrings**: 全ての公開関数に Google Style の docstring を記述すること。
