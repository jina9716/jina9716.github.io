---
layout: post
title: "MSA - 원칙, 아키텍처, 그리고 DB 분리"
subtitle: "왜 하는지부터 서비스 경계, 아키텍처 유형, 데이터 일관성, DB 분리까지"
date: 2026-07-09
category: blog
tags: [msa, architecture, event-driven, saga, database]
canonical_url: https://boostbrothers.github.io/2026-07-16-msa-principles-architecture-db-split/
---

MSA 전환을 진행하면서 정리했던 내용을 한 편으로 묶었습니다. 왜 하는지에서 출발해 원칙, 서비스 경계, 아키텍처 유형, 통신·resilience 패턴, 데이터 일관성 순서로 내려가고 마지막 장은 직접 진행한 DB 분리 작업입니다.

이 글은 다듬어서 사내 기술 블로그에 실었습니다. 전문은 아래에서 볼 수 있습니다.

**→ [MSA - 원칙, 아키텍처, 그리고 DB 분리 (전문)](https://boostbrothers.github.io/2026-07-16-msa-principles-architecture-db-split/)**

다루는 내용:

1. 왜 MSA인가 - 모놀리스의 기술적 한계
2. MSA의 핵심 원칙
3. 서비스 경계 정하는 법
4. MSA 아키텍처 유형
5. 지원 패턴 - 통신과 resilience
6. 데이터 일관성 - dual-write, outbox, saga
7. DB 분리
8. 마치며
