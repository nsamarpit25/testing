# Reel 18 Pub/Sub — handoff (continue v5)

## Goal
Build v5 of reel 18 "Pub/Sub" as a polished, professional Blender (EEVEE, scripted bpy) video, render it at 480p on AWS EC2, burn in captions plus the profile-card end, and send it to the user. The user wants "extraordinary" Blender quality matching their reference reel (`/Users/samarpit/Downloads/69d9432666b94cb899ddd22b8630de49.MP4`, @charles.zhengg LLM explainer). That means taking the reference's quality as an example, not copying it object for object.

## History and user feedback
| Version | Look | User's verdict |
|---|---|---|
| v1 | Plain | Hook bad, video plain |
| v2 | Dark navy stage, white pods, neon chips | "don't like it at all" |
| v3 | Isometric ortho diorama, cartoon icons | "childish", "not polished", the "2 million" screen fonts were "very bad" |
| v4 | Glossy graphite modules, iOS notification cards | "reflections too much", "not professional" |

The user then said "don't match it from the reference, just take it as an example". An agent studied the reference and wrote the v5 art direction, which is now the spec.

**Spec: `videos/18-pub-sub/design_v5.md`.** Read it fully. The design is a warm 1930s Art Deco "Dispatch Hall":
- **Materials:** satin cobalt machines (#2547B5) with cream enamel nameplates, thin brass trims and brick red (red means "problem" only). No glass, no gloss.
- **Mechanisms:**
  - mechanical drum counters (DIN Alternate on cream facets) and octagonal status-word drums (DIN Condensed);
  - printed "new post" message cards on roller conveyors;
  - a topic drum that rises from a floor hatch;
  - a PUB/SUB enamel sign with chasing bulbs, plus a FOLLOWERS scoreboard reading 2,000,000;
  - about 7,300 bulb pins that light up in a wave on "Everyone notified".
- **Queue vignette:** in the left aisle.
- **Radio metaphor:** a dusk rooftop at x = 200 with a tower that sends one ring and 3 tuned radios.
- **Camera:** perspective lenses 24–85 mm with depth of field, and whip pans between sections.
- **Look:** warm haze volume, pendant lamps, amber windows, AgX Medium High Contrast.

## Current state of the files
- `videos/18-pub-sub/scene.py` is still **v4**. It is backed up identically at `v4/scene.py`; v2 and v3 backups are in `v2/` and `v3/`. **The v5 scene has not been written yet.** The draft I wrote was lost (the Write call failed), so write v5 into `scene.py` from scratch.
- Reuse these helpers and patterns from v4's header:
  - arg parsing: `--res --fps --samples --stills --range --skip --cutfix`;
  - `W(tok, after)` word timing, `L(li, pi)` phrase start, `F(t) = 1 + round(t*FPS)`, `END = min(voice, last end + 1.8)` = 63.6 s, so F(END) = 1527;
  - `hx()`, `mat()`, `sock()`;
  - the render block: EEVEE, AgX, compositor with no bloom, still/cutfix/animation modes.
- **Fonts are already copied into `videos/18-pub-sub/fonts/`:**
  - InstrumentSerif-Regular.woff2 and InstrumentSerif-Italic.woff2
  - DINCondensed-Bold.ttf and DINAlternate-Bold.ttf
  - JetBrainsMono-Medium.ttf and JetBrainsMono-Bold.ttf
  - Inter-{Medium,SemiBold,Bold,ExtraBold}.ttf

  Load them via `f'{D}/fonts/...'` so the same paths work on AWS.
- `script.json`, `voice/voice.wav`, `voice/timings.json` and `voice/words.json` are final. Keep the v2 script and voice; the user said the explanation is good.
- `captions.py` (house style, CY=822) and `hud.py` (chapter titles plus the ending profile card with cursor clicking Follow, as concat lists) exist and work.
  - Captions stay in house style.
  - The brief optionally suggests recolouring the caption and HUD accents to brass and brick. Only do that if it looks better; it is not required.

## Word timings (s)
| Section | Words |
|---|---|
| Hook | post 0.44, two 1.34, notification 2.86, (and 3.36) button 4.52, keeps 5.40, spinning 5.68 |
| Why | Here's 6.66, every 8.48, itself 9.20, Notify 10.10, emails 11.52, feeds 12.58, one 12.94 |
| Pattern interrupt | Spot 14.44 |
| Problem | If 15.74, slow 16.38, waits 17.38, and 17.74, new 18.56, rewriting 19.60, service 20.64, Again 21.32 |
| Queue | a 22.04, queue 22.50, It 23.56 (hands ≈ 23.50), one 25.14 |
| Fix | The 26.36, fix 26.46, PubSub 27.30, (The 27.70) publishes 28.68, topic 30.32, done 31.06, button 31.70, stops 31.98 |
| Fan-out | Every 33.14, subscribes 33.80, Each 35.54, copy 36.52, same 37.54 |
| Radio | Like 38.24, radio 38.54, broadcasts 39.62, once 40.04, tuned 41.80, hears 42.36 |
| New feature | New 43.14, subscribe 44.22, never 45.78 |
| Payoff | So 47.04, million 47.94, One 49.34, publish 49.54, Everyone 50.36 |
| Products | That's 51.76, Google 52.24, Amazon 53.68 |
| CTA | Haven't 55.48, If 58.20, follow 59.44; voice ends 61.8 |

Phrase keys: (0,0) (0,1) (0,2) (1,0) (1,1) (2,0) (3,0) (3,1) (4,0) (5,0) (5,1) (6,0) (7,0) (8,0) (9,0) (10,0) (11,0) (11,1). **There is no (6,1)**; use `W('each')` (35.54) for that point.

## Build decisions already worked out (deviations from or fixes to the brief)
1. **Keyframe registry.**
   - Key everything through a registry `K(owner, path, t, val, interp, fr=None)`. Write it once at the end with `keyframe_insert`.
   - Then set each keyframe's interpolation by finding its fcurves. Blender 5 uses slotted actions, so use `bpy_extras.anim_utils.action_get_channelbag_for_slot(action, animation_data.action_slot)`. Match `data_path` (`owner.path_from_id(path)` for non-ID owners such as sockets, `camd.dof`, `sc.render`, `sc.view_settings`).
   - This fixes the old "CONSTANT not applied" problem.
2. **Shared bulb shaders.** Drive a whole group of bulbs from one material:
   - Spinner: 16 bulbs. Object coords relative to an empty → atan2 → phase Value node → fract → comet tail.
   - PUB/SUB sign: x-position sweep Value node.
   - Field: distance from an empty at (0, 6.5, 0), plus snapped white-noise jitter, compared against a keyed `wave_r` Value node, times a level node.
3. **Drums.**
   - An N-gon of facet boxes. Facet i normal is (0, −cos iθ, sin iθ), box rotation x = −iθ, text rotation x = π/2 − iθ. Rolling forward = rotation_euler.x += steps·θ.
   - Put each drum behind a **housing front plate** (4 boxes around the opening plus a brass bezel) that stands proud of the face by `protrude` = 0.04. Drum centre y = face_y − protrude + apothem + 0.008. Plate half-height = sqrt(Rc² − dd²) + 0.012.
   - Odometer roll: digits right of the leading changed digit spin whole turns (4,3,3,2,2,1 revs). The leading digit steps with smoothstep carries. Bake one key per frame.
4. **Layout changes to the brief.**
   - There is no room for a side chute between the post module and NOTIFY, so the monolith bays shift right: NOTIFY x = 1.40, EMAIL 2.35, FEED 3.30.
   - Monolith cap: centred at x 2.125, length 3.35. Ledge: x 0.55 → 3.90 at y −0.625, top z 0.30. Crate hovers at x 4.30.
   - Side chute: rollers from (0, 0.18, 1.268) → (0.70, 0.05, 1.10) → (0.70, −0.625, 0.31).
5. **Gate.** Use a brass **stamp arm** cantilevered from the bay face (mount at z 0.575, arm to y −0.665, head at (0, −0.625, 0.548) dropping to about 0.527), not a posted arch.
   - With no posts, cards can arrive from any direction and be absorbed by sliding into the bay face (local +y).
   - Card: root at the carrier bottom, 0.30 × 0.19, top at z 0.51 when sitting on a z 0.30 belt.
6. **Pub/sub arc.** Bays sit at NOTIFY (−1.89, 3.12), EMAIL (−0.75, 4.16), FEED (0.75, 4.16), BADGES (1.89, 3.12).
   - Yaw = 0.75 × atan2(d.x, −d.y), where d is the direction from the bay to the topic centre (0, 2.2).
   - Gate point = pos + (0.625 sin yaw, −0.625 cos yaw, 0.30). Port direction u = (gate − T).normalized; port at T + 0.705u, z 0.28–0.56.
   - Lanes start at T + 0.70u (z 0.30) and are scaled in X from 0 to 1 when subscribing.
   - Copies keep yaw = the bay's yaw.
   - Bays teleport onto the arc at the 27.30 cut (a one-frame snap).
7. **Publish timing.**
   - First publish: card pops at 28.68 and drops into the topic slot at about 30.47 (chute duration ≈ 1.07 s).
   - Payoff: card at 49.54, quick (scale 0.55, chute 0.16 s), drops by about 50.10. Copies run 50.12 → gates 50.30, then the wave sweeps 50.40 → 51.30.
   - CTA loops at 55.7, 58.5 and 61.3 (chute 0.35 s, copies arrive 0.5 s after the drop).
8. **Topic dial ring text.** Place letters individually at θᵢ = −π/2 − 0.35 + 2πi/n, rotation z = θ + π/2 (counter-clockwise, up pointing inward, reads correctly from the camera at −Y).
9. **Pendant lamps.** Shades must cast shadows (pools of light). Only the bulb sphere and glow planes get `visible_shadow = False`. The haze is a volume box (density 0.010), never a world volume.
10. **Hall lighting.**
    - Closed hall box; lights use cutoff_distance 45.
    - "Spot the problem": all hall lights and glow emissions drop to 6 % at 14.44 and restore at 15.74, with one 16° spot.
    - The radio set's SUN is keyed on only for 38.0–43.1 s.
11. **Camera.** TRACK_TO an empty, DOF focus_object = that empty, lens and f-stop keyed CONSTANT per shot.
    - Shot list: brief §7, with the bay x shift applied.
    - Whips last 4 frames out and 4 frames in: the target is offset by dist·tan 18°, and motion_blur_shutter is keyed to 1.0 on whip frames.
    - Collect all cut times for `--cutfix`.
12. **Frame-safe zones.** Keep content between 18 % and 77 % of the frame height. Captions sit at about 80–88 %; the HUD title is top-left, about 16 %.

## AWS render box
- Connect: `ssh -F ~/.ssh/ctv2_aws.conf ctv2-gpu` (g6e.xlarge L40S, us-east-1). AWS CLI commands need `--profile manmeet`.
- Blender: `~/blender-5.2.2-linux-x64/blender`.
- The box auto-shuts down at about **00:07 UTC Oct 21** (`shutdown -h`). Check with `shutdown --show`; cancel or extend only if the user agrees.
- The user said the box is now empty, with no other jobs.
- Project copy on the box is `~/pubsub/`: scene.py, script.json, voice, fonts, pscap480, pshud480 (paths inside rewritten to /home/ubuntu/pubsub/...). Rsync the new `scene.py` and the `fonts/` folder there.
- Speed: about 120 frames/min with 3 Blender processes at 480p (v4). Volumetrics will make v5 slower.
- Stills: `blender -b -P scene.py -- stills_v5 --res 480 --stills 0.4,2.0,8.6,11.5,14.6,16.4,19.9,25.2,27.4,28.7,37.6,41.9,44.6,50.9,52.3`
- Full render: three processes with `--range` splits, plus `--skip`; then `--cutfix`.
- Process control: identify my jobs by the cmdline containing `pubsub/scene.py`. Never use `pkill -f` broadly.
- Scratchpad helper scripts are in the old session's scratchpad (`aws_finish.sh`, `launch_retry.sh`). They may be unavailable in the new chat; recreate them if needed. Encode = render frames + overlay chain (vignette, light noise, eq) + HUD + card + captions. The brief suggests `vignette=PI/6, noise=alls=4:allf=t`.
- A second-g6e launch retry loop ran in terminal tab c1 (no capacity). Ignore it unless the user asks.

## Next steps
1. Write v5 `scene.py` per `design_v5.md` plus the decisions above.
2. Rsync it to AWS and render the 15 test stills. Fix errors.
3. **Show the user only the new v5 stills**, never old ones. Iterate on what they say.
4. Full 480p render on AWS, cutfix, then encode with captions (`captions.py <dir> --res 480`) and `hud.py` (titles plus the profile card).
5. Fetch the result to `media/18-pub-sub/18-pub-sub-v5-480p.mp4` and send it.
6. Later: 1080p, cover (kicker + title + handle, no reel number), caption, and TOPICS.md.

## Standing rules
- Never commit or push without asking. No Co-Authored-By or AI attribution lines.
- No option buttons at the end of a turn; ask in plain text.
- Never print keys. Don't explore SSH credentials.
- Don't stop other people's jobs.
- Objects only: no characters, no story. Low glow, no bloom.
- Ending line: "Haven't seen message queues? That reel's on my profile. If you're a vibe coder, follow for the system design your AI skipped."
- Keep all hooks and open loops; about 60 s is fine. Blender stays Blender (no Three.js).
