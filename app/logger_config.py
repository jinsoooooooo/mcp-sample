import logging
import logging.config
from contextvars import ContextVar

# 요청 단위 추적값 저장소(기본값 "-")
_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """
    모든 로그 레코드에 request_id를 주입한다.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_ctx.get()
        return True


def set_request_id(request_id: str) -> None:
    _request_id_ctx.set(request_id)


def clear_request_id() -> None:
    _request_id_ctx.set("-")

def setup_logging(log_level: str = "INFO") -> None:
    """
    앱 전체에서 공통으로 사용할 콘솔 로그 포맷을 설정한다.
    """
    resolved_level = log_level.upper()

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_id": {"()": RequestIdFilter},
            "decode_bytes": {"()": DecodeBytesFilter},
        },
        "formatters": {
            "standard": {
                "format": "%(asctime)s | %(levelname)s | req=%(request_id)s | %(name)s | %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "filters": ["request_id", "decode_bytes"],
            }
        },
        "loggers": {
            "": {
                "handlers": ["console"],
                "level": resolved_level,
            },
            "uvicorn": {
                "handlers": ["console"],
                "level": resolved_level,
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["console"],
                "level": resolved_level,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["console"],
                "level": resolved_level,
                "propagate": False,
            },
            # 노이즈 억제
            "fakeredis": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
            "docket": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            # SSE 내부 chunk/ping DEBUG 로그 차단
            "sse_starlette": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(logging_config)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class DecodeBytesFilter(logging.Filter):
    """
    bytes 인자를 UTF-8 문자열로 변환해 로그 가독성을 높인다.
    """

    @staticmethod
    def _decode(value):
        if isinstance(value, (bytes, bytearray)):
            # 왜: 라이브러리 DEBUG 로그에서 bytes가 그대로 찍히면 한글이 \x.. 형태로 깨져 보인다.
            return value.decode("utf-8", errors="replace")
        if isinstance(value, tuple):
            return tuple(DecodeBytesFilter._decode(v) for v in value)
        if isinstance(value, list):
            return [DecodeBytesFilter._decode(v) for v in value]
        if isinstance(value, dict):
            return {k: DecodeBytesFilter._decode(v) for k, v in value.items()}
        return value

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, (bytes, bytearray)):
            record.msg = self._decode(record.msg)

        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(self._decode(v) for v in record.args)
            elif isinstance(record.args, dict):
                record.args = {k: self._decode(v) for k, v in record.args.items()}
            else:
                record.args = self._decode(record.args)

        return True
