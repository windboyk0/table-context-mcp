# Table Context MCP Server

> Excel 기반 테이블 정의서를 LLM(Claude, Vibe 등)의 지식으로 변환하는 MCP 서버

이 프로젝트는 데이터베이스 테이블 정의서(Excel)를 업로드받아 구조화된 JSON으로 관리하고, 이를 Model Context Protocol(MCP)을 통해 LLM에게 제공합니다. AI가 복잡한 업무 DB 구조를 이해하고 정확한 SQL 쿼리 작성 및 데이터 모델링을 지원합니다.

---

## 주요 기능

- **Excel ↔ JSON 양방향 변환**: 엑셀 정의서 업로드 시 테이블별 고유 JSON 파일 생성, 역방향 엑셀 내보내기도 지원
- **프리미엄 웹 UI**: Glassmorphism 디자인 대시보드에서 테이블 목록 조회 및 상세 스키마 확인
- **MCP 기반 LLM 연동**: `list_tables`, `get_table_schema` 도구를 통해 Claude/Vibe 등이 실시간으로 DB 메타데이터 참조
- **데이터 동기화**: `tableStore/` 디렉토리를 중심으로 웹 서버와 MCP 서버가 데이터 공유

## 기술 스택

- **Backend**: Python, FastAPI, MCP SDK
- **Data Processing**: Pandas, OpenPyXL
- **Frontend**: HTML5, CSS3 (Glassmorphism UI), Vanilla JS

## 프로젝트 구조

```text
table-context-mcp/
├── web_server.py      # FastAPI 기반 웹 대시보드 및 API
├── mcp_server.py      # LLM 연동을 위한 MCP 서버 (stdio 방식)
├── parser.py          # Excel ↔ JSON 변환 핵심 로직 (Core)
├── tableStore/        # 변환된 JSON 데이터 저장소
├── templates/         # 웹 UI (index.html)
└── sampleFile/        # 기준 엑셀 양식 샘플 (TableDefinition_Sample.xlsx)
```

---

## 시작하기

### 1. 가상환경 설정 및 의존성 설치

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 가상환경 활성화 (macOS / Linux)
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 웹 서버 실행

```bash
# 개발 모드 (파일 변경 시 자동 재시작)
uvicorn web_server:app --host 0.0.0.0 --port 8090 --reload

# 운영 모드
uvicorn web_server:app --host 0.0.0.0 --port 8090
```

브라우저에서 `http://localhost:8090` 접속 후 테이블 정의서를 업로드하세요.

### 3. MCP 서버 (직접 실행 시)

```bash
python mcp_server.py
```

> `mcp_server.py`는 stdio 방식으로 실행됩니다. MCP 클라이언트(Claude Desktop, Vibe 등)가 직접 프로세스를 띄우므로 별도 서버 실행은 불필요합니다.

---

## MCP 클라이언트 연결 설정

### Claude Desktop

설정 파일: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "table-context": {
      "command": "C:/본인경로/table-context-mcp/venv/Scripts/python.exe",
      "args": ["C:/본인경로/table-context-mcp/mcp_server.py"]
    }
  }
}
```

> `command`에는 반드시 **venv 내부의 python 경로**를 지정해야 의존성이 정상 로드됩니다.

연결 확인 시 아래 Tool이 노출되면 정상입니다:
- `list_tables` — 저장된 테이블 목록 조회
- `get_table_schema` — 특정 테이블의 컬럼/타입 스키마 조회

---

## JSON 출력 예시

```json
{
  "table_name": "USER_INFO",
  "entity_name": "사용자 정보 테이블",
  "pk_columns": ["USER_ID"],
  "columns": [
    {
      "column_name": "USER_ID",
      "attribute_name": "사용자ID",
      "data_type": "VARCHAR2(20)",
      "is_pk": true,
      "nullable": false,
      "description": "사용자 고유 식별자"
    }
  ]
}
```

---

Author: Kim Jeong-Ung (2026-04-03)
