#!/bin/zsh
# publish_check.sh <name> <video> <audio dir|-> "<premise>"  -> $S/pub/<name>/reply.md
# Final publish gate: Codex gets the COMPLETE video file plus tools (ffmpeg, ffprobe, python3 + numpy/PIL, image viewing)
# in a writable work dir, and must measure cuts, audio, pace and lip sync itself. Approves the file's md5 only on
# "VERDICT: PASS" from Codex AND a clean cutcheck.py.
S=/private/tmp/claude-501/-Users-samarpit-insta-automation/090cc81c-2b8e-489f-b1db-92f85c47225e/scratchpad
REPO=/Users/samarpit/insta-automation/claude-talk-v2
REF=$REPO/output/new/ep4b_final2.mp4   # live reel the owner kept (Ep4 remake): good pace and lip sync, use as the bar
o=$S/pub/$1; mkdir -p $o; rm -f $o/reply.md
cp $2 $o/video.mp4
tl=-; [[ $3 != - ]] && tl=$3/timeline.json
sh=$(python3 $S/new/review.py $o/video.mp4 $tl $o 0)
if [[ $3 != - ]]; then
python3 - $3 > $o/words.txt <<'P'
import json, sys
d = sys.argv[1]; tl = json.load(open(f"{d}/timeline.json")); w = json.load(open(f"{d}/words.json"))
for l in tl["lines"]:
    ws = w.get(str(l["n"]), [])
    print(f'line {l["n"]:2d} {l["who"].upper():6s} {l["t0"]:6.2f}-{l["t1"]:6.2f}  ' + " ".join(f'{x[0]}@{l["t0"] + x[1]:.2f}-{l["t0"] + x[2]:.2f}' for x in ws))
P
fi
cat > $o/brief.md <<B
PUBLISH CHECK. This reel goes LIVE on Instagram (@talkingagents) in the next posting slot unless you stop it. You are the last gate; nobody watches it after you. Be strict: if you are not sure something is fine, measure it, and if you still can't prove it is fine, report it.

The reel: vertical 1080x1920, a short 3D comedy. Cleo (a junior developer, glasses, brown hair) talks to Claude (a small orange AI companion on her desk). Burned-in word-by-word captions. Premise: $4

FILES (all readable; your current directory is writable, put every frame/crop/plot you make there):
- $o/video.mp4  : the COMPLETE video to check, with audio.
- $o/dialogue.txt : each line's start-end time (seconds in the video), speaker and script text.
- $o/words.txt  : every word with its start-end time in the video (from Whisper on the voice clips).
- $REF : a reel from the same channel that the owner KEPT. Use it as the bar for pace and lip sync.
- Attached sheets: the whole video at 2 frames/s (yellow label = seconds). They are only an overview: 2 fps hides flashes, motion and mouths, so do not judge cuts, pace or lip sync from them.
TOOLS: you can run ffmpeg, ffprobe and python3 (numpy, PIL), extract frames at any fps, crop and tile them, measure audio, and look at any image you make. Use them. Every finding needs a measurement or a frame you looked at.

WHY THIS CHECK IS STRICT: the owner deleted 18 of the last 26 reels. The reasons, which you must catch:
1. Lip sync: the speaking character's mouth does not match the voice (mouth moving in silence, closed or barely moving while words are heard, mouth shapes not following syllables, the wrong character's mouth moving, a visible delay). Ep11 was deleted for this even though audio and video were not offset, so look at real mouth motion, not just the offset.
2. Slow pace: Ep10 and Ep11 felt slow and dragged (about 1.75-1.95 spoken words/s overall, pauses that did nothing for the joke). The kept reels run about 2.1-2.2 words/s. Treat these as a reference, not a rule.
3. Flash cuts: shots shorter than 0.6 s, and 1-frame flashes of a screen or another shot after a cut.
4. Chopped audio: a word cut off at the end of a line, a sound effect (phone buzz) that stops dead instead of fading, clicks at cuts.
5. Weird poses: hands raised up by the face, a character facing the wrong way, glitches in the 3D render.
6. Wrong or mistimed captions, captions covering faces or screen text, unreadable or contradicting screen content.

REQUIRED CHECKS. Do every one and report the numbers:
A. CUTS: list every cut (ffmpeg scene detection, then confirm frame by frame around each cut). List any shot < 0.6 s and any 1-2 frame flash (big frame difference that reverts on the next frame).
B. AUDIO: compute a 5-10 ms RMS envelope of the full mix. List every place where loud audio drops to near silence in under ~20 ms (a chop), and check that the last word of every line is complete (compare with words.txt). Check sound effects fade out.
C. PACE: measure spoken words per second for each line and overall, every silence between or inside lines longer than 0.6 s, and the time from the first frame to the first word. Do the same for $REF and compare. There is no fixed number: a slow line or a pause is fine when the scene needs it (a comic beat before a reveal, a reaction, a character thinking), and wrong when it just drags. For every slow stretch, say whether it serves the joke or drags, and why. Dragging that would make a viewer swipe away is MAJOR.
D. LIP SYNC: for EVERY line, find a shot where the speaker's face is visible, crop the mouth, extract it at 15 fps over the line, and compare mouth opening per frame with the voice envelope and word times. Check: mouth opens on words and closes in pauses, motion is big enough to read on a phone, the listener's mouth stays still, no frozen mouth while talking. Estimate any lead or lag in ms. Do the same on 2-3 lines of $REF so you know what good looks like here. Any line clearly worse than $REF is MAJOR; mouth closed or wrong character moving while speaking is a BLOCKER.
E. CAPTIONS: each caption word appears with its spoken word (within ~0.15 s), spelling matches dialogue.txt, nothing covers the faces or important screen text.
F. SCREENS AND VISUALS: monitor/phone screens are readable and agree with the dialogue; no render glitches, no hands-up poses, characters face each other correctly.
G. HOOK AND ENDING: the first 2 s give a reason to keep watching (no text hook overlay is allowed; dialogue captions are fine); the ending is clean (fade to black is intended) and the joke lands.
Allowed, not issues: the small "@talkingagents" handle at the bottom of every frame; Cleo's hair falling over one eye (her design); a short silent beat (under 1 s) before the first line.

REPLY FORMAT (plain text, no preamble):
ISSUES — one per line, worst first: [BLOCKER|MAJOR|MINOR] time — check letter — what is wrong — the measurement or frame that shows it — the fix.
CHECKS — one line each for A to G: PASS or FAIL plus the key numbers (cuts and shortest shot; chops found; words/s for this video vs REF; lip-sync result per line; etc.).
Then the last line exactly "VERDICT: PASS" (no BLOCKER and no MAJOR issues) or "VERDICT: FAIL".
B
codex exec --skip-git-repo-check -C $o -s workspace-write -c model_reasoning_effort="xhigh" $(for f in ${=sh}; do echo -i $f; done) -o $o/reply.md - < $o/brief.md > $o/log.txt 2>&1
echo "== $1"; cat $o/reply.md
mkdir -p $S/passed
if python3 $REPO/scripts/cutcheck.py $2 $o/cuts && grep -q "^VERDICT: PASS" $o/reply.md; then
  echo "$1 $(date +%T) $2" > $S/passed/$(md5 -q $2); echo "APPROVED $(md5 -q $2)"
else
  echo "NOT APPROVED (Codex FAIL or flash cuts; see $o/cuts)"
fi
