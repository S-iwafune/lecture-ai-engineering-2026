# 第3回 解答

## 演習

- 第1回（素のLLM）とエージェントの回答の違い：
  - 第1回の `app.ask`（素のLLM）は「3レベル」の意味を知らず、一般論で説明したり「分からない」と答えたりした
  - エージェントは用語集を検索してから答え、「基礎（講義内容の確認）・実装（自分でコードを書く）・発展（調査や試行）の3段階で、どれか1つに取り組めば完了」と、`data/glossary.json` の `homework-levels` どおりに答えた。回答の最後には `INSTRUCTIONS` の指示どおり「関連する回：第1回」が付いた
- `--trace` で見えたツール呼び出し（ツール名と引数）：
  - 「LoRAとQLoRAの違いは？」：`search_glossary({'query': 'LoRA'})` と `search_glossary({'query': 'QLoRA'})` の2回。docstring の「query には調べたい用語を1つだけ入れる」に従い、用語を1つずつ検索していた。回答は2つの定義をもとに「ベースモデルの重みを量子化するかどうか」の違いとしてまとめ、最後に（第2回）を付けた
  - 「第2回の内容から確認問題を1問出して」：`make_quiz({'lecture': 2})` の1回。`search_glossary` は呼ばなかった
- 1つの質問での LLM 呼び出し回数（`requests`）：
  - どちらの質問も `requests=2`。1回目でモデルがツール呼び出しを返し、ツールの結果を渡した2回目で回答を作った。LoRA/QLoRA の質問では、2つの検索を1回目のリクエストでまとめて出したため（`tool_calls=2`）、呼び出し回数は増えなかった
  - トークン数：LoRA/QLoRA は入力 1424 / 出力 191、確認問題は入力 947 / 出力 60
- 追加したツールと、docstring に書いた説明：
  - `make_quiz(lecture: int) -> str`：用語集から `lecture` が指定の回の用語を集めて `random.choice` で1つ選び、`{"question": "「○○」の意味は？", "answer": 定義}` を `json.dumps` で返す。用語の無い回（第0回など）を指定されたら、用語がある回の一覧をメッセージで返す（`uv run pytest -q` は 11 件すべて成功）
  - docstring：「指定した回（1始まりの整数）の用語から確認問題を1問作り、問題と答えを返す。『第2回の確認問題を出して』『復習のクイズを出して』のように、確認問題やクイズを求められたときに使う。返された answer は、利用者が答えるまで見せずに、まず question だけを出題すること。」
  - 実行すると、モデルは「『事前学習』の意味は？」だけを出題し、答え（定義）は見せずに「考えてみた答えを教えてくださいね！」と返した。docstring に書いた「answer は見せない」がそのまま効いていた

## 宿題

- 取り組んだレベル：実装
- やったこと：
  - `app/tools.py` に `save_learning_log(topic: str, note: str) -> str` を作った
    - 保存先はリポジトリ直下の `learning_log/log.jsonl`（`.gitignore` 済み）。1行に1件の JSON Lines にして、`open(path, "a")` で末尾に追記する。1つの JSON 配列にすると、追記のたびにファイル全体を読み直して書き直す必要があるため
    - 日時はモデルに引数で渡させず、関数の中で `datetime.now().isoformat(timespec="seconds")` で入れる。モデルは今日の日付を正確に知らないことがあり、コードで入れる方が確実なため
    - `json.dump(..., ensure_ascii=False)` で日本語をそのまま読める形で保存する
    - 返り値は「学習ログを保存しました: learning_log/log.jsonl, topic: …, note: …, day: …」。保存先（`relative_to` で相対パスにした）・内容・日時を返し、モデルが利用者に報告しやすくした
    - docstring には「ユーザーから学習内容の記録を求められたときに使う」と、`topic`・`note` に入れる内容を書いた
  - `app/agent.py` で `agent.tool_plain(tools.save_learning_log, requires_approval=True)` と登録し、`Agent` の `output_type` を `[str, DeferredToolRequests]` にした
  - `main()` で、結果が `DeferredToolRequests` の間は `while` で繰り返し、`approvals` の呼び出しごとにツール名と引数を表示して `input()` で y/N を聞く。答えを `DeferredToolResults` の `approvals[tool_call_id]` に入れ、`message_history=result.all_messages()` と `deferred_tool_results` を渡してもう一度 `run_sync` する
  - `INSTRUCTIONS` に「受講生の学習内容を記録するには、save_learning_log を使う。保存を断られた時は、保存しなかったことを伝える。」を足した
- 結果：
  - 質問「今日はLoRAとQLoRAの違いを学んだ。学習ログに記録して」で試した
  - 承認の処理を書く前（`requires_approval=True` と `output_type` だけ）：`result.output` は回答の文章ではなく `DeferredToolRequests(approvals=[ToolCallPart(tool_name='save_learning_log', …)])` になった。trace には `save_learning_log` の `[tool call]` はあるが `[tool return]` が無く、実行される直前で止まっていた。ファイルは作られなかった
  - y と答えた場合：`learning_log/log.jsonl` に `{"topic": "LoRAとQLoRAの違い", "note": "LoRAとQLoRAの違いについて学習した。", "day": "2026-11-04T11:49:10"}` が1行追記された
  - N と答えた場合：ファイルは変わらず、ツールの結果は `The tool call was denied.` になった
  - `INSTRUCTIONS` に1行足す前と後の比較（どちらも N と答えた。ツールの返す文字列は変えていない）

    | | 変更前 | 変更後 |
    |---|---|---|
    | 断ったあと、もう一度保存を頼んだか | 頼んだ（`note` を「学習した。」→「学習しました。」と言い換えて再度呼んだ） | 頼まなかった |
    | 最後の回答で、保存しなかったことに触れたか | 触れず、LoRA と QLoRA の説明だけを返した | 冒頭で「保存が許可されなかったため学習ログには記録できませんでした」と伝えた |

  - `uv run pytest -q` は 11 件すべて成功
- 気づき・疑問：
  - `requires_approval=True` を付け忘れて `output_type` だけを変えた状態では、`uv run pytest -q` を実行しただけで `{"topic": "a", "note": "a", …}` が保存された。テストの TestModel が全部のツールをダミーの引数で呼ぶためで、「利用者が頼んでいないのに取り消しにくい操作が実行される」ことを実際に体験した。付けたあとは、テストでも承認待ちで止まり、保存されなくなった
  - `output_type` の `DeferredToolRequests` は「止まってもよい」という許可で、「どのツールで止まるか」は `requires_approval` で決まる。両方そろって初めて承認待ちになる
  - 断られたモデルは、言い換えて同じ保存を頼み直してきた。承認の処理を `if` ではなく `while` にしておかないと、2回目の依頼が確認されないまま残る
  - モデルは断られた理由を `The tool call was denied.` という決まり文句でしか知らないので、そのままでは利用者に何も伝えなかった。`INSTRUCTIONS` に断られたときの振る舞いを書くと改善した。ただし試したのは1回なので、毎回こうなるかは確かめられていない。`ToolDenied("…")` で理由をツールの結果として返す方法との比較もしていない
  - `note` の中身が「LoRAとQLoRAの違いについて学習した」と薄かった。`requests=1` の1回の呼び出しで、`search_glossary` 2回と `save_learning_log` を同時に出していたため、検索結果を見る前に `note` を書いていた。docstring の `note` の説明を具体的にすると変わるかは、まだ試していない
  - `--trace` の `[usage]` の `requests` は、最後の `run_sync` の分しか数えていない。承認のたびに `run_sync` をやり直すので、実際の LLM 呼び出し回数はもっと多い
