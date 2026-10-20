# @app.engineering: how their reels are made

Studied on 2026-10-20 in the browser (read only). Sources: the profile grid (40 posts), views on 24 reels, frame-by-frame looks at three reels, and the downloaded reference Video-7013.mp4 (scene detection, silence detection, spectrogram, Whisper transcript).

Reels looked at closely:
- Video-7013: TikTok algorithm, ~69 s.
- Deoo7XvBjyH: "How would the US president talk to a submarine?", 87.5 s, 383K views.
- DenIXzvkmBC: "How SmartGate knows it is really you?", 75.9 s, 273K views.

## 1. Account at a glance

- 24.1K followers, verified, 40 posts. Bio: "How everyday internet & network works, Explained."
- Posts almost daily. Every post is a reel.
- Views range from 5.5K to 383K. The top 4 are 383K, 273K, 201K and 141K; the median is about 25K.
- Likes run about 3–4% of views (SmartGate: 10.2K likes, 238 comments on 273K views).
- Topics are everyday things people touch, never abstract backend concepts:
  - TikTok algorithm, VPN, Fortnite servers, in-flight Wi-Fi, Uber Eats ETA, Google Maps.
  - Submarine radio, airport SmartGate, Singapore data centres.
- Post titles are a "How does X…?" question, for example "How SmartGate knows it is really you?"

## 2. Visual style: one look, every video

| Element | What they do |
|---|---|
| Canvas | 1080×1920. Dark navy background (about #0B1220). A faint isometric floor grid that fades out toward the edges, plus a soft vignette. |
| Camera | Isometric with an orthographic camera (no perspective) in every shot. Slow drift or push-in, never a hard camera cut. |
| Objects | Extruded blocks with blue-grey faces, a slight gradient per face and thin light edge lines. No textures and no characters. |
| Glass | Translucent volumes, such as the seawater tank with a depth ruler, and glassy passport layers. |
| Accent colours | Cyan is the main accent for signals, highlights and keywords. Amber/orange marks the "twist" or a new idea. Green ticks. Very little red. |
| Glow | Glow only on signals: waves, antenna beams, the active outline. Everything else stays matte. |
| Exploded views | A passport splits into floating layers (photo page, chip, signature); stacked layers spread apart to show the inside. |
| Layout | The main scene sits in the middle 60%. The HUD is at the top and captions are in the lower third, so the scene is never covered. |

### Rendering tech (best guess)

- The scenes have real depth sorting, many repeated 3D props (dozens of queue stanchions and e-gates in SmartGate), contact shadows and translucent volumes. That points to a **real 3D renderer**, not hand-drawn SVG:
  - Likely Three.js / React Three Fiber with an orthographic camera.
  - Probably rendered through Remotion (`@remotion/three`) or a headless browser.
- The HUD, captions, source cards and data bars are crisp flat UI. They are almost certainly HTML or SVG overlays on top of the 3D layer.
- A commenter (not the creator) said it is "made entirely with AI", naming Claude. That fits **code-generated video**: an LLM writes the Remotion/Three code for each scene. The creator hasn't confirmed it.
- Some covers (the plane wing for in-flight Wi-Fi) look more like a polished 3D render (Blender-like). They may mix tools for hero shots.

## 3. Recurring animation building blocks

1. **Signal waves:** glowing cyan sine waves travel along a path or through a volume. In the submarine reel, radio waves shrink as they enter the water.
2. **Antenna / emitter bursts:** short lines radiate from a mast, with a glow pulse.
3. **Dashed trajectories:** a dotted curve traces a moving object's path (the aircraft circling and trailing its antenna wire).
4. **Draw-on outlines:** an object gets a cyan stroke that draws around it when it's mentioned.
5. **Exploded layers:** a flat object splits into 2–4 floating planes, each labelled.
6. **Data bars:** small rows of cyan bars labelled `DATA` and `SIGNED` to stand for bytes or hashes. They fill or compare in step with the voice.
7. **Kinetic titles:** big words animate in for key terms ("watch time"). A word gets struck through when the idea is debunked ("your mind").
8. **Colour flip:** an element switches from cyan to orange to mark a new state ("new interest").
9. **Transitions:** soft cross-fades and push-ins with no hard cuts. Scene detection on Video-7013 found almost no cut points, so the video is one continuous-feeling world.

## 4. The top HUD: their signature device

Every reel has a thin pill-bordered bar near the top (about 10% down, clear of Instagram's top UI). It tracks story progress in the topic's own terms:

- SmartGate: `KEY ✓  CHIP ✓  SEAL ○  FACE ○`. Each step ticks as the voice reaches it, so it works as a chapter checklist.
- Submarine: `ORDER [▢▢▢▢▢▢▢▢▢] → REPLY`. The blocks fill cyan one by one as the message travels, so it works as a progress meter. At 45 s it was empty; at 58 s it was full.
- TikTok: `WATCH TIME` segments. Google Maps: `ARRIVE IN 25`. Uber Eats: `ETA 32 min` with kitchen, driver and rider chips. Others: `PING SEEN NOW`, `SITE STATUS`, `NEW BUILDS OPEN`.

It gives the viewer a reason to keep watching ("two steps left") and makes every reel look like part of a series.

## 5. Evidence cards (real-world proof)

- **Real photos as inset cards:** a rounded card with a monospace credit line under it, for example `E-6B Mercury · U.S. Navy photo`.
- **Recreated web pages:** a card with fake browser chrome and the real URL in mono (`abf.gov.au/smartgate`), the official logo or screenshot, and a mono source line like `Australian Border Force site · 17 Oct 2025`. Video-7013 does the same with `newsroom.tiktok.com`.
- The cards slide in over the 3D scene for 2–4 s, then leave. They make the video feel researched and give commenters less to dispute.

## 6. Captions

- Bold geometric sans (Inter or SF-like, heavy weight), white, 2–4 words at a time, in the lower third (about 72–75% down).
- One or two **keywords per chunk in cyan** ("trailing", "SmartGate", "never", "radio?").
- They use two treatments:
  - A dark rounded pill (SmartGate, Video-7013). Video-7013 also does karaoke: current word cyan, spoken words white, upcoming words grey.
  - A cyan vertical bar on the left with no box (submarine).
- Captions are word-timed, almost certainly from a forced-alignment or Whisper pass on the voice.

## 7. Audio

- **Voice:** clean, even, male, about 171 words per minute, with no breaths or mouth noise. Almost certainly TTS (ElevenLabs-class). There are no gaps longer than 0.25 s, so pauses are trimmed tight.
- **Music:** a very quiet bed under the voice. A viewer commented "Make the music louder next time".
- **SFX:** soft UI dings and ticks on HUD ticks and highlights. Sparse, not on every motion.

## 8. Script structure (same template every time)

1. **Hook question** (0–3 s), tied to a person or situation: "If the US president…", "How does SmartGate know it's really you?"
2. **"Imagine…" setup:** put the viewer in the scene (in the queue, in the sub).
3. **Mechanism in 3–4 named steps.** These match the HUD stages (KEY → CHIP → SEAL → FACE).
4. **Real-world proof** at each step (photo or official page card).
5. **Twist or reframe** near the end: "it's not reading your mind, it's reading your pauses."
6. **Closing question plus a share CTA:** "Send this to the friend whose For You page is completely unhinged."

- Length is 69–88 s, longer than our 52–62 s, and they still get 200K–380K views. The HUD checklist is what carries viewers through the length.
- Comments are full of "actually…" corrections ("Bro this is wrong…") and "we have this in Dubai/Korea/HK". The slightly simplified claims and the country-specific framing drive comments, probably on purpose.

## 9. Us (@how.its.engineered) vs them

| | Them | Us now (reel 21, Remotion) |
|---|---|---|
| Renderer | 3D (Three-style) plus HTML overlays | SVG isometric plus HTML overlays |
| Depth | Real occlusion, translucent volumes, many props | Hand-projected boxes, few props |
| Top HUD | Topic checklist or progress meter, always present | TRANSACTION chip HUD (similar idea) ✅ |
| Captions | 2–4 words, cyan keywords, pill or bar | 4-word pill, colour-coded runs ✅ |
| Evidence | Real photos plus recreated source pages with credits | Product cards (Spanner, psql), no real photos or URLs |
| Length | 69–88 s | 52–62 s |
| Topics | Consumer things you touch | Backend and system-design concepts |
| Hook | Person or situation question | Problem scenario ✅ |
| Music | Quiet bed | None |
| SFX | Sparse UI dings | Synthesized UI set ✅ |

## 10. What to adopt, in priority order

1. **A checklist-style HUD:** name 3–4 steps up front and tick them (for example `PREPARE ○ VOTE ○ COMMIT ○`). It's cheap to do; our Hud component already has chips.
2. **Evidence cards:** a real screenshot or photo with a mono URL and source line (docs page, engineering blog, RFC) on 1–2 beats per reel. Use public pages and credit the source on screen.
3. **Topic framing:** keep the system-design core but open on the consumer moment ("Why your Uber price jumps", "How Netflix never buffers"). Title posts as "How does X…?"
4. **A quiet music bed** at about −28 LUFS under the voice. Sidechain it so it ducks under speech.
5. **Try `@remotion/three` for one reel:** an orthographic camera with MeshStandard plus edge lines, keeping our SVG/HTML overlays. That gets real occlusion and glass volumes. Keep the SVG pipeline as the fallback.
6. **Allow 65–80 s** when the step checklist justifies it. Don't pad.
7. **Keep the twist line** near the end ("it's not X, it's Y"). It's a strong rewatch and share trigger.

## 11. Unknowns

- Their exact tools aren't confirmed. The "Claude made it" claim comes from a commenter, not the creator.
- The TTS vendor and voice are unknown.
- Instagram's player often went black when seeking, so some timestamps couldn't be captured (submarine 12 s and 33 s; SmartGate 2 s and 30 s). The observations above come from the frames that did render plus Video-7013.
