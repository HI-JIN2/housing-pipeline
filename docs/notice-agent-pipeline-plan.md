# SH/LH 공고 자동화 에이전트 파이프라인 기획서

## 1. 문서 목적

본 문서는 현재 `housing-pipeline` 프로젝트를 확장하여, SH/LH 신규 공고를 자동으로 감지하고, 공고문을 파싱하고, 지도에 반영하고, Slack으로 알림을 보내는 전체 흐름을 자동화하기 위한 설계 방향을 정리한다.

특히 다음 두 가지를 동시에 만족하는 것을 목표로 한다.

- 신규 공고 감지부터 최종 사용자 노출까지의 전 과정 자동화
- 단계 간 강결합을 피하기 위한 파이프라인 기반 아키텍처 도입

이 문서는 구현 전 기획 문서이며, 이후 상세 설계와 개발 작업의 기준 문서로 사용한다.

## 1.1 착수 상태 (2026-05-05)

- `notice-agent`의 기존 `crawl_once()` 기반 감지 로직을 파이프라인 실행 단위로 감싸는 1차 골격을 먼저 도입한다.
- 1차 구현 범위는 `DISCOVERED -> NOTIFIED` 상태 기록과 실행 이력 저장이다.
- 이후 상세 수집, 첨부 다운로드, 파싱, 지오 보강, 최종 발행 단계를 순서대로 확장한다.

### 권장 구현 순서

1. 파이프라인 실행 이력 및 공고별 상태 저장소 도입
2. SH/LH 상세 페이지 수집 및 첨부 메타데이터 적재
3. 첨부 다운로드와 parser-agent 연동
4. geo-agent 연동 및 최종 발행 저장소 반영
5. Slack 알림 분기, 실패 재시도, GitHub Actions 스케줄링 고도화

---

## 2. 배경

현재 프로젝트는 다음 역할을 가진 여러 서비스로 구성되어 있다.

- `parser-agent`: PDF/XLSX 텍스트 추출, LLM 파싱, 조회 API
- `geo-agent`: 주소 좌표화, 역세권 계산, 지리 데이터 보강
- `admin-agent`: 업로드, 저장, 관리 기능
- `frontend`: 공고 목록/상세/지도 시각화

추가로 `codex/sh-lh-slack-notifier` 브랜치에서는 SH/LH 공고 게시판을 크롤링하고 Slack으로 알리는 `notice-agent` 초안이 도입되었다.

하지만 현재 초안은 다음 한계를 가진다.

- “신규 공고 감지 + Slack 알림”까지만 담당한다.
- 감지된 공고를 기존 파싱/지도 반영 흐름으로 자동 연결하지 않는다.
- 단계별 상태와 실패 재시도 정책이 충분히 구조화되어 있지 않다.
- 장기적으로는 크롤링, 파싱, 지오보강, 발행, 알림이 하나의 운영 흐름으로 관리되어야 한다.

따라서 단순 크롤러가 아니라, 상태를 가지고 다음 행동을 결정하는 에이전트가 필요하다.

---

## 3. 문제 정의

우리가 해결하려는 문제는 단순히 “새 공고를 찾는 것”이 아니다.

실제로 자동화가 필요한 전체 흐름은 다음과 같다.

1. SH/LH 사이트에서 신규 공고 감지
2. 공고 상세 페이지 및 첨부파일 수집
3. 공고 원문/첨부파일 파싱
4. 주소, 좌표, 인접 역 등 지리 정보 보강
5. 프론트엔드에서 바로 볼 수 있는 형태로 저장
6. 운영자에게 Slack 알림 발송
7. 중간 실패 시 재시도, 상태 추적, 수동 재실행 지원

이 흐름을 하나의 거대한 함수나 서비스에 몰아넣으면 다음 문제가 생긴다.

- 단계별 책임이 섞여 유지보수성이 떨어진다.
- 특정 단계만 교체하거나 수정하기 어렵다.
- 중간 상태를 관찰하거나 재실행하기 어렵다.
- 실패 원인 추적과 재시도 정책 분리가 어렵다.

따라서 단계별 책임을 분리하고, 순차 실행 흐름을 선언적으로 표현하는 파이프라인 구조가 필요하다.

---

## 4. 목표

### 4.1 기능 목표

- SH/LH 신규 공고를 자동 감지한다.
- 감지된 공고의 상세 정보와 첨부파일을 수집한다.
- 기존 `parser-agent`, `geo-agent`를 재사용하여 공고를 자동 파싱하고 보강한다.
- 최종 결과를 프론트엔드에서 즉시 조회/지도 표시 가능한 데이터로 반영한다.
- 단계 완료 또는 실패 상태를 Slack으로 알릴 수 있다.

### 4.2 아키텍처 목표

- 전체 자동화 흐름을 파이프라인으로 표현한다.
- 각 단계는 단일 책임을 가진 Job으로 분리한다.
- 상태 저장소(Store)를 중심으로 단계 간 데이터를 공유한다.
- 단계별 재실행, 교체, 테스트가 쉬운 구조를 만든다.

### 4.3 운영 목표

- 저사양 서버에서도 무리 없이 동작해야 한다.
- 상주 루프 의존도를 최소화한다.
- GitHub Actions cron 또는 외부 트리거를 통해 에이전트를 실행할 수 있다.
- 실패한 작업을 나중에 재처리할 수 있어야 한다.

---

## 5. 비목표

이번 단계에서 바로 포함하지 않는 범위는 다음과 같다.

- 완전한 멀티테넌트 구조
- 대규모 메시지 큐 인프라(Kafka, RabbitMQ) 도입
- LLM 모델 교체 자동화
- 관리자용 전용 운영 콘솔의 완성형 UI
- 모든 공급기관 확장 지원

우선은 SH/LH 두 공급기관에 대해서만 안정적인 자동화 파이프라인을 만드는 데 집중한다.

---

## 6. 핵심 개념

### 6.1 왜 에이전트인가

이 구조는 단순 API 서버를 넘어선다. 에이전트로 부를 수 있으려면 다음 조건이 필요하다.

- 공고별 상태를 저장한다.
- 현재 상태를 바탕으로 다음 행동을 결정한다.
- 외부 도구(크롤러, 파서, 지오 서비스, Slack)를 호출한다.
- 실패 시 재시도 여부를 판단한다.

즉, 단순 함수 호출이 아니라 “관찰 -> 판단 -> 행동”의 흐름을 가진다.

### 6.2 왜 파이프라인인가

에이전트를 구현할 때 가장 중요한 것은 결합도 관리다.

신규 공고 감지, 첨부 수집, 파싱, 지오보강, 저장, 알림이 서로 직접 호출하고 내부 구조를 알게 되면 구조가 급격히 복잡해진다. 따라서 다음 원칙을 적용한다.

- 전체 실행 순서는 Pipeline이 관리한다.
- 각 단계는 Job으로 분리한다.
- 상태는 Store에만 기록하고 읽는다.
- Job끼리는 서로 직접 의존하지 않는다.

---

## 7. 제안 아키텍처

### 7.1 구성 요소

- `notice-agent`
  - 전체 자동화 흐름을 오케스트레이션하는 주체
- `parser-agent`
  - 문서 텍스트 추출 및 LLM 파싱 수행
- `geo-agent`
  - 주소 좌표화 및 역세권 보강 수행
- `MongoDB`
  - 원문, 상태, 작업 이력, 공고 메타데이터 저장
- `PostgreSQL/PostGIS`
  - 지도 시각화에 필요한 최종 지리 정보 저장
- `Slack`
  - 운영 알림 채널
- `GitHub Actions`
  - 저사양 서버 보호를 위한 주기 실행 트리거

### 7.2 역할 분리 원칙

- `notice-agent`는 “두뇌” 역할을 한다.
- `parser-agent`, `geo-agent`는 “도구” 역할을 한다.
- 데이터 저장소는 상태와 결과를 분리해서 관리한다.
- Slack은 상태 변경 결과를 외부에 알리는 출력 채널이다.

---

## 8. 파이프라인 설계

### 8.1 상위 파이프라인

공고 1건에 대해 다음 파이프라인을 정의한다.

1. `DiscoverNoticeJob`
2. `FetchNoticeDetailJob`
3. `DownloadAttachmentsJob`
4. `ParseNoticeJob`
5. `EnrichGeoJob`
6. `PublishAnnouncementJob`
7. `NotifySlackJob`

필요 시 별도로:

- `HandleFailureJob`
- `ScheduleRetryJob`
- `FinalizeJob`

### 8.2 실행 흐름

```text
신규 감지
-> 상세 수집
-> 첨부 다운로드
-> 문서 파싱
-> 지리 보강
-> 최종 발행
-> 슬랙 알림
```

### 8.3 단계별 책임

#### `DiscoverNoticeJob`

- SH/LH 목록 페이지에서 신규 공고를 감지한다.
- `source + external_id` 기준으로 중복 여부를 판단한다.
- 신규 공고의 메타데이터를 Store에 적재한다.

#### `FetchNoticeDetailJob`

- 공고 상세 페이지를 수집한다.
- 상세 설명, 게시일, 첨부 링크 등 파싱에 필요한 기본 자료를 준비한다.

#### `DownloadAttachmentsJob`

- PDF/XLSX/HWP 등 첨부파일을 다운로드한다.
- 저장 위치, 다운로드 성공 여부, 파일 메타데이터를 기록한다.

#### `ParseNoticeJob`

- `parser-agent`를 호출하거나 내부 파서를 통해 내용을 구조화한다.
- 주택 목록, 주소, 보증금, 월세, 기타 메타데이터를 추출한다.

#### `EnrichGeoJob`

- `geo-agent`를 호출해 좌표, 인접 역, 도보 거리 등을 계산한다.
- 지도 반영에 필요한 필드를 채운다.

#### `PublishAnnouncementJob`

- 프론트엔드 조회 API가 보는 최종 저장소를 갱신한다.
- 이 단계가 끝나면 사용자 관점에서 “서비스에 반영 완료” 상태가 된다.

#### `NotifySlackJob`

- 신규 감지 알림 또는 반영 완료 알림을 보낸다.
- 운영 목적상 최종적으로는 `PublishAnnouncementJob` 이후 알림이 더 유용하다.

---

## 9. 상태 모델

공고는 단계별 상태를 가져야 한다.

권장 상태:

- `DISCOVERED`
- `DETAIL_FETCHED`
- `ATTACHMENTS_DOWNLOADED`
- `PARSED`
- `ENRICHED`
- `PUBLISHED`
- `NOTIFIED`
- `FAILED`
- `RETRY_SCHEDULED`

권장 메타데이터:

- `source`
- `external_id`
- `title`
- `detail_url`
- `attachments`
- `status`
- `parse_attempts`
- `enrich_attempts`
- `notify_attempts`
- `last_error`
- `next_retry_at`
- `created_at`
- `updated_at`

이 상태 모델은 “에이전트가 다음에 무엇을 해야 하는가”를 판단하는 기준이 된다.

---

## 10. Store 설계 방향

파이프라인의 각 단계는 같은 Store를 공유한다.

예시:

```python
@dataclass
class NoticePipelineStore:
    source: str
    external_id: str
    title: str = ""
    detail_url: str = ""
    detail_html: str = ""
    attachments: list[dict] = field(default_factory=list)
    downloaded_files: list[str] = field(default_factory=list)
    parsed_houses: list[dict] = field(default_factory=list)
    enriched_houses: list[dict] = field(default_factory=list)
    announcement_id: str | None = None
    status: str = "DISCOVERED"
    errors: list[str] = field(default_factory=list)
```

원칙:

- Job은 Store에서 읽고 Store에만 기록한다.
- 다른 Job 내부 구현을 직접 참조하지 않는다.
- Store는 테스트에서 중간 상태 재현의 기준점이 된다.

---

## 11. 결합도 저감을 위한 규칙

### 11.1 허용되는 의존성

- Pipeline -> Job
- Job -> Store
- Job -> 외부 도구(Service, API client, DB client)

### 11.2 피해야 할 의존성

- Job -> 다른 Job 직접 호출
- Job -> 프론트엔드 응답 구조 직접 의존
- 크롤러 -> 파서 내부 모델 직접 의존
- Slack 알림 로직 -> 지오 로직 세부 구현 의존

### 11.3 인터페이스 분리

가능하면 다음 인터페이스를 둔다.

- `NoticeSourceScraper`
- `AttachmentFetcher`
- `NoticeParser`
- `GeoEnricher`
- `AnnouncementPublisher`
- `Notifier`

이를 통해 SH/LH 외 다른 공급기관도 추가하기 쉬워진다.

---

## 12. 실행 트리거 전략

서버 사양이 열악하므로 상주형 무한 루프보다는 외부 트리거 기반이 적합하다.

권장 전략:

- 로컬/개발: 수동 API 실행
- 운영: GitHub Actions `schedule`이 `POST /api/notices/run-once` 호출

장점:

- 서버 메모리 점유를 최소화한다.
- 크롤링 주기 제어가 GitHub Actions에서 가능하다.
- 실패 이력과 재실행을 워크플로우 관점에서도 관리할 수 있다.

단, 장기적으로 공고 수가 늘거나 처리 단계가 길어지면 외부 큐 도입을 검토한다.

---

## 13. Slack 알림 정책

Slack 알림은 최소 두 종류로 나눌 수 있다.

### 13.1 감지 알림

- 신규 공고를 발견한 즉시 알림
- 장점: 빠르다
- 단점: 아직 파싱/지도 반영 전일 수 있다

### 13.2 반영 완료 알림

- 파싱, 지오보강, 저장 완료 후 알림
- 장점: 운영자가 즉시 결과를 활용할 수 있다
- 권장 기본 정책

최종적으로는 완료 알림을 기본으로 두고, 필요 시 감지 알림을 옵션으로 둔다.

---

## 14. 오류 처리 및 재시도 정책

단계별 오류는 모두 같은 방식으로 다루면 안 된다.

### 재시도 가능 오류

- 네트워크 타임아웃
- 일시적 크롤링 실패
- 외부 API 일시 오류

### 재시도 비권장 오류

- 구조적으로 주소가 없음
- 문서 자체 손상
- 파싱 불가능한 포맷

권장 정책:

- `crawl`: 짧은 backoff
- `parse`: 제한된 횟수 재시도
- `geo enrich`: 주소 품질에 따라 실패 고정 가능
- `notify`: 별도 재시도 가능

모든 실패는 `last_error`와 함께 저장해야 하며, 추후 운영자가 수동 재처리할 수 있어야 한다.

---

## 15. 저장 전략

### MongoDB

용도:

- 감지 원문
- 크롤링 결과 원본
- 작업 상태
- 실패 이력
- 첨부파일 메타데이터

### PostgreSQL/PostGIS 또는 최종 조회 저장소

용도:

- 프론트엔드가 보는 최종 사용자 데이터
- 지도 렌더링용 좌표/역 정보

핵심은 “최종 발행 상태”를 사용자 조회 저장소에서 명확하게 구분하는 것이다.

---

## 16. MVP 범위

1차 MVP에서는 다음만 우선 구현한다.

1. SH/LH 신규 공고 감지
2. 상세 정보/첨부 수집
3. 기존 parser/geo 연동
4. 최종 데이터 저장
5. Slack 완료 알림
6. GitHub Actions cron 실행

다음은 후순위로 둔다.

- 관리자 재처리 UI
- 세부 실패 분석 대시보드
- 공급기관 확장 플러그인 구조
- 큐 기반 비동기 분산 처리

---

## 17. 구현 제안 구조

```text
notice-agent/
  main.py
  api/
    routes.py
  models.py
  services/
    pipeline.py
    state_store.py
    discovery_service.py
    detail_fetch_service.py
    attachment_service.py
    parse_dispatcher.py
    enrich_dispatcher.py
    publish_service.py
    slack_service.py
    retry_policy.py
```

추가 후보:

- `jobs/discover_notice.py`
- `jobs/fetch_notice_detail.py`
- `jobs/download_attachments.py`
- `jobs/parse_notice.py`
- `jobs/enrich_geo.py`
- `jobs/publish_announcement.py`
- `jobs/notify_slack.py`

---

## 18. 기대 효과

이 구조를 적용하면 다음 효과를 기대할 수 있다.

- 크롤링부터 지도 반영까지 완전 자동화
- 각 단계의 책임 분리
- 신규 공급기관 추가 용이
- 중간 상태 추적 가능
- 실패 지점 파악 및 재처리 용이
- 특정 단계만 교체하는 변경 비용 절감

즉, 단순한 크롤러가 아니라 운영 가능한 공고 자동화 에이전트로 확장할 수 있다.

---

## 19. 오픈 이슈

추가 논의가 필요한 주제는 다음과 같다.

- 최종 발행 저장소를 Mongo/Postgres 중 어디에 통일할지
- 첨부파일 저장 위치를 로컬 디스크로 둘지, 별도 스토리지로 둘지
- 파싱 실패 공고를 어떻게 운영자에게 노출할지
- Slack 알림을 “감지” 기준으로 할지 “반영 완료” 기준으로 할지
- GitHub Actions cron 주기를 얼마로 할지

---

## 20. 결론

본 프로젝트가 목표로 하는 것은 단순히 “새 공고를 찾는 기능”이 아니라, 공고 감지부터 파싱, 지도 반영, 운영 알림까지 이어지는 자동화 시스템이다.

이를 안정적으로 구현하려면, `notice-agent`를 상태 기반 에이전트로 정의하고, 내부 구현은 파이프라인 구조로 분리하는 것이 가장 적절하다.

즉 다음 원칙을 채택한다.

- 에이전트는 상태와 다음 행동 결정을 담당한다.
- 파이프라인은 전체 실행 순서를 담당한다.
- Job은 단일 책임만 가진다.
- Store는 단계 간 데이터를 공유한다.

이 문서를 기준으로 다음 단계에서는 실제 데이터 모델과 Job 인터페이스를 구체화하고, MVP 구현 순서를 확정한다.
