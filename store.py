"""tableStore/ 디렉토리 접근 공용 모듈 (web_server.py, mcp_server.py, parser.py 공용).

표준 라이브러리만 사용하므로 MCP 서버 기동 시 pandas 로딩 비용이 없다.
"""
import os
import re
import json
import glob
import tempfile
from typing import Any, Dict, List, Optional

STORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tableStore")

# 영문/숫자/한글/_ 로 시작, 이후 . $ # - 허용 (예: SCHEMA.TABLE, TBL$HIST)
_TABLE_NAME_RE = re.compile(r"^[\w$#][\w$#.\-]*$")


class InvalidTableName(ValueError):
    pass


def is_valid_table_name(name: Any) -> bool:
    return (
        isinstance(name, str)
        and len(name) <= 128
        and bool(_TABLE_NAME_RE.match(name))
        and ".." not in name
    )


def validate_table_name(name: Any) -> str:
    if not is_valid_table_name(name):
        raise InvalidTableName(f"허용되지 않는 테이블명입니다: {name!r}")
    return name


def table_path(name: str) -> str:
    """검증된 테이블명의 JSON 경로. STORE_DIR 밖으로 벗어나지 않음을 보장."""
    validate_table_name(name)
    path = os.path.abspath(os.path.join(STORE_DIR, f"{name}.json"))
    if os.path.dirname(path) != os.path.abspath(STORE_DIR):
        raise InvalidTableName(f"허용되지 않는 테이블명입니다: {name!r}")
    return path


def list_table_names() -> List[str]:
    if not os.path.isdir(STORE_DIR):
        return []
    names = [os.path.basename(f)[: -len(".json")] for f in glob.glob(os.path.join(STORE_DIR, "*.json"))]
    return sorted(names)


def table_exists(name: str) -> bool:
    return os.path.exists(table_path(name))


def resolve_table_name(name: str) -> Optional[str]:
    """대소문자 무시하고 저장된 실제 테이블명을 찾는다. 없으면 None."""
    if not isinstance(name, str):
        return None
    name = name.strip()
    if is_valid_table_name(name) and table_exists(name):
        return name
    lowered = name.lower()
    for stored in list_table_names():
        if stored.lower() == lowered:
            return stored
    return None


def load_table(name: str) -> Dict[str, Any]:
    with open(table_path(name), "r", encoding="utf-8") as f:
        return json.load(f)


def load_all_tables() -> List[Dict[str, Any]]:
    tables = []
    for name in list_table_names():
        try:
            tables.append(load_table(name))
        except (OSError, ValueError):
            continue
    return tables


def save_table(schema: Dict[str, Any]) -> str:
    """테이블 JSON을 원자적으로 저장(upsert). 저장 경로 반환."""
    path = table_path(schema["table_name"])
    os.makedirs(STORE_DIR, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=STORE_DIR, prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(schema, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
    return path


def delete_table(name: str) -> bool:
    path = table_path(name)
    if not os.path.exists(path):
        return False
    os.remove(path)
    return True
