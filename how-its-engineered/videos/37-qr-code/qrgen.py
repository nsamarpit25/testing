# 37 QR code: a tiny QR encoder (version 3, error correction M, byte mode) that also tags what every module is for,
# so the reel can light up the finder squares, the timing lines, the alignment square, data and backup (EC) cells.
import json, sys
TEXT = sys.argv[1] if len(sys.argv) > 1 else 'https://instagram.com/how.its.engineered'
N, DATA_CW, EC_CW, MASK = 29, 44, 26, int(sys.argv[2]) if len(sys.argv) > 2 else -1

EXP, LOG = [0] * 512, [0] * 256
x = 1
for i in range(255):
    EXP[i] = x; LOG[x] = i; x <<= 1
    if x & 256: x ^= 0x11d
for i in range(255, 512): EXP[i] = EXP[i - 255]
def mul(a, b): return 0 if a == 0 or b == 0 else EXP[LOG[a] + LOG[b]]
def rs(data, n):
    g = [1]
    for i in range(n):
        g = [a ^ b for a, b in zip(g + [0], [0] + [mul(c, EXP[i]) for c in g])]
    rem = [0] * n
    for d in data:
        f = d ^ rem[0]; rem = rem[1:] + [0]
        rem = [r ^ mul(gc, f) for r, gc in zip(rem, g[1:])]
    return rem

bits = '0100' + format(len(TEXT), '08b') + ''.join(format(b, '08b') for b in TEXT.encode())
bits += '0' * min(4, DATA_CW * 8 - len(bits)); bits += '0' * (-len(bits) % 8)
cw = [int(bits[i:i + 8], 2) for i in range(0, len(bits), 8)]
pad = [0xEC, 0x11]; i = 0
while len(cw) < DATA_CW: cw.append(pad[i % 2]); i += 1
allcw = cw + rs(cw, EC_CW)

def build(mask):
    M = [[0] * N for _ in range(N)]; R = [[''] * N for _ in range(N)]
    def fn(x, y, v, r): M[y][x] = 1 if v else 0; R[y][x] = r
    for i in range(N): fn(6, i, i % 2 == 0, 't'); fn(i, 6, i % 2 == 0, 't')
    for cx, cy in ((3, 3), (N - 4, 3), (3, N - 4)):
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                x, y = cx + dx, cy + dy
                if 0 <= x < N and 0 <= y < N: fn(x, y, max(abs(dx), abs(dy)) not in (2, 4), 'f')
    for dy in range(-2, 3):
        for dx in range(-2, 3): fn(22 + dx, 22 + dy, max(abs(dx), abs(dy)) != 1, 'a')
    data = 0 << 3 | mask; rem = data
    for _ in range(10): rem = (rem << 1) ^ ((rem >> 9) * 0x537)
    fb = (data << 10 | rem) ^ 0x5412; gb = lambda i: (fb >> i) & 1
    for i in range(6): fn(8, i, gb(i), 'm')
    fn(8, 7, gb(6), 'm'); fn(8, 8, gb(7), 'm'); fn(7, 8, gb(8), 'm')
    for i in range(9, 15): fn(14 - i, 8, gb(i), 'm')
    for i in range(8): fn(N - 1 - i, 8, gb(i), 'm')
    for i in range(8, 15): fn(8, N - 15 + i, gb(i), 'm')
    fn(8, N - 8, 1, 'm')
    i, right = 0, N - 1
    while right >= 1:
        if right == 6: right = 5
        for vert in range(N):
            for j in range(2):
                x = right - j; up = ((right + 1) & 2) == 0; y = N - 1 - vert if up else vert
                if R[y][x]: continue
                if i < len(allcw) * 8:
                    M[y][x] = (allcw[i >> 3] >> (7 - (i & 7))) & 1; R[y][x] = 'd' if (i >> 3) < DATA_CW else 'e'; i += 1
                else: R[y][x] = 'r'
                if [(x + y) % 2 == 0, y % 2 == 0, x % 3 == 0, (x + y) % 3 == 0, (y // 2 + x // 3) % 2 == 0,
                    x * y % 2 + x * y % 3 == 0, (x * y % 2 + x * y % 3) % 2 == 0, ((x + y) % 2 + x * y % 3) % 2 == 0][mask]:
                    M[y][x] ^= 1
        right -= 2
    return M, R

def penalty(M):
    p = 0
    for G in (M, [list(c) for c in zip(*M)]):
        for row in G:
            run = 1
            for a, b in zip(row, row[1:]):
                if a == b: run += 1
                else:
                    if run >= 5: p += run - 2
                    run = 1
            if run >= 5: p += run - 2
            s = ''.join(map(str, row))
            p += 40 * (s.count('1011101') )
    for y in range(N - 1):
        for x in range(N - 1):
            if M[y][x] == M[y][x + 1] == M[y + 1][x] == M[y + 1][x + 1]: p += 3
    dark = sum(map(sum, M)); p += 10 * (abs(dark * 20 - N * N * 10) // (N * N))
    return p

best = MASK if MASK >= 0 else min(range(8), key=lambda m: penalty(build(m)[0]))
M, R = build(best)
out = {'n': N, 'text': TEXT, 'mask': best, 'bits': [''.join(map(str, r)) for r in M], 'role': [''.join(r) for r in R]}
open(sys.path[0] + '/qr.js', 'w').write('window.QR = ' + json.dumps(out) + ';\n')
from collections import Counter
print('mask', best, Counter(''.join(out['role'])))
# a PNG for checking with a real decoder
try:
    import numpy as np, zlib, struct
    S = 10; img = np.full(((N + 8) * S, (N + 8) * S), 255, np.uint8)
    for y in range(N):
        for x in range(N):
            if M[y][x]: img[(y + 4) * S:(y + 5) * S, (x + 4) * S:(x + 5) * S] = 0
    raw = b''.join(b'\0' + r.tobytes() for r in img)
    ch = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d))
    png = b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', img.shape[1], img.shape[0], 8, 0, 0, 0, 0)) + ch(b'IDAT', zlib.compress(raw)) + ch(b'IEND', b'')
    open(sys.path[0] + '/qr_check.png', 'wb').write(png)
except ImportError: pass
