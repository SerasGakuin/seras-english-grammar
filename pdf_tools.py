#!/usr/bin/env python3
"""PDF前処理ツール: 回転・分割"""

from pypdf import PdfReader, PdfWriter
from pathlib import Path


def rotate_pdf(input_path: str, output_path: str, rotation: int = -90):
    """
    PDFの全ページを回転させる
    rotation: -90 = 左に90度, 90 = 右に90度
    """
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for page in reader.pages:
        page.rotate(rotation)
        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)

    print(f"✓ 回転完了: {output_path} ({len(reader.pages)}ページ)")


def split_pdf(input_path: str, output_dir: str, chapters: dict[str, tuple[int, int]]):
    """
    PDFを章ごとに分割する
    chapters: {"章名": (開始ページ, 終了ページ)} ※1-indexed
    """
    reader = PdfReader(input_path)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for name, (start, end) in chapters.items():
        writer = PdfWriter()
        for i in range(start - 1, end):  # 0-indexed に変換
            writer.add_page(reader.pages[i])

        filename = output_path / f"{name}.pdf"
        with open(filename, "wb") as f:
            writer.write(f)

        print(f"✓ {name}: ページ {start}-{end} ({end - start + 1}ページ) → {filename}")


def extract_pages(input_path: str, output_path: str, start: int, end: int):
    """
    指定範囲のページを抽出する
    start, end: 1-indexed
    """
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for i in range(start - 1, end):
        writer.add_page(reader.pages[i])

    with open(output_path, "wb") as f:
        writer.write(f)

    print(f"✓ 抽出完了: ページ {start}-{end} → {output_path}")


def get_pdf_info(input_path: str):
    """PDFの情報を表示"""
    reader = PdfReader(input_path)
    print(f"ファイル: {input_path}")
    print(f"総ページ数: {len(reader.pages)}")

    page = reader.pages[0]
    box = page.mediabox
    print(f"ページサイズ: {float(box.width):.0f} x {float(box.height):.0f} pt")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("使い方:")
        print("  python pdf_tools.py info <input.pdf>")
        print("  python pdf_tools.py rotate <input.pdf> <output.pdf>")
        print("  python pdf_tools.py extract <input.pdf> <output.pdf> <start> <end>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "info":
        get_pdf_info(sys.argv[2])
    elif cmd == "rotate":
        rotate_pdf(sys.argv[2], sys.argv[3])
    elif cmd == "extract":
        extract_pages(sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]))
