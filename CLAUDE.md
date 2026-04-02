# Table Context MCP Server

## 프로젝트 개요
이 프로젝트는 데이터베이스 테이블 정의서(Excel)를 업로드받아 JSON 형식으로 구조화하여 저장하고, 이를 Model Context Protocol (MCP) 서버를 통해 제공함으로써 LLM(Claude, Vibe 등)이 업무 쿼리 작성 시 컨텍스트로 참조할 수 있도록 지원하는 시스템입니다.

## 핵심 요구사항 및 규칙

### 1. Excel 업로드 및 JSON 데이터 변환
- `sampleFile/TableDefinition_Sample.xlsx` 형식의 엑셀 파일을 업로드하면 데이터를 추출하여 JSON 포맷으로 변환 및 저장합니다.
- 생성되는 JSON 파일명은 엑셀 내 **테이블명** 필드의 값을 기준(예: `USER_INFO.json`)으로 생성합니다.
- 테이블 명을 기반으로 생성된 JSON 파일명은 서로 겹치지 않게 테이블마다 **고유하게 생성 및 관리**되어야 합니다.

### 2. UI 및 화면 제공 (HTML/CSS/Vanilla JS)
- **파일 업로드 기능**: 테이블 정의서를 쉽게 첨부할 수 있는 프리미엄 디자인의 업로드 화면을 제공합니다.
- **테이블 목록 및 상세 조회**: 변환되어 저장된 JSON 파일들의 목록 리스트를 화면에 출력하고, 클릭 시 해당 테이블의 상세 구조를 조회할 수 있습니다.
- **파일 다운로드 기능**:
  - 조회한 테이블 정보를 다시 **JSON 파일**로 다운로드할 수 있어야 합니다.
  - 조회한 테이블 정보를 역으로 **Excel 파일** 양식에 맞춰 변환하여 다운로드할 수 있어야 합니다.

### 3. MCP (Model Context Protocol) 연동 기능
- 백엔드에 연동된 LLM 클라이언트가 현재 저장된 데이터베이스 테이블 목록을 조회할 수 있는 Tool을 제공합니다. (예: `list_tables`)
- LLM이 SQL 쿼리 등을 작성하기 위해 필요한 특정 테이블의 구조(컬럼명, 데이터 타입, 설명 등)를 요청하면, 해당 스키마 정보를 반환하는 Tool을 제공합니다. (예: `get_table_schema`)

## 기술 스택 (예정)
- **백엔드/웹서버**: Python, FastAPI
- **데이터 파싱/처리**: Pandas (또는 OpenPyXL)
- **MCP 서버**: mcp SDK (Python stdio 또는 SSE 지원)
- **프론트엔드 (UI)**: 순수 HTML, CSS (Glassmorphism 등 모던 UI 적용), Vanilla JS

## 디렉토리 구조

```
table-context-mcp/
├── requirements.txt          # 필요한 패키지 (fastapi, uvicorn, mcp, pandas, openpyxl, jinja2 등)
├── web_server.py             # 화면 제공, 파일 업로드/다운로드 처리를 위한 FastAPI 서버
├── mcp_server.py             # LLM이 연동될 MCP 서버 (stdio 방식)
├── parser.py                 # Excel ↔ JSON 양방향 변환을 담당하는 핵심 로직
├── templates/
│   └── index.html            # Glassmorphism 등 프리미엄 디자인이 적용된 웹 UI 화면
├── sampleFile/
│   └── TableDefinition_Sample.xlsx   # 파서 개발의 기준이 되는 샘플 엑셀 양식
└── data/                     # 파싱된 테이블별 JSON 파일들이 저장되는 디렉토리
```

## 파일 역할 및 의존 관계

- `parser.py`가 Excel ↔ JSON 변환의 **핵심 로직을 단독으로 담당**하며, `web_server.py`와 `mcp_server.py`는 이를 import하여 사용합니다.
- `web_server.py`와 `mcp_server.py`는 서로 독립적으로 실행되며, `data/` 디렉토리를 공유합니다.

## 데이터 저장 규칙

- JSON 파일은 `data/{테이블명}.json` 경로에 저장됩니다. (예: `data/USER_INFO.json`)
- 동일한 테이블명으로 재업로드 시 기존 파일을 **덮어씁니다(upsert)**.

## JSON 출력 스펙

### 샘플 엑셀 컬럼 구조 (TableDefinition_Sample.xlsx 기준)

| 엑셀 컬럼명 | 설명 | JSON 키 |
|---|---|---|
| 엔티티명 | 테이블의 논리적 이름 | `entity_name` |
| 테이블명 | 물리 테이블명 (파일명 기준) | `table_name` |
| 속성명 | 컬럼의 논리적 이름 | `attribute_name` |
| 컬럼명 | 물리 컬럼명 | `column_name` |
| PK여부 | PK 여부 (`Y` / 공백) | `is_pk` |
| Null여부 | Null 허용 여부 (`Y` / `N`) | `nullable` |
| 논리데이터타입 | 논리 타입 (예: `VARCHAR2(8)`) | `logical_type` |
| 물리데이터타입 | 물리 타입 (예: `VARCHAR2(8)`) | `physical_type` |
| default값 | 기본값 (없으면 `null`) | `default_value` |
| 속성설명 | 컬럼 상세 설명 | `description` |
| 대표컬럼순서번호 | 컬럼 순서 (정수) | `order` |

### JSON 파일 구조 예시

```json
{
  "table_name": "IESM_UNN_CHARGNDUP_TERMREQ_MGMT",
  "entity_name": "OTT상품구매취소청구이력 테이블",
  "description": "OTT 상품 구매 취소 및 청구 이력을 관리하는 테이블",
  "pk_columns": ["CLCT_STRD_DT", "UNNPROD_PURC_NUM"],
  "columns": [
    {
      "column_name": "CLCT_STRD_DT",
      "attribute_name": "수집기준일",
      "data_type": "VARCHAR2(8)",
      "is_pk": true,
      "nullable": false,
      "default_value": null,
      "description": "수집기준일자 설명..."
    },
    {
      "column_name": "UNNPROD_PURC_NUM",
      "attribute_name": "OTT상품구매번호",
      "data_type": "NUMBER",
      "is_pk": true,
      "nullable": false,
      "default_value": null,
      "description": "OTT상품구매번호 설명..."
    },
    {
      "column_name": "UNNPROD_PURC_DT",
      "attribute_name": "OTT상품구매일자",
      "data_type": "VARCHAR2(8)",
      "logical_type": "DATE",
      "is_pk": false,
      "nullable": false,
      "default_value": null,
      "description": "OTT상품구매일자 설명..."
    }
  ]
}
```

> `logical_type`과 `physical_type`이 **다를 경우에만** `logical_type` 필드를 추가합니다. 동일한 경우 `data_type` 하나만 사용합니다.

### 파싱 규칙
- `PK여부` 값이 `"Y"`이면 `is_pk: true`, 그 외(공백/null)는 `false`로 변환합니다.
- `Null여부` 값이 `"Y"`이면 `nullable: true`, `"N"`이면 `false`로 변환합니다.
- `물리데이터타입` 값을 `data_type`으로 사용하며, `논리데이터타입`과 다를 경우에만 `logical_type`을 추가합니다.
- `pk_columns`는 `is_pk: true`인 컬럼의 `column_name`을 순서대로 모아 최상단에 요약합니다.
- `description`(테이블 설명)은 엑셀에 별도 필드가 없을 경우 `entity_name`을 기반으로 생성하거나 빈 문자열로 둡니다.
- 컬럼 배열의 순서가 곧 컬럼 순서이므로 별도 `order` 필드는 사용하지 않습니다.
- 모든 컬럼이 null인 행은 빈 행으로 간주하여 파싱에서 제외합니다.
- 하나의 엑셀 파일에 여러 테이블이 존재할 경우 `테이블명` 기준으로 그룹핑하여 **테이블별로 별도의 JSON 파일**을 생성합니다.

## 개발 순서

1. `sampleFile/TableDefinition_Sample.xlsx`의 구조를 먼저 분석하여 파싱 기준을 확인합니다.
2. `parser.py` 개발 (Excel → JSON, JSON → Excel 양방향 변환).
3. `web_server.py` 및 `templates/index.html` 개발.
4. `mcp_server.py` 개발 및 LLM 클라이언트 연결 테스트.

## 실행 커맨드

### 의존성 설치
```bash
pip install -r requirements.txt
```

### 웹 서버 실행
```bash
# 개발 모드 (파일 변경 시 자동 재시작)
uvicorn web_server:app --host 0.0.0.0 --port 8000 --reload

# 운영 모드
uvicorn web_server:app --host 0.0.0.0 --port 8000
```
- 웹 UI 접근 URL: `http://localhost:8000`

### MCP 서버 실행 (직접 실행 시)
```bash
python mcp_server.py
```
- `mcp_server.py`는 **stdio 방식**으로 실행됩니다.
- Claude Desktop, Cursor 등 MCP 클라이언트에서 아래와 같이 설정합니다:

```json
{
  "mcpServers": {
    "table-context": {
      "command": "python",
      "args": ["C:/path/to/table-context-mcp/mcp_server.py"]
    }
  }
}
```
