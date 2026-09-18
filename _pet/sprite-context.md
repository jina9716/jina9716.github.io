# 블로그 홈 도트 펫 스프라이트 작업 컨텍스트

이 문서는 이미지를 생성할 때 쓴 지침을 그대로 남긴 것이다. 아래 "후처리"와
"시트 배치 & CSS" 절은 계획 단계의 값이고, 실제로 적용한 값은 셀 86×86 과
시트 172×688 이다. 실제 절차와 수치는 `postprocess-context.md` 를 따른다.

## 목적
개인 기술 블로그 홈에 상주할 도트 캐릭터 펫. 클로드 펫 같은 느낌.
블로그/개발 상황에 따라 상태가 바뀐다.

## 산출물
- 크림색 치와와 1마리 × 8가지 상태
- 상태당 2프레임 A/B 루프 → 총 16장
- 16장 전부 이미지 생성으로 뽑는다 (스크립트 변형 없음)
- 최종: 64×64 셀, 가로 2프레임 × 세로 8상태 = 128×512 스프라이트시트

## 해상도 / 렌더링 규칙
- 논리 해상도 64×64. 논리 픽셀 1개 = 균일한 정사각 블록
- 안티에일리어싱 절대 금지, 그라데이션 금지, 디더링 금지
- 블러 / 아우터 글로우 / 드롭섀도우 금지
- 실루엣 전체에 1픽셀 외곽선
- 배경: 단색 #FF00FF 마젠타, 완전히 비움 (바닥·그림자·격자·테두리 없음)
- 네거티브: 텍스트, 글자, 숫자, 워터마크, UI 프레임, 로고, 두 번째 캐릭터,
  3D 렌더링, 회화풍, 벡터 일러스트

### 음영 규칙 (셀 셰이딩)
- 각 색은 **하이라이트 / 기본 / 그림자 / 깊은그림자** 최대 4단계 램프를 쓴다
- 단계 사이 경계는 **하드엣지**. 중간색을 섞거나 디더링으로 잇지 않는다
  → 부드러운 음영이 아니라 색이 딱 끊기는 계단식 밴딩
- 광원: **왼쪽 위 고정**. 8개 상태 전부 동일
- 깊은그림자는 좁은 면적에만 — 턱 아래, 다리 사이, 몸통 밑, 귀 뒤쪽 접히는 면
- 하이라이트도 좁게 — 머리 꼭대기, 귀 위쪽 가장자리, 등 윗면, 머즐 위
- 한 면에 램프 4단계가 전부 들어갈 필요는 없다. 대부분 기본 + 그림자 2단계면 충분
- 액센트 오브젝트도 같은 광원을 따른다 (아래 팔레트에 그림자 톤 지정)
- 예외: 화면 글로우(#6FD8E0)는 평면 단색 유지. 음영 넣지 않는다

## 팔레트 (이 17색 외 사용 금지)

몸통 램프 (크림)
  하이라이트    #FFF8E7
  기본          #F5E6C8
  그림자        #E0C9A0
  깊은그림자    #C4A87C

귀 안쪽 램프 (핑크)
  기본          #E8A0A8
  그림자        #C97F8A

외곽선 / 눈
  외곽선        #2B2118
  눈 하이라이트 #FFFFFF
  투명          transparent

상태 액센트
  체크          #5CB85C   / 그림자 #3F8C42
  X             #D9534F   / 그림자 #A83B38
  머그·연필     #8B5E3C   / 그림자 #6B4529
  불꽃          #F0873F   / 그림자 #C96B2E
  화면 글로우   #6FD8E0   (평면, 음영 없음)

## 캐릭터 기본형
작은 치비 치와와, 크림색 털.
- 애플헤드: 머리가 몸보다 크고 둥글다 (전체 높이의 약 55%)
- 크고 쫑긋한 삼각형 귀 2개, 안쪽 핑크
- 크고 둥근 검은 눈 2개, 각각 흰색 하이라이트 1픽셀
- 아주 작은 검은 코, 짧은 머즐
- 짧고 가는 다리, 작게 말린 꼬리
- 정면 응시, 좌우 대칭이 기본 (포즈에 따라 깨져도 됨)
- 음영: 왼쪽 위 광원. 턱 아래·배 아래·다리 사이에 그림자,
  머리 꼭대기와 귀 윗면에 하이라이트

## 8가지 상태 — 프레임 A

1. deploy-success  — 눈 위로 휜 반달(^^), 작게 벌린 입, 귀 완전 쫑긋,
                     앞발 두 개 만세, 꼬리 흔들림,
                     머리 위 초록 체크(#5CB85C), 옆에 반짝임 픽셀 2개
2. testing         — 무표정 동그란 점 눈, 입은 짧은 가로선, 귀 똑바로,
                     가만히 앉은 자세, 머리 위 로딩 점 3개,
                     얼굴에 #6FD8E0 화면 글로우 (평면 색, 광선 아님)
3. coffee          — 반쯤 감은 아치형 눈(ᵔ ᵔ), 귀 약간 바깥으로 이완,
                     앞발 두 개로 갈색 머그(#8B5E3C)를 든 자세,
                     머그 위로 김 픽셀 3개
4. build-failed    — 눈 꽉 감아 >< 모양, 입 작게 벌어져 당황,
                     귀 뒤로 납작, 앞발로 얼굴 양쪽 감쌈, 꼬리 아래로,
                     옆에 빨간 X(#D9534F)와 땀방울 1픽셀
5. refactoring     — 각진 눈썹, 날카로운 눈, 입은 단단한 가로선, 귀 빳빳,
                     뒷발로 서서 앞발 두 개 든 파이팅 자세,
                     한 발에 작은 렌치, 등 뒤에 주황 불꽃(#F0873F)
6. idle-greeting   — 홈 기본값. 크고 둥근 기본 눈, 살짝 벌린 작은 미소,
                     귀 완전 쫑긋 대칭, 앉아서 한쪽 앞발만 가슴 높이로 인사,
                     꼬리 살짝 위로 말림, 머리 옆 작은 핑크 하트(#E8A0A8) +
                     반짝임 1픽셀. 머리 위 오브젝트 없음 — 8종 중 가장 조용함
7. writing         — 아래로 내리깐 반쯤 감은 눈(정면 아님), 짧은 가로선 입에
                     한쪽 끝만 1픽셀 올림, 한쪽 귀만 끝이 살짝 접힘,
                     앉아서 앞발 하나로 갈색 연필(#8B5E3C)을 쥐고 아래로 끄적임,
                     다른 앞발은 바닥, 앞쪽에 크림 종이(#FFF8E7) +
                     커서 1픽셀(#6FD8E0)
8. debugging       — 짝짝이 눈: 한쪽은 가늘게 뜬 선, 한쪽은 돋보기 너머 2배 확대,
                     입은 작은 O자, 한쪽 귀만 앞으로 쫑긋,
                     상체를 앞으로 기울여 바닥을 살핌, 앞발 하나로 돋보기,
                     꼬리 수평. 렌즈 #6FD8E0 + 테두리 #C4A87C,
                     바닥에 빨간 버그 픽셀 2~3개(#D9534F)

### 포즈별 음영 주의
- refactoring: 뒷발로 선 자세라 배와 가슴이 광원을 정면으로 받는다.
  가슴 위쪽 하이라이트, 배 아래 그림자
- debugging: 상체를 숙이므로 머리가 등에 그림자를 드리우지 않는다.
  광원은 여전히 왼쪽 위 — 숙인 머리 윗면이 가장 밝다
- build-failed: 앞발이 얼굴을 감싸므로 얼굴 가운데가 어둡다.
  앞발에 가려진 볼 부분에 깊은그림자

### 상태 간 구분 규칙 (섞이지 않게)
- idle-greeting vs deploy-success: 한 발 인사 vs 양발 만세.
  idle은 머리 위 오브젝트 없고 전체적으로 차분
- writing vs coffee: writing은 집중(눈 아래 응시·귀 쫑긋),
  coffee는 이완(눈 아치·귀 바깥으로)
- debugging vs build-failed: debugging은 능동적 추적(눈 확대),
  build-failed는 수동적 당황(눈 감김)

## 8가지 상태 — 프레임 B

원칙: B는 새 그림이 아니라 "같은 스프라이트의 한 프레임 뒤".
변화는 **눈에 보이는 수준**으로 준다. 1px 수준의 변화는 모델이 반영하지 못하고
무시하거나 전체를 다시 그려버린다.
각 상태의 정체성(표정 톤·귀 모양·소품 종류)과 **음영 패턴**은 건드리지 않는다.
포즈가 바뀐 부위만 음영이 따라 바뀌고, 광원 방향은 그대로 왼쪽 위.

1. deploy-success  — 만세 앞발을 바운스 바닥까지 2px 내림,
                     체크는 2px 위로 팝, 꼬리 반대쪽으로, 반짝임 위치 변경
2. testing         — 몸을 한 호흡 내려앉힘(발 고정), 로딩 점 3개 1칸 순환,
                     화면 글로우 면적 살짝 축소
3. coffee          — 머그를 입 쪽으로 한 칸 들어올리고 고개 살짝 숙임,
                     김 픽셀 전부 위로 이동, 맨 위 것 삭제하고 아래 새로 1개
4. build-failed    — 머리만 2px 옆으로 기울임(떨림, 목 아래 고정),
                     땀방울 1px 아래, X 1px 이동
5. refactoring     — 렌치 든 앞발을 가슴 높이까지 아래로 휘두름,
                     다른 앞발은 유지, 불꽃 실루엣만 다르게
                     (높이·색 수 동일, 깜빡임 형태만 변경)
6. idle-greeting   — 인사하던 앞발을 가슴 근처까지 내림(흔들기 바닥),
                     몸 전체가 숨 내쉬듯 내려앉음(발 고정), 귀 끝 살짝 처짐,
                     하트는 위로 떠오르며 한 단계 작아짐, 반짝임 사라짐
7. writing         — 연필 쥔 앞발을 종이 반대쪽 끝으로 이동(획 진행),
                     고개 각도 살짝 변경, 종이에 획 픽셀 1개 추가,
                     커서 픽셀 on/off
8. debugging       — 돋보기를 반대쪽 앞발로 옮기고 약간 아래·옆으로,
                     확대된 눈을 반대쪽으로 스왑, 상체 1px 더 기울임,
                     버그 픽셀 위치 이동

## 생성 순서
1. idle-greeting(6번) 프레임 A 먼저 → 애플헤드 55% 비율, 귀 크기,
   **음영 단계 수와 광원 방향**을 여기서 확정
2. 확정되면 그 이미지를 레퍼런스로 첨부해 나머지 7종 A 생성
3. 각 상태의 A를 첨부해 같은 상태의 B 생성 (8회)

## 후처리
나노바나나는 진짜 픽셀 그리드를 보장하지 않으므로 필수.

1. 마젠타 배경 키 아웃 → 투명화
2. nearest-neighbor로 64×64 다운스케일 (bilinear 쓰면 뭉개짐)
3. 팔레트 17색으로 강제 양자화

  magick input.png \
    -fuzz 12% -transparent '#FF00FF' \
    -filter point -resize 64x64 \
    -dither None -remap palette.png \
    out.png

palette.png = 17색을 1픽셀씩 가로로 늘어놓은 이미지
-dither None이 핵심. 이걸 빼면 양자화가 음영 경계를 디더링으로 메워서
픽셀아트 느낌이 깨진다.

### 음영 검수
양자화 후 색 수를 세서 팔레트 밖 색이 남았는지 확인:

  magick out.png -format %k info:

17 이하가 나와야 한다. 넘으면 remap이 제대로 안 걸린 것.
램프 단계가 뭉개져 보이면 다운스케일 전 원본에서 음영 대비가
부족했던 것이므로, 프롬프트에 "clearly visible stepped bands" 강조 후 재생성.

### 프레임 정렬 (8종 전부 필수)
B를 생성으로 뽑으므로 A와 반드시 어긋난다. 이 단계를 빼면 재생 시 떨린다.

1. A·B 각각 다운스케일 + 양자화
2. 두 프레임의 발바닥 최하단 y, 실루엣 좌우 중심 x 계산
3. B를 평행이동해 A에 맞춤
4. A/B 교대 재생하며 의도 외 움직이는 픽셀은 A에서 복사해 덮어쓰기
   → 귀 끝·코 1px 흔들림, **음영 경계선 1px 이동**은 재생하면 바로 보임

4번에서 수정량이 너무 많으면 그 상태는 B 생성을 포기하고
A를 픽셀 시프트해서 B를 만드는 쪽이 빠르다. (특히 변화량이 작은
idle-greeting / testing / coffee / writing에서 자주 발생)

## 시트 배치 & CSS
행 순서: idle-greeting, deploy-success, testing, coffee,
        build-failed, refactoring, writing, debugging
열: frame A, frame B

  .pet {
    width: 64px; height: 64px;
    background-image: url(/pet-sheet.png);
    background-repeat: no-repeat;
    image-rendering: pixelated;
    animation: pet-loop var(--dur) steps(2) infinite;
  }
  @keyframes pet-loop {
    from { background-position-x: 0; }
    to   { background-position-x: -128px; }
  }

상태별 background-position-y: 0 / -64 / -128 / -192 / -256 / -320 / -384 / -448px
속도(--dur): idle 1000ms, deploy 500ms, testing 700ms, coffee 1200ms,
            build-failed 300ms, refactoring 400ms, writing 600ms, debugging 700ms

steps(2)에 -128px까지 가는 게 포인트. steps는 마지막 값에 도달하지 않으므로
0 → -64px 두 칸만 재생된다.
prefers-reduced-motion에서는 animation: none으로 A 프레임 고정.

## 프롬프트 작성 규칙

### 공통
- 공통 스타일 블록 1개 + 개별 블록 구조. 공통 블록은 매번 그대로 반복
- 프롬프트는 영어로 작성 (모델 지시 준수율이 높음)
- 팔레트는 hex로 명시하고 "use ONLY these colors, no others" 명시
- 음영은 반드시 함께 명시: 광원 방향, 하드엣지 밴딩, 그라데이션·디더링 금지
  → "cel-shaded with hard-edged color bands" 같은 표현이
     "shading"만 쓰는 것보다 훨씬 잘 먹는다
- 액센트 오브젝트는 위치까지 지정 (머리 위 / 머리 옆 / 앞발 앞 / 등 뒤)

### 프레임 A (2번째 이후)
레퍼런스 첨부 + 다음 취지를 명시:
동일 비율·팔레트·해상도·외곽선·**광원 방향과 음영 단계 수** 유지,
포즈와 표정과 소품만 변경

### 프레임 B
헤더에서 다음을 고정한 뒤 CHANGE ONLY로 변경점만 열거:
- 캔버스 크기, 팔레트, 외곽선 두께
- 머리/몸통 비율, 실루엣 크기, 캔버스 내 위치
- 발바닥 높이
- **광원 방향과 음영 패턴** (포즈가 바뀐 부위만 따라 변함)
- "새 그림이 아니라 같은 스프라이트의 한 프레임 뒤"임을 명시
- redesign 금지, 전신 재포즈 금지, 카메라 앵글 변경 금지

### 자주 나는 실패와 대응 문구
- 음영이 부드럽게 번짐
  → Shading must be hard-edged flat color bands with visible steps between
    tones. Absolutely no gradient, no soft falloff, no dithering.
- 팔레트 밖 중간색이 생김
  → Every pixel must be exactly one of the listed hex values. Do not blend
    or interpolate between palette colors.
- 광원 방향이 프레임마다 바뀜
  → The light source is fixed at the upper left. Highlights on the top of the
    head and the upper edges of the ears, shadows under the chin and belly.
- 캐릭터 크기가 달라짐
  → The character must occupy the exact same bounding box as in the attached
    image. Do not zoom in or out.
- 발이 떠다님
  → The feet must touch the exact same scanline as in the attached image.
- 지정 안 한 곳까지 바뀜
  → The head and face are locked. Reproduce them pixel for pixel from the
    attached image.
