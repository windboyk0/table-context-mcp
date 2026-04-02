import os
import re
import glob
import json
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from parser import parse_excel_to_json, generate_excel_from_json

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

STORE_DIR = os.path.join(BASE_DIR, "tableStore")

def _validate_table_name(table_name: str) -> str:
    """table_name이 안전한 식별자인지 검증. 위반 시 400 반환."""
    if not re.match(r'^[\w\-]+$', table_name):
        raise HTTPException(status_code=400, detail="Invalid table name")
    return table_name

def cleanup_file(path: str):
    if os.path.exists(path):
        os.remove(path)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.post("/upload")
async def upload_excel(file: UploadFile = File(...)):
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Only .xlsx files are allowed")
    
    # Save temporarily
    temp_path = f"temp_{uuid.uuid4().hex}.xlsx"
    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)
        
    try:
        saved_tables = parse_excel_to_json(temp_path)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=f"Parsing error: {str(e)}")

    if os.path.exists(temp_path):
        os.remove(temp_path)

    return {"message": "Success", "tables": saved_tables}

@app.get("/api/tables")
async def get_tables():
    if not os.path.exists(STORE_DIR):
        return []
    files = glob.glob(os.path.join(STORE_DIR, "*.json"))
    tables = [os.path.basename(f).replace('.json', '') for f in files]
    return tables

@app.get("/api/tables/{table_name}")
async def get_table(table_name: str):
    table_name = _validate_table_name(table_name)
    json_path = os.path.join(STORE_DIR, f"{table_name}.json")
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Table not found")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/download/json/{table_name}")
async def download_json(table_name: str):
    table_name = _validate_table_name(table_name)
    json_path = os.path.join(STORE_DIR, f"{table_name}.json")
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Table not found")
    return FileResponse(json_path, filename=f"{table_name}.json", media_type='application/json')

@app.get("/download/excel/{table_name}")
async def download_excel(table_name: str, background_tasks: BackgroundTasks):
    table_name = _validate_table_name(table_name)
    json_path = os.path.join(STORE_DIR, f"{table_name}.json")
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Table not found")
        
    output_excel = f"temp_{uuid.uuid4().hex}.xlsx"
    generate_excel_from_json([json_path], output_excel)
    background_tasks.add_task(cleanup_file, output_excel)
    return FileResponse(
        output_excel, 
        filename=f"{table_name}.xlsx", 
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
