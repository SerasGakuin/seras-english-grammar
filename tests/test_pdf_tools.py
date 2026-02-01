"""pdf_tools.py のテスト"""

import json
import pytest
from pathlib import Path


class TestPdfInfo:
    """info コマンドのテスト"""

    def test_info_returns_page_count(self, sample_pdf):
        """ページ数を正しく返す"""
        from scripts.pdf_tools import pdf_info

        result = pdf_info(sample_pdf)
        assert result["pages"] == 2

    def test_info_returns_file_name(self, sample_pdf):
        """ファイル名を返す"""
        from scripts.pdf_tools import pdf_info

        result = pdf_info(sample_pdf)
        assert result["file"] == "sample.pdf"

    def test_info_returns_page_size(self, sample_pdf):
        """ページサイズを返す"""
        from scripts.pdf_tools import pdf_info

        result = pdf_info(sample_pdf)
        assert "width" in result["page_size"]
        assert "height" in result["page_size"]

    def test_info_detects_orientation(self, sample_pdf):
        """向き（portrait/landscape）を検出"""
        from scripts.pdf_tools import pdf_info

        result = pdf_info(sample_pdf)
        assert result["orientation"] in ["portrait", "landscape"]

    def test_info_all_pdfs_in_directory(self, pdf_raw_dir):
        """ディレクトリ内の全PDFの情報を取得"""
        from scripts.pdf_tools import pdf_info_all

        results = pdf_info_all(pdf_raw_dir)
        assert len(results) >= 1
        assert all("pages" in r for r in results)

    def test_info_nonexistent_file_raises(self, tmp_output):
        """存在しないファイルでエラー"""
        from scripts.pdf_tools import pdf_info

        with pytest.raises(FileNotFoundError):
            pdf_info(tmp_output / "nonexistent.pdf")


class TestPdfToImages:
    """to-images コマンドのテスト"""

    def test_to_images_creates_files(self, sample_pdf, tmp_output):
        """画像ファイルを作成する"""
        from scripts.pdf_tools import pdf_to_images

        pdf_to_images(sample_pdf, tmp_output, dpi=72)
        assert (tmp_output / "page_001.png").exists()
        assert (tmp_output / "page_002.png").exists()

    def test_to_images_naming_convention(self, sample_pdf, tmp_output):
        """命名規則 page_{:03d}.png に従う"""
        from scripts.pdf_tools import pdf_to_images

        pdf_to_images(sample_pdf, tmp_output, dpi=72)
        files = sorted(tmp_output.glob("*.png"))
        assert files[0].name == "page_001.png"
        assert files[1].name == "page_002.png"

    def test_to_images_with_range(self, sample_pdf, tmp_output):
        """ページ範囲指定で一部のみ変換"""
        from scripts.pdf_tools import pdf_to_images

        pdf_to_images(sample_pdf, tmp_output, dpi=72, page_range="1-1")
        assert (tmp_output / "page_001.png").exists()
        assert not (tmp_output / "page_002.png").exists()

    def test_to_images_returns_file_list(self, sample_pdf, tmp_output):
        """作成したファイルのリストを返す"""
        from scripts.pdf_tools import pdf_to_images

        result = pdf_to_images(sample_pdf, tmp_output, dpi=72)
        assert len(result) == 2
        assert all(Path(f).exists() for f in result)


class TestPdfSplit:
    """split コマンドのテスト"""

    def test_split_creates_pdf_files(self, sample_pdf, tmp_output):
        """分割したPDFファイルを作成"""
        from scripts.pdf_tools import pdf_split

        pdf_split(sample_pdf, tmp_output, ranges=["1-1", "2-2"])
        assert (tmp_output / "part_001.pdf").exists()
        assert (tmp_output / "part_002.pdf").exists()

    def test_split_with_custom_names(self, sample_pdf, tmp_output):
        """カスタム名で分割"""
        from scripts.pdf_tools import pdf_split

        pdf_split(
            sample_pdf,
            tmp_output,
            ranges=["1-1", "2-2"],
            names=["chapter_01", "chapter_02"]
        )
        assert (tmp_output / "chapter_01.pdf").exists()
        assert (tmp_output / "chapter_02.pdf").exists()

    def test_split_preserves_page_count(self, sample_pdf, tmp_output):
        """分割後のページ数が正しい"""
        from scripts.pdf_tools import pdf_split, pdf_info

        pdf_split(sample_pdf, tmp_output, ranges=["1-1", "2-2"])

        part1 = pdf_info(tmp_output / "part_001.pdf")
        part2 = pdf_info(tmp_output / "part_002.pdf")

        assert part1["pages"] == 1
        assert part2["pages"] == 1


class TestPageMap:
    """page-map コマンドのテスト"""

    def test_page_map_returns_structure(self, project_root):
        """マッピング構造を返す"""
        from scripts.pdf_tools import generate_page_map

        result = generate_page_map("核心", project_root / "pdf" / "raw")

        assert result["book"] == "核心"
        assert "files" in result
        assert "total_book_pages" in result

    def test_page_map_calculates_total_pages(self, project_root):
        """総ページ数を計算"""
        from scripts.pdf_tools import generate_page_map

        result = generate_page_map("核心", project_root / "pdf" / "raw")

        # 核心: 前半186 + 後半150 = 336
        assert result["total_book_pages"] == 336

    def test_page_map_includes_book_pages(self, project_root):
        """各ファイルにbook_pagesを含む"""
        from scripts.pdf_tools import generate_page_map

        result = generate_page_map("核心", project_root / "pdf" / "raw")

        for file_info in result["files"]:
            assert "book_start" in file_info
            assert "book_end" in file_info
