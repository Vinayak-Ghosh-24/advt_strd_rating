from typing import Dict, Any
from mcp.server.fastmcp import FastMCP

# Import local evaluation helpers
from greenscore import get_input_schema as _get_schema, evaluate_named as _evaluate_named


# Name your MCP server
mcp = FastMCP("advant-standard-mcp")


@mcp.tool()
def get_input_schema() -> Dict[str, Any]:
    """Return the input schema/questions derived from advant_standard.json for the agent to ask."""
    return _get_schema()


@mcp.tool()
def evaluate_named(answers: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate results using human-readable names as keys. Missing numbers->0, booleans->false."""
    return _evaluate_named(answers)


if __name__ == "__main__":
    # Run the MCP server over stdio (recommended for local agent integration)
    mcp.run(transport="stdio")