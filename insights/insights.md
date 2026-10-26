# @talkingagents: every live reel, best first

Fetched 2026-10-24 ~21:15 IST, 19 live reels.

**Score (0–100)** ranks each reel against the others: skip rate 30% (lower is better), watch % 25%, like rate 15%, share rate 15%, save rate 5%, views 10%. Rates are per account reached. Quality counts for most of the score because views are stuck between about 1.3k and 3k on every reel.

**Name swap: how easy it is to change "@talkingagents"**
- **No handle:** the posted reel never had it. Post it as is, or add a new name in one quick pass.
- **Easy:** a clean master (no text) and the caption file are on the Mac. Change the name and run the final encode again: about 1 minute, same quality.
- **Medium:** the handle is baked into the only copy and the AWS render frames are gone. Cover the old name with a soft patch and draw the new one in a single ffmpeg pass (a few minutes). The background there is mostly blurred desk or keyboard, so the patch hides well. The only clean alternative is a full Blender re-render on AWS, which takes hours.

| # | Ep | Story | Score | Views | Skip % | Watch % (avg / length) | Like % | Share % (n) | Save % | Name swap |
|---|----|-------|------:|------:|------:|------|------:|------|------:|-----------|
| 1 | 18 | Claude texted her ex a 14-page report | 79 | 2,082 | **26.3** | 54% (30/56 s) | 3.0 | 0.30 (4) | 0.15 | Easy |
| 2 | 5 (var C) | CSS fixes sent to the wrong localhost | 78 | 1,746 | **24.7** | 48% (39/83 s) | 3.3 | 0.23 (3) | 0.47 | Medium |
| 3 | 6 | Side project: the trumpet button | 77 | **3,031** | 34.6 | 47% (26/55 s) | 4.6 | 0.52 (12) | 0.47 | Easy |
| 4 | 3 | AI refactor broke working code | 68 | 2,901 | 34.1 | 42% (35/82 s) | 3.0 | **1.37 (28)** | 0.34 | No handle |
| 5 | 9 | Sharing a localhost link | 63 | 1,794 | 36.1 | 43% (22/50 s) | 4.5 | 0.38 (5) | 0.23 | Medium |
| 6 | 19 | Promoted for typing "done yet?" | 60 | 1,522 | 34.3 | **55%** (27/49 s) | 2.1 | 0.17 (2) | 0.25 | Easy |
| 7 | 8 | Password reset was a 2019 TODO | 60 | 2,209 | 29.5 | **55%** (24/43 s) | 1.9 | 0 | 0.20 | Medium |
| 8 | 17 | Battery 3%: storm, power cut ⏳ | 55 | 1,503 | 29.1 | 46% (27/58 s) | 3.1 | 0 | 0 | Easy |
| 9 | 20 | Claude blocked her 1 AM planner | 55 | 1,846 | 31.0 | 48% (22/46 s) | 2.4 | 0 | 0.08 | Easy |
| 10 | 1 (remake) | Imposter syndrome | 51 | 1,469 | 36.3 | 38% (24/63 s) | 4.1 | 0.34 (4) | 0.34 | Medium |
| 11 | 4 | useEffect loop: 45,000 DB reads | 48 | 3,040 | 40.8 | 38% (35/91 s) | 3.5 | 0.12 (3) | 0.58 | Medium (larger handle) |
| 12 | 12 | Two hours to center a box | 43 | 1,404 | 39.4 | 37% (20/55 s) | **6.1** | 0.17 (2) | 0.44 | Medium |
| 13 | 21 | 24 hours without AI, via Hawaii | 38 | 1,822 | 37.5 | 45% (22/49 s) | 2.0 | 0.08 (1) | 0.08 | Easy |
| 14 | 10 (remake) | Test email to 40,000 customers | 37 | 2,023 | 44.7 | 48% (25/53 s) | 2.8 | 0 | 0.20 | Medium |
| 15 | 2 | API key pushed to GitHub | 31 | 2,105 | 46.5 | 39% (30/77 s) | 2.8 | 0.07 (1) | 0.13 | No handle |
| 16 | 14 | fetch() confetti on a 500 | 30 | 1,382 | 36.6 | 35% (21/61 s) | 2.6 | 0.09 (1) | 0.09 | Medium |
| 17 | 7 | Save button solved by her old answer | 30 | 1,557 | 38.1 | 41% (17/43 s) | 2.4 | 0 | 0.33 | Medium |
| 18 | 15 | CORS: Postman vs Chrome | 24 | 1,313 | 47.0 | 25% (17/68 s) | 3.0 | 0.09 (1) | **0.71** | Medium |
| 19 | 16 | git bisect, nature documentary ⏳ | 10 | 362 | 42.2 | 22% (16/72 s) | 2.2 | 0 | 0.32 | Medium |

⏳ = posted less than a day ago, so its numbers will still move (ep17 has been up about 11 h, ep16 about 3 h).

## What stands out
- **Ep18, Ep5C, Ep6 and Ep3 are the strongest to bring to a new channel.** They have the lowest skip rates, good watch %, and real shares (ep3 got 28 and ep6 got 12).
- **The story episodes (ep17–20) hold viewers best:** skip rate is around 26–34% and they keep about half of every viewing. They get almost no shares, though.
- **The "dev tip" episodes (ep14, ep15, ep16, ep7) are the weakest:** high skip, low watch %. People save them (ep15 has the best save rate) but don't watch them through.
- **Long reels lose people.** Every reel over 70 s, apart from ep5C, watches below 40%.
- **The views ceiling is the same for every reel, good or bad.** Ep18 and ep2 both got about 2k even though ep18 has a much better skip and watch rate. That points to account-level reach being limited, not to the content.
