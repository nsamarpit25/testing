"""sqgeom.py: exact rolling geometry for a square wheel, in units of the wheel's apothem (half-side) a = 1.

Matched road: a chain of inverted catenary arcs  y = -cosh(x - kP),  |x - kP| <= L,  L = asinh(1),  P = 2L.
With the axle held at y = 0 the contact point is always straight below it (the contact is the instant centre of a
non-slipping roll and the axle moves horizontally). For axle x = c, local u = c - kP:
    contact = (c, -cosh u),  wheel angle phi = -k*pi/2 - atan(sinh u)   (clockwise = rolling right)
The face sits tangent to the road (slope -sinh u) at distance cosh(u) * cos(atan(sinh u)) = 1 from the axle, and the
rolled arc length sinh(u) equals the distance from the face midpoint to the contact, so there is no slip. At u = +-L the
corner (distance sqrt 2) lands exactly in the join, where the next arc takes the next face.
For a steady motor (phi linear in time) the axle speed dc/d|phi| = cosh(u) runs 1 .. sqrt2: it varies, honestly.

Flat road (y = -1): the square pivots on each corner; the axle height runs between 0 and sqrt2 - 1.
"""
from math import asinh, sinh, cosh, atan, tan, pi, sqrt, floor, cos, sin

L = asinh(1.0)
P = 2 * L
Q = pi / 2

def road_y(x):
    k = round(x / P); return -cosh(x - k * P)

def matched_from_phi(phi):
    """wheel angle (rad, <= 0 rolling right) -> (axle x, axle y, contact x, contact y). phi = 0: face down on crest 0."""
    k = floor((-phi + pi / 4) / Q)          # which face is down
    pl = phi + k * Q                        # local angle in [-pi/4, pi/4]
    u = asinh(tan(-pl)); c = k * P + u
    return c, 0.0, c, -cosh(u)

def flat_from_phi(phi):
    """same wheel on a flat floor at y = -1, phi = 0 face down with axle at (0, 0)."""
    k = floor(-phi / Q); pl = phi + k * Q   # pivot on corner k, local angle in (-pi/2, 0]
    px = 1 + 2 * k
    cx = px + (-1) * cos(pl) - 1 * sin(pl); cy = -1 + (-1) * sin(pl) + 1 * cos(pl)
    return cx, cy, px, -1.0

def square_pts(cx, cy, phi, n=40):
    """points on the wheel outline (corners at +-1, +-1 in the wheel frame)."""
    out = []
    for s in range(4):
        a0 = [(1, -1), (1, 1), (-1, 1), (-1, -1)][s]; a1 = [(1, 1), (-1, 1), (-1, -1), (1, -1)][s]
        for i in range(n):
            u = i / n; x = a0[0] + (a1[0] - a0[0]) * u; y = a0[1] + (a1[1] - a0[1]) * u
            out.append((cx + x * cos(phi) - y * sin(phi), cy + x * sin(phi) + y * cos(phi)))
    return out

if __name__ == '__main__':
    import sys
    worst_h = 0; worst_pen = 0; worst_gap = 0; slip = 0
    N = 20000
    for i in range(N + 1):
        phi = -i / N * 4 * pi                       # two full turns
        cx, cy, kx, ky = matched_from_phi(phi)
        worst_h = max(worst_h, abs(cy))
        pts = square_pts(cx, cy, phi, 60)
        d = min(py - road_y(px) for px, py in pts)  # >= 0: outline on or above the road
        worst_pen = min(worst_pen, d); worst_gap = max(worst_gap, d)
        # no-slip: road arc length from the crest to the contact == distance along the down face from its midpoint
        k = round(cx / P); u = cx - k * P; pl = phi + k * Q
        dx, dy = kx - cx, ky - cy                   # contact in the wheel frame
        along = dx * cos(pl) + dy * sin(pl)
        slip = max(slip, abs(along - sinh(u)))
    # flat road
    fh = [flat_from_phi(-i / N * 2 * pi)[1] for i in range(N + 1)]
    fpen = min(min(py + 1 for px, py in square_pts(*flat_from_phi(-i / 500 * 2 * pi)[:2], -i / 500 * 2 * pi, 60)) for i in range(501))
    # speed variation under a steady motor
    sp = []
    for i in range(1, 2001):
        p0, p1 = -(i - 1) / 2000 * pi, -i / 2000 * pi
        sp.append((matched_from_phi(p1)[0] - matched_from_phi(p0)[0]) / (p0 - p1))
    print(f'L = {L:.6f}  P = {P:.6f}  join depth = {-cosh(L):.6f} (sqrt2 = {sqrt(2):.6f})')
    print(f'matched: max |axle height| = {worst_h:.2e}, min clearance = {worst_pen:.2e}, max face gap = {worst_gap:.3f}')
    print(f'flat:    axle height range {min(fh):.4f} .. {max(fh):.4f} (sqrt2-1 = {sqrt(2) - 1:.4f}), min clearance {fpen:.2e}')
    print(f'steady motor on matched road: axle speed {min(sp):.3f} .. {max(sp):.3f} x apothem per rad')
    # face-to-road tangency at the contact (slope of face == slope of road)
    err = 0
    for i in range(2001):
        phi = -i / 2000 * 2 * pi; cx, _, kx, ky = matched_from_phi(phi); k = round(cx / P); u = cx - k * P
        err = max(err, abs(((phi + k * Q + pi) % (pi / 2)) - ((-atan(sinh(u)) + pi) % (pi / 2))) % (pi / 2))
    print(f'face/road tangency error {err:.2e} rad, no-slip error {slip:.2e}')
    sys.exit(0 if worst_h < 1e-12 and worst_pen > -1e-9 and slip < 1e-9 else 1)
