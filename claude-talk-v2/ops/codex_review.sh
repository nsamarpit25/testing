#!/bin/zsh
# codex_review.sh <name> <video> <timeline.json|-> "<premise>" [offset] [extra notes]  -> $S/rev/<name>/reply.md
S=/private/tmp/claude-501/-Users-samarpit-insta-automation/090cc81c-2b8e-489f-b1db-92f85c47225e/scratchpad
o=$S/rev/$1; sh=$(python3 $S/new/review.py $2 $3 $o ${5:-0})
cat > $o/brief.md <<B
You are the final reviewer for a vertical Instagram reel (1080x1920) on @talkingagents: a short 3D comedy where Cleo, a junior developer, talks to Claude, a small orange AI companion on her desk. The attached sheets are the COMPLETE video at 2 frames/second (yellow label = time in seconds), with burned-in word-by-word captions. Timed dialogue:

$(cat $o/dialogue.txt)

Premise: $4
${6}

Review the whole video for anything that would hurt it on Instagram or look broken: wrong or missing captions vs dialogue, captions overlapping important content, unreadable, cropped or wrong screen content, screens that contradict the dialogue, shots that are too short (flash cuts), a character facing the wrong way, visual glitches, a weak opening (no hook TEXT overlay is allowed in the first scene; dialogue captions are fine), the ending (fade to black is intended), and whether the joke lands.
Allowed by the channel owner, not issues: the small "@talkingagents" handle near the bottom on every frame; Cleo's hair falling over one eye (her design); a short silent beat before the first line.

Reply with a short list of concrete issues (time, what, fix) ranked by severity, then a final line exactly "VERDICT: PASS" (good to upload as is, minor nits only) or "VERDICT: FAIL" (must fix first).
B
codex exec --skip-git-repo-check -s read-only -c model_reasoning_effort="high" $(for f in ${=sh}; do echo -i $f; done) -o $o/reply.md - < $o/brief.md > $o/log.txt 2>&1
echo "== $1"; cat $o/reply.md
# Gate: record this exact file as approved only if Codex PASSes AND no flash cuts (Codex samples 2 fps, so it can't see shots < 0.5 s).
mkdir -p $S/passed
if python3 /Users/samarpit/insta-automation/claude-talk-v2/scripts/cutcheck.py $2 $o/cuts && grep -q "VERDICT: PASS" $o/reply.md; then
  echo "$1 $(date +%T) $2" > $S/passed/$(md5 -q $2); echo "APPROVED $(md5 -q $2)"
else
  echo "NOT APPROVED (Codex FAIL or flash cuts; see $o/cuts)"
fi
