# MCP Mail Server (FastMCP)

Microsoft Graph 메일 조회/발송 기능을 MCP 서버로 제공하는 샘플 프로젝트입니다.

## 1. 프로젝트 개요
- `FastMCP` (MCP 서버를 빠르게 구성하는 파이썬 라이브러리) 기반 서버
- Microsoft Graph API 연동으로 메일 조회/발송 도구 제공
- HTTP 레벨 + MCP 도구 레벨 로깅 분리
- `request_id` 기반 요청 추적

## 2. 주요 기능
- `search_my_emails`: 최근 메일 조회
- `search_unread_mail`: 읽지 않은 메일 조회
- `send_my_email`: 메일 발송
- `ping`: 서버 점검
- `add`: 샘플 연산 도구

## 3. 프로젝트 구조
```text
app/
  main.py                # FastMCP 서버 진입점, 도구 등록
  auth.py                # MSAL 토큰 발급
  config.py              # .env 설정 로드
  logger_config.py       # 로깅 설정(Formatter/Filter/Handler)
  http_middleware.py     # HTTP 요청 로깅 + request_id + 마스킹/요약
  mcp_midleware.py       # MCP tool 호출 단위 로깅

docs/
  CODEX_WORKFLOW_GUIDE.md
  SKILL_GUIDE.md
  CODE_GUIDE.md
  EXAMPLE_GUIDE.md
  DIAGRAM_GUIDE.md
```

## 4. 사전 준비
- Python 3.11+
- Node.js (MCP Inspector 사용 시)
- Microsoft Entra ID 앱 등록 및 Graph 권한 부여

### 필수 Graph 권한
- `Mail.Read`
- `Mail.Send`
- 관리자 동의(Grant admin consent)

### 4.1 MS Entra ID 앱 등록 상세 절차
1. Azure Portal에서 `Microsoft Entra ID`로 이동 후 `앱 등록(App registrations)` 클릭
2. `+ 새 등록(New registration)` 클릭
3. 이름 입력 (예: `FastMCP-Mail`)
4. 지원 계정 유형은 개인 환경 포함 옵션 선택
  - `모든 조직 디렉터리의 계정 및 개인 Microsoft 계정`
5. 등록 완료 후 `애플리케이션 ID(Client ID)`와 `디렉터리 ID(Tenant ID)`를 메모

### 4.2 API 권한 부여 (.default 스코프 기준)
1. 등록한 앱에서 `API 권한(API permissions)` 이동
2. `+ 권한 추가(Add a permission)` 클릭
3. `Microsoft Graph` 선택
4. `애플리케이션 권한(Application permissions)` 선택
5. `Mail.Read` 추가
6. 메일 발송 사용 시 `Mail.Send`도 추가
7. `관리자 동의 부여(Grant admin consent)` 실행

참고:
- 현재 코드(`app/auth.py`)는 아래 스코프를 사용합니다.
```python
SCOPES = ["https://graph.microsoft.com/.default"]
```
- 따라서 토큰은 위에서 승인된 애플리케이션 권한 기준으로 발급됩니다.

### 4.3 클라이언트 자격 증명(Client Secret) 생성
1. 앱 등록 화면에서 `인증서 및 비밀(Certificates & secrets)` 이동
2. `새 클라이언트 비밀(New client secret)` 생성
3. 발급 직후 `값(Value)`을 복사하여 안전한 곳에 보관
4. `.env`의 `AZURE_CLIENT_SECRET`에 설정

### 4.4 `.env`에 등록 정보 반영
아래 4개 값은 반드시 실제 테넌트 값으로 채웁니다.
```env
AZURE_CLIENT_ID=...
AZURE_TENANT_ID=...
AZURE_CLIENT_SECRET=...
DEFAULT_USER_EMAIL=...
```

## 5. 설치 및 실행
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### `.env` 예시
```env
AZURE_CLIENT_ID=...
AZURE_TENANT_ID=...
AZURE_CLIENT_SECRET=...
DEFAULT_USER_EMAIL=no-reply@company.com
LOG_LEVEL=INFO
```

### 서버 실행
```bash
./.venv/bin/python app/main.py
```

### 테스트 실행
```bash
PYTHONPATH=. ./.venv/bin/pytest -q
```

## 6. Inspector 연결
```bash
npx @modelcontextprotocol/inspector
```
- Transport Type: `streamable-http`
- URL: `http://127.0.0.1:8000/mcp`

## 7. 로깅 설계
### 7.1 HTTP 레벨 로깅
- 파일: `app/http_middleware.py`
- 기능:
1. `x-request-id` 생성/전파
2. 허용 헤더만 기록(allowlist)
3. payload 요약 기록(summary)
4. 민감 키 마스킹(masking)

### 7.2 MCP 도구 레벨 로깅
- 파일: `app/mcp_midleware.py`
- 기능:
1. 도구명
2. 실행 시간(`elapsed_ms`)
3. 성공/실패
4. 인자 키 목록

### 7.3 로그 정책
- 원문 body 전체 저장 지양
- 민감정보(`token`, `secret`, `password`, `body`) 마스킹
- 운영은 `INFO`, 분석 시에만 제한적으로 `DEBUG`

## 8. 트러블슈팅
### `GET /mcp` 404
- 원인: 기존/만료 세션 재사용
- 해결: Inspector 연결 재설정 후 재시도

### `MCPLoggingMiddleware() takes no arguments`
- 원인: 클래스 자체 등록
- 해결:
```python
mcp.add_middleware(MCPLoggingMiddleware())
```

### DEBUG 로그 과다
- 원인: 외부 라이브러리 로거까지 DEBUG 노출
- 해결: `logger_config.py`에서 `sse_starlette` 등 로거 레벨 조정

## 9. 문서 안내
- 워크플로우: `docs/CODEX_WORKFLOW_GUIDE.md`
- 개념/실수포인트: `docs/SKILL_GUIDE.md`
- 코드 흐름: `docs/CODE_GUIDE.md`
- 실행 예시: `docs/EXAMPLE_GUIDE.md`
- 다이어그램: `docs/DIAGRAM_GUIDE.md`
