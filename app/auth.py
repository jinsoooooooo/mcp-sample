import msal
from config import settings

CLIENT_ID = settings.CLIENT_ID
TENANT_ID = settings.TENANT_ID

# 우리가 요청할 권한 (메일 읽기)
SCOPES = ["Mail.Read"]

# Microsoft 인증 서버 주소 설정
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

def get_access_token():
    """
    MSAL을 사용하여 Access Token을 발급받거나 캐시에서 가져옵니다.
    """

    #1. MSAL 퍼블릭 클라이어느 앱 초기화
    app = msal.PublicClientApplication(
        CLIENT_ID,
        authority=AUTHORITY
    )

    # 2. 기존에 로그인한 기록(캐시)이 있는지 확인
    accounts = app.get_accounts()
    if accounts:
        print("기존 로그인 정보를 사용하여 토큰을 갱신합니다...")
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            return result["access_token"]
    
    # 3. 캐시가 없다면 브라우저를 열어 대화형 로그인 진행
    print("브라우저를 열어 Microsoft 로그인을 진행합니다...")
    # 여기서 Level 1 때 설정한 리디렉션 URI가 백그라운드에서 사용됩니다.
    result = app.acquire_token_interactive(scopes=SCOPES)
    
    if "access_token" in result:
        print("✅ 토큰 발급 성공!")
        return result["access_token"]
    else:
        error_msg = result.get('error_description', '알 수 없는 오류')
        raise Exception(f"로그인 실패: {error_msg}")    


# 단독 실행 테스트용 코드
if __name__ == "__main__":
    try:
        token = get_access_token()
        # 보안상 토큰 전체를 출력하지 않고 앞 20자리만 확인합니다.
        print(f"발급된 Access Token: {token[:20]}...") 
    except Exception as e:
        print(e)