# MSA 리서치 노트 (웹 서치 정리, 2026-07)

> 발표 자료·블로그 글 작성 시 근거로 쓰는 참고 노트. 발행용 아님.

## 1. MSA는 왜 하는가

핵심 동기는 **조직과 시스템이 커졌을 때 변경 속도를 유지하는 것**. 모놀리스는 커질수록 배포 조율 비용·장애 전파 범위·확장 비효율이 같이 커진다. 업계 자료(Atlassian/IBM)가 공통으로 꼽는 트리거:

- 한 부분의 장애가 전체 중단으로 번짐 (fault isolation 필요)
- 특정 기능만 트래픽이 느는데 서버 통짜로 scale-out
- 팀은 여러 개인데 배포 파이프라인은 하나 → 배포 병목
- 기술 스택/버전 업그레이드가 전체 단위로 묶임

## 2. 이점

- **독립 확장** — 서비스별로 필요한 만큼만 scale-out
- **장애 격리(resilience)** — 한 서비스가 죽어도 나머지는 동작
- **배포 속도** — 팀별 독립 배포, 릴리즈 사이클 단축
- **기술 유연성** — 서비스마다 최적 스택 선택 가능
- **팀 자율성** — 작은 팀이 자기 서비스를 end-to-end 소유 (Conway's Law 정렬)

단, 공짜가 아님. **코드 복잡도를 운영 복잡도로 바꾸는 거래** — 네트워크 호출마다 지연, 서비스마다 모니터링 오버헤드, 분산 디버깅·서비스 간 인증 비용이 새로 생김.

## 3. 뭐가 중요한가 (원칙)

- **경계(Bounded Context)** — 기술이 아니라 비즈니스 도메인으로 자른다. 경계를 잘못 자르면 나머지가 다 무너짐
- **데이터 오너십(DB per Service)** — 다른 컨텍스트의 DB에 직접 접근하지 않는다. 이게 안 되면 **분산 모놀리스**: 서비스처럼 보이지만 강결합이라 배포는 더 복잡해지고 장애는 그대로 전파되는 최악의 형태. DB만 쪼개놓고 실시간 데이터가 필요해서 복잡한 동기화 레이어를 다시 짓는 안티패턴이 흔함
- **자율성·독립 배포** — 배포에 다른 팀 조율이 필요하면 경계가 잘못된 신호
- **최종 일관성 수용** — DB를 나누면 전체 ACID 트랜잭션을 잃는다. 이벤트/메시징으로 변경을 전파하는 eventual consistency 설계가 따라옴
- **관측 가능성(observability)** — tracing·metrics 없이는 분산 디버깅이 추측 게임. CI/CD 자동화 없이는 규모에서 붕괴

## 4. 어떻게 설계하는가

1. 도메인 분석 — 비즈니스 기능/도메인 식별 (DDD 전략적 설계, Bounded Context)
2. 서비스 경계 정의 — 책임이 겹치지 않게, loosely coupled + highly cohesive
3. API 계약 설계 — 서비스 간 상호작용은 잘 정의된 인터페이스로만
4. 데이터 분리 — 서비스가 자기 데이터를 캡슐화, cross-service 조회는 API/이벤트로
5. 점진 전환 — 모놀리스에서 갈 때는 Strangler Fig로 라우팅 단위 점진 이관 (빅뱅 금지)

## 5. 기술 스택 (2025 기준 표준 구성)

| 레이어 | 기술 |
|---|---|
| 외부 진입점 | API Gateway (인증·라우팅·rate limiting — north-south) |
| 서비스 간 통신 | 동기 REST/gRPC + service mesh(Istio, Linkerd — mTLS, east-west) |
| 비동기 이벤트 | Kafka / RabbitMQ — event streaming |
| 배포 | 컨테이너 + Kubernetes, CI/CD 자동화 |
| 관측 | Prometheus(메트릭) + Jaeger/OpenTelemetry(tracing) + ELK/Loki(로그) |

Gateway와 mesh는 보완 관계 — Gateway는 외부→내부 경계, mesh는 내부 서비스 간. 우리 스택(Gateway/BFF + Kafka + K8s + Prometheus + Loki)은 mesh만 없는 표준 구성.

## 6. 언제 하면 안 되는가

- 스타트업/작은 팀/제품 검증 단계 → **modular monolith 먼저**가 업계 중론. "잘 설계된 모듈러 모놀리스는 생각보다 훨씬 멀리 간다"
- 조직 성숙도(자동화·관측·on-call)가 안 따라오면 스케일 문제 대신 조정·일관성·운영 오버헤드라는 새 문제를 만듦
- 팀 규모와 아키텍처를 맞추는 게 우선 — 작은 팀에 마이크로서비스는 대개 과함

## 출처

- https://www.atlassian.com/microservices/cloud-computing/advantages-of-microservices
- https://www.ibm.com/think/insights/microservices-advantages-disadvantages
- https://www.geeksforgeeks.org/database-per-service-pattern-for-microservices/
- https://xebia.com/blog/microservices-architecture-principle-3-small-bounded-contexts-over-one-comprehensive-model/
- https://www.cerbos.dev/blog/determining-service-boundaries-and-decomposing-monolith
- https://apisix.apache.org/learning-center/api-gateway-for-microservices/
- https://cloudurable.com/blog/microservices-architecture-2025/
- https://www.gravitee.io/blog/microservices-discovery-api-gateway-vs-service-mesh
- https://www.ibm.com/think/topics/microservices-design-patterns
- https://getdx.com/blog/monolithic-vs-microservices/
- https://terem.tech/are-your-microservices-just-a-distributed-monolith/
- https://www.atlassian.com/microservices/microservices-architecture/microservices-vs-monolith

---

# Part 2 — 운영·통신·관측성 심화 (웹 서치 2024~2026, 시니어용)

> 대상: 10년차+ 백엔드, Kubernetes 전제. 트레이드오프 위주로 정리.

## 7. 서비스 간 통신 — sync vs async

### REST vs gRPC (동기)
- REST: 범용·언어 무관·툴 성숙. 대신 고동시성·느린 네트워크·강한 전달 보장이 필요한 지점에서 무너짐.
- gRPC: 내부 service-to-service, 계약 중요, streaming·저지연·강타입에 유리. HTTP/2 바이너리라 디버깅 난도는 올라감.
- 실무 기본형: 외부/BFF 경계는 REST(+JSON), 내부 east-west 핫패스는 gRPC. 대부분 hybrid로 감.

### async 메시징 (Kafka 등)
- 처리량·persistence·loose coupling·장애 격리에서 유리. producer/consumer 독립 확장.
- 대가: 요청-응답 상관관계가 사라져 상태 파악·디버깅·모니터링이 어려워짐. 에러 핸들링이 async로 흩어짐.
- 선택 기준: 결과를 즉시 돌려줄 필요가 없고, eventual consistency를 받아들일 수 있는 도메인 이벤트 → async. 즉답·강결정 흐름 → sync.

### fan-out과 tail latency (핵심)
- fan-out 아키텍처에서 p99를 지배하는 건 실패가 아니라 **straggler**(죽지 않고 느리게 끝나는 요청). 100개 downstream, 각 straggler율 1%면 **top-level 요청의 63%가 최소 하나의 straggler에 걸림**. ("The Tail at Scale", Dean & Barroso 2013)
- 완화책: hedged request(짧은 지연 뒤 백업 요청 발사, 먼저 오는 걸 채택). gRPC는 `hedgingPolicy`로 네이티브 지원하나 hedgingDelay가 정적이고 부하 증폭을 막는 budget이 없음.
- adaptive hedging(호스트별 지연 분포 학습, p90 초과 시 백업): p99 64ms→17ms(**-74%**), 오버헤드 ~9% 사례.

### retry storm / cascading failure
- retry storm: 여러 서비스가 동시에 실패 요청을 재시도 → 회복 중인 서비스를 다시 눌러버리는 self-inflicted DoS.
- **retry budget**: 재시도를 정상 트래픽의 10~20%로 토큰버킷 제한, 소진 시 재시도 대신 fail-fast. (retry는 여기가 핵심 — 개별 재시도 횟수보다 전체 재시도 예산이 중요)
- backoff + jitter로 재시도 타이밍 분산. circuit breaker가 열리면 재시도 자체를 차단.
- 비멱등 연산(결제·리소스 생성)은 idempotency key로 중복 제거 필수 — 없으면 재시도가 곧 데이터 오염.

출처:
- https://medium.com/@platform.engineers/a-deep-dive-into-communication-styles-for-microservices-rest-vs-grpc-vs-message-queues-ea72011173b3
- https://www.signadot.com/blog/how-microservices-communicate-with-each-other/
- https://www.infoq.com/articles/adaptive-hedged-requests-p99-latency/
- https://grpc.io/docs/guides/request-hedging/
- https://aayanand.medium.com/the-tail-at-scale-concepts-techniques-and-impact-106b69b5c770
- https://arxiv.org/html/2511.23278v1 (RetryGuard)
- https://oneuptime.com/blog/post/2026-01-24-retry-storm-microservices/view
- https://hokstadconsulting.com/blog/retry-backoff-in-distributed-systems

## 8. Service mesh 현재 상태 (2024~2026)

### 아키텍처 지형
- **Istio ambient**: sidecar 제거. ztunnel(노드당 DaemonSet, L4 mTLS) + waypoint(네임스페이스당 선택적 L7 Envoy) 2계층. 2024-11 GA.
- **Cilium**: eBPF로 커널에서 처리, sidecar-free 가능(성능↑, 일부 기능 trade-off). full 기능은 Envoy sidecar 모드.
- **Linkerd**: Rust proxy, **여전히 sidecar 고수**. sidecarless에 보수적. 절대 지연 성능 리더.

### 성능 숫자
- Istio ambient mTLS 오버헤드 8% vs sidecar 166%.
- 학술 벤치(2025-10): 5만 pod 엔터프라이즈 규모에서 Istio Ambient가 Cilium보다 코어당 QPS 56% 높음.
- Cilium eBPF: 절대 지연 최저(커널 공간). 금융권 사례 네트워크 오버헤드 40~60% 감소 보고.
- Linkerd vs Istio Ambient: 2000 RPS에서 p99 차이 11.2ms(2.24%)로 미미.

### "정말 필요한가" 논쟁
- 전통 sidecar mesh 채택률 **2023 50% → 2024 42%로 하락** — 복잡도가 문제보다 커진 지점.
- 그러나 CNCF 2024 설문: mesh 도입 조직 80%가 신뢰성 개선, 60%가 time-to-market 단축.
- 대체적 합의: 서비스 12개 넘고, 규제 압박 있고, multi-cloud 보면 → 필요. 그 미만이면 과함. mTLS/재시도/타임아웃만 필요하면 라이브러리·게이트웨이로 충분한 경우 많음.
- 방향성: self-managed 복잡 mesh → managed·ambient·eBPF로 단순화하는 흐름.
- 우리 스택 관점: Gateway/BFF + Kafka + K8s로 north-south는 커버됨. east-west mTLS·트래픽 정책이 실제 아프기 전엔 mesh 도입 보류가 합리적.

출처:
- https://platformengineeringplaybook.com/blog/service-mesh-showdown-cilium-istio-ambient-comparison/
- https://lucaberton.com/blog/service-mesh-istio-ambient-cilium/
- https://jimmysong.io/blog/service-mesh-sidecar-vs-sidecarless-debate/
- https://www.techtarget.com/searchitoperations/news/365535362/Sidecarless-eBPF-service-mesh-sparks-debate
- https://cloudnativenow.com/contributed-content/why-service-mesh-is-poised-for-a-dramatic-comeback-in-2026/
- https://cloudsecurityalliance.org/articles/do-you-really-need-a-service-mesh
- https://arxiv.org/html/2411.02267v1 (mTLS 성능 비교)

## 9. API Gateway / BFF

- 성숙한 구성: **BFF가 Gateway 뒤에 위치**. Gateway는 인프라 관심사(라우팅, 인증·인가, rate limit, SSL 종료, 버전 관리 — north-south), BFF는 클라이언트별 응답 최적화.
- **책임 경계(중요)**: BFF는 여러 서비스 응답을 aggregate·transform 하되 **비즈니스 로직은 넣지 않는다**. "데이터가 어떻게 보일지"는 BFF, "어떻게 동작할지"는 서비스. 여기 흐려지면 BFF가 또 하나의 모놀리스가 됨.
- 인증 이중 검증: Gateway가 토큰 검증, BFF가 claim·클라이언트별 인가 적용.
- BFF 장점: 클라이언트 왕복 횟수 감소, 클라이언트별 캐싱 포인트(각 BFF는 자기 클라이언트가 뭘 얼마나 자주 필요로 하는지 앎).
- 트레이드오프: 서비스 수 증가 → 운영·모니터링 비용, BFF 간 로직 중복 위험, 강제 업데이트 안 되는 모바일의 버전 관리 난제.
- 언제 도입? 단일 API 복잡도가 여러 BFF 운영 복잡도를 넘어설 때만. 유연한 백엔드 API(필드 선택·embed)가 이미 있으면 BFF 이득은 marginal.

출처:
- https://learn.microsoft.com/en-us/azure/architecture/patterns/backends-for-frontends
- https://aws.amazon.com/blogs/mobile/backends-for-frontends-pattern/
- https://marmelab.com/blog/2025/10/01/do-you-need-a-backend-for-frontend.html
- https://medium.com/@platform.engineers/api-gateway-and-backends-for-frontends-bff-patterns-a-technical-overview-8d2b7e8a0617

## 10. 관측성 (OpenTelemetry + Grafana 스택)

### OTel 표준화 현황 (2025)
- traces/metrics/logs를 shared trace context + resource metadata로 상관. 로그에 trace_id/span_id 자동 주입 → 로그↔트레이스 강한 상관.
- 2025 sampling 진전: W3C TraceContext L2 `Random` flag 채택 → **consistent probability sampling**. TraceID 하위 56bit 랜덤성 표준화로, 서비스별 독립 샘플링률(Frontend 100%, Cache 0.1%, Storage 10%)에도 트레이스 완결성 유지.
- `tracestate`에 `ot` 키로 샘플링 threshold 인코딩: `ot=th:0`=100%, `ot=th:fd7`≈1%. rate-limited·adaptive·multi-stage 샘플링 아키텍처 가능.

### 샘플링 전략 (실전)
- **tail-based sampling(Gateway collector)**: 트레이스가 충분한 span 증거를 모은 뒤 보존 결정 → 에러·고지연 트레이스는 무조건 보관. 순수 확률 샘플링보다 유효.
- head sampling은 저렴하지만 드문 에러를 놓침 → 보통 head(비용 방어) + tail(에러/고지연 포착) 조합.

### Grafana 스택 (Prometheus + Loki + Tempo)
- 역할: metrics=뭔가 잘못됨을 앎 / logs=왜인지 진단 / traces=분산 시스템 어디인지.
- **Tempo**: 트레이스를 object storage(S3/GCS) flat file로 저장 → Jaeger의 Elasticsearch 대비 운영 저렴. trace ID로 조회.
- **exemplar**: Prometheus 히스토그램 스파이크의 데이터포인트에 trace ID 주석 → 클릭 한 번으로 해당 Tempo 트레이스로 점프. 트레이스 span → Loki 로그로도 점프. 단일 Grafana 안에서 3-signal cross-navigation.
- Tempo가 트레이스에서 **RED 메트릭(Rate/Error/Duration)**·service graph를 자동 생성해 Prometheus로 push.
- 우리 스택(Prometheus + Loki)에 Tempo + OTel Collector만 얹으면 트레이싱까지 상관 가능. Collector는 Grafana Alloy로 통합 가능.

출처:
- https://opentelemetry.io/blog/2025/sampling-milestones/
- https://opentelemetry.io/docs/concepts/context-propagation/
- https://www.controltheory.com/resources/tail-sampling-with-the-otel-collector/
- https://grafana.com/docs/grafana/latest/fundamentals/exemplars/
- https://grafana.com/docs/tempo/latest/metrics-from-traces/
- https://cloudrps.com/blog/prometheus-loki-grafana-observability-stack/

## 11. Resilience 패턴

- **Circuit Breaker**: Closed/Open/Half-Open 상태머신. 실패율이 systemic이면 open해서 호출 차단·재시도 억제, 회복 기회 부여.
- **Bulkhead**: 서비스별 리소스 풀(thread/connection/memory) 분리 → 한 곳의 포화가 전체로 안 번지게. blast radius 격리.
- **Adaptive concurrency / backpressure**: 2025 담론의 핵심은 **overload를 1급 관심사로**. edge admission control → 각 hop의 adaptive concurrency까지 end-to-end backpressure. token bucket으로 버스트 평탄화, queue budget/queue-time SLO, x-request-start·queue budget 헤더로 경로 전체가 같은 예산 언어를 씀.
- **Timeout budget**: 상위 요청의 총 예산을 hop마다 나눠 쓰고, 남은 예산을 downstream에 전파(deadline propagation). 각 hop 고정 타임아웃보다 정확.
- 조합이 원칙: circuit breaker는 용량 계획·retry·bulkhead·backpressure의 대체재가 아님. timeout + 제한된 retry + rate limit + 리소스 격리를 함께.

출처:
- https://debugg.ai/resources/backpressure-by-design-2025-concurrency-limits-admission-control-queueing-patterns
- https://arxiv.org/html/2512.16959v1 (resilient microservices systematic review)
- https://system-design.space/en/chapter/resilience-patterns/
- https://talent500.com/blog/circuit-breaker-pattern-microservices-design-best-practices/

## 12. 테스트 전략

### Contract testing
- 목적: 서비스 간 "계약"(주고받는 데이터)만 검증 → 전체 E2E보다 복잡도↓, 통합 이슈 조기 발견. 독립 개발/배포 가능케 함.
- **Consumer-Driven(Pact)**: consumer가 기대 상호작용을 정의 → provider가 backward compatibility 유지 검증. REST·async 메시지 계약 모두 지원. 멀티팀은 중앙 **Pact Broker**로 계약 생명주기 조율.
- **Bi-directional(PactFlow)**: provider가 OpenAPI spec 발행 + consumer가 자기 부분집합 발행 → broker가 호환성 비교(consumer가 의존하는 필드를 provider가 제거하면 flag). provider 주도 설계 + consumer 의존성 자동 검증.

### 통합 테스트의 어려움 → testing in production
- 완전한 통합 환경 재현이 비싸고 flaky. 그래서 프로덕션에서 안전하게 검증하는 progressive delivery로 이동.
- **Canary**: 인프라/네트워킹 계층. 트래픽 %·내부 사용자 IP로 타겟. SRE/DevOps가 조율.
- **Feature flag**: 애플리케이션 계층. 실행 컨텍스트 아는 모든 것으로 정밀 타겟, 즉시 on/off. 코드 배포와 기능 릴리즈를 분리 — 버그 기능만 "fade to black". 앱팀(엔지니어·PM)이 조율.
- 실전: 둘을 결합 — canary로 트래픽 비율 올리며(1%→100%) 관측, feature flag로 대상·롤백 정밀 제어.

출처:
- https://docs.pact.io/
- https://www.sachith.co.uk/contract-testing-with-pact-best-practices-in-2025-practical-guide-feb-10-2026/
- https://totalshiftleft.ai/blog/contract-testing-for-microservices
- https://www.harness.io/blog/canary-release-feature-flags
- https://configcat.com/blog/how-to-implement-a-canary-release-with-feature-flags/

## 13. MSA 비용 문제

- MSA는 코드 복잡도를 운영·인프라 비용으로 바꾸는 거래. 서비스 간 통신이 전부 네트워크 → 데이터 전송·중복 리소스 비용이 새로 붙음.
- **cross-AZ 트래픽이 조용한 주범**:
  - 바쁜 MSA 환경에서 cross-AZ 트래픽만 월 $2,000~8,000, 청구서엔 "EC2-Other"로 숨어 대부분 팀이 안 봄.
  - Datadog 2024 State of Cloud Costs: cross-AZ가 전체 데이터 전송 비용의 **약 50%**, 조직의 98%가 영향.
  - 근본 원인: 이중화 위해 서비스를 여러 AZ에 배포 + K8s 기본 라우팅은 AZ-aware가 아님 → us-east-1a 노드 요청이 1c pod로 넘어감. (topology-aware routing / hints로 완화)
- 데이터 전송은 전형적 클라우드 청구서의 **6~12%**(CloudZero 2025). 2025 AWS 요금 개편으로 네트워크 비용 10~15%↑ 전망, inter-VPC 통신에 NDPU 신규 과금.
- 낭비: 엔터프라이즈 클라우드 지출의 ~21%(약 $44.5B)가 저활용 리소스 낭비, 상당 부분이 아무도 안 보는 네트워크 라인아이템(Harness, 2025).
- 실전 완화: cross-AZ 감축(topology-aware routing), 사례로 AWS 데이터 전송 비용 80% 절감 보고도 있음.

출처:
- https://www.economize.cloud/blog/aws-data-transfer-costs-2026/
- https://brainagents.ai/blog/eks-cross-az-traffic-cost-optimization-guide
- https://medium.com/@debyroth340/the-hidden-cross-az-cost-how-we-reduced-aws-data-transfer-cost-by-80-836b6d06886d
- https://aws.amazon.com/blogs/apn/aws-data-transfer-charges-for-server-and-serverless-architectures/

---

# Part 3 — 기업별 실전 사례 (웹 서치 2026-07, 시니어용)

> 성공담 홍보가 아니라 기술 결정·수치·실패/회귀 중심. 각 항목 출처 URL 포함.

## 14. 해외 사례 — 전환 과정의 기술 결정과 문제

### Uber — DOMA(Domain-Oriented Microservice Architecture)

- **규모**: critical 마이크로서비스 **약 2,200개**(2018~2020년경)를 **70개 도메인**으로 재분류. 발표 시점 도메인의 약 50% 구현.
- **초기 모놀리스 문제(2012 이전)**: 단일 회귀(regression) 하나가 전체 시스템을 내림. 배포가 위험하고 롤백 잦음.
- **플랫한 마이크로서비스로 갔더니 생긴 문제**: 장애 하나 추적하려고 **12개 팀의 50개 서비스**를 헤집어야 함. 의존성이 여러 층 깊이로 뻗어 latency cascade. 간단한 기능 하나에 회의·설계·리뷰가 과도. 서로 배포를 맞춰야 하는 **"networked monolith(분산 모놀리스)"** 형성.
- **해결 구조**: 5계층(Infrastructure → Business → Product → Presentation → Edge), 의존성은 아래 방향으로만. 도메인마다 **Gateway 단일 진입점**으로 내부 서비스 복잡도를 숨김. 확장은 core 코드를 안 건드리는 Logic Extension(플러그인)·Data Extension(protobuf `Any`).
- **핵심 수치**: 마이크로서비스 **half-life 1.5년**(18개월마다 절반 교체) → Gateway로 소비자를 underlying 서비스 변경에서 분리해 "migration hell" 완화. 온보딩 touchpoint 25~50%↓, 한 기능 통합 3일 → 3시간. 플랫폼 지원 비용 order of magnitude↓.
- 교훈: 서비스를 "평평하게" 늘리는 것 자체가 병목. 도메인·계층·게이트웨이로 **경계와 의존성 방향을 강제**하는 게 핵심.
- 출처: https://www.uber.com/us/en/blog/microservice-architecture/

### Netflix — 7년에 걸친 점진 전환

- **트리거**: 2008년 DB 손상으로 **3일간 서비스 중단**. 모놀리스 취약성이 시발점.
- **규모/기간**: 2009→2016, **7년**. 구독자 940만 → 약 8,900만. **700개+ 마이크로서비스**, 30개+ 팀.
- **방식**: 모놀리스와 마이크로서비스를 7년간 **병행 운영**. Strangler Fig로 신규 서비스에 트래픽 태우고 모놀리스는 fallback으로 유지하며 서서히 굶김. **가장 쉬운(결합 낮은) 것부터, billing 같은 stateful·금전 민감 서비스는 맨 마지막**.
- 교훈: "마이크로서비스는 그 복잡도를 제품 엔지니어에게서 숨겨줄 **플랫폼 레이어에 투자할 수 있는 만큼만** 지속 가능하다."
- 출처: https://sujeet.pro/articles/netflix-microservices-evolution , https://newsletter.systemdesign.one/p/netflix-microservices

### Airbnb — "The Great Migration"(모놀리스 → SOA)

- **배경**: 2008년 Ruby on Rails 단일 앱(Monorail)이 비대해짐 → 2018년 전사 SOA 착수. 엔지니어 200명(2015) → 1,000명.
- **구체 문제**: 리버트·롤백 때문에 배포가 **주당 평균 15시간 지연**.
- **데이터 마이그레이션 기법(주목)**: **dual read + 응답 비교** — 읽기를 old/new 양쪽에 태워 comparison framework로 대조. 쓰기는 dual-write 불가하니 **shadow DB**에 먼저 쓰고 비교가 깨끗해진 뒤 완전 전환. 모놀리스 안 모든 쿼리를 고치지 않으려고 **커스텀 ActiveRecord adapter**로 DB 호출을 신규 서비스로 우회.
- 결과: 페이지 로드 최대 10배 개선. SOA는 툴·프레임워크·문서에 대한 **높은 초기 투자**가 전제.
- 출처: https://www.infoq.com/presentations/airbnb-soa-migration/ , https://www.infoq.com/news/2019/02/airbnb-monolith-migration-soa/

### Monzo — 1,600개 마이크로서비스 뱅킹

- **규모**: AWS 위 **1,600개+ 마이크로서비스**(2020), 고객 400만+. Go, Cassandra, Kubernetes(초기 베팅).
- **철학**: 아주 작은 단일 목적 서비스 다수. "비접촉 결제 바꿀 때 chip&PIN을 안 건드린다"는 변경 리스크 최소화.
- **자체 도구**: 배포 도구 **Shipper**(K8s 롤링 배포 + Cassandra 마이그레이션, 단일 명령 수 분 내 배포). RPC filter가 안 떠 있는 downstream을 감지해 컴파일·기동 후 요청 전달.
- 시사점: 강정합 도메인(뱅킹)도 잘게 쪼갠 사례. 단 배포/디스커버리 자동화에 대한 자체 투자가 전제.
- 출처: https://www.theregister.com/2020/03/09/monzo_microservices/ , https://www.infoq.com/presentations/monzo-microservices/

### DoorDash — Django 모놀리스 → 마이크로서비스(2019~2023)

- **왜 떠났나**: 작은 변경에도 예기치 않은 side effect·테스트 실패. Python 동적 타이핑이 breaking change 방지를 어렵게 함. DB 부하·K8s 용량 병목. 거대 코드베이스 온보딩 고통.
- **방식**: Strangler Fig + **shadow testing(scream test)** — 같은 입력을 신규 서비스에 병렬로 흘려 결과를 뒤에서 비교한 뒤 실트래픽 전환. Kotlin 주력(+Node/Python), Kafka/ES/Redis. 서비스 디스커버리 DNS + client-side LB. 배포는 지리적 cell/zone 단위 canary.
- **셀 기반 아키텍처**: 트래픽을 cell/geo로 나눠 장애 격리·점진 릴리즈. 단 **cross-AZ 전송 비용 증가**가 새 문제로 등장해 비용 최적화를 다시 함.
- **규모**: 주문 피크 35,000 RPS, 풀스택 500,000+ RPS. 프론트 ~200명 / 백엔드 ~700명, 하루 ~1,000 머지.
- 출처: https://careersatdoordash.com/blog/how-doordash-transitioned-from-a-monolith-to-microservices/ , https://careersatdoordash.com/blog/inside-doordashs-service-mesh-journey-part-1-migration-at-scale/

### Stripe — Ruby 모놀리스 → 도메인 중심 마이크로서비스

- Ruby 모놀리스에서 이벤트 버스로 연결되는 도메인 중심 마이크로서비스로 진화. 결제 플로우: API Gateway → Payments → Risk → Ledger → Treasury → Notification.
- 주력은 여전히 Ruby, 핫패스에 Go(레이턴시 Ruby 500µs+ → Go 150µs). PCI 격리 등 규제 경계를 서비스 경계로 활용.
- **롤아웃 원칙**: 코드 작성 1개월 : **검증 2개월** 비율로 느리고 점진적으로 프로덕션 반영.
- 출처: https://www.infoq.com/presentations/stripe-api-pci/

## 15. 실패·회귀 사례 (microservices/serverless → monolith)

### Amazon Prime Video — 오디오/비디오 모니터링 서비스 (2023)

- **원 아키텍처**: 서버리스 분산(AWS Step Functions + Lambda + 중간 저장소 S3). 라이브 스트림 수천 개를 실시간 분석(block corruption, freeze, sync 오류 탐지).
- **병목(핵심)**: 예상 부하의 **약 5%에서 하드 스케일 한계**. 원인은 (1) Step Functions **state transition 과금**이 규모에서 폭발, (2) 프레임을 S3에 중간 저장하며 발생하는 **tier read/write 비용**. "building block 비용이 대규모에서 수용 불가."
- **바꾼 것**: 모든 컴포넌트를 **단일 프로세스(단일 Amazon ECS task)** 로 합침 → 데이터 전송을 in-memory로, S3 중간 저장 제거. **비용 90% 절감.**
- **⚠️ 중요 캐비엇**: 이건 **한 팀의 한 컴포넌트**(비디오 품질 모니터링) 이야기지 Prime Video 전체나 "마이크로서비스는 틀렸다"가 아님. **오케스트레이션 오버헤드가 실제 계산/전송보다 비싼 워크로드**(고빈도·대용량 데이터 이동)에서 분산이 역효과라는 사례. Adrian Cockcroft도 "serverless-first로 빠르게 검증 후 무거운 워크로드는 컨테이너로"라고 정리.
- 출처: https://www.thestack.technology/amazon-prime-video-microservices-monolith/ (원문 primevideotech 글은 현재 내려감), https://devops.com/microservices-amazon-monolithic-richixbw/

### Segment — 마이크로서비스 → 모놀리스(Centrifuge) 회귀

- **간 이유**: destination(연동 대상)별 워커 서비스로 fault isolation·모듈성 확보. 하지만 **월 3개꼴로 destination이 50개+로 증가**하며 역전.
- **왜 실패했나**: destination마다 개별 repo → 관리 불가. **공유 라이브러리 한 번 바꾸면 테스트 때문에 개발자 일주일**. 버전을 나누면 공유의 이점 자체가 사라짐. 진짜 fault isolation을 하려면 **큐×고객당 하나 = 10,000개+ 마이크로서비스**가 필요해 비현실적. 서비스마다 부하·CPU가 제각각이라 **획일적 auto-scaling 규칙이 안 맞음**.
- **회귀 결과**: 수백 개 repo → 단일 repo, 모든 워커가 같은 공유 라이브러리 버전, 배포가 분 단위, 하루 수십억 메시지 처리. "다시 신제품을 만들 수 있게 됐다." 모듈성·격리·가시성을 의도적으로 포기하고 **운영 오버헤드를 제거**.
- 시사점: 워크로드가 **수(고객/대상)에 비례해 선형 증식**하는 팬아웃형이면 서비스당 1개 매핑은 폭발. 작은 팀에서 서비스 수 > 사람 수가 되면 위험 신호.
- 출처: https://www.infoq.com/news/2020/04/microservices-back-again/ , https://news.ycombinator.com/item?id=23017160

## 16. 국내 사례

### 우아한형제들(배달의민족)
- **출발점**: 대부분 로직이 **MS SQL Server의 Stored Procedure**, API는 PHP. DBMS에 부하 집중 → 특정 요청 오류가 DBMS 부하 장애로 전파. Java/Spring 도입이 MSA 여정의 첫걸음.
- 장애 전파 차단 + 대량 트래픽 고성능 조회를 위해 **이벤트 기반 아키텍처 + CQRS** 도입.
- 출처: https://velog.io/@ariul-dev/우아콘-2020-배달의민족-마이크로서비스-여행기 , https://sihyung92.oopy.io/architecture/woowa-msa-travel

### 토스뱅크 — 은행 최초 코어뱅킹 MSA 전환("지금 이자 받기")
- **동기**: 모놀리식 코어뱅킹은 트래픽 몰릴 때 **특정 서비스만 scale-out 불가**, 한 컴포넌트 장애가 전체 마비. 가장 트래픽 많은 "지금 이자 받기"를 계정계에서 분리.
- **스택**: Spring Boot, Kotlin, JPA, Kafka, Redis on Kubernetes. 도메인 분리 = 고객정보/금리조회/이자회계처리.
- **정합성/동시성**: Redis Global Lock + JPA `@Lock`, **계좌 단위 row locking**으로 데드락 방지. Kafka로 트랜잭션 분리 → **DML 80회 → 50회**.
- **검증·전환**: 온라인 검증(실시간 old/new 결과 비교) + 배치 검증(staging 대량) + E2E(잔액 구간별·명의도용/사망 등 고객 상태 시나리오). **순차 배포**: 내부팀 → 전직원 → 일부 고객 → 전체. 빅뱅 탈피, 무중단 전환.
- **수치**: 거래 속도 평균 300ms 기준 **170배 개선**.
- 출처: https://toss.tech/article/slash23-corebanking

### 쿠팡 — 2013년 모놀리스 → 마이크로서비스
- **간 이유(5가지)**: 부분 장애의 전체 확대, 공유 모듈 유지불가, 통짜 확장, 전체 회귀 테스트 부담, **5줄 변경 배포에 2~3일** 대기.
- **자체 도구**: Vitamin 프레임워크(표준 라이브러리·스켈레톤), API 콜 모듈 라이브러리, **Vitamin MQ**(강결합 트랜잭션을 비동기 이벤트로 변환, DLQ로 서비스 다운 시에도 전달 보장).
- 출처: https://medium.com/coupang-engineering/how-coupang-built-a-microservice-architecture-fd584fff7f2b

### 카카오뱅크
- 모놀리스 → MSA 과정에서 서비스 간 의존성·트래픽 증가 대응. **Consul 기반 서비스 레지스트리 + 서비스 메시**로 서비스 디스커버리 도입.
- 출처: https://tech.kakaobank.com/tags/msa/ , https://tech.kakaobank.com/posts/2502-implementing-service-discovery-in-banking/

### 오늘의집(버킷플레이스)
- 모놀리스 → MSA, **비즈니스 멈추고 3개월 집중**해 백엔드 분리(Phase 1). 기간 내 임팩트 큰 것부터.
- 출처: https://www.bucketplace.com/post/2022-01-14-오늘의집-msa-phase-1-백엔드-분리작업/

### 핀다(FINDA) — 금융서비스 DB 분리
- 여신관리를 대출비교 DB에서 독립, 수신/자산/배치가 각자 DB를 갖는 구조로. 강결합 해소 + 대량 트래픽 대응. **DB 분리 실전기**로 참고할 만함.
- 출처: https://medium.com/finda-tech/금융서비스-msa-전환기-db-분리-1편-63d09e7ebe0e

## 17. 강한 정합성 도메인(헬스케어/예약/금융)과 MSA

- 서비스 경계를 넘는 순간 **전역 ACID를 잃음**. 분산 트랜잭션은 2PC 같은 취약한 코디네이터 대신 **Saga(로컬 트랜잭션 시퀀스 + 보상 트랜잭션)** 로 eventual consistency를 수용하는 게 정석. 구현은 choreography(이벤트 연쇄) vs orchestration(중앙 조정).
- **한계 인식**: 진짜 원자성(all-or-nothing, 완료 전 아무에게도 안 보임)이 필요하면 Saga로는 안 됨 — 복식부기 회계 등은 더 강한 보장 필요. 예약·결제처럼 **일부 스텝은 강한 정합성(계좌 row lock), 나머지는 이벤트 전파**로 나누는 하이브리드가 현실적(토스뱅크가 이 형태).
- 뱅킹에서도 MSA는 가능(Monzo 1,600개, 카카오뱅크, 토스뱅크) — 단 정합성이 필요한 코어는 **동시성 제어(Global Lock, row locking)** 를 명시적으로 설계하고 나머지를 비동기로 뗀다.
- 출처: https://temporal.io/blog/mastering-saga-patterns-for-distributed-transactions-in-microservices , https://learn.microsoft.com/en-us/azure/architecture/patterns/saga

## 18. 규모 데이터 한눈에

| 사례 | 서비스 수 | 팀/인원 | 기간 | 비고 |
|---|---|---|---|---|
| Uber | ~2,200 → 70 도메인 | 엔지니어 수천 | DOMA 2018~ | 서비스 half-life 1.5년 |
| Netflix | 700+ | 30+ 팀 | 2009~2016 (7년) | 3일 장애가 트리거 |
| Airbnb | SOA 다수 | 200→1,000명 | 2018~ | 배포 주당 15h 지연 |
| Monzo | 1,600+ | — | 2015~ | Go/Cassandra/K8s |
| DoorDash | 다수 | 백엔드 ~700 | 2019~2023 | 셀 기반, 500k RPS |
| Segment | 수백 → 1 (회귀) | 소규모 팀 | 2017 회귀 | 10,000개 필요 → 비현실적 |
| Prime Video | 분산 → 1 (회귀) | 1개 팀/1 컴포넌트 | 2023 | 5% 부하서 한계, 90%↓ |
| 토스뱅크 | 코어 3 도메인 분리 | — | slash23 | 300ms→170배, 순차배포 |
| 쿠팡 | 다수 | — | 2013~ | 5줄 배포 2~3일이 트리거 |

---

# Part 4 — 담론·논쟁 (2023~2026, 시니어용)

> 신뢰도 표기: 1차 출처(기업 블로그·당사자 발언)는 그대로, 2차/집계 통계는 [검증필요].

## 19. Modular Monolith vs Microservices — 논쟁 지형

핵심은 "둘 중 하나"에서 **"어디서 시작해서 어떤 단위로 쪼갤 것인가"** 로 프레임 이동.

- **Sam Newman**: 마이크로서비스 책 저자 본인이 "스타트업은 대개 모놀리스로 시작하는 게 낫다". monolith → 모듈화 → 필요한 것만 하나씩 서비스로.
- **Martin Fowler**: "Monolith First". 마이크로서비스로 성공한 사례 대부분이 모놀리스에서 출발해 점진 분해. 분해 전략은 Strangler Fig가 정석.
- **DHH**: "Majestic Monolith". 마이크로서비스는 "소규모 팀에게 '크게 생각하고 있다'는 착각을 심어주면서 정작 움직일 능력을 체계적으로 파괴한다".
- **Kelsey Hightower**: "Monoliths are the future" (GoTime, 2020). distributed monolith 비판의 원조격.
- **Shopify**: 분해 대신 Majestic Monolith 유지. Rails 단일 앱 약 280만 줄·50만 커밋, **Packwerk**로 코드 레벨 모듈 경계(명시적 public 인터페이스·의존성 자동 검사) 강제. "쪼개지 않되 경계는 강제한다"는 modular monolith 레퍼런스 구현.
- Modular Monolith 합의 정의: 단일 배포 단위 + 강한 내부 논리 경계. 2024→2025 담론에서 "대부분의 엔터프라이즈 앱에 맞는 출발점"으로 재평가.

출처: https://martinfowler.com/bliki/MonolithFirst.html , https://shopify.engineering/shopify-monolith , https://shopify.engineering/deconstructing-monolith-designing-software-maximizes-developer-productivity , https://changelog.com/posts/monoliths-are-the-future , https://www.infoq.com/articles/monolith-versus-microservices/ , https://foojay.io/today/monolith-vs-microservices-2025/

## 20. MSA → 모놀리스 회귀 사례 (기술적 사유)

### Amazon Prime Video — VQA 모니터링 서비스 (2023-03)
- 범위 주의: 전사가 아니라 **실시간 오디오/비디오 품질 모니터링 서비스 1개**. "아마존이 MSA를 버렸다"는 헤드라인은 과장.
- 원래 구조: Step Functions 오케스트레이션 + Lambda + 중간 저장소 S3.
- 병목: ① 스트림 초당 다수의 state transition → 계정 한도 도달, ② 프레임 S3 중간 저장 → Tier-1 S3 호출 + 데이터 전송 비용.
- 해결: 전 컴포넌트를 단일 ECS task로 통합, 프레임 전달을 프로세스 메모리 내부로 → **비용 약 90% 절감**.
- 반론: "MSA 실패가 아니라 서버리스 오케스트레이션이 부적합한 워크로드(고빈도·저지연 스트림)였을 뿐". 일반화 금지.
- 출처: https://thenewstack.io/return-of-the-monolith-amazon-dumps-microservices-for-video-monitoring/

### Segment — "Goodbye Microservices"
- destination마다 서비스 → 운영 오버헤드가 destination 수에 선형 비례, 140+ 서비스 관리가 "세금". 온콜이 상시 페이징.
- 140+ 서비스를 단일 서비스로 통합 → 워커 풀이 스파이크 흡수, 페이징 급감.
- 출처: https://www.twilio.com/en-us/blog/developers/best-practices/goodbye-microservices

### Istio — 과분산 되감기
- **istiod (v1.5, 2020)**: Pilot·Galley·Citadel·sidecar injector를 단일 바이너리로 통합. control plane을 마이크로서비스로 쪼갰다가 모놀리식으로 되돌린 케이스.
- **Ambient Mesh (v1.22 Beta, 2024)**: pod별 Envoy sidecar 제거 → 노드 단위 L4(ztunnel) + 선택적 L7(waypoint). 일부 케이스 90%+ CPU/메모리 절감.
- 출처: https://istio.io/latest/blog/2020/istiod/ , https://istio.io/latest/blog/2024/ambient-reaches-beta/

## 21. "적정 서비스 크기" — nanoservices / macroservices / Uber DOMA

- **Nanoservices 안티패턴**: 함수 수준까지 쪼개면 네트워크 홉·직렬화·배포 단위 폭증. 경계 비용 > 경계 이득.
- **Uber DOMA**: 마이크로서비스 ~2,200개, 단일 root cause 디버깅에 12개 팀 ~50개 서비스. "networked monoliths" — "can't live with them, can't live without them."
  - Domain(서비스 묶음) + Layer 5계층(Infra→Business→Product→Presentation→Edge, 하위 의존만 허용) + 도메인별 Gateway 단일 진입점 + Extension(logic/data).
  - 2,200개 → 70개 도메인. 온보딩 25~50% 단축. "마이크로서비스의 유연함 + 모놀리스의 편의성"이지 MSA 부정이 아님.
- 출처: https://www.uber.com/en-IT/blog/microservice-architecture/

## 22. 2024~2026 관점 변화 — "microservices tax" / distributed monolith

- **Microservices Tax**: 비용을 세 화폐로 — Latency, Consistency, Cognitive Load. 증상: 설명 안 되는 지연, 8개 팀이 한 Zoom에 모여야 풀리는 장애.
- **Distributed Monolith**: 동기 point-to-point 호출(A→B→C)로 얽힌 서비스망은 물리적으로만 분리 — 함수 호출을 네트워크 너머로 던지고 돌아오길 기도하는 구조(Kelsey Hightower). 분산 비용만 내고 이득은 없는 최악 조합.
- [검증필요] "MSA 도입 조직 42%가 modular monolith로 회귀", "개발자 55%가 테스트 어려움" 등의 수치는 2차 집계 매체(byteiota 등) 순환 인용 — CNCF 설문 원본 미확인. 포스트에 쓰려면 원 설문 재확인 또는 "일부 매체 집계" 단서 필수.
- 출처: https://gabezen.com/thoughts/microservices-coordination-tax/ , https://byteiota.com/microservices-tax-42-ditch-architecture-in-2026/ (통계 원출처 미확인)

## 23. 조직 관점 — Conway's Law × Team Topologies

- Conway's Law: 팀 경계가 곧 소프트웨어 경계. 서비스 경계 논쟁은 결국 조직 설계 논쟁.
- Inverse Conway Maneuver: 원하는 아키텍처를 얻기 위해 팀 구조를 먼저 바꾼다.
- Stream-aligned team: 가치 흐름 단위로 팀 정렬 → 서비스 경계 = 팀 경계 = 도메인 경계.
- **Cognitive Load가 크기의 기준**: 서비스 크기는 소유 팀의 인지 부하 한계로 정한다. nanoservice(경계 과다)도 거대 서비스(부하 과다)도 이 기준으로 걸러짐 — Team Topologies의 핵심 기여.
- 출처: https://www.softwareseni.com/applying-team-topologies-to-reduce-cognitive-load-and-burnout/ , https://candost.blog/books/team-topologies-book-review-summary-and-notes/

---

# Part 5 — 전환(decomposition) 기술 패턴 심화

## 24. Strangler Fig — 라우팅 계층 설계와 롤백

- 구조: 시스템 경계의 facade(interceptor)가 URL 패턴·요청 타입 기준으로 레거시/신규 분기. transform → coexist → eliminate 3단계.
- **Gateway 기반**: gateway가 facade 겸 라우팅 테이블 소유(서비스는 소유 안 함) — 단일 control plane에서 마이그레이션 제어·즉시 롤백·A/B. **Proxy 기반**: nginx/envoy를 얇게 두고 인프라 레이어에서 재지향, 레거시 코드 무변경.
- 전환 단위: 엔드포인트/경로 prefix. 이미 decouple된 기능부터, 모니터링 데이터 기반 반복. facade가 트래픽 가중치를 쥐어 점진 canary 가능.
- 롤백: 라우팅 config만 변경해 100% 레거시 복귀 — 코드 재배포 없는 롤백이 안전성의 근거.
- 출처: https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-decomposing-monoliths/strangler-fig.html , https://circleci.com/blog/strangler-pattern-implementation-for-safe-microservices-transition/

## 25. DB 분해

- **Shared DB 안티패턴**: 여러 서비스가 한 DB/schema 공유 → implementation coupling → distributed monolith. "DB를 공유하거나 coordinated deploy가 필요하면 이미 distributed monolith다"가 판별 기준.
- **논리 분리 → 물리 분리**: 같은 물리 DB 안에서 테이블 소유권을 서비스별로 먼저 확정, 그 다음 물리 이전. 각 테이블은 단일 서비스 소유, cross-service join은 API 호출로 대체, 경계 넘는 트랜잭션은 Saga + eventual consistency.
- **MongoShake**: MongoDB oplog 기반 복제. full sync + incremental sync. 성공 동기화된 oplog timestamp를 checkpoint로 보관 → 재시작 시 무손실 이어받기. sharding이면 shard별 병렬 크롤링. tunnel은 Direct(target에 직접 write)/RPC.
- **CDC 무중단 컷오버 (범용)**: ① bulk load 시 스냅샷 시점의 log 위치(LSN/binlog/oplog ts) 기록 → CDC는 그 위치부터 ② replication lag 모니터링(목표 <1초) ③ 검증 3단계: row count → checksum/MD5 샘플 → 앱 테스트 스위트 ④ 컷오버: source read-only → lag 0 수렴 대기 → 최종 검증 → connection string 교체 → **source를 24시간+ read-only 유지해 롤백 보전**.
- 실패 모드: sequence drift(setval로 선제 조정), circular FK(제약 일시 해제), encoding/collation 불일치, schema drift.
- "유지보수 창은 초 단위여야 한다. lag이 분 단위면 pre-cutover baseline을 잘못 잡은 것."
- 출처: https://www.oreilly.com/library/view/monolith-to-microservices/9781492047834/ch04.html , https://github.com/alibaba/MongoShake , https://streamkap.com/resources-and-guides/zero-downtime-database-migration-cdc

## 26. 데이터 일관성 — dual-write / outbox / saga

- **dual-write problem**: 로컬 DB write 후 event publish 전에 broker가 죽으면 saga가 조용히 멈춰 재개 불가. orchestration·choreography 모두 영향.
- **Transactional Outbox**: 상태 변경 + event를 같은 로컬 트랜잭션으로 outbox 테이블에 기록 → relay(Debezium CDC 등)가 Kafka로 발행. at-least-once → 소비자 idempotency 필수.
- **dual-write 대안 5패턴(Red Hat)**: Modular Monolith / 2PC·XA(blocking, K8s 부적합) / Orchestration Saga / Choreography Saga(+outbox 또는 event sourcing) / Parallel Pipelines(listen-to-yourself).
- **Orchestration vs Choreography**: orchestrator(Camunda/Conductor 등)는 상태가 한 곳 — 관측·디버깅 유리, 대신 복잡+병목. choreography는 Kafka partition/consumer group에 자연 매핑 — 확장·느슨한 결합, 대신 전역 saga 상태가 암묵적(많은 팀이 별도 event tracker를 만듦).
- **실패 처리**: 보상 트랜잭션은 rollback이 아니라 semantic reversal — 보상 자체도 실패 가능. **pivot transaction** 이후는 forward recovery(성공까지 retry). timeout 핸들러가 보상 개시자. 모든 step에 idempotency key + dedup store. 실패한 보상은 DLQ + alerting + runbook.
- **event sourcing**: event store append가 상태 저장 + 메시지 큐를 겸함 → dual-write 자체가 소멸. 대신 프로그래밍 모델이 낯설다는 비용.
- 출처: https://developers.redhat.com/articles/2021/09/21/distributed-transaction-patterns-microservices-compared , https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html

## 27. 분해 경계 결정

- 세 접근: **DDD bounded context**(context가 제공하는 capability 중심) / **데이터 접근 패턴**(함께 read/write되는 데이터 클러스터, 호출·쿼리 그래프 분석) / **팀 구조**(Conway).
- 잘못 그었을 때 증상: distributed monolith(DB 공유·동시 배포), **chatty services**(한 유스케이스가 여러 서비스 왕복 — 경계가 트랜잭션 경계를 가름), coarse/fine 양극단 모두 실패.
- bounded context는 불변이 아님 — split/merge/모델 정제로 reshape. 이미 decouple된 기능부터 시작해 monitoring·tracing 데이터 기반 반복(Netflix 방식).
- 출처: https://www.cerbos.dev/blog/determining-service-boundaries-and-decomposing-monolith , https://arxiv.org/pdf/2003.02603

## 28. 마이그레이션 검증 — Branch by Abstraction / Parallel Run / Dark Launch

- **Branch by Abstraction**: 코드베이스 내부에서 abstraction layer로 old/new 공존 → 소비자 하나씩 이전 → old 제거. trunk 위에서 진행. Strangler Fig는 시스템 경계, 이것은 코드베이스 내부 — 함께 쓴다.
- **Parallel Run**: old/new 동시 실행 + 출력 비교로 정확성 검증.
- **Dark Launch / Shadow Traffic**: 신규 경로에 production 트래픽을 흘리되 응답은 숨김. DB 마이그레이션에 특히 유용 — 양쪽 DB shadow write + read는 레거시(system of record) 유지 → 비교가 깨끗해지면 신규를 system of record로 승격. (Airbnb dual read + comparison framework, DoorDash scream test와 같은 계열)
- 출처: https://trunkbaseddevelopment.com/branch-by-abstraction/ , https://oneuptime.com/blog/post/2026-01-30-dark-launch-patterns/view

## 29. 공통 코드/라이브러리

- shared library는 서비스를 라이브러리에 결합시킴 — 사소한 변경에도 cross-team 조정 → 오버헤드만 늘어난 모놀리스로 회귀. 특히 도메인 로직 공유를 경계.
- 기준: **서비스 간 중복은 허용, 서비스 내부 중복은 불가**. 복잡한 공통 로직은 라이브러리보다 별도 서비스 추출. 순수 기술 관심사(HTTP client, connection pool, circuit breaker)만 공용 라이브러리 후보.
- 출처: https://medium.com/standard-bank/microservices-dont-create-shared-libraries-2e803b033552 , https://www.grahamlea.com/2016/04/shared-libraries-in-microservices-bad-advice/

---

# Part 6 — MSA 아키텍처 유형·스타일 (웹 서치 2026-07, 시니어용)

## 30. 시스템 수준 아키텍처 스타일

### Event-Driven Architecture (EDA)
- **토폴로지(Mark Richards)**: Broker(중앙 조율자 없이 broker 경유 이벤트 연쇄 — 확장성·decoupling↑, 워크플로 제어·에러 복구 어려움) vs Mediator(오케스트레이션 엔진이 상태·에러·재시도 관리 — 제어 쉬움, mediator가 병목/결합점). 이 구분이 곧 choreography vs orchestration 선택과 직결.
- **Fowler 4분류** ("event-driven"이 뭉뚱그리는 4가지): ① Event Notification(얇은 이벤트 + 필요 시 소스 콜백 — 흐름 추적 불가, 역방향 호출 부하) ② Event-Carried State Transfer(이벤트에 상태를 실어 수신자가 로컬 복제본 유지 — 콜백 제거·resilience↑, 데이터 중복·eventual consistency) ③ Event Sourcing ④ CQRS. 넷을 섞어 쓰면 아키텍처 실수의 근원.
- 출처: https://martinfowler.com/articles/201701-event-driven.html

### CQRS
- 읽기/쓰기 모델 분리(Greg Young). 구현 스펙트럼: 같은 DB 다른 모델(가벼움) → 물리 분리 read store(이벤트/CDC로 denormalized view projection, 읽기·쓰기 독립 scale-out).
- **eventual consistency 창**(쓰기→read model 반영 지연)을 도메인/UX가 감당 가능한지가 도입 전제. Fowler 경고: 대부분은 CRUD로 충분, 전체 시스템 기본 아키텍처로 삼지 말고 경합 심하거나 읽기/쓰기 비대칭 큰 bounded context에만.
- 출처: https://martinfowler.com/bliki/CQRS.html , https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs

### Event Sourcing
- 상태 변경 전체를 append-only 불변 이벤트 시퀀스로, 현재 상태는 replay 파생물. expected version 체크로 optimistic concurrency. snapshot으로 replay 비용 절감.
- 쓸 곳: 감사 추적·규제, 변경 이력이 도메인 가치(금융 원장, 예약 상태 전이), CQRS 이벤트 소스. 쓰면 안 되는 곳: 단순 CRUD, 이벤트 스키마가 자주 바뀌는 초기 도메인(과거 이벤트 마이그레이션 지옥).
- 출처: https://martinfowler.com/eaaDev/EventSourcing.html

### Cell-Based Architecture
- cell = compute+storage+config의 자기완결 슬라이스. 전체 스택 scale-up 대신 cell 복제로 scale-out, **blast radius**를 cell 단위로 제한. gray failure(성능 저하형 간헐 장애)에 강함 — 문제 cell 트래픽 재라우팅.
- **cell router**는 얇고 단순하게(DNS 수준~Gateway+키-투-셀 매핑) — 라우터 자신이 장애점이 되면 안 됨.
- 사례: DoorDash(Envoy mesh zone-aware routing → AZ 기반 cell, cross-AZ 비용 절감 부수 효과), Slack(AZ-scoped cell), AWS Well-Architected 정식화.
- 트레이드오프: 셀 간 데이터 파티셔닝·리밸런싱, cross-cell 트랜잭션 회피, 운영 복잡도.
- 출처: https://www.infoq.com/articles/cell-based-architecture-distributed-systems/ , https://docs.aws.amazon.com/wellarchitected/latest/reducing-scope-of-impact-with-cell-based-architecture/

### Domain-Oriented (Uber DOMA류)
- 설계 단위를 개별 서비스가 아니라 도메인(1~수십 개 서비스 묶음)으로. 도메인 Gateway가 단일 진입점 — 내부 서비스·테이블 은닉, 내부 rewrite 시 상류 마이그레이션 불필요, 경계 강제 담당. 5계층(Infra→Business→Product→Presentation→Edge)으로 호출 방향 규율. Extension(logic 플러그인 + protobuf `Any` data).
- 출처: https://www.uber.com/us/en/blog/microservice-architecture/

### Serverless Microservices / Space-Based (짧게)
- FaaS 조합: API Gateway→Lambda→관리형 저장소, 이벤트 소스→함수 fan-out. 적합: 스파이크성·간헐 워크로드. 부적합: 상시 고부하(cold start), 장시간 실행. 
- Space-based: DB를 병목에서 제거, processing unit + in-memory data grid 복제. 극단적 동시성 특수 케이스용.
- 출처: https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/serverless

## 31. 서비스 내부 아키텍처

### Layered vs Hexagonal vs Onion vs Clean
- Hexagonal(Cockburn)·Onion(Palermo)·Clean(Martin)은 같은 원리의 세 변주 — 비즈니스 로직 중심, 의존성은 안쪽으로(DIP). **런타임 차이는 거의 없고 어휘·계층 세분도 차이.**
- 진짜 차이는 Layered와의 차이 = **의존성 역전 유무**. Layered는 도메인이 ORM/DB에 직접 의존 → 교체·단위 테스트 어려움. Hex/Onion/Clean은 도메인이 port(인터페이스)에만 의존 → DB를 in-memory fake로 바꿔 도메인만 격리 테스트.
- Hexagonal 구조: 코어가 port 정의, 어댑터가 구현. driving(inbound: API/컨슈머/test) / driven(outbound: DB/MQ/외부 API) 대칭.
- 비용: 인터페이스·어댑터·DTO 보일러플레이트. 도메인 로직 얇은 단순 CRUD 서비스엔 과설계 — layered가 낫다.
- 출처: https://alistair.cockburn.us/hexagonal-architecture/ , https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html

### DDD 전술 패턴과의 접점
- **Aggregate** = 일관성 경계 = 로컬 트랜잭션 경계 → saga의 local transaction 단위, outbox 이벤트 발행 단위.
- **Repository** = outbound port(도메인이 인터페이스 소유), ORM 구현체가 driven adapter — 도메인은 저장 기술을 모름.
- **Domain Event**: aggregate 발행 → application layer 수집 → outbox 경유 integration event로 외부 발행. EDA와 서비스 내부가 만나는 지점.
- **Application Service** = inbound port. 트랜잭션 경계·오케스트레이션 담당, 도메인 규칙은 aggregate에.
- 출처: https://martinfowler.com/bliki/DDD_Aggregate.html , https://learn.microsoft.com/en-us/dotnet/architecture/microservices/microservice-ddd-cqrs-patterns/

### 왜 MSA에서 Hexagonal이 권장되나
1. 인프라 교체 자유도(서비스별 저장소·메시징이 다르고 자주 바뀜 — 어댑터 교체로 흡수)
2. 테스트 격리(MSA는 통합 테스트가 비싸서 네트워크 없는 도메인 단위 테스트가 특히 값짐)
3. 경계 명료화(inbound/outbound port로 서비스 계약이 코드 구조에 드러남, Strangler Fig 이관 시 어댑터만 교체)

## 32. 지원 인프라 패턴 × 스타일 매핑

| 패턴 | 역할 | 조합 |
|---|---|---|
| API Gateway | 단일 진입점, 라우팅·인증·rate limit | DOMA 도메인 게이트웨이, cell router로도 |
| BFF | 클라이언트별 전용 백엔드(집계·성형) | Gateway 뒤 배치, Gateway의 클라이언트 단위 특수화 |
| Service Mesh | 통신(mTLS·retry·관측)을 데이터플레인으로 | cell-based의 zone-aware routing (DoorDash) |
| Sidecar/Ambient | mesh 배치 방식 — ambient는 사이드카 제거(L4 ztunnel + L7 waypoint opt-in) | 대규모에서 사이드카 비용 → ambient 추세 |
| Saga | 서비스 간 일관성을 보상 트랜잭션 체인으로 | orchestration/choreography 축, aggregate = local tx |
| Outbox | 쓰기+이벤트 발행을 한 로컬 트랜잭션으로(dual-write 해결) | EDA/ECST/ES의 신뢰성 발행 필수 요소 |
| Circuit Breaker | Closed→Open→Half-Open으로 cascading failure 방지 | 동기 호출 많은 구간, cell blast radius와 상보 |

## 33. 선택 기준과 조합

- 워크로드: 읽기/쓰기 비대칭·경합 → CQRS. 변경 이력이 도메인 가치 → Event Sourcing. 비동기 파급이 본질 → EDA(통지=notification, 수신자 자립=ECST). 다단계 트랜잭션+롤백 → Saga(가시성 중요=orchestration, 단순·자율=choreography). 격리·SLA → cell. 스파이크성 → serverless.
- 조직: 서비스 폭발·팀 경계 흐림 → DOMA류 도메인+게이트웨이 재정렬. 스택 다양·교체 잦음 → 내부는 Hexagonal.
- 조합 사례: EDA+CQRS+ES(+Outbox), Cell+Mesh(DoorDash), DOMA+Gateway/BFF, Saga+Outbox+Hexagonal(aggregate=local tx 경계).
- **공통 원칙: 단일 스타일 전역 적용이 아니라 bounded context 단위로 국소 적용.** CQRS·ES·cell 같은 고비용 패턴은 복잡도를 정당화하는 컨텍스트에만.
- 출처: https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/ , https://microservices.io/patterns/index.html
