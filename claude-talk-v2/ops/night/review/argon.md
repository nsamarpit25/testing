### Ep14: `fetch()` and HTTP 500
**1. Technical Accuracy:** Spot on. `fetch()` only rejects on network failure; HTTP 500 resolves normally with `response.ok === false`.
**2. Weakest Lines & Rewrites:**
*   *Line 2:* "Why confetti?" -> *Rewrite:* "Confetti is bad?" (A deadpan question makes her panic funnier).
*   *Line 9:* "So my app heard "no"... and threw a party?" -> *Rewrite:* "The server crashed, and my app celebrated?" (Avoids repeating the "party" noun from line 3 and the "throw" verb from line 1).
*   *Line 11:* "If not response dot ok... throw... It's red! It actually failed!" -> *Rewrite:* "Okay, if not response dot ok, throw Error... Yes! Big red box!" (Sounds more like actual typing and gives a punchier visual reaction).
**3. Hook & Ending:** The hook is fantastic—visual, urgent, and fits the 1.5s window. The "surprise party" callback lands great.
**4. Score:** 8.5/10

```tsv
cleo	Claude, checkout is down, and my app is throwing confetti.
claude	Confetti is bad?
cleo	That's the success screen. Every failed order gets a party.
claude	Didn't you add error handling?
cleo	Try, catch, a big red error message. I tested it. Nothing went red.
claude	Because nothing threw. The server sent back a five hundred.
cleo	So the catch should catch it!
claude	Fetch only throws when the network fails. A five hundred is still an answer.
cleo	The server crashed, and my app celebrated?
claude	Check response dot ok. If it's false, throw the error yourself.
cleo	Okay, if not response dot ok, throw Error... Yes! Big red box!
claude	Congratulations. Your failure works.
cleo	Oh no. Support says thirty people got confetti... and no order.
claude	Tell them it was a surprise party.
```

---

### Ep15: CORS at the Whiteboard
**1. Technical Accuracy:** Accurate for a simple request (GET). (Preflight `OPTIONS` requests do block the actual request, but skipping preflight is standard and smart for a 60s explainer).
**2. Weakest Lines & Rewrites:**
*   *Line 10:* "Postman isn't a browser. Nobody checks Postman's ID." -> *Rewrite:* "Postman isn't a browser. It doesn't care about the guest list." (Sets up the bouncer/guest-list metaphor *before* line 12 so the joke connects better).
*   *Line 15:* "What happens in production?" -> *Rewrite:* "Why? What's in production?" (Snappier pacing).
*   *Line 16:* "A different origin." -> *Rewrite:* "A whole new guest list." (Hits the callback harder while meaning the exact same thing).
**3. Hook & Ending:** The hook is the #1 most relatable junior dev question—instant stop-scroll. With the tweak to line 16, the ending becomes a true callback to the guest list metaphor.
**4. Score:** 9/10

```tsv
cleo	Claude, my API works in Postman, but Chrome says "blocked by CORS policy."
claude	Finally. Board time.
cleo	Since when do you have a board?
claude	Since now. This is your page, on localhost three thousand. This is your API, on port eight thousand.
cleo	Same laptop.
claude	Different port, different origin. To Chrome, that's a stranger.
cleo	So Chrome blocks the request?
claude	The server still answers. Chrome just won't let your page read it, unless the API says your page is allowed.
cleo	And Postman?
claude	Postman isn't a browser. It doesn't care about the guest list.
cleo	So I fix it in the front end?
claude	No. A guest can't put herself on the guest list. The server adds an Access-Control-Allow-Origin header.
cleo	Allow origin... localhost three thousand... It loaded!
claude	Next week on the board: production.
cleo	Why? What's in production?
claude	A whole new guest list.
```

---

### Ep16: `git bisect` Nature Documentary
**1. Technical Accuracy:** Good, though strictly speaking, bisecting a 128-commit range takes 7 steps only if the endpoints are already known to be good/bad ($\log_2(128) = 7$). Totally fine for comedy.
**2. Weakest Lines & Rewrites:**
*   *Line 1:* "Claude, checkout broke somewhere in the last hundred and twenty-eight commits. I'm checking them one by one." -> *Rewrite:* "Claude, checkout broke, and I'm checking a hundred and twenty-eight commits one by one." (Original puts the punch/hook too late; this puts "Claude, checkout broke" in the first 1.5s).
*   *Line 7:* "And then?" -> *Rewrite:* "And then what?" (Gives TTS a slightly better rhythm).
*   *Line 12:* "Nature is brutal." -> *Rewrite:* "In the wild, the developer is her own worst predator." (Ties the self-sabotage directly back to the nature documentary gimmick).
**3. Hook & Ending:** Once front-loaded, the hook works well. The rewritten ending makes the documentary format pay off much harder.
**4. Score:** 9/10

```tsv
cleo	Claude, checkout broke, and I'm checking a hundred and twenty-eight commits one by one.
claude	Here we observe the junior developer, in her natural habitat.
claude	She is on commit four. At this pace, she will finish on Thursday.
cleo	Are you... narrating me?
claude	The developer has noticed us.
claude	Try git bisect. Mark one commit good, one commit bad. Git picks the middle.
cleo	And then what?
claude	You test it. Good or bad. It cuts the pile in half, every time.
cleo	Bad. Good. Good. Bad. Good. Bad. Bad.
claude	A hundred and twenty-eight suspects. Seven questions. Remarkable.
cleo	Found it! "Small harmless cleanup." Who wrote... oh. It's me.
claude	In the wild, the developer is her own worst predator.
```