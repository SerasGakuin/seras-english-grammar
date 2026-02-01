"""pytest共通fixture"""

import sys
from pathlib import Path

# scriptsディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


@pytest.fixture
def project_root() -> Path:
    """プロジェクトルートディレクトリ"""
    return Path(__file__).parent.parent


@pytest.fixture
def fixtures_dir() -> Path:
    """テストフィクスチャディレクトリ"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_pdf(fixtures_dir) -> Path:
    """テスト用サンプルPDF（2ページ）"""
    return fixtures_dir / "sample.pdf"


@pytest.fixture
def pdf_raw_dir(project_root) -> Path:
    """元PDFディレクトリ"""
    return project_root / "pdf" / "raw"


@pytest.fixture
def tmp_output(tmp_path) -> Path:
    """一時出力ディレクトリ"""
    return tmp_path
