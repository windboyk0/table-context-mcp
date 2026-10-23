import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import mcp_server
from parser import parse_excel_to_json
from web_server import app
from conftest import SAMPLE_XLSX

TABLE = "IESM_UNN_CHARGNDUP_TERMREQ_MGMT"


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def loaded():
    parse_excel_to_json(SAMPLE_XLSX)


# ---------------- web_server ----------------

def test_upload_and_list(client):
    with open(SAMPLE_XLSX, "rb") as f:
        res = client.post("/upload", files={"file": ("Sample.XLSX", f)})
    assert res.status_code == 200
    assert res.json()["created"] == [TABLE]

    tables = client.get("/api/tables").json()
    assert tables == [{"table_name": TABLE, "entity_name": tables[0]["entity_name"], "column_count": 3}]


def test_upload_invalid_format_is_400(client):
    buf = io.BytesIO()
    pd.DataFrame([{"foo": 1}]).to_excel(buf, index=False)
    res = client.post("/upload", files={"file": ("bad.xlsx", buf.getvalue())})
    assert res.status_code == 400


def test_upload_rejects_non_xlsx(client):
    res = client.post("/upload", files={"file": ("a.csv", b"x")})
    assert res.status_code == 400


def test_bulk_excel_download(client, loaded):
    res = client.post("/download/excel", json={"tables": []})
    assert res.status_code == 200
    df = pd.read_excel(io.BytesIO(res.content))
    assert set(df["테이블명"]) == {TABLE}


def test_unknown_and_invalid_names(client):
    assert client.get("/api/tables/NOPE").status_code == 404
    assert client.get("/api/tables/..%2F..%2Fx").status_code in (400, 404)
    assert client.request("DELETE", "/api/tables/batch", json={"tables": ["../x"]}).status_code == 400


# ---------------- mcp_server ----------------

def test_mcp_list_and_search(loaded):
    assert [t["table_name"] for t in mcp_server.list_tables()] == [TABLE]
    assert mcp_server.list_tables("XXX") == []
    hits = mcp_server.search_tables("구매번호")
    assert hits[0]["table_name"] == TABLE
    assert any(c["column_name"] == "UNNPROD_PURC_NUM" for c in hits[0]["matched_columns"])


def test_mcp_case_insensitive_and_suggestion(loaded):
    assert mcp_server.get_table_schema(TABLE.lower())["table_name"] == TABLE
    with pytest.raises(ValueError, match=TABLE):
        mcp_server.get_table_schema(TABLE[:-1])
    with pytest.raises(ValueError):
        mcp_server.get_table_schema("../../etc")


def test_mcp_find_columns_and_multi(loaded):
    found = mcp_server.find_columns("unnprod_purc_num")
    assert found[0]["table_name"] == TABLE and found[0]["is_pk"] is True
    multi = mcp_server.get_table_schemas([TABLE, "NOPE"])
    assert len(multi["tables"]) == 1 and multi["not_found"] == ["NOPE"]


def test_mcp_ddl(loaded):
    ddl = mcp_server.get_table_ddl([TABLE])
    assert ddl.splitlines()[1] == f"CREATE TABLE {TABLE} ("
    assert "PRIMARY KEY (CLCT_STRD_DT, UNNPROD_PURC_NUM)" in ddl
