import time
from typing import Any

from fastmcp.server.middleware.middleware import CallNext, Middleware, MiddlewareContext
from mcp.types import CallToolRequestParams

from logger_config import get_logger

logger = get_logger("app.mcp.tool")


class MCPLoggingMiddleware(Middleware):
    """
    MCP tool 호출 단위 관측 로그를 남긴다.
    """

    async def on_call_tool(
        self,
        context: MiddlewareContext[CallToolRequestParams],
        call_next: CallNext[CallToolRequestParams, Any],
    ) -> Any:
        params = context.message
        tool_name = params.name

        # 왜: 인자 원문을 남기면 민감정보 유출 위험이 있으므로 key 목록만 기록한다.
        argument_keys = list((params.arguments or {}).keys())

        started = time.perf_counter()
        try:
            result = await call_next(context)
            elapsed_ms = (time.perf_counter() - started) * 1000.0

            logger.info(
                "mcp_tool_call tool=%s status=success elapsed_ms=%.1f argument_keys=%s",
                tool_name,
                elapsed_ms,
                argument_keys,
            )
            return result
        except Exception:
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            logger.exception(
                "mcp_tool_call tool=%s status=error elapsed_ms=%.1f argument_keys=%s",
                tool_name,
                elapsed_ms,
                argument_keys,
            )
            raise
