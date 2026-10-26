# 3D series: next video ideas

Fully procedural Blender reels: about 35 s, one mechanism, no characters, a number for the hook in the first second.
Made so far: ep 1 Taipei 101 tuned mass damper (live), ep 2 Kingda Ka magnetic brakes (in Up next).
Pace: Sam found ep 2 slow and had it sped up 1.25x, so write tighter and voice faster from the start.

## Top picks

1. **Hoover Dam's hidden fridge**: poured in one go, the concrete would have taken about 125 years to cool and would
   have cracked. Fix: pour it in blocks and run cold water through hundreds of miles of pipe inside them. Reuses the
   thermal view from ep 2 (a glowing block cools as the pipes light up). Check the exact figures first.
2. **The bullet train that copied a bird**: early Shinkansen made a sonic "boom" bursting out of tunnels; an engineer
   who was a birdwatcher reshaped the nose like a kingfisher's beak, so it got quieter, faster and used less power.
   Reuses train and track assets, plus a pressure-wave x-ray in the tunnel.
3. **Jet engine blades that run hotter than their melting point**: the gas hitting them is hotter than the metal can
   survive. They live because they're grown as a single crystal, coated in ceramic, and breathe cool air out of tiny
   holes. X-ray blade with airflow ribbons. (ep 3, in progress)

## More

4. **Falkirk Wheel**: rotating boat lift; both sides always weigh the same (Archimedes), so a half turn uses about as
   much energy as boiling a few kettles. Needs water, so it's harder procedurally.
5. **Rotterdam's storm barrier (Maeslantkering)**: two huge floating gate arms swing out, fill with water and sink to
   close the river.
6. **Mars sky crane**: Curiosity lowered on cables from a hovering rocket stage, which then flew off to crash.
7. **Falcon 9 landing**: grid fins steer it; the landing burn is timed to reach zero speed exactly at the ground.
8. **Panama Canal locks**: ships lifted 26 m using only gravity and no pumps; the new locks reuse most of their water
   in side basins.

## New-chat prompt for ep 3 (jet engine blades, premium version)

Paste this into a new Claude Code chat opened in /Users/samarpit/insta-automation:

```
Make episode 3 of the @how.its.engineered 3D reel series: "Jet engine blades that run hotter than their melting point"
(idea #3 in how-its-engineered/experiment.md). This one must be the most premium video on the channel.

Feedback on ep 2 (Kingda Ka): "still not very premium" and "slow" (I had it sped up 1.25x). Gemini's review of ep 2
blamed low-poly cone trees and grey boxes, a boxy faceted train, and wide outdoor shots that looked like a blockout.
So for ep 3:
- Look: a high-end product film (Rolls-Royce / GE Aerospace / Apple commercial). One hero object in a dark studio,
  no outdoor world, no low-poly scenery. Smooth subdivided and bevelled geometry everywhere (no visible facets),
  real materials (polished and brushed nickel superalloy, matte ceramic coating, anodised titanium disc), soft area
  lights plus coloured rim lights, a gradient backdrop or floor reflection, shallow depth of field, macro lenses,
  slow precise camera moves (orbit, push-in, rack focus) cut fast with a few hard match cuts. Heat is a thermal
  colour ramp and glowing flow ribbons or heat haze; cooling air is a second accent colour. No fluid or fire sims.
- Story beats to show: the whole engine and the spinning turbine disc, one blade lifting out into the studio, gas
  hotter than the metal's melting point (thermal view), many grains vs one single crystal, x-ray of the internal
  serpentine cooling channels, cool air leaving hundreds of tiny film-cooling holes and blanketing the surface,
  the ceramic thermal barrier coating peeling away as a layer, and a scale fact (power per blade or centrifugal
  load) only if a manufacturer or university source backs it.
- Pace: about 30 s, 85-95 words, dense and punchy, voice at Gemini TTS atempo about 1.3 (ep 2 was 1.12 and felt
  slow). Cuts every 1-2 s. Spoken cold-open hook only: no on-screen text hook in the opening. Last line: "Follow for
  how the world is really engineered."
- Voice: one narrator, Gemini TTS (Cloud TTS) voice Puck, gemini-2.5-pro-tts, premium documentary style prompt.

Reuse ep 2's pipeline (read it first, don't rebuild from scratch):
- how-its-engineered/videos/3d-02-kingda-ka-brakes/: src/ (kk_head.py, helpers2.py, kk_body.py, kk_shots.py, kkrun.sh
  = assemble, build and render test stills on the PC, contact sheet), tts.py, words.py (run with
  ~/Developer/reel-builder/.whisper/bin/python), overlay.py (ASS captions + 3D-tracked callouts + HUD from
  labels.json), sound.py (numpy sound design + music + ducking), encode.sh (bloom, vignette, grain, ASS, audio).
- Ep 1 is how-its-engineered/videos/3d-01-tuned-mass-damper/ (tmd.py, captions.py, cover recipe with Futura).
- Ideas and fact checks: python3 claude-talk-v2/scripts/ask_argon.py prompt.md reply.md
  Video review: python3 claude-talk-v2/scripts/argon_video_check.py video.mp4 prompt.md reply.md 10
- Render on the PC: Blender 5.2.2 at ~/apps/blender-5.2.2-linux-x64/blender over
  ssh -o BatchMode=yes -o HostKeyAlias=192.168.0.102 sam@192.168.0.103 '...' </dev/null
  Work only in /mnt/ssd/render/3d-03-jet-blades/ (never the PC's home or root disk). Run long jobs detached:
  (nohup ... > log 2>&1 < /dev/null &). Never stop a Blender job you didn't start (check pgrep -a blender first),
  never pkill -f with a pattern that matches the ssh command, and don't wait with `while pgrep -f "<pattern>"` inside
  the same ssh command: it matches itself and loops forever (ep 2 lost 10 minutes to this). Eevee at 1080x1920,
  ~48 samples, ran ~1 frame/s; consider more samples, AO, bloom-friendly emission and better motion blur for premium.

Workflow:
1. Argon: fact list with sources, 8-10 line script, shot plan per line, look note. Show me the script before voicing.
2. Voice + word timings, build the scene, iterate on test-still contact sheets until every shot reads as premium
   (judge each still: would it pass in a Rolls-Royce ad?).
3. Overlay (captions, tracked callouts, thermal/x-ray tags), sound (turbine whine, airflow, impacts, a premium score
   ducked under the voice).
4. Show me a 10-second preview before the full render, then render on the PC, encode, and review: Codex final review
   loop (frames at least 1 per second + timed voiceover) until PASS, Gemini/Argon only if Codex is unavailable.
5. Cover: topic only on the key frame, no subtitle or kicker line, no number. Caption: 1-2 keyword-rich lines,
   max 1 emoji, exactly 5 hashtags (a set not used on other reels).
6. Put it in Up next: copy the MP4, cover.png and caption.txt into how-its-engineered/media/3d-03-jet-blades/ and
   add it to MADE, KNOWN and NEXT in how-its-engineered/tools/remake/bin/library.py, then rebuild the library page.
   Don't post anything without my OK.

Rules: never print API keys or tokens, never read ~/.ssh, never add Co-Authored-By or AI attribution to commits,
don't end turns with option buttons (ask in plain text). Read my memory notes in
~/.claude-2/projects/-Users-samarpit-insta-automation/memory/ first.
```
