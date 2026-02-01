#!/usr/bin/env python3
"""status.json v1.0 → v2.0 移行スクリプト"""

import json
import shutil
from datetime import datetime
from pathlib import Path

import click

# 依存スクリプトのインポート
from pdf_tools import generate_page_map
from extract_chapters import extract_chapters


def migrate_to_v2(project_root: Path) -> dict:
    """status.json を v1.0 から v2.0 に移行"""
    status_path = project_root / "progress" / "status.json"
    raw_dir = project_root / "pdf" / "raw"
    output_dir = project_root / "pdf" / "output"

    # 現在のstatus.jsonを読み込み
    with open(status_path, encoding="utf-8") as f:
        old_status = json.load(f)

    # バックアップ
    backup_path = status_path.with_suffix(".json.bak")
    shutil.copy(status_path, backup_path)

    # 新しいスキーマを構築
    new_status = {
        "version": "2.0",
        "last_updated": datetime.now().isoformat(),
        "config": {
            "image_naming": "page_{:03d}.png",
            "dpi": 150,
            "spot_check_interval": 5,
            "max_retry": {
                "image_conversion": 3,
                "subagent_ocr": 2,
                "codex_review": 2
            }
        },
        "books": {}
    }

    # 書籍ごとに移行
    for book_name, old_book in old_status.get("books", {}).items():
        # ページマッピングを生成
        try:
            page_map = generate_page_map(book_name, raw_dir)
        except Exception as e:
            page_map = {"files": [], "total_book_pages": 0}
            print(f"Warning: Could not generate page map for {book_name}: {e}")

        # ファイル分類
        main_files = []
        supplement_files = []
        for f in page_map.get("files", []):
            if "別冊" in f["file"]:
                supplement_files.append(f["file"])
            else:
                main_files.append(f["file"])

        # 章情報を抽出
        chapters = []
        supplement_info = None
        toc_path = output_dir / book_name / "00_目次.md"

        if toc_path.exists():
            try:
                chapter_data = extract_chapters(toc_path)
                chapters = chapter_data.get("chapters", [])

                # 別冊情報
                if chapter_data.get("supplement"):
                    supplement_info = chapter_data["supplement"]
            except Exception as e:
                print(f"Warning: Could not extract chapters for {book_name}: {e}")

        # 章にステータス情報を追加
        for i, ch in enumerate(chapters):
            ch["status"] = "pending"
            ch["output_file"] = None
            ch["review_status"] = None
            # スポットチェック対象: 最初の章、5の倍数
            ch_num = int(ch.get("number", "0").lstrip("0") or "0")
            ch["spot_check_required"] = (i == 0) or (ch_num > 0 and ch_num % 5 == 0)

        # ページマッピング辞書を作成
        page_mapping = {}
        for f in page_map.get("files", []):
            page_mapping[f["file"]] = {
                "pdf_pages": f["pdf_pages"],
                "book_start": f["book_start"],
                "book_end": f["book_end"],
                "is_supplement": "別冊" in f["file"]
            }

        # 新書籍データ
        new_book = {
            "status": old_book.get("status", "not_started"),
            "files": {
                "main": main_files,
                "supplement": supplement_files
            },
            "page_mapping": page_mapping,
            "total_pages": page_map.get("total_book_pages", 0),
            "toc_pages": old_book.get("toc_pages"),
            "chapters": chapters,
            "completed_chapters": old_book.get("completed_chapters", 0),
            "total_chapters": len(chapters),
            "notes": old_book.get("notes", "")
        }

        # 別冊がある場合
        if supplement_files and supplement_info:
            new_book["supplement"] = {
                "file": supplement_files[0] if supplement_files else None,
                "title": supplement_info.get("title", ""),
                "status": "not_started",
                "chapters": supplement_info.get("chapters", [])
            }

        new_status["books"][book_name] = new_book

    return new_status


@click.command()
@click.option("--dry-run", is_flag=True, help="実行せずに結果を表示")
@click.option("--output", "-o", type=click.Path(), help="出力先（デフォルト: 上書き）")
def main(dry_run, output):
    """status.json を v2.0 に移行"""
    project_root = Path(__file__).parent.parent
    status_path = project_root / "progress" / "status.json"

    click.echo("status.json v1.0 → v2.0 移行を開始...")

    new_status = migrate_to_v2(project_root)

    if dry_run:
        click.echo("\n[Dry Run] 以下の内容で更新されます:\n")
        click.echo(json.dumps(new_status, indent=2, ensure_ascii=False)[:2000])
        click.echo("\n... (truncated)")
    else:
        output_path = Path(output) if output else status_path
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(new_status, f, indent=2, ensure_ascii=False)
        click.echo(f"\n✅ 移行完了: {output_path}")
        click.echo(f"   バックアップ: {status_path.with_suffix('.json.bak')}")

        # サマリー表示
        click.echo("\n📊 サマリー:")
        for book_name, book in new_status["books"].items():
            click.echo(f"   {book_name}: {book['total_chapters']}章, {book['total_pages']}ページ")


if __name__ == "__main__":
    main()
