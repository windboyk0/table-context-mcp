import difflib
from typing import Any

from mcp.server.fastmcp import FastMCP

import store

# Initialize FastMCP Server
mcp = FastMCP("Table Context")


def _resolve_or_raise(table_name: str) -> str:
    """대소문자 무시로 테이블명을 찾고, 없으면 유사한 이름을 제안하는 에러를 발생."""
    resolved = store.resolve_table_name(table_name)
    if resolved:
        return resolved
    names = store.list_table_names()
    suggestions = difflib.get_close_matches(str(table_name).upper(), [n.upper() for n in names], n=5, cutoff=0.5)
    by_upper = {n.upper(): n for n in names}
    hint = f" 유사한 테이블: {', '.join(by_upper[s] for s in suggestions)}" if suggestions else ""
    raise ValueError(f"Table '{table_name}' not found.{hint} (search_tables 로 검색해 보세요)")


def _summary(schema: dict) -> dict:
    return {
        "table_name": schema.get("table_name", ""),
        "entity_name": schema.get("entity_name", ""),
        "column_count": len(schema.get("columns", [])),
    }


def _one_line(text: Any) -> str:
    return " ".join(str(text or "").split())


def _to_ddl(schema: dict) -> str:
    lines = []
    for col in schema.get("columns", []):
        parts = [f"    {col['column_name']} {col.get('data_type') or ''}".rstrip()]
        if col.get("default_value") is not None:
            parts.append(f"DEFAULT {col['default_value']}")
        if not col.get("nullable"):
            parts.append("NOT NULL")
        comment = " | ".join(x for x in [
            _one_line(col.get("attribute_name")),
            f"logical:{col['logical_type']}" if col.get("logical_type") else "",
            _one_line(col.get("description")),
        ] if x)
        lines.append((" ".join(parts), comment))
    if schema.get("pk_columns"):
        lines.append((f"    PRIMARY KEY ({', '.join(schema['pk_columns'])})", ""))

    body = []
    for i, (definition, comment) in enumerate(lines):
        sep = "," if i < len(lines) - 1 else ""
        body.append(f"{definition}{sep}" + (f"  -- {comment}" if comment else ""))
    header = f"-- {_one_line(schema.get('entity_name'))}\n" if schema.get("entity_name") else ""
    return f"{header}CREATE TABLE {schema['table_name']} (\n" + "\n".join(body) + "\n);"


@mcp.tool()
def list_tables(prefix: str = "") -> list[dict]:
    """Retrieve all available database tables with their logical (Korean) entity names.

    Args:
        prefix: Optional table name prefix filter (case-insensitive), e.g. "IESV_".
    """
    p = prefix.upper()
    return [_summary(t) for t in store.load_all_tables() if t.get("table_name", "").upper().startswith(p)]


@mcp.tool()
def search_tables(keyword: str, limit: int = 20) -> list[dict]:
    """Search tables by keyword across table name, entity name, column names, attribute names and descriptions.
    Use this first to find relevant tables for a business term (e.g. "쿠폰", "구매취소", "CUST_ID").
    Multiple space-separated keywords are combined with AND.

    Args:
        keyword: Search keyword(s), case-insensitive.
        limit: Maximum number of tables to return.
    """
    terms = [t.lower() for t in keyword.split() if t]
    if not terms:
        raise ValueError("keyword를 입력하세요.")

    results = []
    for schema in store.load_all_tables():
        table_text = f"{schema.get('table_name', '')} {schema.get('entity_name', '')} {schema.get('description', '')}".lower()
        col_texts = [
            (col, f"{col.get('column_name', '')} {col.get('attribute_name') or ''} {col.get('description') or ''}".lower())
            for col in schema.get("columns", [])
        ]
        score = 0
        matched_cols = []
        for term in terms:
            hit_table = term in table_text
            hits = [col for col, text in col_texts if term in text]
            if not hit_table and not hits:
                break
            score += (10 if hit_table else 0) + len(hits)
            matched_cols.extend(c for c in hits if c not in matched_cols)
        else:
            results.append((score, {
                **_summary(schema),
                "matched_columns": [
                    {"column_name": c["column_name"], "attribute_name": c.get("attribute_name")}
                    for c in matched_cols[:10]
                ],
            }))

    results.sort(key=lambda r: (-r[0], r[1]["table_name"]))
    return [r[1] for r in results[:max(1, limit)]]


@mcp.tool()
def find_columns(column_name: str, exact: bool = True) -> list[dict]:
    """Find all tables containing a given physical column. Useful for discovering join keys between tables.

    Args:
        column_name: Physical column name, e.g. "CUST_ID" (case-insensitive).
        exact: True for exact match, False for substring match.
    """
    target = column_name.strip().upper()
    found = []
    for schema in store.load_all_tables():
        for col in schema.get("columns", []):
            name = str(col.get("column_name", "")).upper()
            if name == target if exact else target in name:
                found.append({
                    "table_name": schema.get("table_name", ""),
                    "entity_name": schema.get("entity_name", ""),
                    "column_name": col.get("column_name"),
                    "attribute_name": col.get("attribute_name"),
                    "data_type": col.get("data_type"),
                    "is_pk": col.get("is_pk", False),
                })
    return found


@mcp.tool()
def get_table_schema(table_name: str) -> dict:
    """Retrieve the schema details for a specific table including columns, data types, and descriptions.

    Args:
        table_name: The name of the table to retrieve the schema for (e.g., USER_INFO). Case-insensitive.
    """
    return store.load_table(_resolve_or_raise(table_name))


@mcp.tool()
def get_table_schemas(table_names: list[str]) -> dict:
    """Retrieve schemas of multiple tables at once (e.g. for writing JOIN queries).

    Args:
        table_names: List of table names. Case-insensitive.

    Returns: {"tables": [schema, ...], "not_found": [name, ...]}
    """
    tables, not_found = [], []
    for name in table_names:
        resolved = store.resolve_table_name(name)
        if resolved:
            tables.append(store.load_table(resolved))
        else:
            not_found.append(name)
    return {"tables": tables, "not_found": not_found}


@mcp.tool()
def get_table_ddl(table_names: list[str]) -> str:
    """Retrieve schemas as compact CREATE TABLE DDL with column comments (fewer tokens than JSON).

    Args:
        table_names: List of table names. Case-insensitive.
    """
    return "\n\n".join(_to_ddl(store.load_table(_resolve_or_raise(name))) for name in table_names)

if __name__ == "__main__":
    # ─────────────────────────────────────────────────────────────────────────
    # [현재] stdio 방식 (Claude Desktop / Vibe 등 로컬 클라이언트용)
    # Claude Desktop claude_desktop_config.json 에서 "command"/"args" 로 프로세스 직접 실행
    # ─────────────────────────────────────────────────────────────────────────
    mcp.run()  # transport 기본값 = "stdio"

    # ─────────────────────────────────────────────────────────────────────────
    # [SSE 방식] Server-Sent Events — HTTP 기반, 원격 클라이언트 연결 가능
    #
    # 사용법:
    #   mcp.run(transport="sse", host="0.0.0.0", port=8001)
    #
    # 클라이언트 연결 엔드포인트:
    #   GET  http://<host>:8001/sse        ← 이벤트 스트림 구독
    #   POST http://<host>:8001/messages/  ← 클라이언트 → 서버 메시지 전송
    #
    # Claude Desktop 설정 예시 (claude_desktop_config.json):
    #   {
    #     "mcpServers": {
    #       "table-context": {
    #         "url": "http://localhost:8001/sse"
    #       }
    #     }
    #   }
    #
    # 장점: 원격 서버 배포 가능, 여러 클라이언트 동시 접속 가능
    # 단점: MCP SSE spec 은 Deprecated 예정 (Streamable HTTP 로 전환 권장)
    # ─────────────────────────────────────────────────────────────────────────
    # mcp.run(transport="sse", host="0.0.0.0", port=8001)

    # ─────────────────────────────────────────────────────────────────────────
    # [Streamable HTTP 방식] 최신 MCP 표준 (2025-03-26 spec) — 권장 방식
    #
    # 사용법:
    #   mcp.run(transport="streamable-http", host="0.0.0.0", port=8001)
    #
    # 클라이언트 연결 엔드포인트:
    #   POST http://<host>:8001/mcp   ← 단일 엔드포인트로 요청/스트리밍 모두 처리
    #                                    (서버가 스트리밍 필요 시 SSE 청크로 응답)
    #
    # Claude Desktop 설정 예시 (claude_desktop_config.json):
    #   {
    #     "mcpServers": {
    #       "table-context": {
    #         "url": "http://localhost:8001/mcp"
    #       }
    #     }
    #   }
    #
    # uvicorn 으로 직접 실행하는 경우:
    #   uvicorn mcp_server:mcp.streamable_http_app() --host 0.0.0.0 --port 8001
    #   (또는 stateless 모드: mcp.run(transport="streamable-http", stateless_http=True))
    #
    # 장점: SSE 와 단순 HTTP JSON 응답을 단일 엔드포인트에서 처리
    #       세션 관리 불필요한 경우 stateless_http=True 로 스케일아웃 용이
    # ─────────────────────────────────────────────────────────────────────────
    # mcp.run(transport="streamable-http", host="0.0.0.0", port=8001)
