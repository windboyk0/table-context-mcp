import json
import math
import os
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

import store
from store import STORE_DIR  # noqa: F401  (기존 import 호환)

REQUIRED_COLS = ["테이블명", "컬럼명", "물리데이터타입"]
EXCEL_COLS = ["엔티티명", "테이블명", "속성명", "컬럼명", "PK여부", "Null여부", "논리데이터타입", "물리데이터타입", "default값", "속성설명", "대표컬럼순서번호"]
# 헤더 행 탐색 범위 (표지/제목 행이 위에 있는 양식 대응)
HEADER_SCAN_ROWS = 30


def clean_value(val: Any) -> Any:
    """pandas NaN / 공백 문자열을 None으로 정규화"""
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return None
    return val


def clean_boolean_str(val: Any, true_val="Y") -> bool:
    clean = clean_value(val)
    if clean is None:
        return False
    return str(clean).upper() == true_val


def _find_header_row(raw: pd.DataFrame) -> Optional[int]:
    for idx in range(min(HEADER_SCAN_ROWS, len(raw))):
        cells = {str(v).strip() for v in raw.iloc[idx].tolist() if clean_value(v) is not None}
        if all(col in cells for col in REQUIRED_COLS):
            return idx
    return None


def _read_definition_sheets(excel_path: str) -> List[pd.DataFrame]:
    """모든 시트를 읽어 헤더 행을 찾은 DataFrame 목록 반환. 정의서 형식이 아닌 시트는 건너뜀."""
    # dtype=str: default값 '0'이 0.0으로 바뀌는 등 숫자 변환을 막는다
    sheets = pd.read_excel(excel_path, sheet_name=None, header=None, dtype=str)
    frames = []
    for raw in sheets.values():
        header_idx = _find_header_row(raw)
        if header_idx is None:
            continue
        df = raw.iloc[header_idx + 1:].copy()
        df.columns = [str(c).strip() if clean_value(c) is not None else f"_unnamed_{i}"
                      for i, c in enumerate(raw.iloc[header_idx].tolist())]
        frames.append(df.dropna(how="all"))
    if not frames:
        raise ValueError(f"필수 컬럼({', '.join(REQUIRED_COLS)})을 포함한 헤더 행을 찾지 못했습니다. "
                         f"시트 목록: {list(sheets.keys())}")
    return frames


def parse_excel(excel_path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """Excel을 테이블별 스키마 dict 목록으로 변환 (저장하지 않음).

    Returns: (schemas, skipped) — skipped는 [{"table_name", "reason"}]
    """
    rows_by_table: Dict[str, List[pd.Series]] = {}
    for df in _read_definition_sheets(excel_path):
        for _, row in df.iterrows():
            table_name = clean_value(row.get("테이블명"))
            if table_name is None:
                continue
            rows_by_table.setdefault(str(table_name), []).append(row)

    schemas: List[Dict[str, Any]] = []
    skipped: List[Dict[str, str]] = []

    for table_name, rows in rows_by_table.items():
        if not store.is_valid_table_name(table_name):
            skipped.append({"table_name": table_name, "reason": "허용되지 않는 테이블명 (영문/숫자/한글/_ . $ # - 만 가능)"})
            continue

        columns = []
        pk_columns = []
        entity_name = None
        seen_columns = set()

        for row in rows:
            col_name = clean_value(row.get("컬럼명"))
            if not col_name or col_name in seen_columns:
                continue
            seen_columns.add(col_name)

            is_pk = clean_boolean_str(row.get("PK여부"), "Y")
            data_type = clean_value(row.get("물리데이터타입"))
            logical_type = clean_value(row.get("논리데이터타입"))

            if entity_name is None:
                entity_name = clean_value(row.get("엔티티명"))

            col_info = {
                "column_name": col_name,
                "attribute_name": clean_value(row.get("속성명")),
                "data_type": data_type,
                "is_pk": is_pk,
                "nullable": clean_boolean_str(row.get("Null여부"), "Y"),
                "default_value": clean_value(row.get("default값")),
                "description": clean_value(row.get("속성설명")) or "",
            }
            if logical_type and logical_type != data_type:
                col_info["logical_type"] = logical_type

            columns.append(col_info)
            if is_pk:
                pk_columns.append(col_name)

        if not columns:
            skipped.append({"table_name": table_name, "reason": "유효한 컬럼이 없음"})
            continue

        schemas.append({
            "table_name": table_name,
            "entity_name": entity_name or "",
            # 테이블 설명 - 별도 필드가 없으므로 entity_name을 그대로 사용
            "description": entity_name or "",
            "pk_columns": pk_columns,
            "columns": columns,
        })

    return schemas, skipped


def parse_excel_to_json(excel_path: str) -> Dict[str, Any]:
    """Excel을 파싱하여 tableStore에 테이블별 JSON 저장 (Upsert).

    Returns: {"created": [...], "updated": [...], "skipped": [{"table_name", "reason"}]}
    """
    schemas, skipped = parse_excel(excel_path)
    created, updated = [], []
    for schema in schemas:
        existed = store.table_exists(schema["table_name"])
        store.save_table(schema)
        (updated if existed else created).append(schema["table_name"])
    return {"created": created, "updated": updated, "skipped": skipped}


def generate_excel(schemas: List[Dict[str, Any]], output_excel_path: str):
    """스키마 dict 목록을 단일 Excel 양식으로 변환 (다운로드용)"""
    rows = []
    for table_schema in schemas:
        table_name = table_schema.get("table_name", "")
        entity_name = table_schema.get("entity_name", "")
        for idx, col in enumerate(table_schema.get("columns", [])):
            rows.append({
                "엔티티명": entity_name,
                "테이블명": table_name,
                "속성명": col.get("attribute_name") or "",
                "컬럼명": col.get("column_name", ""),
                "PK여부": "Y" if col.get("is_pk") else "",
                "Null여부": "Y" if col.get("nullable") else "N",
                "논리데이터타입": col.get("logical_type") or col.get("data_type") or "",
                "물리데이터타입": col.get("data_type") or "",
                "default값": col.get("default_value") if col.get("default_value") is not None else "",
                "속성설명": col.get("description") or "",
                "대표컬럼순서번호": idx + 1,
            })

    df = pd.DataFrame(rows, columns=EXCEL_COLS)
    with pd.ExcelWriter(output_excel_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="테이블정의서")
        ws = writer.sheets["테이블정의서"]
        widths = {"엔티티명": 30, "테이블명": 32, "속성명": 22, "컬럼명": 28, "논리데이터타입": 16,
                  "물리데이터타입": 16, "default값": 12, "속성설명": 60}
        for i, col in enumerate(EXCEL_COLS, start=1):
            ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = widths.get(col, 10)
        ws.freeze_panes = "A2"


def generate_excel_from_json(json_files: List[str], output_excel_path: str):
    """JSON 파일(들)을 읽어 단일 Excel 양식으로 변환 (다운로드용)"""
    schemas = []
    for json_path in json_files:
        if not os.path.exists(json_path):
            continue
        with open(json_path, "r", encoding="utf-8") as f:
            schemas.append(json.load(f))
    generate_excel(schemas, output_excel_path)
