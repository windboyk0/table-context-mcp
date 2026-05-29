---
author: Kim Jeong-woong
date: 2026-04-03
description: MCP(Model Context Protocol) Server Implementation & Table Context Guide
status: In Progress
---

# Table Context MCP Server 구현 계획

데이터베이스 테이블 정의서(Excel)를 업로드받아 JSON으로 저장하고, 이를 LLM(Claude, Vibe 등)에서 참조할 수 있도록 제공하는 Model Context Protocol (MCP) 서버 구현 계획입니다.

## 아키텍처 개요

본 프로젝트는 두 가지 주요 기능을 수행해야 하므로, 다음과 같이 구성합니다 (단일 Python 풀스택).

1. **Web UI 및 파싱 서버 (FastAPI)**
   - 사용자가 브라우저 화면에서 Excel 파일을 업로드할 수 있는 웹 페이지 제공
   - 업로드된 Excel 파일을 파싱하여 테이블별로 `JSON` 파일로 변환 후 로컬 디렉토리(`tableStore/`)에 저장
   - 저장된 JSON들을 조회하고, 다시 엑셀이나 JSON으로 다운로드하는 기능 포함
2. **MCP 서버 (mcp SDK)**
   - LLM 클라이언트(Claude Desktop, Cursor, Vibe 등)가 연결하여 쿼리 작성에 필요한 Context(테이블 정보)를 요청할 수 있도록 Tool 제공
   - 저장된 `JSON` 파일들을 읽어 LLM에게 구조화된 형태로 제공

## 예상 디렉토리 구조

```text
table-context-mcp/
├── requirements.txt      # 필요한 패키지 (fastapi, uvicorn, mcp, pandas, openpyxl, jinja2 등)
├── web_server.py         # 화면 제공, 파일 업로드/다운로드 처리를 위한 FastAPI 서버
├── mcp_server.py         # LLM이 연동될 MCP 서버 (stdio 방식)
├── parser.py             # Excel <-> JSON 양방향 변환을 담당하는 핵심 로직
├── templates/
│   └── index.html        # Glassmorphism 등 프리미엄 디자인이 적용된 웹 UI 화면
├── sampleFile/
│   └── TableDefinition_Sample.xlsx   # 테스트 기준이 될 샘플 엑셀 양식
└── tableStore/                 # 파싱된 테이블별 고유 JSON 파일들이 저장될 디렉토리
```

## 주요 기능 구현 Flow

### 1. 웹 파트 (UI & FastAPI)
- 브라우저를 통해 `http://localhost:8000` 접근
- 드래그 앤 드롭 및 클릭으로 `TableDefinition_Sample.xlsx` 형식 파일 폼 전송
- 서버는 pandas로 이를 파싱하여 테이블명(`테이블명` 필드 기준)을 추출하고 `tableStore/{테이블명}.json` 파일로 각각 고유하게 저장
- 저장 완료 후, 현재 시스템에 보관된 테이블 목록(JSON 리스트)을 화면에 표시
- 리스트 내부에서 원할 경우 해당 항목을 다시 `.json` 파일 또는 `.xlsx` 파일로 사용자 PC에 다운로드

### 2. MCP Server 연동 기능
- 백엔드에서 LLM을 위해 호출될 Tool 함수들을 제공:
  - `list_tables()` : `tableStore/` 폴더 내에 저장된 모든 테이블 목록 반환
  - `get_table_schema(table_name)` : 특정 테이블의 상세 컬럼 및 타입 정보 스키마 반환

## 작업 현황 (Task)

- [x] 샘플 엑셀 파일 준비 (`sampleFile/TableDefinition_Sample.xlsx` 존재)
- [x] 엑셀 컬럼 구조 분석 및 파싱 스펙 확정 (CLAUDE.md에 문서화)
- [ ] `parser.py` 개발 (Excel → JSON, JSON → Excel 양방향 변환)
- [ ] `web_server.py` 및 `templates/index.html` 개발
- [ ] `mcp_server.py` 개발 및 LLM 클라이언트 연결 테스트
