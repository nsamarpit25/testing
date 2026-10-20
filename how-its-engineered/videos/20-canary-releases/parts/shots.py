CX = CAN.x
KN = V3(DX, DY, 1.03); CANS = V3(CX, 0.0, 0.85); MET = V3(MX, MFY, 1.0)
# L0 the one phone, then crane back over the hundred
push(0.0, (CX + 0.35, -2.55, 1.02), (CX, 0.0, 0.84), 0.9, 50, 2.0)
def _s1(t, u, e, s):
    k = EZ['io'](u); kz = EZ['out'](u)
    P0, P1 = V3(CX + 0.4, -2.7, 1.05), V3(CX + 5.0, -15.5, 9.8)
    P = P0.lerp(P1, k); P.z = P0.z + (P1.z - P0.z) * kz
    return P, CANS.lerp(V3(0.0, 8.0, 0.2), k)
shot(t99 - 0.1, (0, 0, 0), (0, 0, 1), None, None, 35, 3.5, fnP=_s1, ez='io', foc=lambda t, P, G: CANS.lerp(V3(0, 6, 0.4), EZ['io'](clamp((t - t99) / 2.2))))
# L1 everyone at once
shot(tUSUAL, (13.0, -6.5, 1.8), (1.0, 7.0, 0.9), (11.5, -5.5, 2.4), (0.0, 7.0, 0.9), 32, 4.0)
shot(tEVERY, (-3.0, -13.0, 10.0), (0.5, 9.0, 0.0), (-2.0, -12.5, 11.0), None, 30, 6.0)
# L2 spot the problem
push(tSPOT, (5.2, -2.6, 1.05), (-2.0, 12.0, 0.95), 0.9, 40, 2.2, foc=lambda t, P, G: V3(ORIGIN.x, ORIGIN.y, 0.85))
# L3 one bug -> every phone
OG = V3(ORIGIN.x, ORIGIN.y, 0.85)
def _s5(t, u, e, s):
    k = EZ['io'](clamp((t - (tEVERY2 - 0.1)) / 1.5)); kz = EZ['out'](k)
    P0, P1 = V3(ORIGIN.x, ORIGIN.y - 3.4, 1.2), V3(ORIGIN.x + 2.0, ORIGIN.y - 13.5, 6.5)
    P = P0.lerp(P1, k); P.z = P0.z + (P1.z - P0.z) * kz
    P = P + (OG - P) * 0.05 * e * (1 - k)
    return P, OG.lerp(V3(0.5, 7.0, 0.5), k)
shot(tONEBUG, (0, 0, 0), (0, 0, 1), None, None, 40, 2.8, fnP=_s5, foc=lambda t, P, G: OG.lerp(V3(0.5, 6, 0.5), EZ['io'](clamp((t - tEVERY2) / 1.4))))
shot(tTESTER, (0, 0, 1), (0, 0, 0), None, None, 30, 8.0, fnP=lambda t, u, e, s: (V3(0, 9.0, 0) + Matrix.Rotation(rad(-9 + 14 * EZ['io'](u)), 3, 'Z') @ V3(0, -15.0, 17.0), V3(0, 9.0, 0)), ez='io')
shot(tBYTIME, (-7.0, -6.5, 1.5), (2.0, 8.0, 1.0), (-6.0, -6.8, 1.75), None, 30, 4.0)
# L4 the dial
GD = KN + V3(0, 0.02, 0)
shot(tFIX, (0, 0, 0), (0, 0, 1), None, None, 50, 2.0, fnP=lambda t, u, e, s: (GD + Matrix.Rotation(rad(14 - 20 * EZ['io'](u)), 3, 'Z') @ V3(0.2, -1.25, 0.5), GD), ez='io')
POV = V3(DX - 0.55, DY - 1.05, 1.45)
def overdial(k_canary):
    return lambda t, P, G: KN.lerp(CANS, EZ['io'](clamp((t - k_canary) / 0.4)))
shot(tSEND, POV, KN.lerp(CANS, 0.62), POV + V3(0.08, 0.1, -0.02), None, 35, 2.4, foc=overdial(t1 + 0.15))
shot(tUSERS, (CX + 2.0, -9.0, 5.5), (CX + 0.5, 5.0, 0.3), (CX + 2.4, -9.4, 5.8), None, 35, 5.0)
# L5 watch the numbers
push(tWATCH, (MX + 0.25, MY - 1.75, 1.12), (MX, MFY, 0.95), 0.93, 50, 2.4)
PM = V3(MX - 0.95, MY - 1.55, 1.25)
shot(tIF, PM, MET.lerp(CANS, 0.55), PM + V3(0.05, 0.12, 0), None, 32, 4.5, foc=lambda t, P, G: MET.lerp(CANS, 0.75))
shot(tROLLS - 0.02, POV + V3(0.1, 0.25, -0.05), KN.lerp(CANS, 0.6), POV + V3(0.15, 0.32, -0.06), None, 40, 2.4, foc=overdial(tROLLS + 0.3))
# L6 1 -> 5 -> 25 -> 100, craning up off the dial
def _s14(t, u, e, s):
    k = EZ['io'](clamp((t - (t5 + 0.3)) / 1.7)); kz = EZ['out'](k)
    P0, P1 = V3(DX + 0.55, DY - 1.25, 1.55), V3(-1.5, -14.5, 11.0)
    P = P0.lerp(P1, k); P.z = P0.z + (P1.z - P0.z) * kz
    return P, KN.lerp(V3(0.0, 8.0, 0.0), k)
shot(tGOOD, (0, 0, 0), (0, 0, 1), None, None, 35, 3.0, fnP=_s14, foc=lambda t, P, G: KN.lerp(V3(0, 6, 0.4), EZ['io'](clamp((t - (t5 + 0.3)) / 1.7))))
# L7 the restaurant
HP = V3(HT[0], HT[1], 0.82)
shot(tDISH - 0.02, (RX + 2.6, -5.6, 2.4), (RX, 3.0, 0.9), (RX + 2.1, -5.1, 2.25), None, 30, 4.0, whip='R')
push(tSERVE, (HT[0] + 0.55, HT[1] - 1.2, 1.25), HP, 0.92, 50, 2.0)
def _s17(t, u, e, s):
    pp = V3(*glide(clamp(t, G0, G1))) + V3(0, 0, 0.1); return V3(HT[0] + 2.4, HT[1] + 0.8 + 0.5 * e, 1.75), pp
shot(tIF2, (0, 0, 0), (0, 0, 1), None, None, 35, 2.8, fnP=_s17, foc=lambda t, P, G: G)
shot(tREST, (RX - 4.6, -4.4, 5.0), (RX, 3.4, 0.5), (RX - 4.1, -4.8, 5.3), None, 28, 5.0)
# L8 a bug can still ship
shot(tBUG2, (4.0, -11.0, 4.2), (0.0, 6.0, 0.6), (3.5, -10.5, 4.0), None, 32, 5.0, whip='L')
shot(tHITS - 0.2, (CX + 1.0, -4.2, 1.6), (CX, 1.5, 0.85), (CX + 0.8, -4.0, 1.5), None, 32, 3.5, foc=lambda t, P, G: CANS)
# L9 a few, then everyone
shot(tFEW0, (-4.0, -12.0, 9.0), (0.0, 8.0, 0.0), (-3.0, -12.5, 9.5), None, 30, 6.0)
# L10 the plaques
shot(tARGO - 0.12, (DX - 0.22, PF - 1.25, 0.64), (DX - 0.06, PF, 0.60), (DX + 0.12, PF - 1.2, 0.48), (DX + 0.04, PF, 0.43), 50, 2.8, ez='io')
# L11 wide orbit
G23 = V3(0.0, 8.0, 0.4)
shot(tCTA, orbit(G23, -24, 22.0, 9.0), G23, None, None, 28, 6.0, fnP=lambda t, u, e, s: (orbit(G23, -24 + 18 * EZ['io'](u), 22.0, 9.0 - 1.0 * u), G23), ez='io')
