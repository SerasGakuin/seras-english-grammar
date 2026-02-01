#!/usr/bin/env python3
"""
status.json から CLAUDE.md の対象書籍テーブルを自動更新するスクリプト。

Single Source of Truth: status.json
更新対象: CLAUDE.md, .rules/ocr-workflow.md
"""

import json
import re
import sys
from pathlib import Path

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
STATUS_FILE = PROJECT_ROOT / "progress" / "status.json"
CLAUDE_MD = PROJECT_ROOT / "CLAUDE.md"
WORKFLOW_MD = PROJECT_ROOT / ".rules" / "ocr-workflow.md"

# 書籍の表示順序（本体 → 別冊の順）
BOOK_ORDER = [
    "核心",
    "成川",
    "成川_別冊",
    "スクランブル",
    "肘井",
    "肘井_別冊",
    "入門英文",
    "入門英文_別冊",
    "はじめの英文読解ドリル",
]


def load_status() -> dict:
    """status.json を読み込む"""
    with open(STATUS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_file_structure(book_data: dict, book_name: str) -> str:
    """ファイル構成を取得"""
    files = book_data.get("files", {})
    main_files = files.get("main", [])

    if "_別冊" in book_name:
        return "1ファイル"

    if len(main_files) == 2:
        if "前半" in main_files[0] and "後半" in main_files[1]:
            return "前半 + 後半"
        else:
            return "本体"
    elif len(main_files) == 1:
        return "1ファイル"
    else:
        return "複数ファイル"


def get_status_text(book_data: dict) -> str:
    """ステータステキストを生成"""
    status = book_data.get("status", "unknown")
    chapters = book_data.get("chapters", [])
    chapter_count = len(chapters)

    if status == "not_started":
        return "未着手"
    elif status == "toc_in_progress":
        return "目次作業中"
    elif status == "toc_completed":
        return f"目次完了（{chapter_count}章）"
    elif status == "chapters_in_progress":
        completed = sum(1 for c in chapters if c.get("status") == "completed")
        return f"章作業中（{completed}/{chapter_count}章）"
    elif status == "completed":
        return f"完了（{chapter_count}章）"
    else:
        return status


def generate_books_table(status_data: dict) -> str:
    """対象書籍テーブルを生成"""
    books = status_data.get("books", {})

    # 本体と別冊をカウント
    main_count = sum(1 for name in books if "_別冊" not in name)
    supplement_count = sum(1 for name in books if "_別冊" in name)

    lines = [
        f"### 対象書籍（{main_count}冊 + 別冊{supplement_count}冊）",
        "",
        "| 書籍名 | ファイル構成 | ステータス |",
        "|--------|-------------|-----------|",
    ]

    # 定義された順序で出力
    for book_name in BOOK_ORDER:
        if book_name in books:
            book_data = books[book_name]
            file_structure = get_file_structure(book_data, book_name)
            status_text = get_status_text(book_data)
            lines.append(f"| {book_name} | {file_structure} | {status_text} |")

    # 未定義の書籍があれば追加
    for book_name in books:
        if book_name not in BOOK_ORDER:
            book_data = books[book_name]
            file_structure = get_file_structure(book_data, book_name)
            status_text = get_status_text(book_data)
            lines.append(f"| {book_name} | {file_structure} | {status_text} |")

    return "\n".join(lines)


def update_claude_md(new_table: str, dry_run: bool = False) -> bool:
    """CLAUDE.md の対象書籍テーブルを更新"""
    content = CLAUDE_MD.read_text(encoding="utf-8")

    # テーブル部分を検索（### 対象書籍 から次の --- まで）
    pattern = r"(### 対象書籍.*?\n\n\|.*?\|.*?\n\|[-|]+\n(?:\|.*?\|\n)*)"

    match = re.search(pattern, content, re.DOTALL)
    if not match:
        print("Error: CLAUDE.md に対象書籍テーブルが見つかりません", file=sys.stderr)
        return False

    old_table = match.group(1).rstrip("\n")
    new_table_with_newline = new_table

    if old_table == new_table_with_newline:
        print("CLAUDE.md: 変更なし")
        return True

    if dry_run:
        print("CLAUDE.md: 更新が必要")
        print("--- 現在 ---")
        print(old_table)
        print("--- 更新後 ---")
        print(new_table_with_newline)
        return False

    new_content = content.replace(old_table, new_table_with_newline)
    CLAUDE_MD.write_text(new_content, encoding="utf-8")
    print("CLAUDE.md: 更新完了")
    return True


def update_workflow_md(status_data: dict, dry_run: bool = False) -> bool:
    """ocr-workflow.md の対象書籍テーブルを更新"""
    if not WORKFLOW_MD.exists():
        print(f"Warning: {WORKFLOW_MD} が存在しません", file=sys.stderr)
        return True

    content = WORKFLOW_MD.read_text(encoding="utf-8")
    books = status_data.get("books", {})

    # シンプルなテーブル（本体のみ）を生成
    lines = [
        "| 書籍名 | ファイル構成 | ステータス |",
        "|--------|-------------|-----------|",
    ]

    main_books = ["核心", "成川", "スクランブル", "肘井", "入門英文", "はじめの英文読解ドリル"]
    for book_name in main_books:
        if book_name in books:
            book_data = books[book_name]
            file_structure = get_file_structure(book_data, book_name)
            status_text = get_status_text(book_data)
            # 章数は省略してシンプルに
            if "目次完了" in status_text:
                status_text = "目次完了"
            elif "完了" in status_text:
                status_text = "完了"
            lines.append(f"| {book_name} | {file_structure} | {status_text} |")

    new_table = "\n".join(lines)

    # テーブル部分を検索
    pattern = r"(## 対象書籍\n\n\|.*?\|.*?\n\|[-|]+\n(?:\|.*?\|\n)*)"

    match = re.search(pattern, content, re.DOTALL)
    if not match:
        print("Warning: ocr-workflow.md に対象書籍テーブルが見つかりません", file=sys.stderr)
        return True

    old_section = match.group(1).rstrip("\n")
    new_section = "## 対象書籍\n\n" + new_table

    if old_section == new_section:
        print("ocr-workflow.md: 変更なし")
        return True

    if dry_run:
        print("ocr-workflow.md: 更新が必要")
        return False

    new_content = content.replace(old_section, new_section)
    WORKFLOW_MD.write_text(new_content, encoding="utf-8")
    print("ocr-workflow.md: 更新完了")
    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="status.json から CLAUDE.md を自動更新"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="整合性チェックのみ（変更しない）"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="出力を抑制"
    )
    args = parser.parse_args()

    if not STATUS_FILE.exists():
        print(f"Error: {STATUS_FILE} が見つかりません", file=sys.stderr)
        sys.exit(1)

    status_data = load_status()
    new_table = generate_books_table(status_data)

    claude_ok = update_claude_md(new_table, dry_run=args.check)
    workflow_ok = update_workflow_md(status_data, dry_run=args.check)

    if args.check:
        if claude_ok and workflow_ok:
            if not args.quiet:
                print("OK: ドキュメントは最新です")
            sys.exit(0)
        else:
            if not args.quiet:
                print("NG: ドキュメントの更新が必要です")
                print("実行: python scripts/sync_docs.py")
            sys.exit(1)
    else:
        if not args.quiet:
            print("同期完了")


if __name__ == "__main__":
    main()
