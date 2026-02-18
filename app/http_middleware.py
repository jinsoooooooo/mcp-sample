import json
import time
from typing import Any
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from logger_config import clear_request_id, get_logger, set_request_id

logger = get_logger("app.http")

# 운영 로그에서 안전하게 남겨도 되는 헤더만 허용한다.
# 이유: 전체 헤더를 저장하면 인증/쿠키 정보가 유출될 수 있다.
ALLOWED_HEADER_KEYS = {
    "user-agent",
    "content-type",
    "content-length",
    "x-request-id",
    "mcp-session-id",
}

# 키 이름에 아래 단어가 포함되면 민감 데이터로 간주해 마스킹한다.
# 이유: 호출부가 늘어날수록 실수로 민감값을 로그에 남길 위험이 커진다.
SENSITIVE_KEY_HINTS = {
    "authorization",
    "cookie",
    "token",
    "secret",
    "password",
    "body",
    "my_email",
    "to_address",
    "cc_address",
}

# 과도한 본문 로그로 성능/비용/보안 리스크가 커지는 것을 막기 위한 상한선.
MAX_BODY_LOG_BYTES = 4096


def _is_sensitive_key(key: str) -> bool:
    key_lower = key.lower()
    return any(hint in key_lower for hint in SENSITIVE_KEY_HINTS)


def _mask_value_by_key(key: str, value: Any) -> Any:
    # 이유: 중첩된 dict/list 구조에서도 민감 정보가 새지 않도록 재귀 마스킹한다.
    if _is_sensitive_key(key):
        return "***masked***"

    if isinstance(value, dict):
        return {k: _mask_value_by_key(k, v) for k, v in value.items()}

    if isinstance(value, list):
        return [_mask_value_by_key(key, item) for item in value]

    return value


def _extract_allowed_headers(headers: Headers) -> dict[str, str]:
    # 이유: 허용 목록 기반으로만 기록해 예기치 않은 민감 헤더 유출을 차단한다.
    result: dict[str, str] = {}
    for key, value in headers.items():
        lower_key = key.lower()
        if lower_key in ALLOWED_HEADER_KEYS:
            result[lower_key] = "***masked***" if _is_sensitive_key(lower_key) else value
    return result


def _summarize_payload(raw_body: bytes, content_type: str | None) -> dict[str, Any]:
    # 이유: 원문 저장 대신 요약 정보를 남겨 디버깅 가능성과 보안 사이 균형을 맞춘다.
    summary: dict[str, Any] = {"body_size": len(raw_body)}

    if not raw_body:
        return summary

    if len(raw_body) > MAX_BODY_LOG_BYTES:
        summary["body_preview"] = "omitted_too_large"
        return summary

    if content_type and "application/json" in content_type.lower():
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:
            summary["body_preview"] = "invalid_json"
            return summary

        if isinstance(payload, dict):
            summary["json_keys"] = list(payload.keys())
            summary["rpc_method"] = payload.get("method")
            summary["rpc_id"] = payload.get("id")

            params = payload.get("params")
            if isinstance(params, dict):
                summary["params_keys"] = list(params.keys())
                summary["tool_name"] = params.get("name")
                arguments = params.get("arguments")
                if isinstance(arguments, dict):
                    summary["arguments"] = _mask_value_by_key("arguments", arguments)
            return summary

    # JSON이 아니면 일부 미리보기만 남긴다(전체 원문 저장 방지).
    summary["body_preview"] = raw_body[:200].decode("utf-8", errors="replace")
    return summary


class RequestIdMiddleware:
    """
    요청 단위 request_id를 관리하고, 안전한 HTTP 요청 로그를 남긴다.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # HTTP 요청이 아니면 건드리지 않는다.
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)

        # 외부에서 전달한 x-request-id가 있으면 추적 연속성을 위해 재사용한다.
        # 없으면 서버에서 새로 생성한다.
        request_id = headers.get("x-request-id") or uuid4().hex

        method = scope.get("method", "-")
        path = scope.get("path", "-")
        client = scope.get("client")
        client_ip = client[0] if client else "-"

        started = time.perf_counter()
        status_code = 500
        body_chunks: list[bytes] = []

        async def receive_wrapper() -> Message:
            # 이유: ASGI 본문은 한 번만 읽을 수 있으므로,
            # 원본 흐름을 유지하면서 복사본만 로그 요약용으로 수집한다.
            message = await receive()
            if message["type"] == "http.request":
                body_chunks.append(message.get("body", b""))
            return message

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                # 이유: 클라이언트와 서버 양쪽에서 동일 request_id를 추적하도록 응답 헤더에 넣는다.
                response_headers = MutableHeaders(raw=message["headers"])
                response_headers["x-request-id"] = request_id
            await send(message)

        set_request_id(request_id)
        try:
            await self.app(scope, receive_wrapper, send_wrapper)
        except Exception:
            logger.exception(
                "http_request_failed method=%s path=%s client_ip=%s",
                method,
                path,
                client_ip,
            )
            raise
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            raw_body = b"".join(body_chunks)

            logger.info(
                "http_request method=%s path=%s status=%s elapsed_ms=%.1f client_ip=%s headers=%s payload=%s",
                method,
                path,
                status_code,
                elapsed_ms,
                client_ip,
                _extract_allowed_headers(headers),
                _summarize_payload(raw_body, headers.get("content-type")),
            )

            # 이유: clear를 빼먹으면 다음 요청 로그에 이전 request_id가 섞일 수 있다.
            clear_request_id()
