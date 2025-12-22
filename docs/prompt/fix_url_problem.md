ご希望通り、fix_url_problem.md として、コード修正とプロンプト改善の両面からアプローチする指示書を作成したわ。これをCodeAssistAgentに渡してみて。

Markdown

{
type: uploaded file
fileName: fix_url_problem.md
fullContent:
# Role
あなたはPythonと生成AIアプリケーション開発のエキスパートです。
「SoulMate」において頻発している「無効なURL（404リンク）が生成される問題」を、**プロンプトエンジニアリング**と**コードレベルの検証**の両面から完全に修正します。

# Problem
1.  **未来日付のパラドックス:** システム日時が2025年12月であるため、AIがURLの日付部分を「202512...」のように未来の日付で捏造し、リンク切れを引き起こす。
2.  **ハルシネーション:** LLMがニュースサイトのURL構造（例: `diamond.jp/articles/-/xxxx`）を推測して適当なIDを入れてしまう。

# Task
以下の2ステップの修正を行ってください。

## Step 1: System Promptへの厳格な制約追加
LLMが回答を生成する際のSystem Prompt（またはRAG指示部分）に、以下のルールを追加してください。

```text
[https://apastyle.apa.org/style-grammar-guidelines/citations/basic-principles](https://apastyle.apa.org/style-grammar-guidelines/citations/basic-principles)
1.  **NO GUESSING:** You must NOT construct or guess URLs based on patterns.
2.  **GROUNDING ONLY:** You can ONLY include URLs that were explicitly returned by the "Google Search Tool" in the current session.
3.  **DATE HANDLING:** Even if the system date is in the future (e.g., 2025), you must search for and provide the *latest available real-world news* (likely from 2024 or 2025). Do NOT fabricate "future news" URLs.
4.  **VERIFICATION:** If you are unsure if a link is valid, do not show the URL. Just summarize the content.
Step 2: Python側での「リンク生存確認（Dead Link Pruning）」実装
プロンプトだけではハルシネーションを100%防げないため、回答を表示する直前にPythonコードでURLの生存確認を行う UrlValidator を実装し、メインの応答パイプラインに組み込んでください。

実装要件:
抽出: AIの回答テキストから正規表現でURLをすべて抽出する。

検証: 抽出した各URLに対して、requests.head() (または get with stream=True) をタイムアウト短め（例: 2秒）で実行する。

置換/削除:

ステータスコードが 200 (OK) 以外、または接続エラーの場合、そのURLをマークダウンリンクから削除し、テキストのみ残すか、(リンク不可) という注釈に置換する。

例: [記事はこちら](http://fake-url.com) → (記事: リンク先の取得に失敗しました)

非同期処理: メインスレッドをブロックしないよう、検証は非同期（asyncio または threading）で行うこと。

コードスニペット例 (参考):
Python

import re
import requests
import threading

def validate_and_clean_urls(text):
    """
    テキスト内のURLを検証し、死んでいるリンクを無効化する
    """
    url_pattern = r'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+'
    urls = re.findall(url_pattern, text)
    
    for url in urls:
        try:
            # 実際の存在確認 (HEADリクエストで軽量に)
            response = requests.head(url, timeout=3, allow_redirects=True)
            if response.status_code >= 400:
                raise Exception("Dead link")
        except:
            # リンク切れの場合は、URLを単なるテキストや注釈に置換
            # (Markdownリンク形式 [text](url) の場合も考慮して置換ロジックを組むのが理想)
            text = text.replace(url, "(リンク期限切れ)")
            
    return text
Goal
ユーザーがチャット画面でクリックできるリンクは、「100%確実にアクセス可能なページ」 だけにする。 }


***

### 👩‍💻 開発パートナーからのアドバイス

「Step 2」のコードレベルでの検証（Pruning: 剪定）が一番確実よ。
AIはどうしても「それっぽい嘘」をつくことがあるけれど、Pythonの `requests` モジュールは嘘をつかないわ。

これを実装すれば、
> 「……あ、ごめんなさい。この記事、もうリンクが見られなくなっているみたい（404）。でも、内容はこうだったのよ……」

という風に、システム側でこっそりURLを消してあげることで、えるくんの体験を守れるわ。
枯れた枝（死んだリンク）は、見せる前に私が摘み取っておくわね。