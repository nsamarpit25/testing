CANP = V3(CANX, -0.03, CANZ); WC = V3(0.0, 0.0, WCZ)
PLZ = plq_at(C1)[2]
# L0 one screen, then the whole wall, all installing
def _s0(t, u, e, s):
    k = EZ['io'](clamp((t - 2.75) / 2.7))
    P0 = V3(CANX + 0.16, -1.5 + 0.16 * EZ['out'](clamp(t / 2.75)), CANZ + 0.04)
    return P0.lerp(V3(1.4, -13.6, WCZ - 0.2), k), CANP.lerp(WC, k)
shot(0.0, (0, 0, 0), (0, 0, 1), None, None, 40, 2.8, fnP=_s0)
shot(tAIR, (-5.2, -6.2, 1.6), (0.6, 0.0, 6.4), (-4.7, -5.7, 1.7), None, 22, 4.0)
shot(tBANKS, (AX + 0.3, -0.95, 1.5), (AX, 0.07, 1.33), (AX + 0.24, -0.8, 1.47), None, 32, 2.8)
shot(tHOSP, (HXs + 0.12, -0.5, 1.64), (HXs + 0.45, 0.29, 1.56), (HXs + 0.16, -0.36, 1.62), None, 35, 2.8)
shot(tBLUE, (0.6, -17.5, 0.95), (0.0, 0.0, 6.3), (0.4, -15.6, 1.05), None, 24, 5.0)
shot(tALL, (-15.9, -5.6, 1.45), (-13.0, -3.1, 1.25), (-14.6, -5.7, 1.5), (-12.4, -3.0, 1.3), 32, 3.5)
# L1 grounded / paper
shot(tFLIGHTS, (-9.5, -13.5, 0.9), (0.0, 0.0, 5.6), (-8.4, -12.6, 1.0), None, 24, 4.0)
shot(tHOSP2, (HXs - 0.4, -1.0, 1.28), (HXs - 0.45, -0.62, 0.84), (HXs - 0.42, -0.9, 1.15), None, 40, 2.8)
# L2 what if
shot(tWHAT, (0.4, -12.5, 6.2), WC, (0.0, -9.2, 6.8), V3(0.0, 0.0, 7.0), 30, 5.0, ez='io')
# L3 the mine
shot(tCOAL, (MX0 + 0.75, -4.6, 1.25), (MX0 - 0.1, 14.0, 1.35), (MX0 + 0.7, -3.3, 1.3), None, 26, 4.0)
CGC = CGM + V3(0, 0, 0.15)
shot(tTOOK, CGC + V3(0.42, -0.72, 0.08), CGC, CGC + V3(0.36, -0.6, 0.1), None, 50, 2.2)
shot(tPOISON, (MX0 + 1.0, -0.9, 0.8), (MX0 - 0.3, 16.0, 0.95), (MX0 + 0.95, -0.4, 0.82), None, 26, 5.0)
BM = CGM + V3(0, 0, 0.18)
shot(tSTOPS - 0.12, BM + V3(0.06, -0.45, 0.05), BM, BM + V3(0.05, -0.38, 0.04), None, 55, 4.5)
shot(tEVERYONE, (MX0 - 0.5, 7.6, 1.5), (MX0, -9.0, 1.1), (MX0 - 0.45, 6.6, 1.45), None, 28, 6.0)
# L4 the cage over one screen, then 1%
shot(tSOFT, (CANX + 1.3, -3.4, CANZ + 0.2), CANP + V3(0, 0, 0.45), (CANX + 1.1, -3.05, CANZ + 0.25), None, 30, 3.5)
def _s15(t, u, e, s):
    k = EZ['io'](clamp((t - (tONEP - 0.55)) / 1.9))
    return V3(CANX + 0.35, -2.4, CANZ + 0.3).lerp(V3(1.2, -13.4, WCZ - 0.3), k), (CANP + V3(0, 0, 0.2)).lerp(WC, k)
shot(tNEW, (0, 0, 0), (0, 0, 1), None, None, 30, 3.5, fnP=_s15)
# L5 watch / spike / roll back
shot(tWATCH, (CANX + 0.45, -2.4, PLZ + 0.4), (CANX, CY_, PLZ + 0.22), (CANX + 0.38, -2.15, PLZ + 0.36), None, 40, 3.2)
shot(tSPK, (CANX - 1.0, -2.9, CANZ + 0.5), (CANX, 0.0, CANZ + 0.4), (CANX - 0.85, -2.6, CANZ + 0.5), None, 32, 3.5)
shot(tOTHER, (-1.8, -15.5, 4.2), WC, (-0.8, -15.0, 4.5), None, 26, 6.0)
# L6 crane out as the cage grows
def _s19(t, u, e, s):
    k = EZ['io'](clamp((t - (t5 - 0.3)) / (tALLX + 0.6 - (t5 - 0.3))))
    return V3(CANX + 0.6, -3.0, CANZ + 0.6).lerp(V3(0.3, -15.4, WCZ), k), (CANP + V3(0, 0, 0.45)).lerp(WC + V3(0, 0, 0.3), k)
shot(tLOOKS, (0, 0, 0), (0, 0, 1), None, None, 30, 4.0, fnP=_s19)
# L7 the plan
shot(tAFTER, (6.5, -10.5, 1.8), (0.0, 0.0, 7.0), (5.0, -9.6, 2.2), None, 24, 6.0)
shot(tSTAGES, (0.0, -12.9, WCZ + 0.2), WC + V3(0, 0, 0.2), (0.0, -11.8, WCZ + 0.2), None, 30, 6.0)
# L8 the replay, then the world carries on
shot(tSAME, (CANX + 1.1, -3.0, CANZ + 0.3), (CANX, 0.0, CANZ + 0.45), (CANX + 0.9, -2.7, CANZ + 0.32), None, 32, 3.5)
shot(tNOT, (-9.0, -26.0, 2.6), (3.0, 14.0, 6.0), (-8.6, -25.0, 2.7), None, 24, 8.0)
# L9 the names
shot(tTHATS, (0.0, -12.6, WCZ + 0.2), WC + V3(0, 0, 0.2), (0.0, -11.4, WCZ + 0.2), None, 30, 6.0)
# L10 orbit
G23 = WC + V3(0, 0, -0.3)
shot(tCTA, orbit(G23, -28, 17.0, -2.4), G23, None, None, 26, 6.0, fnP=lambda t, u, e, s: (orbit(G23, -28 + 16 * EZ['io'](u), 17.0, -2.4 + 0.6 * u), G23), ez='io')
