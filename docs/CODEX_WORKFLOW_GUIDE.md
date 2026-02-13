# CODEX_WORKFLOW_GUIDE.md

## 목적
- Copilot 인라인 자동완성 대신, Codex 에이전트 중심으로 빠르게 코드 작성/수정/검증하는 작업 흐름을 사용한다.
- 학습모드 기준으로 결과를 받는다: 문제 정의 -> 접근 방법 -> 코드 -> 검증 -> 한 줄 요약.

## 빠른 시작
1. `Cmd+Shift+P` -> `Tasks: Run Task` 실행
2. 아래 태스크 중 하나 선택
3. 코드 선택 후 스니펫(`cx-*`)으로 요청문 생성
4. Codex 채팅에 붙여넣고 실행
5. 변경 후 `Test: Pytest (all)`로 검증

사용 가능한 태스크:
- `MCP: Run Server`
- `Test: Pytest (all)`
- `Test: Pytest (target)`
- `MCP: Inspector`

## 워크플로우 5개

### 1) 버그 수정
- 언제: 에러 메시지가 발생하거나 특정 입력에서 오동작할 때
- 프롬프트 스니펫: `cx-bug`
- 검증: `PYTHONPATH=. ./.venv/bin/pytest -q` 또는 `PYTHONPATH=. ./.venv/bin/pytest -q tests/test_server.py::test_add`

예시:
```text
아래 코드/에러를 분석해줘.
요구사항:
- 재현 조건
- 근본 원인
- 최소 수정안
- 회귀 방지 테스트 1개

에러/코드:
...붙여넣기...
```

### 2) 리팩토링
- 언제: 동작은 맞지만 가독성/유지보수성이 떨어질 때
- 프롬프트 스니펫: `cx-refactor`
- 검증: 기존 테스트 통과 + 변경 함수 수동 호출

### 3) 테스트 추가
- 언제: 새 기능 추가 전/후, 회귀 방지를 강화할 때
- 프롬프트 스니펫: `cx-test`
- 검증: `Test: Pytest (target)`로 빠르게 반복

### 4) 문서와 예시 정리
- 언제: 코드 변경을 팀원이 따라가기 어렵다고 느낄 때
- 프롬프트 스니펫: `cx-doc`
- 산출물: 다이어그램, 실행 예시, 실패 사례 + 해결 방법

### 5) 리뷰 요청
- 언제: PR 전 위험요소를 빠르게 점검할 때
- 프롬프트 스니펫: `cx-review`
- 검증: 지적된 리스크 기준으로 테스트 케이스 보강

## 추천 단축키 (수동 등록)
VSCode는 워크스페이스에서 단축키 파일을 강제 적용하지 않으므로, 아래를 사용자 `keybindings.json`에 직접 추가한다.

```json
[
  {
    "key": "cmd+shift+r",
    "command": "workbench.action.tasks.runTask",
    "args": "MCP: Run Server"
  },
  {
    "key": "cmd+shift+t",
    "command": "workbench.action.tasks.runTask",
    "args": "Test: Pytest (all)"
  }
]
```

## 흐름 다이어그램
```mermaid
flowchart LR
    A[코드 선택] --> B[스니펫 cx-* 생성]
    B --> C[Codex 요청 실행]
    C --> D[변경 반영]
    D --> E[pytest 검증]
    E --> F[문서/가이드 업데이트]
```

설명:
- 선택 코드 기반으로 요청 품질이 올라간다.
- 프롬프트 스니펫으로 반복 입력을 줄인다.
- 테스트를 마지막이 아니라 매 반복마다 실행한다.
- 변경이 끝나면 가이드 문서를 함께 갱신한다.

## 실패 사례와 해결
- 사례: Codex 응답이 너무 길고 핵심 패치가 흐려짐
- 해결: 요청에 "최대 변경 파일 2개, diff 요약 5줄 이내" 제한을 추가

## 이 프로젝트 기준 실행 예시
```bash
./.venv/bin/python app/main.py
PYTHONPATH=. ./.venv/bin/pytest -q
```
