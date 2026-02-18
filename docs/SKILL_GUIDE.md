# SKILL_GUIDE.md

## 핵심 개념
- `Logger`: 로그를 남기는 객체
- `Handler`: 로그 출력 대상(콘솔/파일)
- `Formatter`: 로그 출력 형식
- `Filter`: 로그 레코드 보정 규칙
- `ContextVar`: 비동기 요청 단위 상태 저장소

## 사용 패턴
1. 서버 시작 시 `setup_logging()`을 1회 실행한다.
2. HTTP 요청은 `RequestIdMiddleware`에서 추적한다.
3. MCP 도구 호출은 `MCPLoggingMiddleware`에서 추적한다.
4. 민감정보는 허용 목록 + 마스킹 정책으로 통제한다.

## 실수 포인트
- `mcp.add_middleware(MCPLoggingMiddleware)`처럼 클래스만 전달하는 실수
- `%(request_id)s` 포맷 사용 후 필터 미연결
- 전역 DEBUG 사용으로 외부 라이브러리 로그 폭주
- body 원문 로그 저장으로 개인정보 노출 위험 증가

## 로깅 레벨 운영 가이드
- 개발 기본: `LOG_LEVEL=INFO`
- 국소 디버깅: `LOG_LEVEL=DEBUG`
- 운영 권장: INFO 이상 + 특정 로거만 세밀 조정

## 체크리스트
- request_id가 요청 단위로 정상 변경되는가
- headers/payload 로그가 마스킹 규칙을 지키는가
- tool 호출 성공/실패 로그가 분리되는가
