---
layout: about
title: 소개
permalink: /about
work:
  - when: "2025.04—현재"
    title: "예약 플랫폼 백엔드 설계·개발·운영"
    desc: "핵심 도메인의 API와 운영 도구를 맡고 있습니다. 외부 시스템 연동은 Outbox로 본 처리와 분리해 응답이 외부 상태에 묶이지 않게 했습니다. 도메인 정책과 테크스펙을 문서로 정리해 AI 에이전트의 컨텍스트로 쓰고, QA 케이스는 API e2e 검증으로 전환했습니다."
  - when: "2021.06—2026.04"
    title: "데이터 플랫폼 구축·전환"
    desc: "Redshift와 Glue ETL을 Snowflake로 재설계해 집계 성능을 최대 15배 올리고 월 운영 비용을 약 17% 줄였습니다. 반복되던 데이터 추출 업무는 주 8시간에서 0시간이 됐습니다."
  - when: "2020.03—2025.09"
    title: "검색 설계·운영"
    desc: "한글을 자소 단위로 분해하는 분석기로 초성 검색과 오타 보정을 함께 지원하고 복합 키워드 자동완성을 더해, 검색 결과 클릭률을 35% 올렸습니다."
  - when: "2024.09—2025.07"
    title: "MSA 전환"
    desc: "8년간 운영된 단일 서버를 10개 도메인 서버로 무중단 이관했습니다. PL로 백엔드 5명과 진행했고, 단일 MongoDB의 104개 컬렉션도 도메인별 6개 DB로 나눴습니다."
  - when: "2019.05—2020.03"
    title: "머신러닝 플랫폼 백엔드 개발"
    desc: "전처리·학습·배포를 API로 실행하는 플랫폼을 만들었습니다. API Gateway에 Kubernetes 클라이언트를 연동해 작업을 컨테이너로 띄우고, 배포 단계마다 체크포인트를 뒀습니다."
  - when: "2018.02—2019.05"
    title: "마케팅 고객분석 플랫폼"
    desc: "배너 노출 대상을 개발자가 코드로 넣던 구조에서 마케팅팀이 타겟 조건을 직접 설정해 집행하는 구조로 바꿨습니다."
skills:
  - TypeScript
  - Kotlin
  - Python
  - Nest.js
  - Spring Boot
  - MongoDB
  - PostgreSQL
  - Redis
  - Elasticsearch
  - Kafka
  - Snowflake
  - AWS
  - Kubernetes
  - Argo
likes:
  - icon: game-controller
    title: "게임"
    desc: "PS5로 RPG를 주로 합니다. 캐릭터를 키우는 재미로 오래 붙잡는 쪽입니다."
    now: "데이브 더 다이버"
  - icon: tennis-ball
    title: "테니스"
    desc: "주 1회 칩니다. 쳐도 쳐도 어려워서 아직 배우는 중입니다."
    now: "서브 배우는 중"
  - icon: cube
    title: "3D 프린터"
    desc: "최근에 시작했습니다. 아직 남이 만든 모델을 가져다 쓰는 단계입니다."
    now: "이것저것 뽑는 중"
---

예약 플랫폼의 핵심 도메인을 맡고 있습니다. 검색 시스템과 데이터 플랫폼을 전담했고, 8년간 운영된 모놀리식 서버를 도메인 서버로 나누는 MSA 전환을 PL로 이끌었습니다.
