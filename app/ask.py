"""第1回: 素のLLMに質問するスクリプト。

使い方:
    uv run python -m app.ask "LoRAとは何ですか？"
    uv run python -m app.ask --interactive
    uv run python -m app.ask            # 質問を省略すると、講座に固有の質問をする

第1回の演習では、トークン数を表示し、第1回の宿題では、会話履歴を保ちながら
複数回質問できるようにする。
"""

import argparse
from typing import Any

from google import genai
from google.genai import errors

from app.config import MODEL, api_error_message, get_api_key

# 講座に固有の質問。正しい答えは data/glossary.json の homework-levels にある
DEFAULT_QUESTION = "AIE2026の講座の宿題にある「3レベル」とは何ですか？"


def _read_usage_count(metadata: Any, *names: str) -> int | None:
    if metadata is None:
        return None

    for name in names:
        value = getattr(metadata, name, None)
        if value is not None:
            return int(value)

        if isinstance(metadata, dict):
            value = metadata.get(name)
            if value is not None:
                return int(value)

    return None


def _print_usage(response: Any) -> None:
    metadata = getattr(response, "usage_metadata", None)
    prompt_tokens = _read_usage_count(metadata, "prompt_token_count", "input_tokens", "prompt_tokens")
    completion_tokens = _read_usage_count(
        metadata,
        "completion_token_count",
        "output_tokens",
        "candidates_token_count",
        "completion_tokens",
    )

    print(
        "[token] "
        f"入力: {prompt_tokens if prompt_tokens is not None else '不明'} / "
        f"出力: {completion_tokens if completion_tokens is not None else '不明'}"
    )


def ask(question: str, chat: Any | None = None) -> str:
    client = genai.Client(api_key=get_api_key())
    if chat is None:
        chat = client.chats.create(model=MODEL)

    response = chat.send_message(question)
    _print_usage(response)
    return response.text or ""


def main() -> None:
    parser = argparse.ArgumentParser(description="素のLLMに質問する")
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="会話履歴を保ったまま複数回質問する",
    )
    args = parser.parse_args()

    print(f"[model] {MODEL}")
    try:
        if args.interactive:
            client = genai.Client(api_key=get_api_key())
            chat = client.chats.create(model=MODEL)
            print("[mode] 会話履歴あり（空行で終了）")
            while True:
                question = input("質問> ").strip()
                if not question:
                    break
                print(f"[質問] {question}\n")
                print(ask(question, chat=chat))
                print()
            return

        print(f"[質問] {args.question}\n")
        print(ask(args.question))
    except errors.APIError as e:
        print(api_error_message(e.code, e.message))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
