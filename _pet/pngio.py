"""PNG 디코딩. 표준 라이브러리만 쓴다.

8비트 non-interlaced PNG 만 다룬다. 스프라이트시트 후처리에 필요한 범위다.
"""

import struct
import zlib

CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def decode(path):
    """PNG 파일을 (width, height, 행별 RGBA 튜플 리스트) 로 읽는다."""
    data = open(path, 'rb').read()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('PNG 가 아니다')

    idat = bytearray()
    plte = trns = None
    i = 8
    while i < len(data):
        ln = struct.unpack('>I', data[i:i + 4])[0]
        tag = data[i + 4:i + 8]
        body = data[i + 8:i + 8 + ln]
        if tag == b'IHDR':
            w, h, depth, ctype, _, _, interlace = struct.unpack('>IIBBBBB', body)
            if depth != 8 or interlace:
                raise ValueError(f'8비트 non-interlaced 만 읽는다 (depth={depth}, interlace={interlace})')
        elif tag == b'PLTE':
            plte = body
        elif tag == b'tRNS':
            trns = body
        elif tag == b'IDAT':
            idat += body
        elif tag == b'IEND':
            break
        i += 12 + ln

    raw = zlib.decompress(bytes(idat))
    nch = CHANNELS[ctype]
    stride = w * nch

    # 필터 해제. 스캔라인마다 앞줄을 참조하므로 순서대로 처리한다
    out = []
    prev = bytearray(stride)
    pos = 0
    for _ in range(h):
        ft = raw[pos]
        line = bytearray(raw[pos + 1:pos + 1 + stride])
        pos += 1 + stride
        if ft == 1:
            for x in range(nch, stride):
                line[x] = (line[x] + line[x - nch]) & 0xFF
        elif ft == 2:
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 0xFF
        elif ft == 3:
            for x in range(stride):
                a = line[x - nch] if x >= nch else 0
                line[x] = (line[x] + ((a + prev[x]) >> 1)) & 0xFF
        elif ft == 4:
            for x in range(stride):
                a = line[x - nch] if x >= nch else 0
                c = prev[x - nch] if x >= nch else 0
                line[x] = (line[x] + _paeth(a, prev[x], c)) & 0xFF
        elif ft != 0:
            raise ValueError(f'알 수 없는 필터 타입 {ft}')
        out.append(bytes(line))
        prev = line

    return w, h, [_to_rgba(line, w, ctype, plte, trns) for line in out]


def _to_rgba(line, w, ctype, plte, trns):
    """스캔라인 한 줄을 RGBA 튜플 리스트로 편다."""
    if ctype == 6:
        return [tuple(line[x * 4:x * 4 + 4]) for x in range(w)]
    if ctype == 2:
        return [tuple(line[x * 3:x * 3 + 3]) + (255,) for x in range(w)]
    if ctype == 0:
        return [(line[x], line[x], line[x], 255) for x in range(w)]
    if ctype == 4:
        return [(line[x * 2], line[x * 2], line[x * 2], line[x * 2 + 1]) for x in range(w)]
    if ctype == 3:
        px = []
        for x in range(w):
            k = line[x]
            a = trns[k] if trns and k < len(trns) else 255
            px.append((plte[k * 3], plte[k * 3 + 1], plte[k * 3 + 2], a))
        return px
    raise ValueError(f'지원하지 않는 컬러 타입 {ctype}')


def encode(rows, scale=1):
    """RGBA 행렬을 PNG 바이트로. 확대는 픽셀 복제라 nearest-neighbor 와 같다."""
    h = len(rows) * scale
    w = len(rows[0]) * scale
    raw = bytearray()
    for row in rows:
        line = bytearray()
        for px in row:
            line.extend(bytes(px) * scale)
        for _ in range(scale):
            raw.append(0)  # 필터 타입 None
            raw.extend(line)

    def chunk(tag, data):
        body = tag + data
        return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body) & 0xFFFFFFFF)

    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(bytes(raw), 9))
            + chunk(b'IEND', b''))
