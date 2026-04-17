---
layout: post
title: "Elasticsearch로 헬스케어 검색 운영하기"
subtitle: "분석기 설계부터 도메인 룰, 운영 자동화까지"
date: 2025-10-18
category: blog
tags: [Elasticsearch, 검색, 한국어NLP]
---

몇 년 동안 똑닥(헬스케어 플랫폼) 병원 검색을 담당하면서 해온 것들을 기록으로 남긴다.<br>
분석기 → 동의어 → 스코어링 → 도메인 룰 → 운영 순서로 정리한다.

## 검색이 풀어야 했던 것

병원 검색은 단순한 키워드 매칭이 아니다. 사용자가 "이비인후과"라고 검색했을 때 보여줄 결과를 정하는 데 다음이 같이 들어간다.

- **위치** — 사용자 위치에서 가까울수록 위로
- **실시간 상태** — 지금 접수/예약이 가능한 병원이 위로
- **인기도** — 조회수 + 한 달간 접수/예약 완료 건수
- **한국어 검색 디테일** — "삼성동" vs `ㅅㅅㄷ`, "충북" vs "충청북도", "독감예방접종" vs "예방접종"
- **도메인 룰** — "예약"이 들어간 검색은 실시간 예약 가능 병원만, 명절 연휴 처리, 진료과 자동완성 등

처음에는 단일 nori 분석기 + 단순 텍스트 매칭으로 시작했지만, 위 요구가 하나씩 붙으면서 분석기 체계와 스코어링을 둘 다 재설계해야 하는 시점이 왔다.

## 분석기 — 다층 + 초성

기존 단일 nori를 용도별로 쪼갰다.

| Analyzer | 용도 | 핵심 구성 |
|----------|------|-----------|
| `nori_analyzer` | 인덱싱용 형태소 | nori_tokenizer + synonym + lowercase |
| `nori_search_analyzer` | 검색 쿼리용 형태소 | nori + 검색용 동의어 |
| `nori_address_analyzer` | 주소 특화 | nori + 주소 동의어 |
| `nori_disease_analyzer` | 질병/진료 특화 | nori + 질병 동의어 |
| `ngram_analyzer` | 부분 문자열 매칭 | ngram(1-50) + trim + asciifolding |
| `consonant_analyzer` | 초성 검색 | ICU NFD 분해 + 모음 제거 + ngram |
| `nfd_ngram_analyzer` | 유니코드 정규화 + ngram | NFD normalizer + ngram + unique |
| `tel_ngram_analyzer` | 전화번호 부분 검색 | 숫자 ngram(4-20) |

핵심은 인덱싱 시점과 검색 시점에 다른 분석기를 쓰는 것이다. 인덱싱은 `nori_analyzer`로 무겁게 처리하고, 검색 쿼리에는 `nori_search_analyzer`를 적용해 동의어 확장을 검색 시점에만 일어나게 했다. 인덱스 사이즈를 억제하기 위한 선택이다.

### nori 설정의 디테일

```json
{
  "nori_tokenizer": {
    "type": "nori_tokenizer",
    "decompound_mode": "discard",
    "user_dictionary": "userdict_ko.txt"
  }
}
```

처음에는 `decompound_mode`를 `mixed`로 깔았다. 그런데 "소아청소년과" 같은 복합어가 원형 + 분해 토큰으로 같이 들어가면서 매칭 결과가 산만해졌다. `discard`로 바꾸고 user_dictionary에 도메인 복합어 규칙을 직접 넣는 쪽이 깔끔했다.

### 초성 검색

한국어 검색에서 제일 재밌는 부분이었다. 핵심은 유니코드 NFD 분해.

```json
{
  "consonant_analyzer": {
    "type": "custom",
    "char_filter": ["nfd_normalizer", "vowel_remove"],
    "tokenizer": "ngram_tokenizer"
  },
  "char_filter": {
    "nfd_normalizer": {
      "type": "icu_normalizer",
      "name": "nfc",
      "mode": "decompose"
    },
    "vowel_remove": {
      "type": "pattern_replace",
      "pattern": "[^ᄀ-ᄒ]",
      "replacement": ""
    }
  }
}
```

동작 순서:

1. ICU Normalizer로 "삼성동"을 자모로 분해
2. `vowel_remove`로 초성(`ᄀ-ᄒ`) 외 모든 문자 제거 → `ᄉᄉᄃ`
3. `ngram_tokenizer`로 `ᄉ`, `ᄉᄉ`, `ᄉᄉᄃ` 분할

검색 시에는 `nfkc_cf_normalized`로 사용자가 입력한 `ㅅㅅㄷ`를 같은 방식으로 정규화한다. 모바일에서 초성 검색은 사실상 디폴트 기대값이라, 적용 후 모바일 검색 전환율이 눈에 띄게 올라갔다.

### Multi-field 매핑

하나의 필드에 여러 분석기를 동시에 걸어두는 패턴이다. 검색 시 boost를 다르게 줘서 우선순위를 만든다.

```json
{
  "title": {
    "type": "text",
    "analyzer": "nori_analyzer",
    "fields": {
      "consonant": { "analyzer": "consonant_analyzer", ... },
      "nfd_ngram": { "analyzer": "nfd_ngram_analyzer", ... },
      "ngram":     { "analyzer": "ngram_analyzer", ... },
      "keyword":   { "type": "keyword" },
      "standard":  { "analyzer": "standard", "type": "text" }
    }
  }
}
```

`title.consonant`로 초성 검색, `title.ngram`으로 부분 문자열 매칭, `title`로 형태소 매칭을 동시에 수행하고, 필드별 boost로 우선순위를 둔다.

## 동의어 사전

검색 품질에 즉각적으로 효과가 드러나는 건 동의어 사전이다. 용도별로 분리해서 관리했다.

```text
# 주소 (synonym_address)
충북,충청북도
경북,경상북도
하남,하남시

# 질병 (synonym_disease)
감기,상기도감염,급성비인두염
독감,인플루엔자

# 단방향 확장 (synonym_custom_disease)
건강검진 => 국가검진,무료검진,암검진,위암검진,대장암검진

# 검색어 (synonym_search)
독감예방접종 => 예방접종
청소년과 => 소아청소년과

# 병원명 보정 (synonym_title)
소아청소년과 => 소아,청소년,소아청소년과,아동병원
```

쉼표(`,`)는 양방향, `=>`는 단방향이다. "건강검진"으로 검색하면 "암검진"도 매칭되지만, 반대로 "암검진"을 친 사람한테 "건강검진" 결과를 같이 줄 필요는 없다. 이 방향성을 잡는 게 동의어 설계의 핵심이었다.

## 스코어링 — 정렬별로 다른 전략

`function_score`를 정렬 종류마다 다르게 구성했다.

### 관련도순 — multi_match + Decay

```json
{
  "function_score": {
    "query": {
      "multi_match": {
        "query": "이비인후과",
        "fields": [
          "title^10",
          "mainDepartment^15",
          "careTags^3",
          "address^1",
          "subways^1",
          "theme.features.title^10",
          "doctors^1"
        ]
      }
    },
    "functions": [{
      "gauss": {
        "location": {
          "origin": { "lat": 37.28, "lon": 127.05 },
          "scale": "2km",
          "offset": "1km",
          "decay": 0.3
        }
      }
    }],
    "score_mode": "sum"
  }
}
```

field-level boost가 핵심이다. 병원명(`title^10`)과 대표진료과(`mainDepartment^15`)에 가장 높은 가중치를 두고, 부가 정보(주소/지하철/의사명/장비)는 1로 깐다. 거리 가중치는 Gauss decay function으로 처리한다(스케일 2km, 오프셋 1km, 감쇠 0.3).

이 boost 비율은 한 번에 정한 게 아니라 실제 검색 결과를 모니터링하면서 계속 튜닝해서 안착했다.

### 인기순 — modifier 선택의 근거

조회수, 한 달 접수 완료 건수, 한 달 예약 완료 건수를 합쳐 가중치를 만든다. 이전 버전은 단순히 "건수순"으로 정렬해서, 검색 스코어가 낮은 병원도 인기 많으면 무조건 위로 올라오는 문제가 있었다.

```text
Score = 검색 스코어 × ((조회수 × factor) + (접수건수 × factor) + (예약건수 × factor))
```

문제는 factor에 어떤 함수를 곱하느냐다. 실제 케이스로 비교해봤다 (factor=2 가정, 검색 스코어 19.47).

| 데이터 | 조회수 | 접수 | 예약 | 배수 결과 | 로그 결과 | 제곱근 결과 |
|--------|--------|------|------|-----------|-----------|-------------|
| 케이스 1 | 129 | 13 | 2 | 5,606 | 88 | 450 |
| 케이스 2 | 4,000 | 469 | 185 | 181,207 | 183 | 2,711 |

- **배수**: 값이 클수록 점수가 폭발적으로 커져서 검색 스코어 영향력이 사라진다
- **로그**: 가중치 차이가 너무 적어서 검색 스코어가 모든 걸 덮어버린다
- **제곱근**: 가운데에 있다. 값 차이는 반영하되 폭주는 막아준다

조회수만 `log1p`(편차를 더 강하게 누르고), 접수/예약 건수는 `sqrt`로 갔다. 조회수는 0과 수만 사이를 오가는데, 이 편차를 그대로 두면 오래 살아남은 인기 병원이 신규를 묻어버린다.

### 리뷰순

조회수(`log1p`) + 리뷰 좋아요 수(`sqrt`) 조합이다. 신뢰도가 낮은 리뷰가 위로 올라오지 않도록 실제 서비스 이용 후 남긴 리뷰인지를 가중치에 반영했다.

## 코드에 박힌 도메인 룰

스코어링 다음으로 운영을 어렵게 만드는 게 도메인 룰이다. 헬스케어 검색은 일반 키워드 검색이 안 풀어주는 룰이 많다.

- 검색어에 **"접수"** 가 들어가면 `isRealReceipt: true`인 병원만 보여준다
- 검색어에 **"예약"** 이 들어가면 `isRealReservation: true`인 병원만 보여준다
- **거리 반경**은 기본 5km로 매칭이 없으면 10km → 30km → 전국 단계로 확장한다
- 명절 연휴가 **토/일과 겹치면** 실시간 접수 가능한 병원도 should에 추가한다
- "설날", "추석", "연휴"로 검색하면 검색 토큰에서 **"병원"을 빼버린다** — 안 그러면 병원명에 "병원"이 들어간 곳이 위로 올라오는 사고가 있었다
- 진료중 필터를 켜면 운영 환경에서 `[TEST]` 병원이 나오지 않도록 prefix 쿼리를 명시적으로 박는다

마지막 케이스는 한 번 사고 나서 들어간 룰이다. 명절 + 토일 같은 케이스도 사용자 문의를 받고 후속으로 추가됐다. 이런 룰은 코드 안에 들어가지 않으면 검색 결과의 의도를 영영 설명할 수 없다.

스코어링 측의 should boost도 같이 보면 의도가 더 잘 보인다.

```text
isMember          : boost 2
isReceipt         : boost 20
isReservation     : boost 20
isRealReservation : boost 70   (오늘 예약 가능 날짜와 매칭될 때)
isRealReceipt     : boost 140  (지금 실시간 접수 가능)
```

지금 당장 접수 가능한 병원을 가장 위로, 그 다음이 오늘 예약 가능한 병원, 그 다음이 단순 멤버 병원. 가중치만 봐도 정책 의도가 읽힌다.

## 운영 — Batch + Consumer + ILM

### 배치 (Argo Workflow)

| 커맨드 | 시점 |
|--------|------|
| init-search-index:hospital | 매일 04:00 |
| init-search-index:disease | 매일 04:00 |
| init-search-index:related_keyword | 매일 04:00 |
| init-auto-complete-index | 매일 03:00 |
| search-hospital-view-count | 매일 03:40 |
| collect-search-log | 매일 03:00 |
| update-hospital-index:abnormal | 5분마다 |
| sync-mongo | 매주 월 02:00 |

배치 재인덱싱은 새 인덱스에 데이터를 깐 뒤 alias만 전환하는 방식으로 무중단 처리했다. `update-hospital-index:abnormal`은 5분 간격으로 도는 짧은 배치인데, 비정상 설정(임시 휴진 등)은 실시간성이 중요해서 짧게 잡았다.

### 컨슈머 (Kafka)

MongoDB Change Stream을 받는 토픽이 다수 있다.

```text
mongo.ddocdoc.hospitals      → 병원 콜렉션 변경
search.users.db              → 유저 콜렉션 변경
ddocdoc.mongo.doctors        → 의사 변경
ddocdoc.mongo.hospitalagents → 에이전트 변경
search.hospital.queueing     → 검색 인덱스 큐잉 이벤트
```

병원 인덱스 업데이트 이벤트는 타입에 따라 분기한다.

- `abnormal` — 접수/예약 상태 업데이트
- `schedule` — 병원 스케줄 업데이트
- `reservationSchedule` — 실시간 예약 스케줄(Redis)
- 빈 값 — 도큐먼트 전체 업데이트

조회수처럼 부분 변경만 일어나는 케이스에 도큐먼트 전체를 다시 인덱싱하면 인덱싱 비용이 의미 없이 커진다. 이벤트 타입으로 부분 업데이트와 전체 업데이트를 갈라줘야 한다.

### 인덱스 라이프사이클

검색 로그 인덱스는 3일 후 삭제 정책을 적용했다. 검색 로그는 최근 데이터만 의미가 있다는 판단이고, 트렌드 분석은 별도 집계 파이프라인이 처리하기 때문이다.

운영하면서 항상 같이 봐야 했던 지표.

- **Search Latency (p95, p99)** — 200ms 넘으면 사용자가 체감하기 시작한다
- **Indexing Rate** — Kafka 컨슈머 처리 속도와 ES 인덱싱 속도 사이의 갭
- **JVM Heap Usage** — 75% 넘으면 GC 패턴부터 본다
- **Rejected Thread Count** — search/write thread pool rejected 급증은 클러스터 부하 신호

## 회고

### 잘 됐던 것

- **다층 분석기 체계** — 새 요구사항이 들어와도 분석기 조합이나 추가로 받아낼 수 있었다. 초기에 시간을 쓴 게 뒤로 갈수록 이득이었다
- **동의어 사전 분리** — 주소/질병/검색어/병원명 사전을 따로 둔 덕에, 한 영역의 변경이 다른 영역으로 새지 않아서 운영이 편해졌다
- **인기순 modifier 선택** — 단순 건수 정렬에서 검색 스코어 × log/sqrt 가중치 조합으로 바꾸면서, 신규 병원도 노출 기회를 얻을 수 있게 됐다

### 어려웠던 것

- **스코어링 튜닝은 끝이 없다** — A 쿼리를 개선하면 B 쿼리가 나빠지는 일이 반복됐다. 주요 검색 시나리오마다 회귀 테스트 케이스를 만들어 관리했다
- **동의어 사전 변경의 운영 비용** — 변경 시 인덱스 close/open이 필요한 경우가 있어, 일일 배치 재인덱싱 시점에 새 사전을 같이 반영하는 패턴으로 정리했다
- **Analyzer 디버깅** — 분석기가 여러 개 겹치면 어디서 토큰이 어떻게 깎였는지 추적하기 어려웠다. `_analyze` API를 습관적으로 돌려보고, 분석기별 기대 결과를 문서화해두는 편이 도움이 됐다
- **Mapping 변경의 비용** — 분석기와 필드 매핑은 한 번 들어가면 reindex 없이는 못 바꾼다. 초기 설계에서 multi-field를 충분히 깔아두는 게 결과적으로 품이 덜 들었다
