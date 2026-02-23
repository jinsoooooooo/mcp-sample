요청하신 목적에 맞게, TEXT 기반 AI Agent가 문서의 목적, 아키텍처, 보안 원칙 및 세부 구현 스펙을 완벽하게 이해할 수 있도록 PDF 슬라이드의 모든 내용을 누락 없이 구조화된 **"텍스트 보고서"**로 변환해 드립니다.

---

# [문서 요약 정보]
*   **문서명:** 사내 채팅형 AI Agent를 위한 Outlook MCP Gateway 구축 보고서
*   **부제:** Multi-tenant 아키텍처, 보안 전략 및 51개 Tool 구현 범위 정의
*   **문서 유형:** 기술검토/배포 설계안 v2.1 (작성일: 2026-02-18)
*   **보고 대상:** 팀장/임원 (Confidential / Internal)

---

## 1. 핵심 요약 (Executive Summary)
*   **목표 (Goal):** 전 임직원이 사내 채팅에서 자연어로 Outlook(메일/일정)을 제어할 수 있는 표준 Gateway 구축. App-only(테넌트 전권) 권한을 확보한 후, 사내 Gateway 레벨에서 엄격하게 스코프 및 보안을 통제하는 것이 핵심 목적임.
*   **Tool 구현 범위 (총 51개 Tool):**
    *   **Core (16개):** 즉시 구현 (검색, 조회, 발송 등)
    *   **Advanced (20개):** 조건부 제공 (규칙, 폴더, 일정 조율 등)
    *   **Pass (15개):** 미구현 (개인설정, 리스크 항목 등)
*   **주요 기술 의사결정:**
    1. 멀티 테넌트 라우팅 (`tenant_routing_token` 적용)
    2. 요청자 검증 (`actor_email` 바인딩을 통한 Impersonation(계정 도용) 방지)
    3. 2계층 로깅 (보안 감사 + 운영 관측)
    4. 비즈니스 로직 최소화 (Thin Server, Thick Context)

## 2. 설계 원칙 (Design Principles): Thin Server, Thick Context
1.  **Business Logic Minimization (비즈니스 로직 최소화):** MCP 서버는 데이터 접근(Data Access)과 액션(Action)만 수행. 판단, 요약, 추천, 워크플로우 제어는 전적으로 AI Agent에게 위임.
2.  **Rich Documentation (상세한 문서화):** 코드 로직 대신 'Description', 'Arguments', 'Returns' 명세를 상세화하여 AI의 오호출을 방지. 프롬프트 레벨에서 '언제 사용하는지', '실패 시 대안'을 가이드.
3.  **Safety First (안전 최우선):** 표준 인터페이스로 래핑하여 필수 공통 기능(인증/라우팅/로깅)을 강제 적용. 모든 요청에 대해 Audit(감사) 추적성을 확보.

## 3. 전체 아키텍처 (High-Level Architecture)
*   **데이터 흐름:** Employees (Chat UI) ➔ AI Agent (Planner/Orchestrator) ➔ **MCP Gateway (Internal)** ➔ Microsoft Graph ➔ Exchange / Entra
*   **MCP Gateway 내부 모듈 구성:**
    *   `mcp-common` (인증 및 로깅 처리)
    *   `mcp-mail` (메일 처리)
    *   `mcp-calendar` (일정 처리)
*   **연계 시스템:** MCP Gateway는 App-only Token을 사용하여 Graph와 통신하며, 내부적으로 Observability(Grafana/Loki) 및 Tenant Audit DB와 연결됨.

## 4. 인프라 및 배포 구조 (Implementation)
*   **Kubernetes Cluster 기반 배포:**
    *   Ingress / API GW를 통해 요청 수신.
    *   Pod 구조: `mcp-mail` (High Scalability, HPA 적용됨), `mcp-calendar`, `mcp-common` (Auth, Logging, Utils)가 각각 분리된 Pod로 운영됨.
*   Secrets/Config에서 Tenant Keys를 관리하여 K8s Cluster에 제공. 모든 Pod의 데이터는 Observability(Logs/Metrics/Trace)로 전송됨.

## 5. 핵심 전략 및 가이드
### 5.1 멀티 테넌트 라우팅 전략
*   요청(Request) 헤더에 Opaque 값인 `tenant_routing_token` 포함.
*   **Tenant Registry Lookup:** Token을 조회하여 `tenant_id`, `client_id`, `credential_ref` 추출.
*   **Token Provider:** Secret을 로드하여 MS Graph에 App-only Token 요청.
*   운영 디테일: 테넌트별 키 롤오버 지원, 장애 격리(Bulkhead) 적용.

### 5.2 보안: 요청자 검증 (Anti-Impersonation)
*   **문제점:** App-only 권한은 매우 강력하여, 사용자가 `actor_email` 파라미터를 조작해 타인의 메일을 훔쳐보는 공격을 방지해야 함.
*   **해결책:** User Assertion Token Binding 적용. `actor_email`은 신뢰 입력값이 아닌 검증 대상으로 취급.
*   **검증 로직:** AI Agent가 Tool 호출 시 `actor_email` 인자와 함께 User Assertion Token(Signed JWT, `upn`, `tenant_key_id` 포함)을 첨부. MCP Request Verifier가 `args.actor_email`과 `token.actor_upn`이 일치하는지 확인. (일치 시 Tool 실행, 불일치 시 403 Forbidden).

### 5.3 2계층 로깅 전략 (Audit & Operations)
*   **Layer 1 (Audit Log):** 보안 감사를 목적으로 Tenant DB에 저장 (1년 이상 보관). 기록 내용: Who(User), When, What(Tool), Target.
*   **Layer 2 (Ops Log):** 장애 대응 및 성능 분석을 목적으로 Promtail -> Loki -> Grafana 스택에 저장. 기록 내용: Latency, Error Rate, Graph Throttling.
*   **Privacy Rule (개인정보 보호):** 메일 본문(Body) 및 첨부파일 Raw Data는 로그에서 절대 제외하며 메타데이터만 기록함.

### 5.4 예외 처리 가이드
*   **첨부파일 (Attachments):**
    *   메타데이터 확인 (`hasAttachments=true` 확인 후 이름/크기 조회) ➔ Agent가 필요한 파일만 선별 요청 (`download_attachment`) ➔ Gateway에서 악성코드 스캔 후 임시 URL(Signed URL) 발급 ➔ Agent가 URL을 통해 문서 파이프라인(OCR/요약) 처리.
    *   대용량 파일 정책: 3MB~150MB 파일은 Upload Session/Streaming 처리 지원.
*   **긴 메일 스레드 (Long Threads):**
    *   중복 인용문을 제외하고 신규 내용만 추출하는 `uniqueBody` 우선 적용 ➔ HTML을 Text로 변환 ➔ 서명/인용문 Regex 제거 및 Max Token 제한 (Smart Truncation) ➔ 최근 N자 + `bodyPreview` + `conversationId`를 통해 Clean Summary Context 생성.
    *   매우 긴 스레드는 `conversationId`로 분할 조회하여 단계적 요약(Rolling Summary) 수행.

## 6. Tool 구현 범위 및 분류 기준 (총 51개 Tools)

### [Scope 1] Mail Core Tools (핵심 기능 - 전사 보편 시나리오)
*   `get_messages` (folder, top, filter): 메일 목록 조회. 리스트 확인 후 선별.
*   `get_message` (messageId): 메일 상세 조회. 요약/답장 판단용 본문 획득.
*   `search_emails` (query): 키워드/발신자/기간 기반 메일 검색.
*   `create_draft` (subject, body, to): 답장/신규 메일 초안 생성 (발송 전 검토용).
*   `send_email` (to, subject, body): 메일 실 발송 (**User Confirm 필수**).
*   `reply_to_email` (messageId, comment): 스레드 유지 회신.
*   `get_attachments` (messageId): 첨부파일 메타데이터 목록 조회.

### [Scope 2] Mail Advanced Tools (심화/정리 기능 - 조건부 제공)
*   `forward_email` (messageId, to): 메일 전달(공유/에스컬레이션).
*   `delete_message` (messageId): 메일 삭제. (Risk 가드 필요, 휴지통 이동 처리).
*   `move_message` (messageId, destFolder): 폴더 이동 (분류 자동화).
*   `mark_as_read` (messageId, isRead): 읽음 처리.
*   `create_mail_rule` (conditions, actions): 메일 규칙 생성.
*   `get_mail_folders`: 폴더 트리 조회.

### [Scope 3] Calendar Core Tools (일정 핵심)
*   `list_events` (start, end): 일정 목록 조회 (오늘의 브리핑 등).
*   `get_event` (eventId): 일정 상세 조회 (본문/참석자 확인).
*   `create_event` (subject, start, end): 새 일정 생성 (회의 잡기).
*   `update_event` (eventId, updates): 일정 변경.
*   `delete_event` (eventId): 일정 삭제/취소.

### [Scope 4] Calendar Advanced & App-only Strategy
*   *App-only 제약 대응 전략:* MS Graph의 `findMeetingTimes` API는 Application 권한을 미지원. 따라서 `get_schedule`(Free/Busy) 조회 API로 데이터를 수집 후, MCP 내부 로직으로 슬롯을 계산하여 Agent에 제공함.
*   `get_schedule` (schedules, timeRange): 참석자 가용성(Free/Busy) 확인.
*   `find_meeting_times` (attendees, duration): Wrapper 형태로 내부 로직으로 구현된 Agent 표준 인터페이스.
*   `accept/decline_event` (eventId, comment): 초대 응답 자동화.

### [Scope 5] Contacts & Organization (연락처/조직)
*   `Contactss` / `search_contacts` (query): 연락처 검색. (수신자 식별).
*   `get_organization`: 조직 정보 조회. (SSO 사용자와 Graph 사용자 매핑).
*   `list_contact_folders`: 폴더 기반 연락처 그룹 조회.

### [Scope 6] 미구현(Pass) 항목 및 제외 사유
*   **High Risk / Admin:** `delete_calendar`, `wipe_data` (오작동 시 복구 불가 및 데이터 손실 위험).
*   **Personal Settings:** `get_user_settings`, `update_user_settings` (챗봇 프로필로 대체하며 Graph 범위 외).
*   **Low Utility:** `batch_request`, `list_subscriptions` (백엔드 전용 기능으로 Agent가 직접 호출할 필요 없음).

## 7. AI Agent를 위한 특화 가이드
### 7.1 AI를 위한 문서화(Documentation) 전략
비즈니스 로직을 API에 넣는 대신 JSON 스키마의 "description" 필드에 AI의 행동을 유도하는 가이드를 상세히 적음.
*(예: `search_emails` 도구의 설명란에 "사용자가 특정 메일(주제/발신자/기간)을 찾을 때 사용. 결과가 많으면 `top`으로 제한됨." 명시)*

### 7.2 활용 시나리오 1: 모닝 브리핑
*   **User Query:** "오늘 일정이랑 어제부터 온 급한 메일 요약해줘."
*   **수행 단계:**
    1. `list_events(today)`로 오늘 미팅 목록 획득.
    2. `search_emails(timeRange=last24h, importance=high)`로 긴급 이메일 목록 획득.
    3. 각 이메일 ID에 대해 `get_message(uniqueBody)`로 본문 획득.
    4. AI가 데이터를 처리하여 요약 생성 및 최종 답변 출력.

### 7.3 활용 시나리오 2: 스마트 답장
*   **User Query:** "이 메일 스레드 정리하고 긍정적으로 답장 초안 써줘."
*   **수행 단계 및 Safety Check:**
    1. `get_message(id, prefer=text)`로 메시지 획득.
    2. AI 로직이 본문 요약 및 초안 작성.
    3. **안전 장치(Safety Check):** `send_email`을 바로 호출하지 않고, 반드시 `create_draft`를 거쳐 사용자에게 검토를 유도함. 사용자가 Outlook에서 링크를 클릭해 리뷰 후 직접 발송하도록 설계.

## 8. 구현 로드맵 및 운영 체크리스트
*   **Implementation Roadmap:**
    *   **Phase 1:** MVP (Core Pack, Single Tenant)
    *   **Phase 2:** Multi-tenant & Security (Router, Anti-impersonation)
    *   **Phase 3:** Advanced Pack & Edge Cases (Attachments)
*   **Operational Checklist:**
    *   Tenant Key Rotation Policy (테넌트 키 롤오버 정책)
    *   Graph API Throttling Monitor (Graph API 스로틀링 모니터링)
    *   Audit Log Access Control (감사 로그 접근 제어)
    *   Latency Dashboard Setup (지연 시간 대시보드 구축)

---
*(이 보고서는 첨부된 "Slide_Enterprise_Outlook_MCP_Gateway_v1.0.pdf" 내 20장 분량의 설계 목적, 보안 원칙, 아키텍처, 51개 도구의 분류 및 시나리오를 AI 모델이 맥락을 완벽히 이해하고 파싱할 수 있는 텍스트 형태로 누락 없이 변환한 결과입니다.)*
