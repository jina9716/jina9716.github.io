---
layout: post
title: "Redshift에서 Snowflake까지 — 데이터 파이프라인 구축기"
subtitle: "NestJS Consumer + Glue를 걷어낸 CDC 파이프라인 전환 기록"
date: 2026-01-17
category: blog
tags: [Kafka, Snowflake, DataPipeline, MongoDB, CDC]
---

서비스 데이터를 유관부서에 안정적으로 제공하기 위해 데이터 파이프라인을 구축했고, 이후 Redshift 기반 레거시 구조를 Snowflake로 갈아끼웠다. 그 과정과 결과를 기록으로 남긴다.

## 왜 파이프라인이 필요했는가

유관부서가 서비스 데이터에 접근하는 방식 자체가 문제였다.

- 운영 DB 직접 조회 — MongoDB에 그대로 쿼리를 날려 운영 DB에 부하가 갔다
- 수동 추출 — 시간이 많이 들고 휴먼 에러가 잦았다
- 분석 환경 부재 — 무거운 분석 쿼리를 돌릴 전용 환경이 없었다

운영에 영향을 주지 않으면서 자유롭게 데이터를 다룰 수 있는 별도의 분석 환경이 필요했다.

## 레거시 아키텍처와 한계

처음에는 Redshift 기반으로 구성했다. 흐름은 다음과 같다.

1. Kafka MongoDB Source Connector로 CDC 이벤트 발행
2. NestJS Consumer가 메시지를 받아 AuroraDB에 적재
3. AWS Glue Crawler가 스키마를 인식하고 ETL Job으로 변환
4. 변환된 데이터를 Redshift에 적재

### 이 구조의 문제

NestJS Consumer 운영 부담이 컸다. 새 컬렉션 하나 붙일 때마다 Entity 정의, Controller 작성, Knex 마이그레이션, 서버 배포까지 코드 레벨 작업이 줄줄이 따라왔다. MongoDB의 유연한 스키마를 PostgreSQL의 정적 스키마로 매핑하다 보니 타입 변환 이슈도 잦았고, 배열 필드는 Redshift에서 JSON 문자열로 저장되는데 대소문자 구분이 안 돼서 키를 snake_case로 다 바꿔야 했다.

AWS Glue ETL도 만만치 않았다. timestamp가 강제로 UTC로 변환되는 이슈, MERGE 모드에서의 정합성 문제 등 Job마다 개별 핸들링이 필요했다. Glue Worker 수보다 동시 실행 Job이 많으면 `Max concurrent runs exceeded` 에러가 났다. 운영은 Worker 5로 두고 동시 실행 Job 5개 미만으로 시간대를 쪼개서 회피하는 방식이었다.

직접적인 트리거는 Redshift 인스턴스 타입 지원 종료였다. `dc2.large`가 단종 예정이라 인스턴스 타입을 교체해야 했고, 그러면 비용이 올랐다. 한정된 리소스로 인한 성능 저하도 같이 누적되고 있었다. 어차피 갈아엎어야 한다면 구조까지 정리하자고 판단했다.

## Snowflake 전환 결정

Redshift와 Snowflake를 비교 검토하고 약 3주(2024년 9월 말~10월 중순) PoC를 돌렸다.

| 항목 | Redshift | Snowflake |
|------|----------|-----------|
| 스케일링 | 수동 리사이즈 | 자동 스케일링 (Warehouse 크기 변경) |
| 비용 모델 | 상시 클러스터 과금 | 사용량 기반 (사용 시만) |
| 동시성 | WLM 설정 필요 | 멀티 클러스터 웨어하우스 |
| 유지보수 | Vacuum, Analyze 필수 | 거의 없음 |
| ETL | 외부 도구(Glue) 의존 | SQL 기반 내장 (Stream, Task) |
| 모니터링 | CloudWatch + 별도 구성 | Snowsight 통합 |

PoC 결과 월 운영 비용은 약 $1,238 → $1,033 으로 17% 정도 줄어드는 것으로 추산됐다. 절대 비용도 비용이지만, 제일 크게 끌렸던 건 NestJS Consumer와 AWS Glue를 걷어내고 Snowflake 내장 기능만으로 CDC ETL을 돌릴 수 있다는 점이었다.

## 신규 아키텍처

<img src="/assets/images/data-pipeline/architecture-comparison.svg" alt="레거시(Redshift 기반) vs 신규(Snowflake 기반) 데이터 파이프라인 아키텍처 비교" />

NestJS Consumer를 S3 Sink Connector로 대체하면서 파이프라인이 짧아졌다. NestJS Consumer + AuroraDB + AWS Glue ETL 세 단계를 걷어내고, Redshift는 Snowflake로 교체했다. 코드 배포 없이 커넥터 설정만으로 새 컬렉션을 붙일 수 있게 됐다.

### MongoDB Source Connector

MongoDB Change Stream으로 변경 이벤트를 Kafka 토픽에 발행한다.

```json
{
  "connector.class": "com.mongodb.kafka.connect.MongoSourceConnector",
  "tasks.max": "1",
  "batch.size": "1000",
  "change.stream.full.document": "updateLookup",
  "heartbeat.interval.ms": "1800000",
  "collection": "orders",
  "database": "myapp_db",
  "topic.prefix": "mongo",
  "output.json.formatter": "com.mongodb.kafka.connect.source.json.formatter.SimplifiedJson",
  "pipeline": "[{\"$project\":{\"fullDocument.__v\":0}}]",
  "poll.await.time.ms": "5000",
  "poll.max.batch.size": "1000",
  "startup.mode": "copy_existing"
}
```

핵심 설정은 다음과 같다.

- `change.stream.full.document: updateLookup` — update 이벤트 시 변경된 문서 전체를 포함
- `startup.mode: copy_existing` — 커넥터 최초 실행 시 기존 데이터를 모두 복제 (`latest`로 두면 이후 변경분만 캡처)
- `pipeline` — `__v` 같은 불필요한 필드 제외

토픽 컨벤션은 `{prefix}.{database}.{collection}`, Replication Factor 3, 7일 보관으로 잡았다.

### S3 Sink Connector — 레거시 Consumer 대체

이전에는 NestJS Consumer가 Kafka 메시지를 받아 AuroraDB에 적재했지만, 이제 S3 Sink Connector가 곧장 S3에 떨군다.

```json
{
  "connector.class": "io.confluent.connect.s3.S3SinkConnector",
  "s3.region": "ap-northeast-2",
  "topics.dir": "cdc-logs",
  "flush.size": "100",
  "tasks.max": "3",
  "s3.compression.type": "gzip",
  "format.class": "io.confluent.connect.s3.format.json.JsonFormat",
  "partitioner.class": "io.confluent.connect.storage.partitioner.DefaultPartitioner",
  "storage.class": "io.confluent.connect.s3.storage.S3Storage",
  "rotate.schedule.interval.ms": "5000",
  "timezone": "Asia/Seoul"
}
```

JSON + gzip 포맷은 Snowflake External Table에서 직접 읽기에 적합하고, `flush.size: 100` + `rotate.schedule.interval.ms: 5000` 조합으로 5초마다 100개 단위로 파일이 떨어진다. 이걸로 NestJS Consumer 서버 관리, Entity 정의, 마이그레이션, 배포 프로세스를 같이 걷어낼 수 있었다.

### Snowflake CDC: External Table → Stream → Task → Table

<img src="/assets/images/data-pipeline/cdc-flow.svg" alt="Snowflake CDC ETL 4단계 흐름 — External Table, Stream, Task, Target Table" />

Snowflake에서는 SQL만으로 CDC ETL을 구성할 수 있다. 4단계로 풀어 보면 이렇다.

**1단계 — External Table: S3 데이터를 Snowflake에서 직접 참조**

```sql
CREATE OR REPLACE EXTERNAL TABLE external_table.example_collection(
  cluster_time variant AS parse_json(
    JSON_EXTRACT_PATH_TEXT(value, 'clusterTime.$timestamp')
  ),
  operation_type varchar AS (
    JSON_EXTRACT_PATH_TEXT(value, 'operationType')
  ),
  _id varchar AS (
    JSON_EXTRACT_PATH_TEXT(value, 'documentKey._id')
  ),
  full_document variant AS (
    parse_json(value):fullDocument::variant
  )
)
LOCATION = @data_stage/cdc-logs/topic.db.collection
FILE_FORMAT = (TYPE = json COMPRESSION = gzip REPLACE_INVALID_CHARACTERS = true);
```

S3의 JSON 파일을 데이터 이동 없이 Snowflake에서 테이블처럼 조회할 수 있다. `cluster_time`을 파싱해두면 이후 MERGE 단계에서 중복 제거 키로 쓴다.

**2단계 — Stream: 변경 감지**

```sql
CREATE OR REPLACE STREAM example_collection_stream
  ON EXTERNAL TABLE external_table.example_collection
  INSERT_ONLY = true;
```

Stream은 External Table에 새로 추가된 행을 자동 추적한다. External Table은 append-only이기 때문에 `INSERT_ONLY = true`를 쓴다.

**3단계 — Target Table 생성**

```sql
CREATE TABLE public.example_collection (
  _id varchar(24),
  col_a varchar COMMENT '컬럼 A 설명',
  col_b varchar COMMENT '컬럼 B 설명',
  col_c number COMMENT '컬럼 C 설명',
  created_at timestamp_ltz COMMENT '생성일',
  updated_at timestamp_ltz COMMENT '갱신일'
) COMMENT = '테이블 설명';
```

모든 컬럼에 COMMENT를 다는 걸 컨벤션으로 잡았다. 유관부서가 별도 문서 없이도 테이블 구조를 이해할 수 있게 하기 위해서다. PII(이름, 생년월일, 전화번호, 이메일)에는 마스킹 정책을 걸었다.

**4단계 — Task: 스케줄 기반 MERGE 실행**

```sql
CREATE OR REPLACE TASK example_collection_cdc
  WAREHOUSE = compute_wh
  AFTER external_table_refresh_task
AS
  MERGE INTO public.example_collection target
  USING (
    SELECT
      ROW_NUMBER() OVER (
        PARTITION BY _id
        ORDER BY cluster_time:t::number DESC, cluster_time:i::number DESC
      ) AS row_num, *
    FROM public.example_collection_stream
    WHERE _id IS NOT NULL
    QUALIFY row_num = 1
  ) src ON target._id = src._id
  WHEN MATCHED AND src.operation_type = 'delete' THEN DELETE
  WHEN MATCHED AND src.operation_type IN ('insert', 'update') THEN UPDATE SET
    col_a = src.full_document:colA::varchar,
    col_b = src.full_document:colB::varchar,
    col_c = src.full_document:colC::number,
    created_at = src.full_document:createdAt::timestamp_ltz,
    updated_at = src.full_document:updatedAt::timestamp_ltz
  WHEN NOT MATCHED AND src.operation_type IN ('insert', 'update') THEN INSERT
    VALUES (
      src._id,
      src.full_document:colA::varchar,
      src.full_document:colB::varchar,
      src.full_document:colC::number,
      src.full_document:createdAt::timestamp_ltz,
      src.full_document:updatedAt::timestamp_ltz
    );
```

이 Task가 하는 일은 셋이다.

1. 같은 `_id`에 여러 이벤트가 쌓여 있으면 `cluster_time` 기준 최신 것만 사용 (`ROW_NUMBER` + `QUALIFY`)
2. `operation_type`에 따라 INSERT / UPDATE / DELETE를 하나의 MERGE 문으로 처리
3. `AFTER external_table_refresh_task`로 External Table Refresh 완료 후 실행되도록 의존성을 건다

별도 스케줄이 필요한 Task는 CRON으로 독립 실행하면서 내부에서 External Table Refresh를 직접 부른다.

```sql
CREATE OR REPLACE TASK another_collection_cdc
  WAREHOUSE = compute_wh
  SCHEDULE = 'USING CRON 50 7 * * * Asia/Seoul'
AS
  EXECUTE IMMEDIATE
  $$
  BEGIN
    ALTER EXTERNAL TABLE external_table.another_collection REFRESH;
    MERGE INTO public.another_collection target
    USING (...) src ON target._id = src._id
    WHEN MATCHED AND src.operation_type = 'delete' THEN DELETE
    WHEN MATCHED THEN UPDATE SET ...
    WHEN NOT MATCHED THEN INSERT VALUES (...);
  END;
  $$;
```

## Snowflake 활용

파이프라인을 깔고 나서는 Snowflake 기능을 같이 붙여가며 분석 환경을 채웠다.

### Dynamic Table — 자동 갱신되는 파생 테이블

기본 테이블에 의존하는 파생 테이블을 Dynamic Table로 잡으면 원본이 변할 때 자동으로 증분 처리된다. `TARGET_LAG = '5 minutes'` 같은 식으로 갱신 주기를 선언만 하면 된다. 별도 통계 배치를 따로 짜고 스케줄을 관리할 필요가 없어진 게 컸다.

### Flatten — 중첩 JSON 처리

MongoDB에서 넘어온 도큐먼트는 중첩 JSON이 많다. `LATERAL FLATTEN`으로 배열을 정규화된 행으로 풀어낼 수 있었다.

```sql
SELECT
  t.item_id,
  f.value:date::date AS event_date,
  f.value:count::number AS event_count
FROM items t,
LATERAL FLATTEN(input => t.nested_data) f;
```

### 시계열 함수

서비스 특성상 시계열 분석이 잦았는데, 전용 함수가 도움이 됐다.

- `TIME_SLICE` — 시계열을 분/시/일 단위로 버케팅
- `DATE_TRUNC` — 타임스탬프를 원하는 단위로 절삭
- `ASOF JOIN` — 시간 기반 퍼지 조인으로 서로 다른 데이터셋을 시간 근접으로 매칭
- `RANGE BETWEEN` — 윈도우 함수에서 시간 범위 기반 집계

Redshift에는 `ASOF JOIN`, `TIME_SLICE` 같은 함수가 없어서 일/월간 집계 쿼리를 직접 풀어 써야 했는데, 이쪽이 훨씬 단순해졌다.

## 결과

### 쿼리 성능과 적재 배치

<img src="/assets/images/data-pipeline/performance-comparison.svg" alt="Redshift vs Snowflake 처리 시간 비교 — 진료 내역 조회 2.17배, 집계 통계 15배, 적재 배치 3.4배" />

X-Small Warehouse만으로 대부분의 쿼리가 무리 없이 돌아갔다. 동일 배치(4개 테이블 업데이트 SP)가 Redshift에서 40초였는데 Snowflake에서는 5초였다. Glue는 Worker 수만큼만 동시 실행이 가능해서 시간대를 쪼개야 했지만, Snowflake Task는 Warehouse queue로 알아서 순차 실행됐다.

전환 후 며칠간 Task 실행 이력을 보면 9분 43초, 7분 1초, 7분 30초 정도로 안정적으로 떨어졌다.

### 운영 개선

- Snowsight 한 화면에서 쿼리, Task 그래프, 비용 추적까지 봤다
- Task History/Task Graph로 의존성과 상태를 시각적으로 추적
- 모니터링 구성을 별도로 짜지 않아도 됐다

## 회고

NestJS Consumer와 AWS Glue를 걷어내고 커넥터 + Snowflake 내장 기능으로 대체하면서 운영 부담이 많이 줄었다. 새 컬렉션을 붙일 때 코드 배포가 필요 없어진 게 체감상 가장 컸고, Stream + Task + MERGE 조합만으로 별도 ETL 도구 없이 CDC가 돌아가는 것도 덤이었다.

MongoDB 쪽 스키마 변경은 여전히 파이프라인에서 제일 까다로운 부분이다. 어느 필드가 언제 추가/변경되는지 따라가기 어렵고, 운영에서는 이 부분을 관성적으로 체크하는 프로세스가 필요하다고 느꼈다.

Kafka lag, S3 적재 상태, Task 실행 이력을 같이 보지 않으면 어디서 막혔는지 잡기 어려웠다. 모니터링은 초기부터 같이 깔아두는 편이 낫겠다고 체감했다.

이 사례는 Snowflake 데이터 혁신 세미나에서 발표했다. 발표 후 질의에서 다른 회사들도 비슷한 지점에서 고민하고 있다는 걸 확인할 수 있었다.

## 다음 스텝

- Amplitude / Google Analytics 데이터를 Snowflake에 함께 올려 서비스 데이터와 크로스 분석
- Snowflake ML 도입 검토
