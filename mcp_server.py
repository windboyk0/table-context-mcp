import os
import glob
import json
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("Table Context")

STORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tableStore")

@mcp.tool()
def list_tables() -> list[str]:
    """Retrieve a list of all available database tables."""
    if not os.path.exists(STORE_DIR):
        return []
    files = glob.glob(os.path.join(STORE_DIR, "*.json"))
    return [os.path.basename(f).replace('.json', '') for f in files]

@mcp.tool()
def get_table_schema(table_name: str) -> dict:
    """Retrieve the schema details for a specific table including columns, data types, and descriptions.
    
    Args:
        table_name: The name of the table to retrieve the schema for (e.g., USER_INFO).
    """
    json_path = os.path.join(STORE_DIR, f"{table_name}.json")
    if not os.path.exists(json_path):
        return {"error": f"Table '{table_name}' not found."}
        
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": f"Failed to read table schema: {str(e)}"}

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
