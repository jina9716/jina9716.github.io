---
layout: post
title: "Elasticsearch 검색 서비스 고도화"
subtitle: "형태소 분석부터 초성 검색, 스코어링 설계까지"
date: 2026-02-25
tags: [Elasticsearch, 검색, 한국어NLP]
---

기존에 운영 중이던 Elasticsearch 검색을 고도화하면서, 다층 분석기 체계와 초성 검색, 동의어 사전, 스코어링 설계까지 전반적으로 개선한 경험을 공유합니다.

## 기존 검색의 한계

서비스에는 이미 Elasticsearch가 도입되어 있었지만, 단순한 nori 분석기 하나로 검색을 처리하고 있었습니다. 서비스가 성장하면서 이 구조의 한계가 명확해졌습니다.

- **동의어 미지원** — "충북"을 검색하면 "충청북도"가 나오지 않음. "독감예방접종"과 "예방접종"이 별개로 취급됨
- **초성 검색 불가** — `ㅅㅇㄷ`로 "삼성동"을 찾을 수 없음. 모바일에서 초성 검색은 사실상 필수
- **스코어링이 단순** — 텍스트 매칭 점수만으로 정렬. 거리 기반 정렬이나 인기도 반영 불가
- **부분 매칭 미흡** — 전화번호나 주소를 정확히 입력해야만 결과가 나옴

단순히 기능을 추가하는 수준이 아니라, 분석기 아키텍처 자체를 재설계해야 하는 상황이었습니다.

## Analyzer 아키텍처 설계

기존 단일 nori analyzer를 **용도별 다층 분석기 체계**로 재설계했습니다.

| Analyzer | 용도 | 핵심 구성 |
|----------|------|-----------|
| `nori_analyzer` | 기본 형태소 분석 | nori_tokenizer + synonym + lowercase |
| `ngram_analyzer` | 부분 문자열 매칭 | ngram(1-50) + trim + asciifolding |
| `consonant_analyzer` | 초성 검색 | ICU NFD 분해 + 모음 제거 + ngram |
| `nfd_ngram_analyzer` | 유니코드 정규화 + ngram | NFD normalizer + ngram + unique |
| `nori_address_analyzer` | 주소 검색 특화 | nori + 주소 동의어 필터 |
| `nori_disease_analyzer` | 질병/진료 검색 특화 | nori + 질병명 동의어 필터 |
| `nori_search_analyzer` | 통합 검색 쿼리 분석 | nori + 검색용 동의어 필터 |
| `tel_ngram_analyzer` | 전화번호 부분 검색 | 숫자 특화 ngram |

핵심은 **인덱싱 시점과 검색 시점에 서로 다른 분석기를 적용**한다는 점입니다. 인덱싱에는 `nori_analyzer`를 쓰고, 검색 쿼리에는 `nori_search_analyzer`를 적용하면 동의어 확장이 검색 시점에만 일어나 인덱스 크기를 억제할 수 있습니다.

### nori_analyzer 구성

```json
{
  "analysis": {
    "analyzer": {
      "nori_analyzer": {
        "type": "custom",
        "char_filter": ["custom_char_filter"],
        "tokenizer": "nori_tokenizer",
        "filter": ["synonym_filter", "synonym_title_filter", "lowercase"]
      }
    },
    "tokenizer": {
      "nori_tokenizer": {
        "type": "nori_tokenizer",
        "decompound_mode": "discard",
        "user_dictionary": "userdict_ko.txt"
      }
    }
  }
}
```

`decompound_mode`를 `discard`로 설정한 이유가 있습니다. `mixed` 모드는 원형과 분해 토큰을 모두 유지하지만, 토큰 수가 늘어나면서 검색 정확도가 떨어지는 문제가 있었습니다. `discard`가 실제 검색 품질에서 더 나은 결과를 보였습니다. `user_dictionary`에는 "소아청소년과"를 "소아", "청소년", "과"로 분리하는 등 도메인 특화 복합어 규칙을 정의했습니다.

## 초성 검색 구현

이번 고도화에서 가장 기술적으로 흥미로운 부분이었습니다. 핵심은 **유니코드 NFD 분해를 활용한 자모 분리**입니다.

### consonant_analyzer 구성

```json
{
  "analysis": {
    "analyzer": {
      "consonant_analyzer": {
        "type": "custom",
        "char_filter": ["icu_normalizer_nfd", "vowel_remove"],
        "tokenizer": "ngram_tokenizer"
      }
    },
    "char_filter": {
      "icu_normalizer_nfd": {
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
}
```

동작 원리를 단계별로 보면:

1. **ICU Normalizer (NFD 분해)** — "삼성동"을 유니코드 자모로 분해
2. **vowel_remove** — 초성(ᄀ-ᄒ) 이외의 모든 문자를 제거: `ᄉᄉᄃ`
3. **ngram_tokenizer** — 초성 시퀀스를 ngram으로 분할: `ᄉ`, `ᄉᄉ`, `ᄉᄉᄃ`, ...

검색 시에는 `nfkc_cf_normalized`를 사용하여 사용자의 초성 입력을 정규화합니다.

### Multi-field 매핑 전략

하나의 필드에 여러 분석기를 적용하는 multi-field 매핑을 사용했습니다.

```json
{
  "mappings": {
    "properties": {
      "title": {
        "type": "text",
        "analyzer": "nori_analyzer",
        "fields": {
          "consonant": {
            "type": "text",
            "analyzer": "consonant_analyzer",
            "search_analyzer": "consonant_search_analyzer"
          },
          "nfd_ngram": { "type": "text", "analyzer": "nfd_ngram_analyzer" },
          "ngram": { "type": "text", "analyzer": "ngram_analyzer" },
          "keyword": { "type": "keyword" },
          "standard": { "type": "text", "analyzer": "standard" }
        }
      }
    }
  }
}
```

`title.consonant`으로 초성 검색, `title.ngram`으로 부분 문자열 검색, `title`로 형태소 기반 검색을 동시에 수행하고, 각 필드에 다른 boost 가중치를 부여합니다.

## 동의어/사용자 사전 전략

검색 품질을 높이는 데 가장 직접적인 효과가 있었던 것은 **동의어 사전**이었습니다. 용도별로 사전을 분리하여 관리했습니다.

### 주소 동의어

```text
# synonym_address.txt
충북,충청북도
충남,충청남도
경북,경상북도
경남,경상남도
전북,전라북도
전남,전라남도
```

사용자는 "충북"이라고 검색하지만 데이터에는 "충청북도"로 저장되어 있는 경우가 대부분입니다. `nori_address_analyzer`에 이 동의어 필터를 적용했습니다.

### 도메인 특화 동의어

```text
# synonym_disease.txt (파일 기반 로딩)
감기,상기도감염,급성비인두염
독감,인플루엔자

# synonym_custom_disease.txt
건강검진 => 국가검진,무료검진,암검진
```

쉼표(`,`) 구분은 **양방향 동의어**, `=>` 구분은 **단방향 확장**입니다. "건강검진"을 검색하면 "암검진"도 매칭되지만, 반대는 성립하지 않습니다. 이 방향성 설계가 검색 의도를 더 정확하게 반영했습니다.

### 검색 쿼리 동의어

```text
# synonym_search.txt
독감예방접종 => 예방접종
청소년과 => 소아청소년과
```

사용자가 흔히 사용하는 축약형 검색어를 정식 용어로 확장합니다.

## 스코어링 설계

단순 텍스트 매칭만으로는 사용자가 원하는 결과를 상위에 노출할 수 없었습니다. `function_score`를 활용해 정렬 목적별로 다른 스코어링 전략을 설계했습니다.

### 관련도순 — Decay Function + Field Boost

```json
{
  "function_score": {
    "query": {
      "multi_match": {
        "query": "검색어",
        "fields": ["title^10", "title.ngram^5", "title.consonant^3", "category^3", "address^1"]
      }
    },
    "functions": [{
      "gauss": {
        "location": {
          "origin": { "lat": 37.5665, "lon": 126.9780 },
          "scale": "3km",
          "offset": "500m",
          "decay": 0.5
        }
      }
    }],
    "score_mode": "multiply",
    "boost_mode": "multiply"
  }
}
```

field-level boost 전략이 중요합니다. `title^10`처럼 정확한 형태소 매칭에 높은 가중치를 두고, ngram, 초성 순으로 줄여갑니다. 이 비율은 실제 검색 결과를 보면서 반복 튜닝했습니다. Gauss decay function은 사용자 위치에서 가까울수록 높은 점수를 부여합니다.

### 인기순 — Field Value Factor

```json
{
  "function_score": {
    "functions": [
      { "field_value_factor": { "field": "viewCount", "modifier": "log1p", "factor": 2 } },
      { "field_value_factor": { "field": "serviceUsageA", "modifier": "sqrt", "factor": 1.5 } },
      { "field_value_factor": { "field": "serviceUsageB", "modifier": "sqrt", "factor": 1 } }
    ],
    "score_mode": "sum",
    "boost_mode": "multiply"
  }
}
```

modifier 선택이 스코어 분포에 큰 영향을 줍니다.

| Modifier | 특성 | 적합한 경우 |
|----------|------|-------------|
| `log1p` | 큰 값의 영향을 크게 억제 | 조회수처럼 편차가 매우 큰 지표 |
| `sqrt` | 중간 정도의 억제 | 이용 횟수처럼 적당한 범위의 지표 |
| `linear` | 억제 없음 | 값의 범위가 좁은 경우 |

조회수가 10 vs 10,000일 때 — `linear`는 1,000배 차이 그대로, `log1p`는 약 3.8배, `sqrt`는 약 31배로 차이가 억제됩니다. 오래된 항목의 누적 조회수가 신규를 묻어버리는 것을 방지하기 위해 `log1p`를 적용했습니다.

리뷰순 정렬도 비슷한 패턴이지만, 실제 서비스 이용 후 남긴 리뷰인지(`hasVerifiedService`)를 가중치에 반영하여 신뢰도 높은 리뷰가 상위에 오도록 설계했습니다.

## 실시간 인덱스 업데이트

검색 인덱스는 데이터의 신선도가 생명입니다. 두 가지 전략을 병행했습니다.

### Kafka Consumer 기반 실시간 업데이트

```text
MongoDB Change Stream → Kafka (mongo.service.*) → ES Index Consumer
                                                        ↓
                                              이벤트 타입에 따라 분기
                                              ├── insert → 전체 문서 인덱싱
                                              ├── update → 변경 필드만 partial update
                                              └── delete → 문서 삭제
```

이벤트 타입에 따라 업데이트 범위를 다르게 처리한 것이 핵심입니다. 조회수만 변경된 경우 `_update` API로 해당 필드만 갱신하면 인덱싱 비용을 크게 줄일 수 있습니다.

### 배치 재인덱싱 — Argo Workflow

실시간만으로는 정합성을 100% 보장하기 어렵습니다. **Argo Workflow 기반 일일 배치 재인덱싱**을 병행했습니다.

```text
Argo Workflow (Daily, Off-peak)
  ├── Step 1: MongoDB 전체 데이터 덤프
  ├── Step 2: Bulk Indexing (새 인덱스에)
  ├── Step 3: Alias 전환 (search-v2-20260225 → search-v2)
  └── Step 4: 이전 인덱스 삭제
```

인덱스 Alias를 활용한 무중단 전환이 포인트입니다. 새 인덱스에 데이터를 넣은 후 alias만 전환하면 서비스 중단 없이 재인덱싱이 완료됩니다.

## ILM & 운영

검색 로그 인덱스에는 **3일 라이프사이클 정책**을 적용했습니다.

| Phase | 조건 | 액션 |
|-------|------|------|
| Hot | 현재 활성 | Primary shard 1, Replica 1 |
| Delete | 3일 경과 | 삭제 |

검색 로그는 최근 데이터만 의미 있다는 판단 하에 짧게 설정했습니다. 트렌드 분석이 필요한 데이터는 별도 집계 파이프라인에서 처리합니다.

운영하면서 반드시 추적해야 했던 지표들:

- **Search Latency (p95, p99)** — 200ms를 넘으면 사용자가 체감하기 시작
- **Indexing Rate** — Kafka Consumer 처리 속도와 ES 인덱싱 속도 간 차이
- **JVM Heap Usage** — 75%를 넘으면 주의. GC 패턴 모니터링 필수
- **Rejected Thread Count** — search/write thread pool rejected 급증 시 클러스터 부하 신호

## 회고 및 배운 점

### 잘된 점

- **다층 분석기 체계가 확장성을 확보해줬다** — 새로운 요구사항에 기존 분석기를 조합하거나 추가하는 것으로 대응 가능. 초기 설계에 공을 들인 보람이 있었습니다
- **동의어 사전의 효과가 컸다** — 사전 하나 추가하는 것만으로 매칭률이 크게 개선되는 경우가 많았습니다
- **초성 검색이 모바일 UX를 크게 개선했다** — 모바일 검색 전환율이 눈에 띄게 올랐습니다

### 어려웠던 점

- **스코어링 튜닝은 끝이 없다** — A 쿼리를 개선하면 B 쿼리가 나빠지는 상황의 반복. 주요 검색 시나리오에 대한 회귀 테스트 케이스를 만들어 관리했습니다
- **동의어 사전 관리가 운영 부담** — 사전 변경 시 인덱스 close/open이 필요한 경우가 있어, 배치 재인덱싱 시점에 새 사전을 반영하는 패턴으로 해결했습니다
- **Analyzer 디버깅이 어렵다** — 여러 분석기가 겹치면 문제 원인 파악이 어려움. `_analyze` API 활용과 분석기별 기대 결과 문서화가 중요했습니다

### 핵심 교훈

1. **검색은 "구현"보다 "운영"이 어렵다** — 사전 관리, 스코어 튜닝, 정합성 관리가 초기 구축보다 더 많은 리소스를 소모합니다
2. **`_analyze` API는 최고의 디버깅 도구다** — 분석기 동작을 확인하는 습관이 트러블슈팅 시간을 줄여줍니다
3. **실시간 + 배치 이중화가 안정적** — Kafka 실시간 업데이트만으로는 정합성 보장이 어렵습니다. 배치를 병행하면 마음이 편해집니다
4. **Mapping은 되돌릴 수 없다** — 분석기와 필드 매핑 변경은 reindex가 필요합니다. 초기 설계에 충분한 시간을 투자해야 합니다

---

검색 고도화는 한 번의 프로젝트로 끝나는 것이 아니라, 사용자 피드백과 데이터 분석을 기반으로 지속 개선하는 과정입니다. 다층 분석기 체계를 갖추고 나니 새로운 요구사항에 대응하는 속도가 크게 빨라졌고, 그것이 이번 고도화의 가장 큰 성과였습니다.
