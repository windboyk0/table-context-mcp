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
    mcp.run()
