import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import store  # noqa: E402

SAMPLE_XLSX = os.path.join(ROOT, "sampleFile", "TableDefinition_Sample.xlsx")


@pytest.fixture(autouse=True)
def temp_store(tmp_path, monkeypatch):
    """모든 테스트는 실제 tableStore 대신 임시 디렉토리를 사용"""
    store_dir = tmp_path / "tableStore"
    store_dir.mkdir()
    monkeypatch.setattr(store, "STORE_DIR", str(store_dir))
    return store_dir
