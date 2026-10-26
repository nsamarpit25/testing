You are script-editing three short vertical comedy reels for @talkingagents (Instagram). Cast: Cleo, a junior web developer, and Claude, a small orange AI companion on her desk. Voices are Gemini TTS; captions are burned in word by word. Target pace ~2.1 words/s, 50-65 s. Cleo's first line starts with "Claude," and is the hook (it must work in the first 1.5 s and must NOT be repeated later). No cold-open replays. Endings are a punchy callback. Our weak spot is lip sync, so the experiments lean on shots where mouths matter less.

Ep14 (NORMAL desk format): fetch() does not reject on HTTP 500; check response.ok.
Ep15 (EXPERIMENT): Claude explains CORS at a small whiteboard on the desk; the board drawings change per line.
Ep16 (EXPERIMENT): nature-documentary parody. Claude turns to the camera and narrates Cleo in a hushed documentary voice (lines 2, 3, 5, 10, 12 are to camera); he teaches git bisect (128 commits -> 7 checks).

For EACH script: (1) technical accuracy problems, (2) the weakest 2-3 lines and a concrete rewrite for each, (3) whether the hook and ending land, (4) a score out of 10. Keep the same structure and length (±10 words); don't add characters. Then output each script's FINAL version as a TSV block (speaker<TAB>line), one line per row, ready to use. Be concise.

=== Ep14
cleo	Claude, checkout is down, and my app is throwing confetti.
claude	Why confetti?
cleo	That's the success screen. Every failed order gets a party.
claude	Didn't you add error handling?
cleo	Try, catch, a big red error message. I tested it. Nothing went red.
claude	Because nothing threw. The server sent back a five hundred.
cleo	So the catch should catch it!
claude	Fetch only throws when the network fails. A five hundred is still an answer.
cleo	So my app heard "no"... and threw a party?
claude	Check response dot ok. If it's false, throw the error yourself.
cleo	If not response dot ok... throw... It's red! It actually failed!
claude	Congratulations. Your failure works.
cleo	Oh no. Support says thirty people got confetti... and no order.
claude	Tell them it was a surprise party.

=== Ep15
cleo	Claude, my API works in Postman, but Chrome says "blocked by CORS policy."
claude	Finally. Board time.
cleo	Since when do you have a board?
claude	Since now. This is your page, on localhost three thousand. This is your API, on port eight thousand.
cleo	Same laptop.
claude	Different port, different origin. To Chrome, that's a stranger.
cleo	So Chrome blocks the request?
claude	The server still answers. Chrome just won't let your page read it, unless the API says your page is allowed.
cleo	And Postman?
claude	Postman isn't a browser. Nobody checks Postman's ID.
cleo	So I fix it in the front end?
claude	No. A guest can't put herself on the guest list. The server adds an Access-Control-Allow-Origin header.
cleo	Allow origin... localhost three thousand... It loaded!
claude	Next week on the board: production.
cleo	What happens in production?
claude	A different origin.

=== Ep16
cleo	Claude, checkout broke somewhere in the last hundred and twenty-eight commits. I'm checking them one by one.
claude	Here we observe the junior developer, in her natural habitat.
claude	She is on commit four. At this pace, she will finish on Thursday.
cleo	Are you... narrating me?
claude	The developer has noticed us.
claude	Try git bisect. Mark one commit good, one commit bad. Git picks the middle.
cleo	And then?
claude	You test it. Good or bad. It cuts the pile in half, every time.
cleo	Bad. Good. Good. Bad. Good. Bad. Bad.
claude	A hundred and twenty-eight suspects. Seven questions. Remarkable.
cleo	Found it! "Small harmless cleanup." Who wrote... oh. It's me.
claude	Nature is brutal.
