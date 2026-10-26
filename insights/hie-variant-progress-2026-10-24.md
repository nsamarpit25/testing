# HIE trial variant continuation — 24 October 2026

Read handoff and Claude 3 hie-trial-variants memory. Puck only; remake existing topics; render PC 192.168.0.113; trials only; one finished/scheduled reel before starting the next.

- GPS t2 verified published: https://www.instagram.com/reel/De4jDiHjxmq/ and registered.
- Touchscreen t2: old job was killed before its slot. Instagram absence and lack of running worker verified at 22:10. Replacement scheduled 22:12 IST (PID 54830).
- Shazam t2: old job was killed. Instagram absence and lack of running worker verified at 22:10. Replacement scheduled 22:35 IST (PID 54836). Existing Argon report PASS with no findings.
- Rate limiting t2: new script/Puck take, altered camera order/angles, PC render, synth bed, new cover/caption, 46.7 s vs 41.0 s. Argon detected a tail audio artifact; corrected version PASS and cutcheck clean. Scheduled 22:52 IST (PID 52431). MD5 ee5bb7a58b296aa54fa04e1d65b5880a.

Added actual-publication spacing and duplicate-caption checks for trial-variant filenames in tools/ig.py. Existing posting jobs were not stopped. Verified spacing logic using mocked API responses. Updated log_variants.py to reconcile existing scheduled rows rather than duplicate them.

Live metrics saved in hie-variant-audit-2026-10-24.json. At approximately 21:50 IST, no variant beat its baseline in total views. Maps t2: 163 vs 1,239 views; 13.631 vs 10.573 seconds average watch; 9.2 vs 48.1 percent skip. Trial reach only 34, so retention is preliminary. Sharding and Tap to pay trials show zero views/reach and are not assessable yet.

- Cron jobs t2: new duplicate-receipt story, new Puck take, 42.8 s vs 31.4 s. Audio/facts PASS; widened camera framing and lowered subtitles after Argon identified overlap. Corrected render PASS and cutcheck clean. Scheduled 23:15 IST, PID 53650; md5 dace681272ea77d21590bd20dba5e65b.

- N+1 t2: new fast-queries/slow-page paradox script, Puck take, reworked perspective camera order/angles, no waiter detour, 40.4 s vs 47.7 s source. Wide previews checked; full PC render and review running. Not scheduled yet.
- All-trial comparison saved in hie-trial-comparison-2026-10-24.md at 22:01 IST. Four comparable current trials; no total-view winner. Maps t2 236 vs 1239 views, 18.8 vs 10.6 s avg watch, 13.8 vs 48.1 percent skip.

- N+1 initial and SQL-ordering reviews passed; latest review noted that a six-line SQL card can hide the final filter. Removed a comment to fit the complete SQL in five rows; final render/review running. Expected slot 23:38, not scheduled until finished.
