import json

import pandas as pd
import pytest

import store
from parser import EXCEL_COLS, generate_excel, parse_excel, parse_excel_to_json
from conftest import SAMPLE_XLSX


def _row(table, column, **kw):
    row = {c: None for c in EXCEL_COLS}
    row.update({"엔티티명": f"{table} 엔티티", "테이블명": table, "컬럼명": column, "물리데이터타입": "VARCHAR2(10)"})
    row.update(kw)
    return row


def test_sample_parses_per_spec(temp_store):
    result = parse_excel_to_json(SAMPLE_XLSX)
    assert result["created"] == ["IESM_UNN_CHARGNDUP_TERMREQ_MGMT"]
    assert result["updated"] == [] and result["skipped"] == []

    schema = json.loads((temp_store / "IESM_UNN_CHARGNDUP_TERMREQ_MGMT.json").read_text(encoding="utf-8"))
    assert schema["pk_columns"] == ["CLCT_STRD_DT", "UNNPROD_PURC_NUM"]
    first = schema["columns"][0]
    assert first["column_name"] == "CLCT_STRD_DT"
    assert first["is_pk"] is True and first["nullable"] is False
    assert "logical_type" not in first  # 논리 == 물리


def test_reupload_reports_update(temp_store):
    parse_excel_to_json(SAMPLE_XLSX)
    result = parse_excel_to_json(SAMPLE_XLSX)
    assert result["created"] == [] and result["updated"] == ["IESM_UNN_CHARGNDUP_TERMREQ_MGMT"]


def test_roundtrip_excel_json_excel(tmp_path):
    schemas, _ = parse_excel(SAMPLE_XLSX)
    out = tmp_path / "out.xlsx"
    generate_excel(schemas, str(out))
    again, _ = parse_excel(str(out))
    assert again == schemas


def test_header_row_offset_multi_sheet_and_string_types(tmp_path):
    path = tmp_path / "multi.xlsx"
    sheet1 = pd.DataFrame([_row("T_ONE", "ID", PK여부="Y", Null여부="N", default값="0"),
                           _row("T_ONE", "DT", 논리데이터타입="DATE", 물리데이터타입="VARCHAR2(8)")])
    sheet2 = pd.DataFrame([_row("T_TWO", "SEQ", 물리데이터타입="NUMBER")])
    with pd.ExcelWriter(path) as w:
        pd.DataFrame([["표지"]]).to_excel(w, sheet_name="표지", index=False, header=False)
        # 제목 2행 아래에 헤더가 있는 시트
        pd.DataFrame([["테이블 정의서"], [None]]).to_excel(w, sheet_name="A", index=False, header=False)
        sheet1.to_excel(w, sheet_name="A", index=False, startrow=2)
        sheet2.to_excel(w, sheet_name="B", index=False)

    schemas, skipped = parse_excel(str(path))
    by_name = {s["table_name"]: s for s in schemas}
    assert set(by_name) == {"T_ONE", "T_TWO"} and skipped == []
    one = by_name["T_ONE"]
    assert one["pk_columns"] == ["ID"]
    assert one["columns"][0]["default_value"] == "0"  # 0.0 으로 바뀌지 않음
    assert one["columns"][1]["logical_type"] == "DATE"


def test_unsafe_table_name_is_skipped_not_written(tmp_path, temp_store):
    path = tmp_path / "evil.xlsx"
    pd.DataFrame([_row("../EVIL", "ID"), _row("OK_TABLE", "ID")]).to_excel(path, index=False)

    result = parse_excel_to_json(str(path))
    assert result["created"] == ["OK_TABLE"]
    assert [s["table_name"] for s in result["skipped"]] == ["../EVIL"]
    assert not (tmp_path / "EVIL.json").exists()


def test_missing_required_column_raises(tmp_path):
    path = tmp_path / "bad.xlsx"
    pd.DataFrame([{"테이블명": "T", "컬럼명": "C"}]).to_excel(path, index=False)
    with pytest.raises(ValueError, match="헤더 행"):
        parse_excel(str(path))


@pytest.mark.parametrize("name,ok", [
    ("USER_INFO", True), ("SCHEMA.TABLE", True), ("TBL$HIST", True), ("한글테이블", True),
    ("../x", False), ("a/b", False), ("a\\b", False), ("", False), (".hidden", False), ("A..B", False),
])
def test_table_name_validation(name, ok):
    assert store.is_valid_table_name(name) is ok
