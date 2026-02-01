#!/usr/bin/env python3
"""目次Markdownから章情報を抽出する"""

import json
import re
import sys
from pathlib import Path
from typing import Optional

import click


def extract_chapters_kakushin(toc_content: str) -> dict:
    """核心の目次をパース

    フォーマット:
    ## Part X > タイトル
    ### テーマ XX タイトル
    - サブタイトル ページ番号
    """
    chapters = []
    current_part = None
    current_chapter = None

    lines = toc_content.split("\n")

    for line in lines:
        # Part検出: ## Part 1 > 品詞
        part_match = re.match(r"^## Part (\d+) > (.+)$", line)
        if part_match:
            current_part = {
                "number": int(part_match.group(1)),
                "title": part_match.group(2).strip()
            }
            continue

        # テーマ検出: ### テーマ 01 冠詞
        theme_match = re.match(r"^### テーマ (\d+) (.+)$", line)
        if theme_match:
            # 前のチャプターの終了ページを設定（後で計算）
            current_chapter = {
                "part": f"Part{current_part['number']}" if current_part else "Part1",
                "part_title": current_part["title"] if current_part else "",
                "number": theme_match.group(1),
                "title": theme_match.group(2).strip(),
                "start_page": None,
                "items": []
            }
            chapters.append(current_chapter)
            continue

        # 最初の項目からページ番号を取得: - タイトル ページ番号
        if current_chapter and current_chapter["start_page"] is None:
            item_match = re.match(r"^- (.+?) (\d+)$", line.strip())
            if item_match:
                current_chapter["start_page"] = int(item_match.group(2))
                current_chapter["items"].append({
                    "title": item_match.group(1),
                    "page": int(item_match.group(2))
                })
                continue

        # その他の項目
        if current_chapter:
            item_match = re.match(r"^(?:- |\s+- )(.+?) (\d+)$", line.strip())
            if item_match:
                current_chapter["items"].append({
                    "title": item_match.group(1),
                    "page": int(item_match.group(2))
                })

    # 章のIDと終了ページを計算
    for i, ch in enumerate(chapters):
        ch["id"] = f"{ch['part']}_{ch['number']}"

        # 終了ページは次の章の開始ページ - 1
        if i + 1 < len(chapters):
            ch["end_page"] = chapters[i + 1]["start_page"] - 1
        else:
            # 最後の章は巻末まで（おおよそ）
            ch["end_page"] = ch["start_page"] + 30  # 推定値

    return {
        "book": "核心",
        "format": "kakushin",
        "total_chapters": len(chapters),
        "chapters": [
            {
                "id": ch["id"],
                "part": ch["part"],
                "part_title": ch["part_title"],
                "number": ch["number"],
                "title": ch["title"],
                "book_pages": {
                    "start": ch["start_page"],
                    "end": ch["end_page"]
                }
            }
            for ch in chapters
        ]
    }


def extract_chapters_narikawa(toc_content: str) -> dict:
    """成川の目次をパース

    フォーマット:
    ## PART XX タイトル
    | No. | タイトル | ページ |
    | 1 | タイトル | 018 |
    """
    # 本体と別冊を分離
    if "# 別冊・もくじ" in toc_content:
        parts = toc_content.split("# 別冊・もくじ")
        main_content = parts[0]
        supplement_content = parts[1] if len(parts) > 1 else ""
    else:
        main_content = toc_content
        supplement_content = ""

    # 本体の章を抽出
    main_chapters = _extract_narikawa_chapters(main_content, is_supplement=False)

    # 別冊の章を抽出
    supplement_chapters = []
    if supplement_content:
        supplement_chapters = _extract_narikawa_supplement(supplement_content)

    return {
        "book": "成川",
        "format": "narikawa",
        "total_chapters": len(main_chapters),
        "chapters": main_chapters,
        "supplement": {
            "title": "要点ハンドブック",
            "total_chapters": len(supplement_chapters),
            "chapters": supplement_chapters
        } if supplement_chapters else None
    }


def _extract_narikawa_chapters(content: str, is_supplement: bool = False) -> list:
    """成川の本体章を抽出"""
    chapters = []
    current_part = None
    current_part_title = None

    lines = content.split("\n")

    for i, line in enumerate(lines):
        # PART検出: ## PART 01 動詞の語法と文型
        part_match = re.match(r"^## PART (\d+) (.+)$", line)
        if part_match:
            current_part = part_match.group(1)
            current_part_title = part_match.group(2).strip()
            continue

        # テーブル行検出: | 1 | タイトル | 018 |
        table_match = re.match(r"^\| (\d+) \| (.+?) \| (\d+) \|$", line)
        if table_match and current_part:
            chapters.append({
                "id": f"Part{current_part}_{table_match.group(1).zfill(2)}",
                "part": f"Part{current_part}",
                "part_title": current_part_title or "",
                "number": table_match.group(1),
                "title": table_match.group(2).strip(),
                "book_pages": {
                    "start": int(table_match.group(3)),
                    "end": None  # 後で計算
                }
            })

    # 終了ページを計算
    for i, ch in enumerate(chapters):
        if i + 1 < len(chapters):
            ch["book_pages"]["end"] = chapters[i + 1]["book_pages"]["start"] - 1
        else:
            # 最後の章は推定
            ch["book_pages"]["end"] = ch["book_pages"]["start"] + 5

    return chapters


def _extract_narikawa_supplement(content: str) -> list:
    """成川の別冊章を抽出"""
    chapters = []

    lines = content.split("\n")

    for line in lines:
        # 別冊テーブル行: | 01 | タイトル | 002 |
        table_match = re.match(r"^\| (\d+) \| (.+?) \| (\d+) \|$", line)
        if table_match:
            chapters.append({
                "id": f"Supplement_{table_match.group(1)}",
                "part": f"Part{table_match.group(1)}",
                "title": table_match.group(2).strip(),
                "book_pages": {
                    "start": int(table_match.group(3)),
                    "end": None
                }
            })

    # 終了ページを計算
    for i, ch in enumerate(chapters):
        if i + 1 < len(chapters):
            ch["book_pages"]["end"] = chapters[i + 1]["book_pages"]["start"] - 1
        else:
            ch["book_pages"]["end"] = ch["book_pages"]["start"] + 10

    return chapters


def extract_chapters_scramble(toc_content: str) -> dict:
    """スクランブルの目次をパース

    フォーマット:
    ## Part N 文法
    ### 第N章 タイトル
    - 番号 タイトル ... ページ
    """
    chapters = []
    current_part = None
    current_part_title = None
    current_chapter = None
    current_chapter_title = None

    lines = toc_content.split("\n")

    for line in lines:
        # Part検出: ## Part 1 文法
        part_match = re.match(r"^## Part (\d+) (.+)$", line)
        if part_match:
            current_part = int(part_match.group(1))
            current_part_title = part_match.group(2).strip()
            continue

        # 章検出: ### 第1章 時制
        chapter_match = re.match(r"^### 第(\d+)章 (.+)$", line)
        if chapter_match:
            current_chapter = int(chapter_match.group(1))
            current_chapter_title = chapter_match.group(2).strip()
            continue

        # 項目検出: - 1 基本3時制の用法 ..... 49
        # ページ番号は ... や空白の後に数字
        item_match = re.match(r"^- (\d+) (.+?) [\.… ]+(\d+)$", line.strip())
        if item_match and current_chapter:
            chapters.append({
                "id": f"Ch{str(current_chapter).zfill(2)}_{item_match.group(1).zfill(3)}",
                "part": f"Part{current_part}" if current_part else "Part1",
                "part_title": current_part_title or "",
                "chapter": current_chapter,
                "chapter_title": current_chapter_title or "",
                "number": item_match.group(1),
                "title": item_match.group(2).strip(),
                "book_pages": {
                    "start": int(item_match.group(3)),
                    "end": None
                }
            })

    # 終了ページを計算（次の項目の開始ページ - 1）
    for i, ch in enumerate(chapters):
        if i + 1 < len(chapters):
            ch["book_pages"]["end"] = chapters[i + 1]["book_pages"]["start"]
        else:
            ch["book_pages"]["end"] = ch["book_pages"]["start"] + 2

    return {
        "book": "スクランブル",
        "format": "scramble",
        "total_chapters": len(chapters),
        "chapters": chapters
    }


def extract_chapters_hijii(toc_content: str) -> dict:
    """肘井の目次をパース

    フォーマット:
    ## 章タイトル
    - テーマNN タイトル ページ
    """
    chapters = []
    current_chapter = None
    current_chapter_title = None
    chapter_num = 0

    lines = toc_content.split("\n")

    for line in lines:
        # 章検出: ## 序章　SVの発見編 or ## 第1章　意味のカタマリ編
        chapter_match = re.match(r"^## (序章|第\d+章)　(.+)$", line)
        if chapter_match:
            chapter_num += 1
            current_chapter = chapter_match.group(1)
            current_chapter_title = chapter_match.group(2).strip()
            continue

        # テーマ検出: - テーマ01　SVの発見で英文が読める①　12
        theme_match = re.match(r"^- テーマ(\d+)　(.+?)　(\d+)$", line.strip())
        if theme_match and current_chapter:
            chapters.append({
                "id": f"Theme_{theme_match.group(1)}",
                "chapter": current_chapter,
                "chapter_title": current_chapter_title or "",
                "number": theme_match.group(1),
                "title": theme_match.group(2).strip(),
                "book_pages": {
                    "start": int(theme_match.group(3)),
                    "end": None
                }
            })

    # 終了ページを計算
    for i, ch in enumerate(chapters):
        if i + 1 < len(chapters):
            ch["book_pages"]["end"] = chapters[i + 1]["book_pages"]["start"] - 1
        else:
            ch["book_pages"]["end"] = ch["book_pages"]["start"] + 5

    return {
        "book": "肘井",
        "format": "hijii",
        "total_chapters": len(chapters),
        "chapters": chapters
    }


def extract_chapters_nyumon(toc_content: str) -> dict:
    """入門英文の目次をパース

    フォーマット:
    ### 第N章　タイトル
    - 番号 タイトル……ページ
    """
    chapters = []
    current_chapter = None
    current_chapter_title = None

    lines = toc_content.split("\n")

    for line in lines:
        # 章検出: ### 第1章　主語と動詞の把握
        chapter_match = re.match(r"^### 第(\d+)章　(.+)$", line)
        if chapter_match:
            current_chapter = int(chapter_match.group(1))
            current_chapter_title = chapter_match.group(2).strip()
            continue

        # 項目検出: - 1 主語の把握（前置詞＋名詞）……28
        item_match = re.match(r"^- (\d+) (.+?)……(\d+)$", line.strip())
        if item_match and current_chapter:
            chapters.append({
                "id": f"Ch{str(current_chapter).zfill(2)}_{item_match.group(1).zfill(2)}",
                "chapter": current_chapter,
                "chapter_title": current_chapter_title or "",
                "number": item_match.group(1),
                "title": item_match.group(2).strip(),
                "book_pages": {
                    "start": int(item_match.group(3)),
                    "end": None
                }
            })

    # 終了ページを計算
    for i, ch in enumerate(chapters):
        if i + 1 < len(chapters):
            ch["book_pages"]["end"] = chapters[i + 1]["book_pages"]["start"] - 1
        else:
            ch["book_pages"]["end"] = ch["book_pages"]["start"] + 1

    return {
        "book": "入門英文",
        "format": "nyumon",
        "total_chapters": len(chapters),
        "chapters": chapters
    }


def extract_chapters_nyumon_supplement(toc_content: str) -> dict:
    """入門英文_別冊の目次をパース

    フォーマット:
    - 1〜4　問題 …… 8
    - 1〜4　語句 …… 10
    """
    chapters = []

    lines = toc_content.split("\n")

    for line in lines:
        # 問題検出: - 1〜4　問題 …… 8
        item_match = re.match(r"^- (\d+)〜(\d+)　(問題|語句) […… ]+(\d+)$", line.strip())
        if item_match:
            range_start = item_match.group(1)
            range_end = item_match.group(2)
            item_type = item_match.group(3)
            page = int(item_match.group(4))

            chapters.append({
                "id": f"Q{range_start}-{range_end}_{item_type}",
                "range": f"{range_start}〜{range_end}",
                "type": item_type,
                "title": f"{range_start}〜{range_end}　{item_type}",
                "book_pages": {
                    "start": page,
                    "end": None
                }
            })

    # 終了ページを計算
    for i, ch in enumerate(chapters):
        if i + 1 < len(chapters):
            ch["book_pages"]["end"] = chapters[i + 1]["book_pages"]["start"] - 1
        else:
            ch["book_pages"]["end"] = ch["book_pages"]["start"] + 1

    return {
        "book": "入門英文_別冊",
        "format": "nyumon_supplement",
        "total_chapters": len(chapters),
        "chapters": chapters
    }


def extract_chapters_narikawa_supplement(toc_content: str) -> dict:
    """成川_別冊の目次をパース

    フォーマット:
    - PART XX　タイトル …… ページ
    - 基本例文のまとめ …… ページ
    """
    chapters = []

    lines = toc_content.split("\n")

    for line in lines:
        # PART行検出: - PART 01　動詞の語法と文型 …… 002
        part_match = re.match(r"^- PART (\d+)　(.+?) [… ]+(\d+)$", line.strip())
        if part_match:
            chapters.append({
                "id": f"Part{part_match.group(1)}",
                "number": part_match.group(1),
                "title": part_match.group(2).strip(),
                "book_pages": {
                    "start": int(part_match.group(3)),
                    "end": None
                }
            })
            continue

        # 基本例文のまとめ: - 基本例文のまとめ …… 131
        matome_match = re.match(r"^- (基本例文のまとめ) [… ]+(\d+)$", line.strip())
        if matome_match:
            chapters.append({
                "id": "Matome",
                "number": "16",
                "title": matome_match.group(1).strip(),
                "book_pages": {
                    "start": int(matome_match.group(2)),
                    "end": None
                }
            })

    # 終了ページを計算
    for i, ch in enumerate(chapters):
        if i + 1 < len(chapters):
            ch["book_pages"]["end"] = chapters[i + 1]["book_pages"]["start"] - 1
        else:
            # 最後の章（成川_別冊は180ページ）
            ch["book_pages"]["end"] = 180

    return {
        "book": "成川_別冊",
        "format": "narikawa_supplement",
        "total_chapters": len(chapters),
        "chapters": chapters
    }


def extract_chapters_hijii_supplement(toc_content: str) -> dict:
    """肘井_別冊の目次をパース

    フォーマット:
    - 序章　タイトル …… ページ
    - 第N章　タイトル …… ページ
    """
    chapters = []

    lines = toc_content.split("\n")

    for line in lines:
        # 序章検出: - 序章　SVの発見編 …… 2
        jo_match = re.match(r"^- (序章)　(.+?) [… ]+(\d+)$", line.strip())
        if jo_match:
            chapters.append({
                "id": "Ch00",
                "chapter": jo_match.group(1),
                "number": "0",
                "title": jo_match.group(2).strip(),
                "book_pages": {
                    "start": int(jo_match.group(3)),
                    "end": None
                }
            })
            continue

        # 章検出: - 第1章　意味のカタマリ編 …… 6
        chapter_match = re.match(r"^- 第(\d+)章　(.+?) [… ]+(\d+)$", line.strip())
        if chapter_match:
            chapters.append({
                "id": f"Ch{chapter_match.group(1).zfill(2)}",
                "chapter": f"第{chapter_match.group(1)}章",
                "number": chapter_match.group(1),
                "title": chapter_match.group(2).strip(),
                "book_pages": {
                    "start": int(chapter_match.group(3)),
                    "end": None
                }
            })

    # 終了ページを計算
    for i, ch in enumerate(chapters):
        if i + 1 < len(chapters):
            ch["book_pages"]["end"] = chapters[i + 1]["book_pages"]["start"] - 1
        else:
            # 最後の章（肘井_別冊は80ページ）
            ch["book_pages"]["end"] = 80

    return {
        "book": "肘井_別冊",
        "format": "hijii_supplement",
        "total_chapters": len(chapters),
        "chapters": chapters
    }


def extract_chapters_hajime(toc_content: str) -> dict:
    """はじめの英文読解ドリルの目次をパース

    フォーマット:
    ## Chapter N　タイトル …… ページ
    番号. タイトル …… ページ
    """
    chapters = []
    current_chapter = None
    current_chapter_title = None

    lines = toc_content.split("\n")

    for line in lines:
        # Chapter検出: ## Chapter 1　「品詞と文型」を始める前に …… 6
        chapter_match = re.match(r"^## Chapter (\d+)　(.+?)(?:\s*…… (\d+))?$", line)
        if chapter_match:
            current_chapter = int(chapter_match.group(1))
            current_chapter_title = chapter_match.group(2).strip()
            continue

        # 項目検出: 1. 5文型と「M」 …… 8
        item_match = re.match(r"^(\d+)\. (.+?) …… (\d+)$", line.strip())
        if item_match and current_chapter:
            chapters.append({
                "id": f"Ch{str(current_chapter).zfill(2)}_{item_match.group(1).zfill(2)}",
                "chapter": current_chapter,
                "chapter_title": current_chapter_title or "",
                "number": item_match.group(1),
                "title": item_match.group(2).strip(),
                "book_pages": {
                    "start": int(item_match.group(3)),
                    "end": None
                }
            })

    # 終了ページを計算
    for i, ch in enumerate(chapters):
        if i + 1 < len(chapters):
            ch["book_pages"]["end"] = chapters[i + 1]["book_pages"]["start"] - 1
        else:
            ch["book_pages"]["end"] = ch["book_pages"]["start"] + 3

    return {
        "book": "はじめの英文読解ドリル",
        "format": "hajime",
        "total_chapters": len(chapters),
        "chapters": chapters
    }


def detect_format(toc_content: str) -> str:
    """目次フォーマットを自動検出"""
    if "### テーマ" in toc_content:
        return "kakushin"
    elif "## PART" in toc_content and "| No. |" in toc_content:
        return "narikawa"
    elif "- PART" in toc_content and "……" in toc_content and "## PART" not in toc_content:
        # 成川_別冊: - PART XX　タイトル …… ページ（テーブル形式ではない）
        return "narikawa_supplement"
    elif "## Part" in toc_content and "### 第" in toc_content:
        return "scramble"
    elif "- テーマ" in toc_content and "## 序章" in toc_content:
        return "hijii"
    elif ("- 序章" in toc_content or "- 第" in toc_content) and "別冊" in toc_content:
        # 肘井_別冊: - 序章 / - 第N章 形式
        return "hijii_supplement"
    elif "### 第" in toc_content and "……" in toc_content:
        return "nyumon"
    elif "〜" in toc_content and "問題" in toc_content and "語句" in toc_content:
        return "nyumon_supplement"
    elif "## Chapter" in toc_content:
        return "hajime"
    else:
        return "unknown"


def extract_chapters(toc_path: Path) -> dict:
    """目次ファイルから章情報を抽出"""
    toc_path = Path(toc_path)
    content = toc_path.read_text(encoding="utf-8")

    format_type = detect_format(content)

    if format_type == "kakushin":
        return extract_chapters_kakushin(content)
    elif format_type == "narikawa":
        return extract_chapters_narikawa(content)
    elif format_type == "narikawa_supplement":
        return extract_chapters_narikawa_supplement(content)
    elif format_type == "scramble":
        return extract_chapters_scramble(content)
    elif format_type == "hijii":
        return extract_chapters_hijii(content)
    elif format_type == "hijii_supplement":
        return extract_chapters_hijii_supplement(content)
    elif format_type == "nyumon":
        return extract_chapters_nyumon(content)
    elif format_type == "nyumon_supplement":
        return extract_chapters_nyumon_supplement(content)
    elif format_type == "hajime":
        return extract_chapters_hajime(content)
    else:
        raise ValueError(f"Unknown TOC format in {toc_path}")


# CLI
@click.command()
@click.argument("toc_path", type=click.Path(exists=True))
@click.option("--json", "as_json", is_flag=True, help="JSON形式で出力")
@click.option("--output", "-o", type=click.Path(), help="出力ファイル")
def main(toc_path, as_json, output):
    """目次ファイルから章情報を抽出"""
    result = extract_chapters(Path(toc_path))

    if as_json or output:
        json_str = json.dumps(result, indent=2, ensure_ascii=False)
        if output:
            Path(output).write_text(json_str, encoding="utf-8")
            click.echo(f"出力: {output}")
        else:
            click.echo(json_str)
    else:
        click.echo(f"書籍: {result['book']}")
        click.echo(f"フォーマット: {result['format']}")
        click.echo(f"総章数: {result['total_chapters']}")
        click.echo("")

        for ch in result["chapters"]:
            pages = ch["book_pages"]
            click.echo(f"  {ch['id']}: {ch['title']} (p.{pages['start']}-{pages['end']})")

        if result.get("supplement"):
            supp = result["supplement"]
            click.echo(f"\n別冊: {supp['title']} ({supp['total_chapters']}章)")
            for ch in supp["chapters"]:
                pages = ch["book_pages"]
                click.echo(f"  {ch['id']}: {ch['title']} (p.{pages['start']}-{pages['end']})")


if __name__ == "__main__":
    main()
