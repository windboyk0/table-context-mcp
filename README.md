# Table Context MCP Server

> Excel 기반 테이블 정의서를 LLM(Claude, Vibe 등)의 지식으로 변환하는 MCP 서버

이 프로젝트는 데이터베이스 테이블 정의서(Excel)를 업로드받아 구조화된 JSON으로 관리하고, 이를 Model Context Protocol(MCP)을 통해 LLM에게 제공합니다. 이를 통해 AI가 복잡한 업무 DB 구조를 완벽히 이해하고, 정확한 SQL 쿼리 작성이나 데이터 모델링 지원을 가능하게 합니다.

---

## 주요 기능
* Excel - JSON 양방향 변환: 엑셀 정의서를 업로드하면 테이블별 고유 JSON 파일을 생성하며, 역으로 엑셀 내보내기도 지원합니다.
* 프리미엄 웹 UI: Glassmorphism 디자인이 적용된 대시보드에서 테이블 목록 조회 및 상세 스키마를 확인할 수 있습니다.
* MCP 기반 LLM 연동: Claude, Vibe 등의 클라이언트가 list_tables, get_table_schema 도구를 통해 실시간으로 DB 메타데이터를 참조합니다.
* 데이터 동기화: tableStore/ 디렉토리를 중심으로 웹 서버와 MCP 서버가 데이터를 공유하며 최신 상태를 유지합니다.

## 기술 스택
* Backend: Python, FastAPI, MCP SDK
* Data Processing: Pandas, OpenPyXL
* Frontend: HTML5, CSS3 (Glassmorphism UI), Vanilla JS

## 프로젝트 구조
```text
table-context-mcp/
├── web_server.py      # FastAPI 기반 웹 대시보드 및 API
├── mcp_server.py      # LLM 연동을 위한 MCP 서버 (stdio 방식)
├── parser.py          # Excel-JSON 변환 핵심 로직 (Core)
├── tableStore/        # 변환된 JSON 데이터 저장소
├── templates/         # 웹 UI 리소스 (index.html)
└── sampleFile/        # 기준 엑셀 양식 샘플 (TableDefinition_Sample.xlsx)
시작하기
1. 환경 설정 및 설치
Bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
2. 웹 서버 실행 (UI 및 파일 업로드)
Bash
uvicorn web_server:app --host 0.0.0.0 --port 8000 --reload
브라우저에서 http://localhost:8000 에 접속하여 테이블 정의서를 업로드하세요.

3. MCP 클라이언트 연동 (Claude Desktop 기준)
%APPDATA%\Claude\claude_desktop_config.json 설정 파일에 아래 내용을 추가합니다.

JSON
{
  "mcpServers": {
    "table-context": {
      "command": "C:/본인경로/venv/Scripts/python.exe",
      "args": ["C:/본인경로/mcp_server.py"]
    }
  }
}
데이터 구조 (JSON Sample)
업로드된 엑셀 데이터는 아래와 같은 표준화된 구조로 변환되어 LLM에게 전달됩니다.

JSON
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

Author: Kim Jeong-woong (2026-04-03)
