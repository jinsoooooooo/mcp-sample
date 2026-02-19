from fastmcp import FastMCP
from config import settings
import requests
import httpx
from typing import Optional, Annotated
from auth import get_access_token
import json
from logger_config import setup_logging, get_logger
from starlette.middleware import Middleware
from http_middleware import RequestIdMiddleware
from mcp_midleware import MCPLoggingMiddleware


AZURE_CLIENT_ID = settings.AZURE_CLIENT_ID
AZURE_TENANT_ID = settings.AZURE_TENANT_ID
DEFAULT_USER_EMAIL = settings.DEFAULT_USER_EMAIL
LOG_LEVEL = settings.LOG_LEVEL

mcp = FastMCP("Demo FastMCP")

@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.tool()
def ping() -> str:
    """
    서버가 정상적으로 구성 되었는지 확인하는 테스트 툴 입니다.
    """
    token = get_access_token()
    print(f"token: {token}")

    return f"pong 메일 읽기 서버 준비 완료. (Client ID 로드 상태: {bool(AZURE_CLIENT_ID)} / token: {token:30} )"


@mcp.tool()
def search_my_emails(
    limit: Annotated[int, "가져올 이메일의 최대 개수 (1에서 50 사이의 정수, 기본값: 5)"] = 5,
    my_email: Annotated[Optional[str], "메일을 조회할 사용자의 이메일 주소 (예: no-reply@microsoft.com). 특정인 지정이 없으면 비워둡니다."] = None
) -> str:
    """
    사용자의 최근 메일을 검색하여 읽어옵니다.
    Microsoft 365 (Outlook) 내 메일함에서 최근 이메일을 검색하고 읽어옵니다.

    [LLM 에이전트 사용 가이드]
    1. 사용자가 "최근 메일 확인해줘"라고 포괄적으로 요청하면 limit 값의 숫자와 my_email의 사용자 메일주소를 넣어서 호출하세요. limit이 지정되어 있지 않으면 기본값 5로 호출합니다.
    2. 결과는 이메일 제목, 보낸사람, 받은시간의 텍스트 목록으로 반환됩니다.

    Args:
        limit: 가져올 이메일의 최대 개수 (기본값: 5개, 최대: 50개)
        my_email: 메일을 조회할 사용자의 이메일 주소 (예: no-reply@microsoft.com). 특정인 지정이 없으면 비워둡니다.
    return:
        메일의 이메일 제목, 보낸사람, 받은시간의 텍스트 목록으로 반환됩니다. 만약 메일이 없다면 "총 0개의 최근 메일을 찾았습니다" 문자열을 반환 합니다.
    rtype: str
    """

    if my_email == None or my_email=="":
        my_email=DEFAULT_USER_EMAIL

    try:
        # 1. Access Token 발급 (캐시가 있으면 바로 가져옴)
        token = get_access_token()

        # 2. Microsoft Graph API 요청 설정
        # /me/messages: 내 메일함 엔드포인트
        # /user/{email_adress}/messages: email_adress 사용자의 메일주소
        # $top: 가져올 개수
        # $select: 제목, 보낸사람, 받은시간만 선택적으로 가져와서 데이터 경량화
        #
        # **핵심 필터링 전략**
        # 받은 편지함 inbox로 조회하면 Outlook의 "규칙(Rules)" 으로 아동된 메일이 안됨
        # from/emailAddress/address ne '{my_email}' -> 보낸 사람이 '나'와 다른 경우만 조회 (즉, 수신 메일만)
        # 쿼리 파라미터로 처리하여 API 단계에서 거릅니다.
        endpoint = (
            f"https://graph.microsoft.com/v1.0/users/{my_email}/messages?"
            f"$top={limit}&"
            f"$filter=from/emailAddress/address ne '{my_email}'&"
            f"$select=subject,sender,receivedDateTime"


        )


        headers = {
            "Authorization" : f"Bearer {token}",
            "Accept" : "application/json",
            "ConsistencyLevel": "eventual"  # Optional: 실시간이 아닌 인덱싱으로 검색 = 데이터가 많은거 조회 할 때 넣는 옵션 속도는 향상되느 정확도가 떨어질 수 있으므로 빼도 됨
        }

        # 3. API 호출
        response = requests.get(endpoint,headers=headers)
        response.raise_for_status() # 에러 발생 시 예외 처리

        print(json.dumps(response.json(), indent=2, ensure_ascii=False))

        emails = response.json().get("value",[])

        # 5. LLM이 읽기 좋게 문자열로 포매팅
        result_text = f"총 {len(emails)}개의 최근 메일을 찾았습니다:\n\n"
        for i, email in enumerate(emails, 1):
            sender_name = email.get("sender", {}).get("emailAddress", {}).get("name", "알 수 없음")
            sender_address = email.get("sender", {}).get("emailAddress", {}).get("address", "")
            subject = email.get("subject", "(제목 없음)")
            received_time = email.get("receivedDateTime", "")

            result_text += f"{i}. 제목: {subject}\n"
            result_text += f"   보낸사람: {sender_name} <{sender_address}>\n"
            result_text += f"   받은시간: {received_time}\n"
            result_text += "-" * 30 + "\n"

        return result_text

    except Exception as e:
        raise RuntimeError(f"메일 로드 실패: {str(e)}")


@mcp.tool()
async def search_unread_mail(
    my_email: Annotated[Optional[str], "메일을 조회할 사용자의 이메일 주소 (예: no-reply@microsoft.com). 특정인 지정이 없으면 비워둡니다."] = None
) -> str:
    """
    사용자의 최근 메일을 검색하여 읽어옵니다.
    Microsoft 365 (Outlook) 내 메일함에서 이메일을 검색하고 읽어옵니다.

    [LLM 에이전트 사용 가이드]
    1. 사용자가 "읽지 않은 메일 확인해줘"라고 포괄적으로 요청하면 호출 하세요
    2. 이 도구를 호출 할때의 Arguments는 없습니다.
    3. 결과는 읽지 않은 메일의 이메일 제목, 보낸사람, 받은시간의 텍스트 목록으로 반환됩니다. 만약 읽지안은 메일이 없다면 "읽지 않은 메일이 없습니다." 문자열을 반환 합니다.

    Args:
        my_email: 메일을 조회할 사용자의 이메일 주소 (예: no-reply@microsoft.com). 특정인 지정이 없으면 비워둡니다.
    return:
        메일의 이메일 제목, 보낸사람, 받은시간의 텍스트 목록으로 반환됩니다. 만약 읽지안은 메일이 없다면 "읽지 않은 메일이 없습니다." 문자열을 반환 합니다.
    rtype: str
    """
    try:
        if my_email == None or my_email=="":
            my_email=DEFAULT_USER_EMAIL

        # 1. Access Token 발급 (캐시가 있으면 바로 가져옴)
        token = get_access_token()

        # 2. Microsoft Graph API 요청 설정
        # URL 설명:
        # $filter=isRead eq false : 읽지 않은(false) 메일만 필터링
        # $top={limit} : 최대 n개만 가져오기
        # $select=... : 필요한 필드만 선택 (성능 최적화)
        # $orderby=receivedDateTime desc : 최신순 정렬 (기본값이지만 명시적으로 적는 것이 좋음)
        endpoint = (
            f"https://graph.microsoft.com/v1.0/users/{my_email}/messages?"
            f"$filter=isRead eq false&"
            f"$select=subject,sender,receivedDateTime,isRead&"
            f"$orderby=receivedDateTime desc"
        )

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "ConsistencyLevel": "eventual" # Optional: 실시간이 아닌 인덱싱으로 검색 = 데이터가 많은거 조회 할 때 넣는 옵션 속도는 향상되느 정확도가 떨어질 수 있으므로 빼도 됨
        }

        # 3. API 호출
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint, headers=headers)

        if response.status_code == 200:

            print(json.dumps(response.json(), indent=2, ensure_ascii=False))

            emails = response.json().get("value",[])

            if len(emails)==0:
                return "읽지 않은 메일이 없습니다."

            result_text = f"총 {len(emails)}개의 최근 메일을 찾았습니다:\n\n"
            for i, email in enumerate(emails, 1):
                sender_name = email.get("sender", {}).get("emailAddress", {}).get("name", "알 수 없음")
                sender_address = email.get("sender", {}).get("emailAddress", {}).get("address", "")
                subject = email.get("subject", "(제목 없음)")
                received_time = email.get("receivedDateTime", "")

                result_text += f"{i}. 제목: {subject}\n"
                result_text += f"   보낸사람: {sender_name} <{sender_address}>\n"
                result_text += f"   받은시간: {received_time}\n"
                result_text += "-" * 30 + "\n"

            return result_text
        else:
            # 에러 처리
            print(f"Error: {response.status_code}, {response.text}")
            response.raise_for_status() # 에러 발생 시 예외 처리

    except Exception as e:
        raise RuntimeError(f"메일 로드 실패: {str(e)}")



@mcp.tool()
async def search_emails_by_keyword(
    keyword: Annotated[str, "검색할 키워드(예: invoice, 회의, 장애)"],
    limit: Annotated[int, "조회 개수(1~50)"] = 10,
    my_email: Annotated[Optional[str], "조회할 사용자 메일. 비우면 DEFAULT_USER_EMAIL 사용"] = None,
) -> str:
    """
    키워드 기반으로 사용자의 최근 메일을 검색하여 읽어옵니다.
    Microsoft 365 (Outlook) 내 메일함에서 키워드로 이메일을 검색하고 읽어옵니다.

    [LLM 에이전트 사용 가이드]
    1. 사용자가 "OOO 메일 확인해줘" 또는 "메일에서 OOO 검색 해줘"라고 포괄적으로 메일함에서 검색 요청하면 키워드화 함께 limit 값의 숫자와 my_email의 사용자 메일주소를 넣어서 호출하세요. limit이 지정되어 있지 않으면 기본값 5로 호출합니다.
    2. 결과는 이메일 제목, 보낸사람, 받은시간의 텍스트 목록으로 반환됩니다.

    Args:
        - keyword (str): 사용자가 검색할 키워드입니다. 만약 키워드가 여러개 라면 콤마(,)로 구분합니다. (예: invoice, 회의, 장애))
        - limit (str): 가져올 이메일의 최대 개수 (기본값: 5개, 최대: 50개)
        - my_email (str): 메일을 조회할 사용자의 이메일 주소 (예: no-reply@microsoft.com). 특정인 지정이 없으면 비워둡니다.
    return:
        메일의 이메일 제목, 보낸사람, 받은시간의 텍스트 목록으로 반환됩니다. 만약 메일이 없다면 "총 0개의 최근 메일을 찾았습니다" 문자열을 반환 합니다.
    rtype: str
    """
    try:
        if my_email is None or my_email == "":
            my_email = DEFAULT_USER_EMAIL

        clean_keyword = keyword.strip()
        if not clean_keyword:
            return "keyword는 비어 있을 수 없습니다."

        safe_limit = max(1, min(limit, 50))
        token = get_access_token()

        endpoint = f"https://graph.microsoft.com/v1.0/users/{my_email}/messages"
        params = {
            # 왜: $search는 따옴표로 감싼 검색어를 요구하므로 쿼리 문자열을 명시적으로 구성한다.
            "$search": f"\"{clean_keyword}\"",
            "$top": safe_limit,
            "$select": "id,subject,sender,receivedDateTime,bodyPreview",
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            # 왜: Graph에서 $search 사용 시 ConsistencyLevel 헤더가 필요하다.
            "ConsistencyLevel": "eventual",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(endpoint, headers=headers, params=params)

        response.raise_for_status()
        emails = response.json().get("value", [])

        if not emails:
            return f"'{clean_keyword}' 키워드로 검색된 메일이 없습니다."

        lines = [f"키워드 '{clean_keyword}' 검색 결과: {len(emails)}건\n"]
        for idx, email in enumerate(emails, 1):
            subject = email.get("subject", "(제목 없음)")
            sender = email.get("sender", {}).get("emailAddress", {}).get("address", "")
            received = email.get("receivedDateTime", "")
            message_id = email.get("id", "")
            preview = (email.get("bodyPreview", "") or "").replace("\n", " ").strip()
            preview = preview[:120]

            lines.append(f"{idx}. 제목: {subject}")
            lines.append(f"   message_id: {message_id}")
            lines.append(f"   보낸사람: {sender}")
            lines.append(f"   받은시간: {received}")
            lines.append(f"   미리보기: {preview}")
            lines.append("-" * 30)

        return "\n".join(lines)

    except httpx.HTTPStatusError as e:
        raise RuntimeError(
            f"키워드 메일 검색 실패(HTTP {e.response.status_code}): {e.response.text}"
        )
    except Exception as e:
        raise RuntimeError(f"키워드 메일 검색 실패: {str(e)}")


@mcp.tool()
async def search_emails_by_sender(
    sender_email: Annotated[str, "조회할 발신자 이메일 (예: user@company.com)"],
    limit: Annotated[int, "조회 개수(1~50)"] = 10,
    my_email: Annotated[Optional[str], "조회할 사용자 메일. 비우면 DEFAULT_USER_EMAIL 사용"] = None,
) -> str:
    """
    사용자의 메일함에서 특정 발신자가 보낸 메일을 조회합니다.
    Microsoft 365 (Outlook) 내 메일함에서 발신자의 이메일주소로 메일을 검색하고 읽어옵니다.
    """
    try:
        if my_email is None or my_email == "":
            my_email = DEFAULT_USER_EMAIL

        clean_sender = sender_email.strip().lower()
        if not clean_sender:
            return "sender_email은 비어 있을 수 없습니다."

        safe_limit = max(1, min(limit, 50))
        token = get_access_token()

        endpoint = f"https://graph.microsoft.com/v1.0/users/{my_email}/messages"
        params = {
            "$top": safe_limit,
            # "$orderby": "receivedDateTime desc",
            "$select": "id,subject,sender,receivedDateTime,bodyPreview",
            "$filter": f"from/emailAddress/address eq '{clean_sender}'",
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(endpoint, headers=headers, params=params)

        response.raise_for_status()
        emails = response.json().get("value", [])

        if not emails:
            return f"발신자 '{clean_sender}' 메일이 없습니다."

        # 왜: Graph orderby를 제거했으므로 최신순은 애플리케이션에서 명시적으로 보장
        emails = sorted(
            emails,
            key=lambda x: x.get("receivedDateTime", ""),
            reverse=True,
        )[:safe_limit]

        lines = [f"발신자 '{clean_sender}' 메일 {len(emails)}건\n"]
        for i, email in enumerate(emails, 1):
            subject = email.get("subject", "(제목 없음)")
            message_id = email.get("id", "")
            received = email.get("receivedDateTime", "")
            preview = (email.get("bodyPreview", "") or "").replace("\n", " ").strip()[:120]

            lines.append(f"{i}. 제목: {subject}")
            lines.append(f"   message_id: {message_id}")
            lines.append(f"   받은시간: {received}")
            lines.append(f"   미리보기: {preview}")
            lines.append("-" * 30)

        return "\n".join(lines)

    except httpx.HTTPStatusError as e:
        raise RuntimeError(
            f"발신자 메일 조회 실패(HTTP {e.response.status_code}): {e.response.text}"
        )
    except Exception as e:
        raise RuntimeError(f"발신자 메일 조회 실패: {str(e)}")

@mcp.tool()
async def send_my_email(
    to_address: Annotated[str,"받는 사람의 이메일주소 입니다. 만약 받는사람이 여려명일 경우 콤마(.)로 구분합니다. (예: abc@company.com,def@compay.com). \n이 필드는 반드시 채워야 하는 **필수값**입니다. "],
    subject: Annotated[str,"발송할 메일의 제목입니다. \n이 필드는 반드시 채워야 하는 **필수값**입니다."],
    body: Annotated[str,"발송할 메일의 본문 내용입니다. 본문 내용의 줄바꿈 문자는 '\n'으로 작성되어야 합니다. \n이 필드는 반드시 채워야 하는 **필수값**입니다."],
    my_email: Annotated[str,"보내는 사람(나)의 이메일주소 입니다. (예: no-reply@microsoft.com). \n특정 사용자가 지정되어 있지 않으면 이 필드는 비워둡니다."]=None,
    cc_address: Annotated[str,"참조자(CC)의 이메일 주소 입니다. 만약 참조자가 여려명일 경우 콤마(.)로 구분합니다. (예: abc@company.com,def@compay.com). \n참조자가 특정되어 있지 않으면 이 필드는 비워둡니다."]=None,
) -> str:
    """
    사용자의 메일주소로 다른 사람에게 메일을 보내는 도구입니다.
    Microsoft 365 (Outlook)의 사용자의 메일주소로 메일을 발송 합니다.

    [LLM 에이전트 사용 가이드]
    1. 사용자가 "메일을 보내줘" 또는 "~에게 메일을 보내주세요"등 메일을 작성을 요청 했을 때 사용합니다.
    2. 이 도구를 사용 할 때, 'to_address', 'subject', 'body' 이 세 가지 필드는 반드시 채워져야 하는 **필수값**입니다.
    3. 이 도구를 통해 보내는 메일의 제목(subject)와 본문(body)는 반드시 UTF-8 인코딩으로 채워져야 합니다.

    Args:
        - to_address (str): 받는 사람의 이메일주소 입니다. 만약 받는사람이 여려명일 경우 콤마(.)로 구분합니다. (예: abc@company.com,def@compay.com). 이 필드는 반드시 채워야 하는 **필수값**입니다.
        - subject (str): 발송할 메일의 제목입니다. 필드는 반드시 채워야 하는 **필수값**입니다.
        - body (str): 발송할 메일의 본문 내용입니다. 필드는 반드시 채워야 하는 **필수값**입니다.
        - my_email (str, optional): 보내는 사람(나)의 이메일주소 입니다. (예: no-reply@microsoft.com). 특정 사용자가 지정되어 있지 않으면 이 필드는 비워둡니다.
        - cc_address (str, optional): 참조자(CC)의 이메일 주소 입니다. 만약 참조자가 여려명일 경우 콤마(.)로 구분합니다. (예: abc@company.com,def@compay.com). 참조자가 특정되어 있지 않으면 이 필드는 비워둡니다.

    Returns:
        str: 발송 결과를 알리는 메시지 문자열입니다.
            성공 시: "메일 발송 성공 (To: 3명)" 형태의 메시지를 반환합니다.

    Raises:
        RuntimeError: 네트워크 오류나 API 인증 실패 시 발생합니다.
    """

    # token 가져오기
    token = get_access_token()

    if my_email is None or my_email=="":
        my_email=DEFAULT_USER_EMAIL

    # 본문 파싱: 줄바꿈 문자 변환
    # html_body = body.replace('\r\n','<br/>').replace('\n','<br/>')
    text_body = f"{body}\n본 메일은 MCP에 의하여 발송되었습니다."

    # 받는사람 cealn & JSON 형식의 리스트로 작성
    to_address_list = []
    for addr in to_address.split(','):
        clean_addr = addr.strip()
        if clean_addr:
            to_address_list.append(
                {
                    "emailAddress": {
                        "address": clean_addr
                    }
                }
            )
    print(f"to_address:{to_address}")
    print(f"to_address_list:{to_address_list}")

    # payload 구성
    message = {
        "subject": subject,
        "body": {
            "contentType": "Text",
            "content": text_body
        },
        "toRecipients": to_address_list
    }

    # 참조자(CC)가 있으면 참조메일주소 넣기
    if cc_address is not None and cc_address != "":
        cc_address_list = []

        for addr in cc_address.split(','):
            clean_addr = addr.strip()
            if clean_addr:
                cc_address_list.append(
                    {
                        "emailAddress": {
                            "address": clean_addr
                        }
                    }
                )
        print(f"cc_address:{cc_address}")
        print(f"cc_address_list:{cc_address_list}")

        # CC 주소가 있으면 추가
        if cc_address_list:
            message["ccRecipients"] = cc_address_list

    payload = {
        "message": message,
        "saveToSentItems": True
    }

    # endpoint 구성
    endpoint = f"https://graph.microsoft.com/v1.0/users/{my_email}/sendMail"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "Leodev901-Corp-Internal-Mailer/1.0 (for Business)"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint,
                headers=headers,
                json=payload
            )
            print(response)
            # 202 Accepted 체크
            if response.status_code == 202:
                return f"성공적으로 메일을 보냈습니다.\n- 받는사람: {to_address}\n- 제목: {subject}"
            else:
                # 에러 발생 시 상세 내용 확인을 위해 raise
                response.raise_for_status()
                return "메일 발송 요청이 처리되었으나, 오류가 발생하였습니다."
    except httpx.HTTPStatusError as e:
        # HTTP 에러 (4xx, 5xx) 처리
        raise RuntimeError(f"메일 발송 HTTP 에러: {e.response.text}")
    except Exception as e:
        # 기타 네트워크 에러 등
        raise RuntimeError(f"메일 발송 실패: {str(e)}")




@mcp.tool()
async def create_calendar_event(
    subject: Annotated[str, "일정 제목"],
    start_datetime: Annotated[str, "시작 시간 (ISO 8601, 예: 2026-02-20T10:00:00)"],
    end_datetime: Annotated[str, "종료 시간 (ISO 8601, 예: 2026-02-20T11:00:00)"],
    my_email: Annotated[Optional[str], "일정을 생성할 사용자 메일. 비우면 DEFAULT_USER_EMAIL 사용"] = None,
    attendees: Annotated[Optional[str], "참석자 메일(콤마 구분)"] = None,
    location: Annotated[Optional[str], "장소"] = None,
    body: Annotated[Optional[str], "일정 설명"] = None,
    timezone: Annotated[str, "타임존 (예: Asia/Seoul)"] = "Asia/Seoul",
) -> str:
    """
    사용자의 메일의 캘린더 일정을 생성하는 도구 입니다.
    Microsoft 365 (Outlook)의 사용자 메일주소를 사용하에 일정을 생성하고 사용자를 초대 할 수 있습니다.

    [LLM 에이전트 사용 가이드]
    1. 사용자가 "일정을 생성해줘" 또는 "일정을 등록해줘" 등, 일정을 생성 하는 요청상하이 있을 때 이 도구를 사용 합니다.
    2. 이 도구를 사용 할 때, 'subject', 'start_datetime', 'end_datetime' 이 세 가지 필드는 반드시 채워져야 하는 **필수값**입니다.
    3. 이 도구를 통해 보내는 메일의 제목(subject)는 반드시 UTF-8 인코딩으로 채워져야 합니다.
    4. 'timezone'에 특정 시간대를 설정하지 않은경우 기본 설정으로 'Asia/Seoul' 시간대를 사룡 합니다.

    Args:
        - subject (str): 생성 할 일정의 제목입니다. 이 필드는 반드시 채워야 하는 **필수값**입니다.
        - start_datetime (str): 생성할 일정의 "시작시간" 입니다. 입력 형식은 ISO 8601 형식으로 예: 2026-02-20T10:00:00 으로 입력합니다. 필드는 반드시 채워야 하는 **필수값**입니다.
        - end_datetime (str): 생성할 일정의 "종료시간" 입니다. 입력 형식은 ISO 8601 형식으로 예: 2026-02-20T10:00:00 으로 입력합니다. 필드는 반드시 채워야 하는 **필수값**입니다.
        - my_email (str, optional): 일정을 사용할 사용자의 메일주소 입니다. (예: no-reply@microsoft.com). 특정 사용자가 지정되어 있지 않으면 이 필드는 비워둡니다.
        - attendees (str, optional): 일정을 함께 참조할 참석지의 이메일 주소 입니다. 만약 참석자가 여려명일 경우 콤마(.)로 구분합니다. (예: abc@company.com,def@compay.com). 참석자가 특정되어 있지 않으면 이 필드는 비워둡니다.
        - location (str, optional): 등록할 일정의 장소(주소) 입니다.
        - body (str, optional): 생성할 일정의 설명(본문내용) 입니다. 이 필드는 반드시 UTF-8 인코딩으로 채워져야 합니다.
        - timezone (str, optional): 타임존 (예: Asia/Seoul)"] = "Asia/Seoul

    Returns:
        str: 일정 생성 결과를 알리는 문자열을 반환합니다.

    """
    try:
        if my_email is None or my_email == "":
            my_email = DEFAULT_USER_EMAIL

        token = get_access_token()

        # 왜: 참석자 입력을 문자열로 받아도 Graph 형식으로 안전하게 변환하기 위함
        attendees_list = []
        if attendees:
            for addr in attendees.split(","):
                clean = addr.strip()
                if clean:
                    attendees_list.append(
                        {
                            "emailAddress": {"address": clean},
                            "type": "required",
                        }
                    )

        payload = {
            "subject": subject,
            "start": {"dateTime": start_datetime, "timeZone": timezone},
            "end": {"dateTime": end_datetime, "timeZone": timezone},
            "body": {"contentType": "Text", "content": body or ""},
        }

        if attendees_list:
            payload["attendees"] = attendees_list
        if location:
            payload["location"] = {"displayName": location}

        endpoint = f"https://graph.microsoft.com/v1.0/users/{my_email}/events"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(endpoint, headers=headers, json=payload)

        response.raise_for_status()
        created = response.json()

        return (
            f"일정 생성 완료\n"
            f"- subject: {created.get('subject', subject)}\n"
            f"- event_id: {created.get('id', '')}\n"
            f"- start: {created.get('start', {}).get('dateTime', start_datetime)}\n"
            f"- end: {created.get('end', {}).get('dateTime', end_datetime)}"
        )

    except Exception as e:
        raise RuntimeError(f"일정 생성 실패: {str(e)}")


@mcp.tool()
async def list_calendar_events(
    start_datetime: Annotated[str, "조회 시작 시간 (ISO 8601, 예: 2026-02-20T00:00:00Z)"],
    end_datetime: Annotated[str, "조회 종료 시간 (ISO 8601, 예: 2026-02-21T00:00:00Z)"],
    limit: Annotated[int, "조회 개수(1~50)"] = 20,
    my_email: Annotated[Optional[str], "조회할 사용자 메일. 비우면 DEFAULT_USER_EMAIL 사용"] = None,
) -> str:
    """
    기간 사용자의 메일의 캘린더 일정을 캘린더 일정을 조회하는 도구 입니다.
    Microsoft 365 (Outlook)의 사용자 메일주소를 사용하여 일정을 조회 할 수 있습니다.

    [LLM 에이전트 사용 가이드]
    1. 사용자가 "일정을 조회해줘" 또는 "일정을 확인해줘" 등, 일정을 생성 하는 요청상하이 있을 때 이 도구를 사용 합니다.
    2. 이 도구를 사용 할 때, 'start_datetime', 'end_datetime' 이 두 가지 필드는 반드시 채워져야 하는 **필수값**입니다.
    """
    try:
        if my_email is None or my_email == "":
            my_email = DEFAULT_USER_EMAIL

        safe_limit = max(1, min(limit, 50))
        token = get_access_token()

        endpoint = f"https://graph.microsoft.com/v1.0/users/{my_email}/calendarView"
        params = {
            "startDateTime": start_datetime,
            "endDateTime": end_datetime,
            "$top": safe_limit,
            "$orderby": "start/dateTime",
            "$select": "id,subject,start,end,organizer,location",
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(endpoint, headers=headers, params=params)

        response.raise_for_status()
        events = response.json().get("value", [])

        if not events:
            return "조회 기간 내 일정이 없습니다."

        lines = [f"총 {len(events)}개의 일정을 찾았습니다.\n"]
        for idx, event in enumerate(events, 1):
            lines.append(f"{idx}. {event.get('subject', '(제목 없음)')}")
            lines.append(f"   id: {event.get('id', '')}")
            lines.append(f"   start: {event.get('start', {}).get('dateTime', '')}")
            lines.append(f"   end: {event.get('end', {}).get('dateTime', '')}")
            lines.append(f"   location: {event.get('location', {}).get('displayName', '')}")
            lines.append("-" * 30)

        return "\n".join(lines)

    except Exception as e:
        raise RuntimeError(f"일정 조회 실패: {str(e)}")


@mcp.tool()
async def delete_calendar_event(
    event_id: Annotated[str, "삭제할 일정의 event id"],
    my_email: Annotated[Optional[str], "사용자 메일. 비우면 DEFAULT_USER_EMAIL 사용"] = None,
) -> str:
    """
    기존 일정을 삭제합니다.
    """
    try:
        if my_email is None or my_email == "":
            my_email = DEFAULT_USER_EMAIL

        token = get_access_token()

        endpoint = f"https://graph.microsoft.com/v1.0/users/{my_email}/events/{event_id}"
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.delete(endpoint, headers=headers)

        response.raise_for_status()
        return f"일정 삭제 완료: event_id={event_id}"

    except httpx.HTTPStatusError as e:
        raise RuntimeError(
            f"일정 삭제 실패(HTTP {e.response.status_code}): {e.response.text}"
        )
    except Exception as e:
        raise RuntimeError(f"일정 삭제 실패: {str(e)}")



@mcp.tool()
async def update_calendar_event(
    event_id: Annotated[str, "수정할 일정의 event id"],
    my_email: Annotated[Optional[str], "사용자 메일. 비우면 DEFAULT_USER_EMAIL 사용"] = None,
    subject: Annotated[Optional[str], "일정 제목"] = None,
    start_iso: Annotated[Optional[str], "시작 시간 ISO 8601"] = None,
    end_iso: Annotated[Optional[str], "종료 시간 ISO 8601"] = None,
    attendees: Annotated[Optional[str], "참석자 메일(콤마 구분)"] = None,
    location: Annotated[Optional[str], "장소"] = None,
    body: Annotated[Optional[str], "설명"] = None,
    timezone: Annotated[str, "타임존"] = "Asia/Seoul",
) -> str:
    """
    기존 일정을 부분 수정합니다.
    """
    try:
        if my_email is None or my_email == "":
            my_email = DEFAULT_USER_EMAIL

        token = get_access_token()

        patch_payload: dict = {}

        # 왜: 입력된 필드만 patch에 넣어 불필요한 덮어쓰기를 방지한다.
        if subject is not None:
            patch_payload["subject"] = subject

        if start_iso is not None:
            patch_payload["start"] = {"dateTime": start_iso, "timeZone": timezone}

        if end_iso is not None:
            patch_payload["end"] = {"dateTime": end_iso, "timeZone": timezone}

        if location is not None:
            patch_payload["location"] = {"displayName": location}

        if body is not None:
            patch_payload["body"] = {"contentType": "Text", "content": body}

        if attendees is not None:
            attendees_list = []
            for addr in attendees.split(","):
                clean = addr.strip()
                if clean:
                    attendees_list.append(
                        {
                            "emailAddress": {"address": clean},
                            "type": "required",
                        }
                    )
            patch_payload["attendees"] = attendees_list

        if not patch_payload:
            return "수정할 필드가 없습니다. (subject/start_iso/end_iso/attendees/location/body 중 1개 이상 필요)"

        endpoint = f"https://graph.microsoft.com/v1.0/users/{my_email}/events/{event_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.patch(endpoint, headers=headers, json=patch_payload)

        response.raise_for_status()
        return f"일정 수정 완료: event_id={event_id}"

    except httpx.HTTPStatusError as e:
        raise RuntimeError(
            f"일정 수정 실패(HTTP {e.response.status_code}): {e.response.text}"
        )
    except Exception as e:
        raise RuntimeError(f"일정 수정 실패: {str(e)}")





@mcp.tool()
async def list_todo_lists(
    my_email: Annotated[Optional[str], "조회할 사용자 메일. 비우면 DEFAULT_USER_EMAIL 사용"] = None
) -> str:
    """
    Microsoft To Do 목록(task lists)을 조회합니다.
    """
    try:
        if my_email is None or my_email == "":
            my_email = DEFAULT_USER_EMAIL

        token = get_access_token()
        endpoint = f"https://graph.microsoft.com/v1.0/users/{my_email}/todo/lists"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(endpoint, headers=headers)

        response.raise_for_status()
        lists = response.json().get("value", [])

        if not lists:
            return "To Do 목록이 없습니다."

        lines = [f"총 {len(lists)}개의 To Do 목록을 찾았습니다.\n"]
        for idx, item in enumerate(lists, 1):
            lines.append(f"{idx}. displayName: {item.get('displayName', '')}")
            lines.append(f"   list_id: {item.get('id', '')}")
            lines.append("-" * 30)

        return "\n".join(lines)

    except httpx.HTTPStatusError as e:
        raise RuntimeError(
            f"To Do 목록 조회 실패(HTTP {e.response.status_code}): {e.response.text}"
        )
    except Exception as e:
        raise RuntimeError(f"To Do 목록 조회 실패: {str(e)}")


@mcp.tool()
async def create_todo_task(
    task_list_id: Annotated[str, "작업을 생성할 To Do 목록 id"],
    title: Annotated[str, "작업 제목"],
    my_email: Annotated[Optional[str], "사용자 메일. 비우면 DEFAULT_USER_EMAIL 사용"] = None,
    body: Annotated[Optional[str], "작업 설명"] = None,
    due_iso: Annotated[Optional[str], "기한 ISO 8601 날짜/시간 (예: 2026-02-20T18:00:00)"] = None,
    timezone: Annotated[str, "타임존"] = "Asia/Seoul",
) -> str:
    """
    To Do 작업을 생성합니다.
    """
    try:
        if my_email is None or my_email == "":
            my_email = DEFAULT_USER_EMAIL

        token = get_access_token()

        payload = {"title": title}
        if body is not None:
            payload["body"] = {"content": body, "contentType": "text"}
        if due_iso is not None:
            payload["dueDateTime"] = {"dateTime": due_iso, "timeZone": timezone}

        endpoint = f"https://graph.microsoft.com/v1.0/users/{my_email}/todo/lists/{task_list_id}/tasks"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(endpoint, headers=headers, json=payload)

        response.raise_for_status()
        created = response.json()

        return (
            f"To Do 생성 완료\n"
            f"- task_id: {created.get('id', '')}\n"
            f"- title: {created.get('title', title)}\n"
            f"- status: {created.get('status', '')}"
        )

    except httpx.HTTPStatusError as e:
        raise RuntimeError(
            f"To Do 생성 실패(HTTP {e.response.status_code}): {e.response.text}"
        )
    except Exception as e:
        raise RuntimeError(f"To Do 생성 실패: {str(e)}")


@mcp.tool()
async def list_todo_tasks(
    task_list_id: Annotated[str, "조회할 To Do 목록 id"],
    my_email: Annotated[Optional[str], "사용자 메일. 비우면 DEFAULT_USER_EMAIL 사용"] = None,
    limit: Annotated[int, "조회 개수(1~100)"] = 30,
) -> str:
    """
    특정 To Do 목록의 작업을 조회합니다.
    """
    try:
        if my_email is None or my_email == "":
            my_email = DEFAULT_USER_EMAIL

        safe_limit = max(1, min(limit, 100))
        token = get_access_token()

        endpoint = f"https://graph.microsoft.com/v1.0/users/{my_email}/todo/lists/{task_list_id}/tasks"
        params = {
            "$top": safe_limit,
            "$select": "id,title,status,createdDateTime,lastModifiedDateTime,dueDateTime",
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(endpoint, headers=headers, params=params)

        response.raise_for_status()
        tasks = response.json().get("value", [])

        if not tasks:
            return "해당 목록에 작업이 없습니다."

        lines = [f"총 {len(tasks)}개의 작업을 찾았습니다.\n"]
        for idx, task in enumerate(tasks, 1):
            lines.append(f"{idx}. {task.get('title', '(제목 없음)')}")
            lines.append(f"   task_id: {task.get('id', '')}")
            lines.append(f"   status: {task.get('status', '')}")
            lines.append(
                f"   due: {task.get('dueDateTime', {}).get('dateTime', '') if task.get('dueDateTime') else ''}"
            )
            lines.append("-" * 30)

        return "\n".join(lines)

    except httpx.HTTPStatusError as e:
        raise RuntimeError(
            f"To Do 조회 실패(HTTP {e.response.status_code}): {e.response.text}"
        )
    except Exception as e:
        raise RuntimeError(f"To Do 조회 실패: {str(e)}")






if __name__ == "__main__":
    print("🚀 FastMCP MS 메일 서버를 HTTP(SSE) 모드로 시작합니다...")
    print("Endpoint: http://localhost:8000/mcp")

    setup_logging(LOG_LEVEL)
    logger = get_logger("app.main")
    logger.info("FastMCP 서버를 HTTP(SSE) 모드로 시작 합니다.")
    logger.info("Endpoint: http://localhost:8000/mcp")
    logger.debug("Deub 로그 활성화 상태 입니다.")

    mcp.add_middleware(MCPLoggingMiddleware())

    # stdio 대신 sse 전송 방식을 사용하여 8000번 포트에서 실행
    mcp.run(
        transport="streamable-http",
        port=8000,
        middleware=[
            Middleware(RequestIdMiddleware),
        ],
        uvicorn_config={"access_log": True
                        # "log_config": None,  # uvicorn 기본 로깅 덮어쓰기 비활성화
                        },

        )
