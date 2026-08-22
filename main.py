from mcp.server import Server, ServerRequestContext
from mcp.types import ListToolsResult, PaginatedRequestParams, Tool

# 1. Define your tool schemas
MY_TOOL = Tool(
    name="my_tool",
    description="Does a helpful thing.",
    input_schema={
        "type": "object",
        "properties": {"param": {"type": "string"}},
        "required": ["param"],
    },
)

# 2. Write standard async functions without decorators
async def list_tools(ctx: ServerRequestContext, params: PaginatedRequestParams | None) -> ListToolsResult:
    return ListToolsResult(tools=[MY_TOOL])

# 3. Pass the functions into the Server constructor
mcp = Server(
    "MyServer", 
    on_list_tools=list_tools,
    # on_call_tool=call_tool  <-- Don't forget to attach your call_tool handler here too!
)
