#!/usr/bin/env python3
"""생성 격자들을 86x86 프레임 18장과 172x774 스프라이트시트로 만든다.

    python3 _pet/build_sheet.py [--size N]

표준 라이브러리만 쓴다. 흐름은 투명화 -> 셀 분할 -> 본체 검출 -> 86x86 재배치
-> 17색 양자화 -> A/B 정렬 -> 시트 병합이다.

셀 경계를 신뢰하지 않는다는 원칙은 그대로 따르되, 정렬 기준을 프레임마다
따로 잡지 않고 행마다 A 프레임 하나에서 뽑아 A 와 B 에 똑같이 적용한다.
프레임마다 본체 상자를 새로 재면 앞발을 벌리거나 귀를 세운 포즈에서 상자가
커져서 개가 커졌다 작아졌다 하고, 그게 재생할 때 떨림으로 보인다.
A 에서 뽑은 기준을 B 에 그대로 쓰면 A/B 사이의 의도된 움직임만 남는다.
"""

import struct
import sys
import zlib
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pngio import decode, encode  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).parent
OUT = ROOT / 'assets' / 'pet'
ALIGNED = HERE / 'aligned'

BACKGROUND = (253, 0, 251, 255)

# 생성 격자들. 셀 높이는 파일마다 다르지만 도트 한 칸이 6px 로 같아서
# 공통 배율 하나로 묶어도 개 크기가 행마다 어긋나지 않는다
SOURCES = [
    {'path': HERE / 'source-grid.png', 'cw': 512, 'ch': 516, 'cols': 2, 'rows': 8},
    {'path': HERE / 'source-barking.png', 'cw': 512, 'ch': 484, 'cols': 2, 'rows': 1},
]

# 시트의 행 순서. (상태 이름, 격자 번호, 그 격자 안의 행 번호)
LAYOUT = [
    ('idle-greeting', 0, 0),
    ('deploy-success', 0, 1),
    ('testing', 0, 2),
    ('coffee', 0, 3),
    ('build-failed', 0, 4),
    ('refactoring', 0, 5),
    ('writing', 0, 6),
    ('debugging', 0, 7),
    ('barking', 1, 0),
]

# 원본 생성 단계에서 남은 결함을 배경색으로 덮는다.
# (격자 번호, 격자 안의 행, 열, x0, x1, y0, y1) 이고 좌표는 셀 안에서 잰 값이다
REPAIRS = [
    # barking 의 번개 표시가 셀 오른쪽으로 길게 뻗어 있다. 배율은 전 프레임이
    # 함께 쓰는 값이라, 이 장식 하나 때문에 아홉 상태의 개가 모두 작아진다.
    # 개는 x477 안쪽에 있으므로 번개 끝 네 칸만 자른다.
    # 이 두 줄을 빼면 배율이 0.1605 에서 0.1467 로 떨어진다
    (1, 0, 0, 478, 511, 0, 483),
    (1, 0, 1, 478, 511, 0, 483),
]

# 원본 도트 한 칸이 6px 이라 셀 512px 의 실제 도트 해상도는 85칸이다.
# 86 은 거기에 맞춘 값이라 화면에서 확대하지 않고 1배로 쓸 수 있다.
# 64 로 뽑으면 칸의 25%를 버리게 되고, 그걸 2배로 늘리면 뭉갠 자국이 커져 보인다
SIZE = 86
# 기준점을 놓는 줄. 줄일 때 마지막 줄이 살아남지 않아서 출력의 발바닥은 한 줄
# 위(80)에 놓인다. 아래로 5칸 남는데 debugging 의 발밑 벌레가 그 칸을 쓴다
FOOT_Y = round(SIZE * 60 / 64)
CENTER_X = SIZE // 2
FRAMES = ['a', 'b']

# 17색 고정 팔레트. 투명은 알파로 처리하므로 여기 넣지 않는다
PALETTE = [
    (0xFF, 0xF8, 0xE7), (0xF5, 0xE6, 0xC8), (0xE0, 0xC9, 0xA0), (0xC4, 0xA8, 0x7C),
    (0xE8, 0xA0, 0xA8), (0xC9, 0x7F, 0x8A),
    (0x2B, 0x21, 0x18), (0xFF, 0xFF, 0xFF),
    (0x5C, 0xB8, 0x5C), (0x3F, 0x8C, 0x42),
    (0xD9, 0x53, 0x4F), (0xA8, 0x3B, 0x38),
    (0x8B, 0x5E, 0x3C), (0x6B, 0x45, 0x29),
    (0xF0, 0x87, 0x3F), (0xC9, 0x6B, 0x2E),
    (0x6F, 0xD8, 0xE0),
]


def is_background(px):
    """생성 이미지라 배경이 #FF00FF 하나가 아니라 잡티 섞인 마젠타 면이다.

    귀 안쪽 분홍은 파랑이 초록보다 크게 높지 않아 걸리지 않는다.
    """
    r, g, b = px[0], px[1], px[2]
    return r > 150 and b > 150 and r - g > 60 and b - g > 55 and abs(r - b) < 70


def repair(px, si):
    """해당 격자의 결함 영역을 배경색으로 덮는다. 본체를 재기 전에 부른다."""
    src = SOURCES[si]
    for gi, ri, ci, x0, x1, y0, y1 in REPAIRS:
        if gi != si:
            continue
        for y in range(ri * src['ch'] + y0, ri * src['ch'] + y1 + 1):
            row = px[y]
            for x in range(ci * src['cw'] + x0, ci * src['cw'] + x1 + 1):
                row[x] = BACKGROUND


def cell_mask(px, ox, oy, cw, ch):
    """셀 하나의 불투명 여부를 행별 bytearray 로."""
    return [bytearray(0 if is_background(px[oy + y][ox + x]) else 1 for x in range(cw))
            for y in range(ch)]


def components(mask):
    """연결 성분을 (픽셀수, x0, x1, y0, y1) 로. 8방향으로 잇는다."""
    ch, cw = len(mask), len(mask[0])
    seen = [bytearray(cw) for _ in range(ch)]
    out = []
    for sy in range(ch):
        for sx in range(cw):
            if not mask[sy][sx] or seen[sy][sx]:
                continue
            stack = [(sy, sx)]
            seen[sy][sx] = 1
            n = 0
            x0 = x1 = sx
            y0 = y1 = sy
            while stack:
                cy, cx = stack.pop()
                n += 1
                x0 = min(x0, cx); x1 = max(x1, cx)
                y0 = min(y0, cy); y1 = max(y1, cy)
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < ch and 0 <= nx < cw and mask[ny][nx] and not seen[ny][nx]:
                            seen[ny][nx] = 1
                            stack.append((ny, nx))
            out.append((n, x0, x1, y0, y1))
    out.sort(reverse=True)
    return out


def nearest(color):
    return min(PALETTE, key=lambda q: sum((color[i] - q[i]) ** 2 for i in range(3)))


def sample(px, ox, oy, xc, yb, scale, cw, ch):
    """셀을 SIZE x SIZE 로 줄인다. 출력 픽셀마다 원본 영역의 최빈색을 쓴다.

    원본 도트 한 칸이 6px 인데 출력 한 픽셀이 그보다 커서, 한 점만 찍어 오면
    그 점이 잡티일 때 눈과 하이라이트가 사라진다. 영역에서 가장 많이 나온 색을
    고르면 색을 섞지 않으므로 원본에 없던 색이 생기지 않는다.
    배경이 영역의 절반을 넘으면 투명으로 둔다.
    """
    out = []
    for oy_i in range(SIZE):
        row = []
        for ox_i in range(SIZE):
            # 출력 픽셀 한 칸이 덮는 원본 사각형
            sx0 = xc + (ox_i - CENTER_X) / scale
            sx1 = xc + (ox_i + 1 - CENTER_X) / scale
            sy0 = yb + (oy_i - FOOT_Y) / scale
            sy1 = yb + (oy_i + 1 - FOOT_Y) / scale
            seen = Counter()
            bg = total = 0
            for y in range(max(int(sy0), 0), min(int(sy1) + 1, ch)):
                line = px[oy + y]
                for x in range(max(int(sx0), 0), min(int(sx1) + 1, cw)):
                    q = line[ox + x]
                    total += 1
                    if is_background(q):
                        bg += 1
                    else:
                        seen[(q[0] >> 3, q[1] >> 3, q[2] >> 3)] += 1
            if not total or bg * 2 >= total or not seen:
                row.append(None)
                continue
            bucket = seen.most_common(1)[0][0]
            exact = Counter()
            for y in range(max(int(sy0), 0), min(int(sy1) + 1, ch)):
                line = px[oy + y]
                for x in range(max(int(sx0), 0), min(int(sx1) + 1, cw)):
                    q = line[ox + x]
                    if not is_background(q) and (q[0] >> 3, q[1] >> 3, q[2] >> 3) == bucket:
                        exact[(q[0], q[1], q[2])] += 1
            row.append(nearest(exact.most_common(1)[0][0]))
        out.append(row)
    return out


def encode_indexed(rows):
    """17색 + 투명을 인덱스 PNG(컬러타입 3)로 쓴다.

    pngquant 나 oxipng 가 없는 환경이라 색 수를 아는 쪽이 직접 줄인다.
    17색뿐이므로 픽셀당 4바이트 대신 1바이트면 되고, 손실은 없다.
    인덱스 0을 투명으로 두고 tRNS 로 알파를 준다.
    """
    index = {c: i + 1 for i, c in enumerate(PALETTE)}
    raw = bytearray()
    for row in rows:
        raw.append(0)  # 필터 타입 None
        raw.extend(0 if c is None else index[c] for c in row)

    def chunk(tag, data):
        body = tag + data
        return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body) & 0xFFFFFFFF)

    plte = bytes((0, 0, 0)) + b''.join(bytes(c) for c in PALETTE)
    trns = bytes([0] + [255] * len(PALETTE))
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', len(rows[0]), len(rows), 8, 3, 0, 0, 0))
            + chunk(b'PLTE', plte)
            + chunk(b'tRNS', trns)
            + chunk(b'IDAT', zlib.compress(bytes(raw), 9))
            + chunk(b'IEND', b''))


def diff_count(fa, fb, dx=0, dy=0):
    """두 프레임에서 서로 다른 픽셀 수. fb 를 (dx, dy) 만큼 옮겨 놓고 센다."""
    n = 0
    for y in range(SIZE):
        for x in range(SIZE):
            sy, sx = y - dy, x - dx
            q = fb[sy][sx] if 0 <= sy < SIZE and 0 <= sx < SIZE else None
            if fa[y][x] != q:
                n += 1
    return n


def best_shift(fa, fb, reach=3):
    """fb 를 몇 칸 옮기면 fa 와 가장 비슷해지는지 찾는다."""
    return min(((diff_count(fa, fb, dx, dy), dx, dy)
                for dx in range(-reach, reach + 1)
                for dy in range(-reach, reach + 1)))[1:]


def main():
    grids = []
    for si, src in enumerate(SOURCES):
        w, h, px = decode(src['path'])
        if (w, h) != (src['cw'] * src['cols'], src['ch'] * src['rows']):
            raise SystemExit(f"{src['path'].name} 격자 크기가 예상과 다르다: {w}x{h}")
        repair(px, si)
        opaque = sum(1 for r in px for p in r if not is_background(p))
        print(f"{src['path'].name}  불투명 비율 {opaque / (w * h):.3f} (0.15~0.5 정상)")
        grids.append(px)

    def origin(li, ci):
        _, si, sr = LAYOUT[li]
        src = SOURCES[si]
        return si, ci * src['cw'], sr * src['ch'], src['cw'], src['ch']

    # 셀마다 본체(가장 큰 연결 성분)와 전체 내용 상자를 잰다
    body, content = {}, {}
    for li in range(len(LAYOUT)):
        for ci in range(len(FRAMES)):
            si, ox, oy, cw, ch = origin(li, ci)
            comps = components(cell_mask(grids[si], ox, oy, cw, ch))
            body[(li, ci)] = comps[0]
            content[(li, ci)] = (min(c[1] for c in comps), max(c[2] for c in comps),
                                 min(c[3] for c in comps), max(c[4] for c in comps))

    # 행마다 A 프레임에서 기준점을 뽑는다
    anchor = {li: ((body[(li, 0)][1] + body[(li, 0)][2]) / 2, body[(li, 0)][4])
              for li in range(len(LAYOUT))}

    # 모든 셀의 내용이 캔버스 안에 들어가는 가장 큰 배율을 고른다.
    # 머리 위 체크와 등 뒤 불꽃 같은 액센트까지 포함한 상자로 따진다.
    # 가장자리에 1px 을 남겨서 액센트가 캔버스 끝에 붙지 않게 한다
    margin = 1
    scale = min(
        limit
        for li in range(len(LAYOUT))
        for ci in range(len(FRAMES))
        for limit in (
            (CENTER_X - margin) / max(anchor[li][0] - content[(li, ci)][0], 1e-9),
            (SIZE - 1 - margin - CENTER_X) / max(content[(li, ci)][1] - anchor[li][0], 1e-9),
            (FOOT_Y - margin) / max(anchor[li][1] - content[(li, ci)][2], 1e-9),
            (SIZE - 1 - margin - FOOT_Y) / max(content[(li, ci)][3] - anchor[li][1], 1e-9),
        )
    )
    print(f'공통 배율 {scale:.4f} (원본 {1 / scale:.1f}px -> 출력 1px)')

    def take(li, ci, xc, yb):
        si, ox, oy, cw, ch = origin(li, ci)
        return sample(grids[si], ox, oy, xc, yb, scale, cw, ch)

    # 본체 최하단을 원본에서 재서 기준점을 잡았지만, 줄일 때 마지막 줄이 살아남는지는
    # 그 줄에 원본 픽셀이 얼마나 걸리느냐에 달려 있어 행마다 1px 씩 갈린다.
    # A 프레임을 한 번 뽑아 보고 최빈값에 맞춰 기준점을 되돌린다
    def body_bottom(frame):
        return max(y for y in range(SIZE)
                   if sum(1 for c in frame[y] if c) >= 4)

    probe = {li: body_bottom(take(li, 0, *anchor[li])) for li in range(len(LAYOUT))}
    target = Counter(probe.values()).most_common(1)[0][0]
    for li, got in probe.items():
        if got != target:
            xc, yb = anchor[li]
            anchor[li] = (xc, yb - (target - got) / scale)
    print(f'발바닥 줄 {target} 로 정렬 '
          f'(보정한 행 {[LAYOUT[li][0] for li, g in probe.items() if g != target] or "없음"})')

    ALIGNED.mkdir(parents=True, exist_ok=True)
    frames = {}
    print('행: A/B 다른 픽셀 (정렬 전 -> 정렬 후, 옮긴 양)')
    for li, (state, si, sr) in enumerate(LAYOUT):
        xc, yb = anchor[li]
        fa = take(li, 0, xc, yb)
        fb = take(li, 1, xc, yb)

        # B 가 셀 안에서 밀려 그려진 만큼을 되돌린다. 출력 한 칸 단위로 대강 찾은 뒤
        # 잘게 흔들어 보고, 고른 양만큼 원본 좌표에서 다시 뽑는다.
        # 출력에서 옮기면 이미 뭉갠 픽셀을 옮기는 것이라 경계가 한 번 더 뭉갠다.
        # 가로는 0.25 칸까지 본다. 0.5 간격이면 실루엣이 한 줄 어긋난 채로 남는 행이 생긴다
        dx, dy = best_shift(fa, fb)
        best = (diff_count(fa, fb), 0.0, 0.0, fb)
        for sx in (dx - 0.5, dx - 0.25, dx, dx + 0.25, dx + 0.5):
            for sy in (dy - 0.5, dy, dy + 0.5):
                cand = take(li, 1, xc - sx / scale, yb - sy / scale)
                n = diff_count(fa, cand)
                if n < best[0]:
                    best = (n, sx, sy, cand)
        frames[(li, 0)], frames[(li, 1)] = fa, best[3]
        print(f'  {state:15} {diff_count(fa, fb):5} -> {best[0]:5}  '
              f'(dx{best[1]:+.2f} dy{best[2]:+.2f})')

        for ci, fr in enumerate(FRAMES):
            rgba = [[c + (255,) if c else (0, 0, 0, 0) for c in row]
                    for row in frames[(li, ci)]]
            (ALIGNED / f'{state}_{fr}.png').write_bytes(encode(rgba))

    sheet = [frames[(li, 0)][y] + frames[(li, 1)][y]
             for li in range(len(LAYOUT)) for y in range(SIZE)]
    path = OUT / 'pet-sheet.png'
    path.write_bytes(encode_indexed(sheet))
    print(f'{path.relative_to(ROOT)}  {SIZE * 2}x{SIZE * len(LAYOUT)}  '
          f'{path.stat().st_size}B')


if __name__ == '__main__':
    if '--size' in sys.argv:
        SIZE = int(sys.argv[sys.argv.index('--size') + 1])
        FOOT_Y = round(SIZE * 60 / 64)
        CENTER_X = SIZE // 2
    main()
