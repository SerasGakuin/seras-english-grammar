#!/usr/bin/env python3
"""全PDFを左90度回転させてrotated/に保存"""

from pypdf import PdfReader, PdfWriter
from pathlib import Path
import sys


def rotate_pdf(input_path: Path, output_path: Path, rotation: int = -90):
    """PDFの全ページを回転させる"""
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for page in reader.pages:
        page.rotate(rotation)
        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)

    return len(reader.pages)


def main():
    base_dir = Path(__file__).parent.parent
    raw_dir = base_dir / "pdf" / "raw"
    rotated_dir = base_dir / "pdf" / "rotated"

    rotated_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = list(raw_dir.glob("*.pdf"))
    total_pages = 0

    print(f"📚 {len(pdf_files)} ファイルを回転します\n")

    for i, pdf_file in enumerate(pdf_files, 1):
        output_file = rotated_dir / pdf_file.name

        # 既に回転済みならスキップ
        if output_file.exists():
            print(f"[{i}/{len(pdf_files)}] ⏭️  {pdf_file.name} (スキップ: 既存)")
            continue

        print(f"[{i}/{len(pdf_files)}] 🔄 {pdf_file.name} ...", end=" ", flush=True)
        pages = rotate_pdf(pdf_file, output_file)
        total_pages += pages
        print(f"✓ ({pages}ページ)")

    print(f"\n✅ 完了: 合計 {total_pages} ページを回転")


if __name__ == "__main__":
    main()
