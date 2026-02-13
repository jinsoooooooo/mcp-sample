from fastmcp import FastMCP
from config import settings
import requests
import httpx
from typing import Optional, Annotated
from auth import get_access_token
import json

AZURE_CLIENT_ID = settings.AZURE_CLIENT_ID
AZURE_TENANT_ID = settings.AZURE_TENANT_ID
DEFAULT_USER_EMAIL = settings.DEFAULT_USER_EMAIL

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
        "Content-Type": "application/json; charset=utf-8"
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






if __name__ == "__main__":
    print("🚀 FastMCP MS 메일 서버를 HTTP(SSE) 모드로 시작합니다...")
    print("Endpoint: http://localhost:8000/mcp")

    # stdio 대신 sse 전송 방식을 사용하여 8000번 포트에서 실행
    mcp.run(transport="streamable-http", port=8000)
