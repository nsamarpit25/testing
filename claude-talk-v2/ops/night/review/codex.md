All revisions preserve speaker order and row counts, stay within ±10 words, and use each hook once. Estimated dialogue times exclude pauses.

**Ep14 — Original: 8/10. Final: 114 words (−9), ~54 seconds.**

- **Accuracy:** “Fetch only throws when the network fails” is too absolute: aborts and invalid requests can also reject. HTTP 500 itself doesn’t reject; use `response.ok`, with `await` inside the `try`. [MDN](https://developer.mozilla.org/en-US/docs/Web/API/Window/fetch)
- **Weakest lines → rewrites:** L1 buries the absurdity → “Claude, checkout's celebrating. Every order failed.” L8 overgeneralizes → “Fetch doesn't reject just because the HTTP status says failure.” L14’s “surprise party” is predictable → “Free confetti. Delivery not included.”
- **Hook/ending:** The original premise lands, but slowly. The revision puts the contradiction first; the ending connects confetti directly to missing deliveries. Open on checkout confetti, then retain normal desk coverage.

```tsv
cleo	Claude, checkout's celebrating. Every order failed.
claude	Why confetti?
cleo	That's the success screen. Every failed order gets a party.
claude	Didn't you add error handling?
cleo	Try, catch, a big red error message. I tested it. Nothing went red.
claude	Because that five hundred is a response, not a rejected promise.
cleo	So the catch should catch it!
claude	Fetch doesn't reject just because the HTTP status says failure.
cleo	So my app heard "no"... and threw a party?
claude	Await fetch, check response dot ok. If false, throw an error.
cleo	If not response dot ok... throw... It's red! It actually failed!
claude	Congratulations. Your failure works.
cleo	Oh no. Support says thirty people got confetti... and no order.
claude	Free confetti. Delivery not included.
```

**Ep15 — Original: 7/10. Final: 126 words (−5), ~60 seconds.**

- **Accuracy:** “The server still answers” misses failed preflights, which prevent the actual request. Origins include scheme, host and port; show `http://localhost:3000`. The single-header fix should demonstrate a simple, credential-free GET; other cases can require additional CORS headers. [MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS)
- **Weakest lines → rewrites:** L8’s blanket claim → “Sometimes. A failed preflight permission check stops it. Otherwise, Chrome hides the response unless the API allows your origin.” L10’s ID analogy blurs CORS with authentication → “Postman doesn't enforce browser CORS rules. No guest list.” L16 merely states a fact → “New address. Back outside.”
- **Hook/ending:** The original hook is relatable but front-loads exposition. “Chrome’s gatekeeping” establishes the joke immediately; “Back outside” pays off the guest list.
- **Board:** Keep Claude beside the small desk board. Change its drawing each row: blocked arrow → board outline → question mark → two origins → laptop enclosure → port circles → stopped arrow → preflight/read branches → Postman label → bypass arrow → page-side pencil → server header → green response → production address → old list → closed gate. No extra characters.

```tsv
cleo	Claude, Chrome's gatekeeping. My API works in Postman. Here? CORS.
claude	Finally. Board time.
cleo	Since when do you have a board?
claude	Since now. Your page: localhost, port three thousand. Your API: same host, port eight thousand. Both HTTP.
cleo	Same laptop.
claude	Different port, different origin. To Chrome, that's a stranger.
cleo	So Chrome blocks the request?
claude	Sometimes. A failed preflight permission check stops it. Otherwise, Chrome hides the response unless the API allows your origin.
cleo	And Postman?
claude	Postman doesn't enforce browser CORS rules. No guest list.
cleo	So I fix it in the front end?
claude	Server side. Add Access-Control-Allow-Origin with your page's exact origin. Guests don't write the guest list.
cleo	Allowed my page's exact origin on the server... It loaded!
claude	Next lesson: production.
cleo	Same guest list?
claude	New address. Back outside.
```

**Ep16 — Original: 8.5/10. Final: 109 words (+2), ~52 seconds.**

- **Accuracy:** Seven checks fits 128 candidate commits in a linear history with a reproducible good→bad transition and no skipped commits. “Half, every time” overpromises for arbitrary histories. Explicitly start bisect and report each test result to Git. [Git documentation](https://git-scm.com/docs/git-bisect)
- **Weakest lines → rewrites:** L1 delays the parody → “Claude, checkout's extinct. A hundred and twenty-eight commits. I'm checking them one by one.” L8 omits reporting results → “Test checkout. Tell Git good or bad. Repeat. Each test roughly halves the suspects.” L12 is generic → “Cause of extinction: the developer.”
- **Hook/ending:** The original author reveal is excellent; keep it. “Extinct” establishes the documentary premise immediately and supplies a specific closing callback. Preserve hushed, to-camera delivery on **2, 3, 5, 10, 12**; use wider framing and Cleo’s hands/screen for the remaining coverage.

```tsv
cleo	Claude, checkout's extinct. A hundred and twenty-eight commits. I'm checking them one by one.
claude	Here we observe the junior developer, in her natural habitat.
claude	She is on commit four. At this pace, she will finish on Thursday.
cleo	Are you... narrating me?
claude	The developer has noticed us.
claude	Run git bisect start. Mark an earlier commit good, the broken one bad. Git picks between them.
cleo	And then?
claude	Test checkout. Tell Git good or bad. Repeat. Each test roughly halves the suspects.
cleo	Bad. Good. Good. Bad. Good. Bad. Bad.
claude	A hundred and twenty-eight suspects. Seven checks. Remarkable.
cleo	Found it! "Small harmless cleanup." Who wrote... oh. It's me.
claude	Cause of extinction: the developer.
```

