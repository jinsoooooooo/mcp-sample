## MCP-SAMPLE PROJECT


### Azure Portal - MS Entra ID 앱등록하기 

Microsoft Graph API 앱 등록 및 권한 획득


1단계: 새 애플리케이션 등록

왼쪽 메뉴에서 [앱 등록](App registrations)을 클릭합니다.

상단의 [+ 새 등록](New registration)을 클릭합니다.

이름: FastMCP-Mail 라고 입력합니다. (원하시는 이름으로 하셔도 무방합니다.)

지원되는 계정 유형 (매우 중요 ⭐️): 세 번째 옵션인 **"모든 조직 디렉터리의 계정 및 개인 Microsoft 계정(예: Skype, Xbox)"**을 선택합니다. (이걸 선택해야 개인 환경에서 작동합니다.)

하단의 파란색 [등록] 버튼을 클릭합니다 .



2단계: 메일 읽기 권한(API Permissions) 부여

앱이 생성되면 화면이 전환됩니다. 왼쪽 메뉴에서 [API 권한](API permissions)을 클릭합니다.

[+ 권한 추가](Add a permission)를 클릭합니다.

팝업 창에서 **[Microsoft Graph]**를 선택합니다.

[위임된 권한](Delegated permissions)을 클릭합니다.

검색창에 Mail.Read를 입력하여 검색한 후, 펼쳐지는 목록에서 Mail.Read 항목에 체크박스를 선택합니다.

하단의 [권한 추가] 버튼을 클릭합니다.



3단계: 터미널 인증 환경 설정 (Authentication)

왼쪽 메뉴에서 [인증](Authentication)을 클릭합니다.
*만약 Authentication (Preview)라면 상단에 To switch to the old experience, please click here.

[+ 플랫폼 추가](Add a platform)를 클릭하고, 나오는 패널에서 **[모바일 및 데스크톱 애플리케이션]**을 선택합니다.

"사용자 지정 리디렉션 URI" 목록에서 첫 번째에 있는 https://login.microsoftonline.com/common/oauth2/nativeclient 체크박스를 선택합니다. (우리가 만들 로컬 Python 환경에서 로그인 화면을 띄울 때 필요합니다.)

사용자 지정 URI에는 http://localhost 입력

하단의 [구성](Configure)을 클릭합니다.



4단계: 핵심 ID 값 메모하기 (Client ID & Tenant ID)

왼쪽 메뉴의 [개요](Overview)로 돌아옵니다.

화면 상단 필수 정보 란에서 아래 두 가지 값을 복사하여 평소 정보 정리에 쓰시는 Notion이나 메모장에 잠시 붙여넣어 주세요.

**애플리케이션 ID (Client ID)** : dccdd2f8-d486-4b10-b702-3a271196aea6

**디렉터리 ID (Tenant ID)** : 


# 공식 MCP Inspector 사용
MCP 서버 공식 UI 테스트 토구. Node.js 환경이 세팅되어 있다면 바로 실행할 수 있습니다.

```bash
npx @modelcontextprotocol/inspector
```
명령어가 실행되면 터미널에 http://localhost:5173 같은 로컬 웹 주소가 나타나며 해당 사이트 접속
MCP Inspector 웹 화면에서 아래와 같이 설정하고 연결합니다.

- Transport Type: streamable-http" 선택
- URL: http://127.0.0.1:8000/mcp 입력
- [Connect] 버튼 클릭