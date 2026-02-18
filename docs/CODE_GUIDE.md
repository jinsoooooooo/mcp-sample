# CODE_GUIDE.md

## 주요 코드 흐름
1. `app/main.py` 시작 시 `setup_logging(LOG_LEVEL)` 호출
2. `mcp.add_middleware(MCPLoggingMiddleware())`로 MCP 미들웨어 등록
3. `mcp.run(..., middleware=[Middleware(RequestIdMiddleware)], ...)` 실행
4. HTTP 요청마다 request_id 생성/전파
5. MCP 도구 호출마다 도구명/실행시간/상태 로깅

## 파일별 역할
- `app/main.py`
  - FastMCP 서버 생성
  - 도구(`search_my_emails`, `search_unread_mail`, `send_my_email`) 등록
  - HTTP/MCP 미들웨어 연결
- `app/logger_config.py`
  - 포맷/핸들러/필터/로거 레벨 설정
  - bytes 디코딩 및 request_id 주입 필터 제공
- `app/http_middleware.py`
  - 요청 단위 추적(request_id)
  - 헤더 허용 목록 필터링
  - payload 요약 + 민감키 마스킹
- `app/mcp_midleware.py`
  - MCP 도구 호출 성공/실패/실행시간 로깅

## 로그 포맷 예시
```text
2026-02-18 21:15:48,614 | INFO | req=... | app.mcp.tool | mcp_tool_call tool=search_unread_mail status=success elapsed_ms=890.9 argument_keys=[]
```

## 코드 경로 참조
- 서버 진입: `app/main.py`
- HTTP 로깅: `app/http_middleware.py`
- MCP 로깅: `app/mcp_midleware.py`
- 로거 설정: `app/logger_config.py`
