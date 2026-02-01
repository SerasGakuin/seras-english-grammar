#!/usr/bin/env python3
"""PDF操作ツール - OCRワークフロー用"""

import json
import sys
from pathlib import Path
from typing import Optional

import click
from pypdf import PdfReader, PdfWriter


def pdf_info(pdf_path: Path) -> dict:
    """PDFの情報を取得"""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    reader = PdfReader(pdf_path)
    first_page = reader.pages[0]

    # ページサイズを取得
    media_box = first_page.mediabox
    width = float(media_box.width)
    height = float(media_box.height)

    # 向きを判定
    orientation = "portrait" if height >= width else "landscape"

    return {
        "file": pdf_path.name,
        "pages": len(reader.pages),
        "page_size": {
            "width": round(width, 2),
            "height": round(height, 2)
        },
        "orientation": orientation
    }


def pdf_info_all(directory: Path) -> list[dict]:
    """ディレクトリ内の全PDFの情報を取得"""
    directory = Path(directory)
    results = []

    for pdf_file in sorted(directory.glob("*.pdf")):
        try:
            info = pdf_info(pdf_file)
            results.append(info)
        except Exception as e:
            results.append({"file": pdf_file.name, "error": str(e)})

    return results


def pdf_to_images(
    pdf_path: Path,
    output_dir: Path,
    dpi: int = 150,
    page_range: Optional[str] = None,
    start_page_num: Optional[int] = None
) -> list[Path]:
    """PDFを画像に変換

    Args:
        pdf_path: 入力PDFのパス
        output_dir: 出力ディレクトリ
        dpi: 解像度（デフォルト: 150）
        page_range: 変換するページ範囲（例: "1-10"）
        start_page_num: 出力ファイル名の開始番号（例: 187でpage_187.pngから開始）
    """
    from pdf2image import convert_from_path

    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ページ範囲をパース
    first_page = None
    last_page = None
    if page_range:
        parts = page_range.split("-")
        first_page = int(parts[0])
        last_page = int(parts[1]) if len(parts) > 1 else first_page

    # 変換
    images = convert_from_path(
        pdf_path,
        dpi=dpi,
        first_page=first_page,
        last_page=last_page
    )

    # 保存
    created_files = []
    # 出力ファイル名の開始番号を決定
    if start_page_num is not None:
        output_start = start_page_num
    elif first_page is not None:
        output_start = first_page
    else:
        output_start = 1

    for i, image in enumerate(images):
        page_num = output_start + i
        output_path = output_dir / f"page_{page_num:03d}.png"
        image.save(output_path, "PNG")
        created_files.append(output_path)

    return created_files


def pdf_split(
    pdf_path: Path,
    output_dir: Path,
    ranges: list[str],
    names: Optional[list[str]] = None
) -> list[Path]:
    """PDFを分割"""
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(pdf_path)
    created_files = []

    for i, page_range in enumerate(ranges):
        # 範囲をパース
        parts = page_range.split("-")
        start = int(parts[0])
        end = int(parts[1]) if len(parts) > 1 else start

        # 出力ファイル名
        if names and i < len(names):
            output_name = f"{names[i]}.pdf"
        else:
            output_name = f"part_{i + 1:03d}.pdf"

        output_path = output_dir / output_name

        # 分割
        writer = PdfWriter()
        for page_num in range(start - 1, end):  # 0-indexed
            if page_num < len(reader.pages):
                writer.add_page(reader.pages[page_num])

        with open(output_path, "wb") as f:
            writer.write(f)

        created_files.append(output_path)

    return created_files


def generate_page_map(book_name: str, raw_dir: Path) -> dict:
    """前半/後半のページマッピングを生成"""
    raw_dir = Path(raw_dir)

    # 書籍に関連するPDFを検索
    patterns = [
        f"{book_name}_前半.pdf",
        f"{book_name}_後半.pdf",
        f"{book_name}.pdf",
        f"{book_name}_別冊.pdf"
    ]

    files = []
    current_book_page = 1

    for pattern in patterns:
        pdf_path = raw_dir / pattern
        if pdf_path.exists():
            info = pdf_info(pdf_path)
            pages = info["pages"]

            files.append({
                "file": pattern,
                "pdf_pages": pages,
                "book_start": current_book_page,
                "book_end": current_book_page + pages - 1
            })

            current_book_page += pages

    total_pages = sum(f["pdf_pages"] for f in files)

    return {
        "book": book_name,
        "files": files,
        "total_book_pages": total_pages
    }


# CLI
@click.group()
def cli():
    """PDF操作ツール"""
    pass


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True), required=False)
@click.option("--all", "show_all", is_flag=True, help="pdf/raw/内の全PDFを表示")
@click.option("--json", "as_json", is_flag=True, help="JSON形式で出力")
def info(pdf_path, show_all, as_json):
    """PDFの情報を表示"""
    if show_all:
        base_dir = Path(__file__).parent.parent
        raw_dir = base_dir / "pdf" / "raw"
        results = pdf_info_all(raw_dir)

        if as_json:
            click.echo(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            for r in results:
                if "error" in r:
                    click.echo(f"  {r['file']}: ERROR - {r['error']}")
                else:
                    click.echo(f"  {r['file']}: {r['pages']}ページ ({r['orientation']})")
    elif pdf_path:
        result = pdf_info(Path(pdf_path))
        if as_json:
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            click.echo(f"ファイル: {result['file']}")
            click.echo(f"ページ数: {result['pages']}")
            click.echo(f"サイズ: {result['page_size']['width']} x {result['page_size']['height']}")
            click.echo(f"向き: {result['orientation']}")
    else:
        click.echo("pdf_pathまたは--allオプションを指定してください")
        sys.exit(1)


@cli.command("to-images")
@click.argument("pdf_path", type=click.Path(exists=True))
@click.argument("output_dir", type=click.Path())
@click.option("--dpi", default=150, help="解像度（デフォルト: 150）")
@click.option("--range", "page_range", help="ページ範囲（例: 1-10）")
@click.option("--start-page", "start_page_num", type=int, help="出力ファイル名の開始番号（例: 187でpage_187.pngから開始）")
def to_images_cmd(pdf_path, output_dir, dpi, page_range, start_page_num):
    """PDFを画像に変換"""
    created = pdf_to_images(Path(pdf_path), Path(output_dir), dpi, page_range, start_page_num)
    click.echo(f"作成: {len(created)}ファイル")
    for f in created:
        click.echo(f"  {f}")


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True))
@click.option("--output-dir", "-o", required=True, type=click.Path(), help="出力ディレクトリ")
@click.option("--ranges", "-r", required=True, help="ページ範囲（カンマ区切り、例: 1-10,11-25）")
@click.option("--names", "-n", help="出力ファイル名（カンマ区切り）")
def split(pdf_path, output_dir, ranges, names):
    """PDFを分割"""
    range_list = [r.strip() for r in ranges.split(",")]
    name_list = [n.strip() for n in names.split(",")] if names else None

    created = pdf_split(Path(pdf_path), Path(output_dir), range_list, name_list)
    click.echo(f"作成: {len(created)}ファイル")
    for f in created:
        click.echo(f"  {f}")


@cli.command("page-map")
@click.argument("book_name")
@click.option("--json", "as_json", is_flag=True, help="JSON形式で出力")
def page_map_cmd(book_name, as_json):
    """前半/後半のページマッピングを生成"""
    base_dir = Path(__file__).parent.parent
    raw_dir = base_dir / "pdf" / "raw"

    result = generate_page_map(book_name, raw_dir)

    if as_json:
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        click.echo(f"書籍: {result['book']}")
        click.echo(f"総ページ数: {result['total_book_pages']}")
        click.echo("")
        for f in result["files"]:
            click.echo(f"  {f['file']}: {f['pdf_pages']}ページ (書籍: {f['book_start']}-{f['book_end']})")


if __name__ == "__main__":
    cli()
