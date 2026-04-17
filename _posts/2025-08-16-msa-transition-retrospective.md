---
layout: post
title: "MSA 전환기"
subtitle: "모놀리식에서 10개 도메인으로 — 10개월 PL 기록"
date: 2025-08-16
category: blog
tags: [MSA, DDD, Architecture]
---

똑닥의 레거시 앱 서버(이하 `app-server`)에 남아 있던 접수·예약·병원·검색·알림·결제 등 핵심 도메인을 10개 도메인 서버로 옮긴 10개월간의 기록입니다. PL로 백엔드 5명과 같이 진행했고, 전수조사부터 라우팅 전환·모니터링까지 끝내고 나니 결과적으로 Jira 티켓이 126개가 찍혀 있었습니다.

## 1. 배경

`app-server`는 Express 4 + TSOA + Mongoose로 시작된 초기 서버입니다. Node.js v12 시절 코드가 v18까지 끌려 왔고, `src/api` 아래에 접수·예약·병원·검색·알림·결제·이벤트·건강검진·약국 등 40여 개 모듈이 평평하게 모여 있었습니다. "도메인 기반 MSA"라는 지향점 자체는 오래전부터 있었고 접수예약·병원·검색·알림 같은 도메인 서버도 이미 떠 있었지만, 본격적인 이관은 매년 미뤄졌습니다. 그 사이 살아있는 트래픽 대부분은 여전히 `app-server`가 받고 있었고, 모놀리식과 도메인 서버가 어정쩡하게 공존하는 상태가 **8년간** 이어졌습니다.

## 2. 왜 옮겨야 했나

서비스와 팀이 커질수록 이 구조의 비용이 계속 올라갔습니다. 쌓여 있던 문제들은 이렇습니다.

- **서비스 성장과 장애 격리** — 병원 수가 늘면서 접수/예약 건수가 계속 증가했고, 검색·결제까지 함께 묶인 서버 전체를 scale-out 해야 했습니다. 한쪽 도메인 DB 장애가 그대로 전체 서비스 중단으로 번지는 구조라 확장과 격리 둘 다 필요했습니다.

- **클라이언트별 요구 분기** — 앱·병원 어드민·내부 운영 도구가 같은 도메인에서도 다른 데이터 표현을 원했습니다. 단일 API로 덮다 보니 오버페칭과 언더페칭이 같이 늘었고, BFF 레이어가 없어 클라이언트가 여러 번 API를 쳐야 하는 흐름도 많았습니다.

- **중복 로직** — `app-server`와 도메인 서버 양쪽에 같은 성격의 로직이 나란히 깔려 있어, 기능 하나를 추가하려면 양쪽을 같이 건드려야 하는 경우가 잦았습니다. 어느 쪽이 정본인지 모호한 영역도 있었습니다.

- **데이터 추적 어려움** — 도메인 간 데이터 소유권이 명확하지 않아 같은 데이터가 여러 곳에 중복돼 있었고, 성능 이슈 원인 추적이 오래 걸렸습니다. 거버넌스가 없는 상태였습니다.

- **기술 단위로 쪼개진 구성** — 기능별/기술별로 쪼개진 서버가 여럿이라, 단순한 Node 버전 업그레이드 하나에도 여러 저장소를 같이 올려야 했고, 도메인 로직이 여러 서비스에 흩어져 일관성 맞추는 비용이 컸습니다.

- **배포 병목** — 팀은 도메인별로 나뉘어 있는데 파이프라인은 하나라 주 2~3회 배포마다 줄을 서야 했고, 다른 팀의 변경 때문에 내 변경이 롤백되는 일도 가끔 있었습니다.

## 3. 설계

### 3.1 쪼개는 기준 — DDD

기술 구분(API / Consumer / Batch)이 아니라 **비즈니스 도메인** 기준으로 자르기로 했습니다. DDD(Domain-Driven Design)를 베이스로 삼아 전략적 설계에서 Bounded Context를 먼저 식별하고, 전술적 설계에서 Entity / Value Object / Aggregate / Repository / Domain Service를 레이어에 매핑했습니다.

도메인 담당자와 각 컨텍스트의 책임·엣지 케이스를 확인하면서 경계를 정리했습니다.

| Bounded Context | 책임 |
|---|---|
| Reception | 접수/예약, 상태 전이, 자동 취소 |
| Hospital | 병원 프로필, 운영 시간 |
| Search | 병원/약국 검색, 형태소·초성·오타 교정 |
| Notification | 푸시·알림톡·SMS |
| User | 사용자, 가족 관계, 인증 |
| Payment | 결제, 환불 |
| ... | (총 10개 도메인) |

### 3.2 "새로 만들지 않고 옮긴다"

이번 프로젝트에서 **새로 만든 도메인 서버는 없습니다.** 접수예약, 병원, 검색, 알림 같은 서버는 저장소가 이미 존재했고 일부 신규 기능이 그쪽에서 돌고 있었습니다. 프로젝트의 실체는 "새 서버 만들기"가 아니라 **`app-server`에 남아 있던 API/Consumer/Batch를 각 도메인 서버로 본격적으로 이관하는 것**이었습니다.

기존 서버 위에 얹는 작업이라 몇 가지 제약이 있었습니다.

- 도메인 서버마다 이미 굴러가는 코드가 있어서 그쪽의 컨벤션·엔티티·스키마를 존중해야 했습니다.
- 옮겨 오는 API가 기존 엔티티와 겹치면 단순 병합이 아니라 재설계가 필요했습니다.
- 도메인 서버의 기존 담당자와 이관자가 같이 붙어 리뷰했습니다.

예를 들어 접수예약 서버는 이미 NestJS 모노레포로 존재했지만, 접수/예약 핵심 로직 상당 부분은 이번 프로젝트를 통해 들어왔습니다. 레포 구조는 이렇게 정리돼 있었고, 옮겨 오는 코드는 여기에 맞춰 재배치했습니다.

```
apps/
  api/          # REST API
  consumer/     # Kafka Consumer
  batch/        # nest-commander 기반 배치
  agent/        # 스케줄러 / 백그라운드 워커
libs/
  domain/       # 순수 도메인 레이어
  core/         # 공통 유틸, 데코레이터, 기반 서비스
  config/
  dd-external-api/  # 외부/타 도메인 서비스 호출
```

`libs/domain`은 프레임워크 의존이 최소화된 순수 도메인 레이어입니다. DDD의 전술적 패턴이 여기에 그대로 녹아 있습니다.

- **Entity** — 식별자로 구분되는 도메인 객체. `HospitalReservation` 같은 Aggregate Root.
- **Value Object** — 식별자 없이 속성 조합으로 의미가 결정되는 객체. 취소 사유(`AutoCancelDetails`), 증상(`SymptomDetails`) 같은 `@Embeddable` 타입이 대표적.
- **Aggregate** — 일관성 경계. Reception에서는 `HospitalReservation`이 Root이고 상태·결제·증상이 한 단위로 묶여 움직입니다.
- **Repository** — 영속성 세부를 감추는 인터페이스. MikroORM 구현은 어댑터에서 주입.
- **Domain Service** — 단일 Entity에 속하지 않는 도메인 로직. `ReceiptCreateService`, `ChangeHospitalReservationUseCase` 같은 것들이 여기 위치.

그리고 `apps/*`는 어댑터 레이어입니다. 이 배치 덕분에 **Hexagonal Architecture**가 자연스럽게 지켜지고, 동일 도메인 로직을 API / Consumer / Batch / Agent 어디에서나 그대로 호출할 수 있습니다.

<img src="/assets/images/msa-transition/hexagonal.svg" alt="Hexagonal — libs/domain이 코어, apps/*는 어댑터" />

```typescript
// libs/domain/src/reception/services/receipt-create.service.ts
@Injectable()
export class ReceiptCreateService {
  async createReceipt(body: BulkRequestReceiptBody): Promise<HospitalReservation> {
    // 순수 도메인 로직 — HTTP, Kafka, DB 드라이버 의존 없음
    // API 컨트롤러, Kafka 컨슈머, 배치 어디서든 동일하게 호출
  }
}
```

### 3.3 분리 단계 — API → 컬렉션 → DB

작업을 한 번에 밀지 않고 3단계로 끊었습니다. 한 번에 밀면 되돌릴 여지가 좁고, 운영 복잡도도 감당하기 어렵기 때문입니다.

- **Phase 1 — API 분리** (완료) — `app-server`에 남아 있던 API/Consumer/Batch를 엔드포인트 단위로 도메인 서버로 옮기는 단계.
- **Phase 2 — 컬렉션 오너십 정리** (완료) — 도메인 서버가 자기 도메인이 아닌 다른 도메인의 MongoDB 컬렉션까지 직접 읽고 쓰는 경우가 꽤 있었습니다. 이걸 끊어서 각 컬렉션 소유권을 해당 도메인 서버로 귀속시켰고, 다른 도메인에서 그 데이터가 필요하면 `dd-external-api`를 통한 API 호출이나 이벤트로 접근하게 바꿨습니다.
- **Phase 3 — DB 논리 분리** (진행 예정) — 처음에는 클러스터를 쪼개는 물리 분리로 갈 계획이었다가 의사결정 과정에서 논리 분리로 방향을 틀었습니다. 같은 클러스터 안에서 Database·접근 권한 경계를 도메인 단위로 더 엄격하게 끊어 가고 있습니다.

Phase 2를 돌리면서 **도메인 간 직접 참조를 전부 걷어냈습니다.** `dd-external-api`는 DDD의 **Anti-Corruption Layer** 역할을 합니다 — 외부 도메인의 DTO 형식이 내 Bounded Context 모델을 직접 오염시키지 않도록, 외부 스키마를 내 도메인 언어로 번역해 넘깁니다.

> **Anti-Corruption Layer(ACL, 부패 방지 계층)** — 외부 시스템(다른 Bounded Context, 외부 API, 레거시 등)과 내 도메인 사이에 두는 번역 계층. 외부의 스키마·용어·상태값이 내 도메인 코드에 직접 섞이지 않도록 가운데서 매핑한다. 외부 API가 바뀌어도 이 계층만 수정하면 되고, 내 도메인 모델은 Ubiquitous Language 그대로 유지된다.

### 3.4 전환 방식 — Strangler Fig

헬스케어 서비스에서 빅뱅 전환은 선택지가 아니었습니다. 접수 실패는 곧 환자의 진료 지연으로 이어집니다. Strangler Fig Pattern으로 `app-server`를 감싼 뒤 엔드포인트 단위로 대체해 나가기로 했습니다.

실질적으로 이 역할을 맡은 건 BFF 성격의 **API Gateway 모노레포**(`ddocdoc-api-gateway-monorepo`)입니다. Gateway 안에는 `packages/proxy`가 라우팅 규칙을, `packages/fetch`가 HTTP 호출(재시도·타임아웃·캐싱·로깅)을, `packages/circuit-breaker`가 서킷 브레이커를 담당합니다. 엔드포인트별로 라우팅 규칙만 바꾸면 트래픽이 `app-server`에서 도메인 서버로 넘어갑니다. **배포와 라우팅 전환을 분리해 둔 덕분에 롤백 비용이 낮았습니다** — 문제가 보이면 라우팅만 되돌리면 됐습니다.

<img src="/assets/images/msa-transition/gateway-routing.svg" alt="API Gateway에서 legacy에서 도메인 서버로 라우팅 전환" />

## 4. 실제로 어떻게 옮겼나

### 4.1 API 전수조사

먼저 한 일은 "지금 `app-server`에서 실제로 살아있는 API가 무엇인가"를 뽑는 것이었습니다. Datadog APM과 OpenSearch 로그를 교차 검증해 최근 호출 이력을 모았고, 이 과정에서 호출되지 않는 **죽은 API**가 생각보다 많이 나왔습니다. 죽은 API는 이관 대상에서 빼고 deprecated 처리.

살아 있는 API는 한 엔드포인트 = 한 Jira 티켓으로 묶어서 관리했습니다. 처음부터 "126건 이관"을 계획한 게 아니라, 전수조사를 하면서 티켓을 하나씩 만들어 붙여 나갔고 프로젝트가 끝나고 돌아보니 126개가 돼 있었습니다.

### 4.2 라우팅 전환과 배포 후 모니터링

엔드포인트 단위로 Gateway 라우팅을 뒤집어 트래픽을 도메인 서버로 넘긴 뒤, **24~72시간은 지표를 계속 보면서 이상 여부를 확인**했습니다. 배포가 끝났다고 바로 손 떼지 않았고, 문제가 있으면 라우팅을 되돌리거나 후속 작업을 새 티켓으로 열었습니다.

### 4.3 동기는 REST, 비동기는 Kafka

규칙은 단순하게 잡았습니다. 응답이 필요하면 REST, 필요 없으면 Kafka.

- Gateway에서 도메인 서버로의 동기 호출은 `packages/fetch`에서 재시도·타임아웃·서킷·캐싱·로깅을 데코레이터 조합으로 붙입니다.
- 알림·통계·캐시 갱신처럼 응답이 불필요한 건은 Kafka.
- 실패가 비즈니스에 즉시 영향을 주지 않는 건은 전부 비동기로.

서킷 브레이커는 `packages/circuit-breaker`에 별도 패키지로 두고, 재시도 전략(`ExponentialBackoffStrategy`, `FixedDelayStrategy`, `LinearBackoffStrategy`)과 조합해서 씁니다. 서킷이 열려 나온 에러는 `defaultIsRetryableError`에서 재시도 대상에서 제외해 이중 부하를 막았습니다.

```typescript
// packages/circuit-breaker — 옵션 요약
// failureThreshold: 실패 임계치
// resetTimeout:     회로 차단 해제 딜레이
// timeout:          요청 취소 딜레이
// 상태: Closed → Open → Half-Open → (성공) Closed
const breaker = createCircuitBreaker(sdk);
breaker.fire(sdk => sdk.get('/reception/...'));
```

### 4.4 이벤트 — 멱등성과 순서

Kafka는 at-least-once 보장이라 컨슈머 쪽에서 순서와 중복을 감당해야 합니다.

- **순서** — `aggregateId` 기반 파티션 키로 해결했습니다. 동일 집계(`hospitalId` 등)의 이벤트는 같은 파티션으로 보내기 때문에 컨슈머 측 순서가 보장됩니다. 실제 프로듀서도 `key: hospitalId.toString()` 형태.
- **중복·역순 이벤트** — 접수 도메인에 원래부터 있던 **상태 머신(`RECEPTION_STATE`) 기반 전이 정책**이 이 역할을 겸합니다. 현재 상태에서 허용되지 않는 전이는 원천 차단되는 정책이라, 중복 이벤트나 순서가 뒤바뀐 이벤트가 와도 대부분 자연스럽게 무시됩니다. Kafka 멱등성을 위해 따로 만든 계층은 아니고, 도메인 정책이 그 역할을 같이 합니다.

```typescript
// apps/consumer/src/reception/controllers/reception.controller.ts
@EventPattern(KAFKA_TOPIC_NAME.HOSPITAL_RESERVATION_CHANGE)
@UseInterceptors(KafkaEventInterceptor)
async changeHospitalReservation(
  @Payload() payload: ChangeHospitalReservationKafkaEvent,
): Promise<void> {
  const body = await this.transformBody(
    ChangeHospitalReservationKafkaEvent,
    payload,
    '진료내역 이벤트 컨슈머에 비정상적인 메시지 전달',
  );
  if (!body) return;
  await this.changeHospitalReservationUseCase.run(body);
}
```

접수·예약 상태 변경처럼 여러 도메인이 함께 반응해야 하는 시나리오는 분산 트랜잭션을 쓰지 않고 Domain Event를 Kafka로 발행해 연쇄 처리합니다. `HOSPITAL_RESERVATION_CHANGE` 토픽을 구독한 각 컨슈머가 캐시 정리·통계 반영·알림 발송을 독립적으로 수행합니다. 발행자(Reception)는 누가 듣는지 모르고, 구독자는 자신의 Bounded Context 안에서 자율적으로 처리합니다. 보상이 필요한 실패 케이스는 컨슈머에서 예외 로깅 후 재처리 큐로 넘기거나, 상태 머신이 허용하지 않는 전이면 명시적으로 무시합니다.

### 4.5 예약 경합과 분산 락

예약 경합(동일 시간대 한 자리에 여러 사용자가 진입)은 분산 환경에서 가장 자주 터지는 장애 원인입니다. 이관 당시에는 Redis `SETNX` 기반 분산 락으로 구현했습니다. 시간 구간(5분) 단위로 키를 쪼개 병렬로 획득하고, **하나라도 실패하면 획득한 키를 전부 해제한 뒤 예외를 던지는** 구조입니다.

```typescript
// 이관 당시 SETNX 기반 구현 개요 — 실제 스니펫이 아니라 패턴 예시
// SET ... NX EX — SETNX + TTL을 원자적으로
const intervals = splitTimeRangeBy5Minutes(reservationTime, endTime);
const keys = intervals.map(i =>
  `reservation-lock:${hospitalId}:${unitKey}:${reservationDate}:${i.start}-${i.end}`,
);

const acquired: string[] = [];
for (const key of keys) {
  const ok = await redis.set(key, '1', 'NX', 'EX', LOCK_TTL_SECONDS);
  if (ok !== 'OK') {
    if (acquired.length > 0) await redis.del(...acquired);
    throw new ForbiddenError(
      '선택하신 시간은 이미 다른 환자가 예약 중이에요. 다른 시간을 선택해 주세요.',
    );
  }
  acquired.push(key);
}
```

5분 단위로 쪼개는 이유는 진료 단위(timeUnit)가 병원마다 다르고(5~30분) 구간이 걸쳐 있는 예약 요청을 안전하게 직렬화하기 위해서입니다.

### 4.6 인프라 정리

- **Lambda 제거** — 단발성 기능을 Kafka Consumer로 통합 이관.
- **AWS Batch → Argo Workflow** — Kubernetes 네이티브로 옮겨 로깅/모니터링을 중앙화. DAG 기반 의존 관리가 선언적으로 됩니다.
- **공유 컬렉션 분리** — 두 도메인이 공유하던 컬렉션을 오너십 기준으로 쪼개고, 반대쪽 도메인은 이벤트/API로 접근.

### 4.7 배포 후 체크리스트

이관 작업이 한참 돌아가던 중반에, "에러 로그 없으면 성공"이라는 기준이 몇 번 실패했습니다. 이관 자체는 성공했는데 외부 연동 타임아웃 설정이 달라 간헐적 실패가 나거나, 신규 엔드포인트 p99가 조용히 늘어나거나 하는 식이었습니다. 그때부터 배포 후 확인 항목을 체크리스트로 고정해 두고 썼습니다.

```text
[이관 배포 후 체크리스트]

□ Datadog APM에서 신규 엔드포인트 p50/p95/p99 응답시간 확인
□ 레거시 app-server 엔드포인트 트래픽 감소 확인 (전환 증거)
□ Kafka Consumer lag 정상 범위 확인 (백프레셔 감지)
□ 외부 연동 API 타임아웃/에러율 확인  ← 가장 놓치기 쉬움
□ 에러율이 아니라 비즈니스 메트릭(접수 건수, 예약 성공률) 비교
□ 이벤트 체인의 각 컨슈머 처리 완료율 모니터링
```

## 5. 결과

| 지표 | Before (모놀리식) | After (MSA) |
|---|---|---|
| 배포 단위 | 전체 서비스 일괄 | 도메인별 독립 배포 |
| 배포 빈도 | 주 2~3회 | 주 8~10회 |
| 평균 배포 시간 | 15분 | 5분 |
| 장애 영향 범위 | 전체 서비스 | 해당 도메인만 격리 |
| 피크 스케일링 단위 | 전체 서버 | 병목 도메인만 |
| 이관 티켓 | — | 126건, 10개월 |
| app-server 트래픽 | 100% | 점진적 감소 후 컷오프 |

## 6. 회고

잘했다고 보는 결정 세 가지.

- **Strangler Fig을 끝까지 유지한 것** — 속도는 느렸지만 되돌릴 수 없는 실수를 만들지 않았습니다. 라우팅만 되돌리면 롤백이 되는 구조 덕에 10개월 동안 문제가 보일 때마다 바로 되돌릴 수 있었습니다.
- **분리를 한 번에 밀지 않고 단계로 끊은 것** — API → 컬렉션 오너십 → DB 순서로 나눈 덕에 매 단계 운영을 안정화한 뒤 다음으로 넘어갈 수 있었습니다. 한 번에 밀었다면 운영 복잡도가 감당 수준을 넘었을 것 같습니다.
- **배포 후 24~72시간 모니터링을 관례로 만든 것** — "에러가 없다"와 "정상이다"를 구분해서 보는 기준이 팀 안에 자리 잡았습니다.

아쉬운 쪽.

- **자동화 테스트를 전환 초기에 더 깔았어야 했습니다.** QA 단계에서 뒤늦게 발견된 엣지 케이스 중 상당수는 E2E 테스트로 미리 잡을 수 있었습니다.
- **문서가 이관 속도를 못 따라갔습니다.** 다른 사람이 옮긴 코드를 6개월 뒤 유지보수할 때 왜 이런 선택을 했는지 단서가 남아 있지 않아서, 처음부터 다시 읽어야 하는 경우가 많았습니다.

시작할 때는 "어떤 패턴, 어떤 도구를 쓸지"가 제일 큰 고민이었는데, 끝나고 보면 "**누가 어떤 도메인을 오너십 있게 가져갈 것인가**"가 제일 어려운 결정이었습니다. 기술 결정과 조직 결정을 분리해서 생각할 수 없다는 걸 이 프로젝트에서 실감했습니다.

## 7. 다음 스텝

- **Phase 3 (DB 논리 분리) 마무리** — 같은 클러스터 안에서 Database·접근 권한 경계를 도메인 단위로 엄격하게 끊는 작업을 계속 진행.
- **이벤트 기반 아키텍처(EDA) 확장** — 지금은 REST 동기 호출과 Kafka 비동기가 섞여 있는데, 응답 필요 여부를 다시 따져 비동기로 옮길 수 있는 지점을 더 찾는 방향. 도메인 간 결합과 호출체인 장애 전파를 한 단계 더 줄이는 쪽으로 갑니다.
- **장애 시나리오 테스트 확보** — 분산 락 경합, 컨슈머 lag, 외부 API 타임아웃처럼 MSA 환경에서 자주 겪는 실패 케이스를 재현할 수 있는 테스트를 확장.
