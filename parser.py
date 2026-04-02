import os
import json
import pandas as pd
import math
from typing import Dict, List, Any

STORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tableStore")

def clean_value(val: Any) -> Any:
    """pandas NaN이나 float nan 처리를 위한 헬퍼 함수"""
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
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

def parse_excel_to_json(excel_path: str) -> List[str]:
    """Excel 파일을 파싱하여 tableStore 디렉토리에 JSON 저장 (Upsert). 저장된 테이블명 목록 반환."""
    if not os.path.exists(STORE_DIR):
        os.makedirs(STORE_DIR)
        
    df = pd.read_excel(excel_path)
    # 컬럼명이 기대와 다를 수 있으니 공백 제거
    df.columns = [str(c).strip() for c in df.columns]
    
    # 필수 컬럼 확인
    required_cols = ["테이블명", "컬럼명", "물리데이터타입"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"필수 컬럼 누락: {col}이(가) 없습니다. 현재 컬럼: {df.columns}")
            
    # 전체가 null인 행 제거
    df = df.dropna(how='all')
    
    # 테이블명 기준으로 그룹핑
    tables = df.groupby('테이블명')
    saved_tables: List[str] = []

    for table_name, group in tables:
        table_name = clean_value(table_name)
        if not table_name:
            continue
            
        columns = []
        pk_columns = []
        entity_name = None
        description = None
        
        for _, row in group.iterrows():
            col_name = clean_value(row.get('컬럼명'))
            if not col_name:
                continue
                
            attr_name = clean_value(row.get('속성명'))
            is_pk = clean_boolean_str(row.get('PK여부'), 'Y')
            nullable = clean_boolean_str(row.get('Null여부'), 'Y')
            data_type = clean_value(row.get('물리데이터타입'))
            logical_type = clean_value(row.get('논리데이터타입'))
            default_val = clean_value(row.get('default값'))
            desc = clean_value(row.get('속성설명'))
            
            # 테이블 전역 메타 정보 (첫 번째 행에서 추출 가능하다고 가정)
            if entity_name is None:
                entity_name = clean_value(row.get('엔티티명'))
            
            col_info = {
                "column_name": col_name,
                "attribute_name": attr_name,
                "data_type": data_type,
                "is_pk": is_pk,
                "nullable": nullable,
                "default_value": default_val,
                "description": desc or ""
            }
            
            if logical_type and logical_type != data_type:
                col_info["logical_type"] = logical_type
                
            columns.append(col_info)
            if is_pk:
                pk_columns.append(col_name)
                
        # 테이블 설명 - 별도 필드가 없으므로 entity_name을 그대로 사용
        table_description = entity_name or ""
            
        table_schema = {
            "table_name": table_name,
            "entity_name": entity_name or "",
            "description": table_description,
            "pk_columns": pk_columns,
            "columns": columns
        }
        
        json_path = os.path.join(STORE_DIR, f"{table_name}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(table_schema, f, ensure_ascii=False, indent=2)
        saved_tables.append(str(table_name))

    return saved_tables

def generate_excel_from_json(json_files: List[str], output_excel_path: str):
    """JSON 파일(들)을 읽어 단일 Excel 양식으로 변환 (다운로드용)"""
    rows = []
    
    for json_path in json_files:
        if not os.path.exists(json_path):
            continue
            
        with open(json_path, 'r', encoding='utf-8') as f:
            table_schema = json.load(f)
            
        table_name = table_schema.get("table_name", "")
        entity_name = table_schema.get("entity_name", "")
        
        for idx, col in enumerate(table_schema.get("columns", [])):
            logical_type = col.get("logical_type") or col.get("data_type", "")
            
            rows.append({
                "엔티티명": entity_name,
                "테이블명": table_name,
                "속성명": col.get("attribute_name", ""),
                "컬럼명": col.get("column_name", ""),
                "PK여부": "Y" if col.get("is_pk") else "",
                "Null여부": "Y" if col.get("nullable") else "N",
                "논리데이터타입": logical_type,
                "물리데이터타입": col.get("data_type", ""),
                "default값": col.get("default_value") if col.get("default_value") is not None else "",
                "속성설명": col.get("description", ""),
                "대표컬럼순서번호": idx + 1
            })
            
    df = pd.DataFrame(rows)
    # 비어있는 경우 빈 컬럼으로 데이터프레임 생성
    if df.empty:
        cols_order = ["엔티티명", "테이블명", "속성명", "컬럼명", "PK여부", "Null여부", "논리데이터타입", "물리데이터타입", "default값", "속성설명", "대표컬럼순서번호"]
        df = pd.DataFrame(columns=cols_order)
    else:
        cols_order = ["엔티티명", "테이블명", "속성명", "컬럼명", "PK여부", "Null여부", "논리데이터타입", "물리데이터타입", "default값", "속성설명", "대표컬럼순서번호"]
        final_cols = [c for c in cols_order if c in df.columns]
        for c in cols_order:
            if c not in final_cols:
                 df[c] = ""
                 final_cols.append(c)
        df = df[cols_order]
        
    df.to_excel(output_excel_path, index=False)
