from fastmcp import FastMCP
from config import settings
import requests
import httpx
from typing import Optional, Annotated
from auth import get_access_token
import json

CLIENT_ID = settings.CLIENT_ID
TENANT_ID = settings.TENANT_ID

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
    return f"pong 메일 읽기 서버 준비 완료. (Client ID 로드 상태: {bool(CLIENT_ID)})"


@mcp.tool()
def search_my_emails(
    limit: Annotated[int, "가져올 이메일의 최대 개수 (1에서 50 사이의 정수, 기본값: 5)"] = 5,
    sender_email: Annotated[Optional[str], "특정 발송자의 메일만 찾을 때 사용하는 정확한 이메일 주소 (예: no-reply@microsoft.com). 특정인 지정이 없으면 None으로 둡니다."] = None
) -> str:
    """
    사용자의 최근 메일을 검색하여 읽어옵니다.
    Microsoft 365 (Outlook) 내 메일함에서 최근 이메일을 검색하고 읽어옵니다.
    
    [LLM 에이전트 사용 가이드]
    1. 사용자가 "최근 메일 확인해줘"라고 포괄적으로 요청하면 limit 값만 넣어서 호출하세요. limit이 지정되어 있지 않으면 기본값 5로 호출합니다.
    2. 결과는 이메일 제목, 보낸사람, 받은시간의 텍스트 목록으로 반환됩니다.
    """
    """
    Microsoft 메일함에서 가장 최근 이메일들을 읽어옵니다.
    
    Args:
        limit: 가져올 이메일의 최대 개수 (기본값: 5개, 최대: 50개)
    """

    try:
        # 1. Access Token 발급 (캐시가 있으면 바로 가져옴)
        token = get_access_token()

        # 2. Microsoft Graph API 요청 설정
        # /me/messages: 내 메일함 엔드포인트
        # $top: 가져올 개수
        # $select: 제목, 보낸사람, 받은시간만 선택적으로 가져와서 데이터 경량화
        endpoint = f"https://graph.microsoft.com/v1.0/me/messages?$top={limit}&$select=subject,sender,receivedDateTime"

        # 특정 발송자 필터링 로직 추가 (Graph API $filter 기능 활용)
        if sender_email:
            # 주의: Graph API 필터 쿼리는 따옴표 처리가 중요합니다.
            endpoint += f"&$filter=from/emailAddress/address eq '{sender_email}'"

        headers = {
            "Authorization" : f"Bearer {token}",
            "Accept" : "application/json"
        }
        
        # 3. API 호출
        response = requests.get(endpoint,headers=headers)
        response.raise_for_status() # 에러 발생 시 예외 처리

        print(json.dumps(response.json(), indent=2, ensure_ascii=False))

        emails = response.json().get("value",[])

        response.raise_for_status() # 에러 발생 시 예외 처리

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



if __name__ == "__main__":
    print("🚀 FastMCP MS 메일 서버를 HTTP(SSE) 모드로 시작합니다...")
    print("Endpoint: http://localhost:8000/mcp")
    
    # stdio 대신 sse 전송 방식을 사용하여 8000번 포트에서 실행
    mcp.run(transport="streamable-http", port=8000)

# 아니 그 방법이면 실제 프로덕션에서 azure tenat 갈때 소스가 달라져서 안돼 
# 차라리 내 auzre에서 지금 코드가 동작하도록 실제 메일을 세팅하는게 좋지 않음? 환경을 프로덕션이랑 맞추는게 낫지


