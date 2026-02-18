# EXAMPLE_GUIDE.md

## 전제조건
- Python 3.11+
- `.venv` 준비
- `.env` 설정 완료
- `LOG_LEVEL` 환경변수 설정 가능

## 예시 1: 서버 실행
```bash
LOG_LEVEL=INFO ./.venv/bin/python app/main.py
```
기대 결과:
- 서버 시작 로그 출력
- `/mcp` 요청 시 `app.http` 로그 출력

## 예시 2: 디버그 실행
```bash
LOG_LEVEL=DEBUG ./.venv/bin/python app/main.py
```
기대 결과:
- `app.main`, `app.http`, `app.mcp.tool` 로그 확인
- `request_id`가 요청 단위로 변경

## 예시 3: Inspector 연결
```bash
npx @modelcontextprotocol/inspector
```
연결 설정:
- Transport Type: `streamable-http`
- URL: `http://127.0.0.1:8000/mcp`

기대 결과:
- `search_unread_mail` 호출 시 `app.mcp.tool` 로그 생성

## 실패 예시 + 해결
실패:
- `MCPLoggingMiddleware() takes no arguments`

원인:
- 클래스 자체를 전달함

해결:
```python
mcp.add_middleware(MCPLoggingMiddleware())
```

## 검증 명령
```bash
PYTHONPATH=. ./.venv/bin/pytest -q
```
성공 기준:
- 테스트가 실패 없이 완료
