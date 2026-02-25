---
layout: post
title: "Kafka에서 Snowflake까지 — 데이터 파이프라인 구축기"
subtitle: "Redshift 레거시 파이프라인을 Snowflake로 전환한 실제 경험"
date: 2026-01-20
tags: [Kafka, Snowflake, DataPipeline, MongoDB, CDC]
---

서비스 데이터를 유관부서에 안정적으로 제공하기 위해 데이터 파이프라인을 구축하고, 레거시 Redshift 기반 아키텍처를 Snowflake로 전환한 경험을 공유합니다.

## 왜 데이터 파이프라인이 필요했는가

유관부서가 서비스 데이터에 접근하는 방식에 근본적인 문제가 있었습니다.

- **운영 DB 직접 조회** — MongoDB에 직접 쿼리를 날려 운영 DB에 부하를 줌
- **수동 데이터 추출** — 시간 소모가 크고, 실수 가능성이 높음
- **분석 환경 부재** — 복잡한 분석 쿼리를 실행할 전용 환경이 없음

유관부서가 운영 환경에 영향을 주지 않으면서 자유롭게 데이터를 다룰 수 있는 별도의 분석 환경이 필요했습니다.

## 레거시 아키텍처와 한계

초기에는 Redshift 기반으로 데이터 파이프라인을 구축했습니다.

```text
MongoDB → Kafka (Source Connector) → NestJS Consumer → AuroraDB (PostgreSQL)
                                                            ↓
                                                       AWS Glue ETL
                                                            ↓
                                                        Redshift
```

작업 흐름은 다음과 같았습니다:

1. Kafka MongoDB Source Connector로 CDC 이벤트 발행
2. NestJS 기반 Consumer가 메시지를 소비하여 AuroraDB에 적재
3. AWS Glue Crawler로 스키마를 인식하고 ETL Job으로 변환
4. 변환된 데이터를 Redshift에 적재

### 이 구조의 문제점

**NestJS Consumer의 운영 부담이 컸습니다.** 새로운 컬렉션을 추가할 때마다 Entity 정의, Controller 작성, 마이그레이션 작성, 서버 배포까지 코드 레벨의 작업이 필요했습니다. MongoDB의 유연한 스키마를 PostgreSQL의 정적 스키마로 매핑하면서 타입 변환 이슈도 빈번했습니다. 특히 배열 타입 필드는 Redshift에서 JSON 문자열로 저장되면서 대소문자 구분이 불가해 키를 snake_case로 변환해야 하는 등의 번거로움이 있었습니다.

**AWS Glue ETL의 복잡도도 문제였습니다.** 타임스탬프 필드의 UTC 강제 변환 이슈, MERGE 모드에서의 데이터 정합성 문제 등 ETL Job마다 개별적인 핸들링이 필요했습니다. Glue Worker 수보다 동시 실행 Job이 많으면 `Max concurrent runs exceeded` 에러가 발생하기도 했습니다.

**Redshift 자체의 한계도 있었습니다.** Vacuum/Analyze 같은 수동 유지보수 작업이 필요했고, 동시성 처리가 제한적이었으며, 리사이즈 시 수동 작업이 필요했습니다.

## Snowflake 전환 결정

Redshift와 Snowflake를 다각도로 비교 검토한 후 전환을 결정했습니다.

| 항목 | Redshift | Snowflake |
|------|----------|-----------|
| 스케일링 | 수동 리사이즈 필요 | 자동 스케일링 (Warehouse 크기 변경) |
| 비용 모델 | 상시 클러스터 과금 | 사용량 기반 과금 (사용 시만 비용) |
| 동시성 | 제한적, WLM 설정 필요 | 멀티 클러스터 웨어하우스 |
| 유지보수 | Vacuum, Analyze 필수 | 거의 없음 |
| ETL 파이프라인 | 외부 도구(Glue) 의존 | SQL 기반 내장 기능 (Stream, Task) |
| 모니터링 | CloudWatch + 별도 구성 | Snowsight 통합 대시보드 |

가장 결정적인 요인은 **파이프라인 단순화** 가능성이었습니다. NestJS Consumer와 AWS Glue를 제거하고 Snowflake의 내장 기능만으로 CDC ETL을 처리할 수 있다는 점이 매력적이었습니다.

## 신규 아키텍처

```text
MongoDB → Kafka (Source Connector) → S3 (Sink Connector) → Snowflake
                                                               ↓
                                                    External Table → Stream → Task → Table
```

NestJS Consumer를 S3 Sink Connector로 대체하면서 파이프라인이 크게 단순해졌습니다. 코드 배포 없이 커넥터 설정만으로 새로운 컬렉션을 추가할 수 있게 되었습니다.

### MongoDB Source Connector

MongoDB Change Stream을 활용하여 변경 사항을 Kafka 토픽에 발행합니다.

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

핵심 설정:
- `change.stream.full.document: updateLookup` — update 이벤트 시 변경된 문서 전체를 포함
- `startup.mode: copy_existing` — 커넥터 최초 실행 시 기존 데이터를 모두 복제 (`latest`로 설정하면 이후 변경분만 캡처)
- `pipeline` — `__v` 같은 불필요한 필드를 제외

토픽 이름은 `{prefix}.{database}.{collection}` 컨벤션을 따르며, Replication Factor 3, 7일 보관 정책을 적용했습니다.

### S3 Sink Connector — 레거시 Consumer 대체

이전에는 NestJS Consumer가 Kafka 메시지를 받아 AuroraDB에 적재했지만, 이제 S3 Sink Connector가 직접 S3에 저장합니다.

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

- **JSON + gzip 포맷** — Snowflake External Table에서 직접 읽기에 최적
- **flush.size: 100** — 100개 레코드 단위로 S3에 파일 생성
- **rotate.schedule.interval.ms: 5000** — 5초마다 파일 로테이션으로 데이터 지연 최소화

이 변경 하나로 NestJS Consumer 서버 관리, Entity 정의, 마이그레이션, 배포 프로세스가 모두 사라졌습니다.

### Snowflake CDC: External Table → Stream → Task → Table

Snowflake의 핵심 장점은 SQL만으로 CDC ETL을 구현할 수 있다는 것입니다. 4단계로 구성됩니다.

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

S3의 JSON 파일을 데이터 이동 없이 Snowflake에서 테이블처럼 조회할 수 있습니다. `cluster_time`을 파싱해두면 이후 MERGE에서 중복 제거에 사용합니다.

**2단계 — Stream: 변경 감지**

```sql
CREATE OR REPLACE STREAM example_collection_stream
  ON EXTERNAL TABLE external_table.example_collection
  INSERT_ONLY = true;
```

Stream은 External Table에 새로 추가된 행을 자동 추적합니다. `INSERT_ONLY = true`는 External Table의 특성상 append-only이기 때문입니다.

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

모든 컬럼에 COMMENT를 작성하는 것을 컨벤션으로 정했습니다. 유관부서가 별도 문서 없이도 테이블 구조를 이해할 수 있게 하기 위해서입니다. PII 데이터(이름, 생년월일, 전화번호, 이메일)에는 마스킹 정책을 적용했습니다.

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

이 Task의 동작 원리:

1. **중복 제거** — 같은 `_id`에 대해 여러 이벤트가 있으면 `cluster_time` 기준 최신 것만 사용 (`ROW_NUMBER` + `QUALIFY`)
2. **CDC 반영** — `operation_type`에 따라 INSERT, UPDATE, DELETE를 하나의 MERGE 문으로 처리
3. **의존성 체인** — `AFTER external_table_refresh_task`로 External Table Refresh 완료 후 실행

별도 스케줄이 필요한 Task는 CRON 표현식으로 독립 실행하면서 내부에서 External Table Refresh를 먼저 수행합니다:

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

## Snowflake 활용 사례

파이프라인 구축 이후 Snowflake의 기능들을 적극 활용하면서 분석 환경을 고도화했습니다.

### Dynamic Table — 자동화된 데이터 변환

기본 테이블에 의존하는 파생 테이블을 Dynamic Table로 구성하면, 원본이 변경될 때 자동으로 증분 처리됩니다. 수동으로 복잡한 데이터 변환 작업을 관리할 필요가 없어졌습니다.

### Flatten — 중첩 JSON 처리

MongoDB에서 넘어온 데이터 중 중첩된 JSON 구조가 많았습니다. `LATERAL FLATTEN`으로 배열을 정규화된 행으로 풀어낼 수 있었습니다.

```sql
SELECT
  t.item_id,
  f.value:date::date AS event_date,
  f.value:count::number AS event_count
FROM items t,
LATERAL FLATTEN(input => t.nested_data) f;
```

### Time Series 함수 — 시계열 데이터 분석

서비스 특성상 시계열 데이터 분석이 중요했는데, Snowflake의 전용 함수들이 큰 도움이 되었습니다.

- **TIME_SLICE** — 시계열 데이터를 분/시/일 단위로 버케팅
- **DATE_TRUNC** — 타임스탬프를 원하는 단위로 절삭
- **ASOF JOIN** — 시간 기반 퍼지 조인으로 서로 다른 데이터셋 간 시간 근접 매칭
- **RANGE BETWEEN** — 윈도우 함수에서 시간 범위 기반 집계

## 성과

### 쿼리 성능

| 쿼리 유형 | Redshift | Snowflake | 개선 |
|-----------|----------|-----------|------|
| 2시간 데이터 리프레시 | 3분 | 1분 23초 | 2.2배 |
| 일간 분석 쿼리 | 1분+ | 4초 | **15배** |

Snowflake X-Small Warehouse만으로도 대부분의 쿼리를 충분히 처리할 수 있었습니다. Warehouse 크기를 조정하면 시계열 쿼리에서 최대 15배까지 성능이 개선되었습니다.

### 파이프라인 속도

전체 파이프라인 처리 시간이 **27분에서 8분**으로 단축되었습니다. AWS Glue ETL을 Snowflake Task로 대체하면서 중간 단계의 오버헤드가 크게 줄었습니다.

### 운영 개선

- **Snowsight 통합 대시보드** — 쿼리 관리, 파이프라인 모니터링, 비용 추적을 하나의 UI에서 처리
- **Task 실행 이력** — Task Graph로 의존성과 실행 상태를 시각적으로 확인
- **실시간 에러 모니터링** — 이전 인프라 대비 모니터링 구성이 대폭 간소화

## 세미나 발표

이 구축 사례를 **Snowflake 데이터 혁신 세미나**에서 발표할 기회가 있었습니다. 데이터 파이프라인 전환 경험을 공유했고, 특히 레거시 파이프라인 단순화와 실제 성능 개선 수치에 대해 많은 관심을 받았습니다. 다른 기업들과 데이터 엔지니어링 경험을 나누면서 각자의 도메인에서 겪는 비슷한 과제들을 확인할 수 있었습니다.

## 회고 및 향후 계획

### 배운 점

- **파이프라인은 단순할수록 좋다** — NestJS Consumer와 AWS Glue를 제거하고 커넥터 + Snowflake 내장 기능으로 대체하면서 운영 부담이 극적으로 줄었습니다
- **SQL 기반 ETL의 힘** — Snowflake의 Stream, Task, MERGE 조합으로 별도 ETL 도구 없이 CDC를 구현할 수 있었습니다
- **스키마 변경 관리가 핵심** — MongoDB의 유연한 스키마가 파이프라인에서는 여전히 가장 까다로운 부분입니다
- **모니터링은 파이프라인의 생명선** — Kafka lag, S3 적재 상태, Task 실행 이력을 모두 추적해야 안정적으로 운영할 수 있습니다

### 향후 계획

- **Amplitude & Google Analytics 데이터 연동** — 사용자 행동 분석 데이터를 Snowflake에 통합하여 서비스 데이터와 크로스 분석
- **Snowflake ML 도입** — 고급 분석과 모델 배포를 통한 데이터 기반 의사결정 강화

---

데이터 파이프라인은 한 번 구축하면 끝이 아니라, 서비스와 함께 진화해야 합니다. Redshift에서 Snowflake로의 전환은 단순한 도구 교체가 아니라 파이프라인 아키텍처 자체를 단순화하는 기회였고, 그 결과 유관부서가 더 빠르고 자유롭게 데이터를 다룰 수 있게 되었습니다.
