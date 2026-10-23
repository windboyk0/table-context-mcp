import os
import tempfile
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.requests import Request

import store
from parser import parse_excel_to_json, generate_excel

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _validate_table_name(table_name: str) -> str:
    """table_name이 안전한 식별자인지 검증. 위반 시 400 반환."""
    if not store.is_valid_table_name(table_name):
        raise HTTPException(status_code=400, detail="Invalid table name")
    return table_name


def _require_table(table_name: str) -> str:
    _validate_table_name(table_name)
    if not store.table_exists(table_name):
        raise HTTPException(status_code=404, detail="Table not found")
    return table_name


def _new_temp_path(suffix: str) -> str:
    fd, path = tempfile.mkstemp(prefix="table_context_", suffix=suffix)
    os.close(fd)
    return path


def cleanup_file(path: str):
    if os.path.exists(path):
        os.remove(path)


def _excel_response(schemas: List[dict], filename: str, background_tasks: BackgroundTasks) -> FileResponse:
    output_excel = _new_temp_path(".xlsx")
    generate_excel(schemas, output_excel)
    background_tasks.add_task(cleanup_file, output_excel)
    return FileResponse(output_excel, filename=filename, media_type=XLSX_MEDIA_TYPE)


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/download/sample")
async def download_sample():
    sample_path = os.path.join(BASE_DIR, "sampleFile", "TableDefinition_Sample.xlsx")
    if not os.path.exists(sample_path):
        raise HTTPException(status_code=404, detail="Sample file not found")
    return FileResponse(sample_path, filename="TableDefinition_Sample.xlsx", media_type=XLSX_MEDIA_TYPE)


@app.post("/upload")
async def upload_excel(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are allowed")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"파일 크기가 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB를 초과합니다")

    temp_path = _new_temp_path(".xlsx")
    try:
        with open(temp_path, "wb") as f:
            f.write(content)
        result = parse_excel_to_json(temp_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parsing error: {e}")
    finally:
        cleanup_file(temp_path)

    return {
        "message": "Success",
        "tables": result["created"] + result["updated"],
        **result,
    }


@app.get("/api/tables")
async def get_tables():
    """테이블 요약 목록 (이름순)"""
    return [
        {
            "table_name": t.get("table_name", ""),
            "entity_name": t.get("entity_name", ""),
            "column_count": len(t.get("columns", [])),
        }
        for t in store.load_all_tables()
    ]


@app.get("/api/tables/{table_name}")
async def get_table(table_name: str):
    return store.load_table(_require_table(table_name))


@app.delete("/api/tables/all")
async def delete_all_tables():
    deleted = [name for name in store.list_table_names() if store.delete_table(name)]
    return {"deleted": deleted}


class TableListRequest(BaseModel):
    tables: List[str] = []


@app.delete("/api/tables/batch")
async def delete_batch_tables(body: TableListRequest):
    for table_name in body.tables:
        _validate_table_name(table_name)
    deleted = [name for name in body.tables if store.delete_table(name)]
    return {"deleted": deleted}


@app.delete("/api/tables/{table_name}")
async def delete_table(table_name: str):
    store.delete_table(_require_table(table_name))
    return {"deleted": table_name}


@app.get("/download/json/{table_name}")
async def download_json(table_name: str):
    _require_table(table_name)
    return FileResponse(store.table_path(table_name), filename=f"{table_name}.json", media_type="application/json")


@app.get("/download/excel/{table_name}")
async def download_excel(table_name: str, background_tasks: BackgroundTasks):
    schema = store.load_table(_require_table(table_name))
    return _excel_response([schema], f"{table_name}.xlsx", background_tasks)


@app.post("/download/excel")
async def download_excel_bulk(body: TableListRequest, background_tasks: BackgroundTasks):
    """선택한 테이블(빈 목록이면 전체)을 하나의 Excel로 다운로드"""
    if body.tables:
        schemas = [store.load_table(_require_table(name)) for name in body.tables]
        filename = "TableDefinition_selected.xlsx"
    else:
        schemas = store.load_all_tables()
        filename = "TableDefinition_all.xlsx"
    if not schemas:
        raise HTTPException(status_code=404, detail="다운로드할 테이블이 없습니다")
    return _excel_response(schemas, filename, background_tasks)
