1. Everyone Is Cleo
Format: CLASSIC
Search: “accidentally ran SQL update without WHERE”
Opening: “Claude, why is every customer called Cleo?”

- Visual: Cleo scrolls through a customer grid; every name is hers.
- She meant to update her own profile. Claude spots the missing WHERE clause. [PostgreSQL](https://www.postgresql.org/docs/15/dml-update.html)
- Invoices, support tickets, and the customer leaderboard now all say Cleo.
- She discovers she is simultaneously the highest-spending customer and banned for fraud.

Final — Claude: “You contain multitudes. Several are overdue.”
View appeal: Instant database panic, escalating consequences, and an absurd visual anyone understands.

2. All Tests Passed
Format: CLASSIC
Search: “unit tests pass but app doesn't work”
Opening: “Claude, all my tests passed. Nobody can log in.”

- Visual: Green test ticks glow beside a login form that keeps shaking red.
- Cleo insists she tested login, logout, and wrong passwords.
- Claude discovers she mocked the login function itself to return success.
- She temporarily removes its real implementation. The tests still pass.

Final — Claude: “Congratulations. Your imaginary app works.”
View appeal: A familiar engineering embarrassment with a reveal that invites confessions in comments.

3. Just Two Lines
Format: CLASSIC
Search: “accidentally committed node_modules”
Opening: “Claude, why does my two-line change have eighteen thousand files?”

- Visual: The changed-files scrollbar shrinks to a dot while Cleo’s smile disappears.
- She staged node_modules along with her code.
- Claude asks what feature required the dependency; she dodges twice.
- Reveal: the terminal now prints “hello” in blue.

Final — Claude: “Eighteen thousand files. One blue word.”
View appeal: Recognizable Git panic, dependency jokes, and a tiny payoff that makes the escalation funnier.

4. The Reminder Was Down
Format: CLASSIC
Search: “website SSL certificate expired”
Opening: “Claude, Chrome says my website is dangerous. It’s a meal planner.”

- Visual: A cheerful broccoli mascot sits behind a huge browser security warning.
- Cleo suspects a hack; Claude finds an expired certificate.
- She proudly explains she built a dashboard to remind her before expiry.
- The reminder dashboard lives on the same affected domain; she cannot open it normally either.

Final — Claude: “You put the spare key inside the house.”
View appeal: A widely experienced outage with an easy-to-grasp, self-inflicted twist.

5. Three Clicks, One Count
Format: BOARD
Search: “React setState multiple times only updates once”
Opening: “Claude, I told React to add three. It added one.”

- Visual: Cleo hits a “+3” button; one lonely counter block appears.
- Claude: “Board time.” Metaphor: three photocopies of the same starting score, each with one added.
- Three calls using count + 1 all read that render’s snapshot.
- Fix: use three functional updates, setCount(c => c + 1); the updates build on each other and the counter rises by three. [React](https://react.dev/reference/react/useState)

Final — Claude: “You sent the same instruction three times. Very managerial.”
View appeal: Strong React recognition, close to your successful useEffect audience, with a distinct lesson.

6. Search Results From the Past
Format: BOARD
Search: “autocomplete race condition”
Opening: “Claude, I searched for React. Why am I getting recipes?”

- Visual: Cleo types “re,” then “react”; correct results appear, then suddenly revert.
- Claude: “Board time.” Metaphor: numbered takeaway orders arriving out of order.
- The older “re” request finishes last and overwrites the newer results.
- Fix: ignore responses belonging to an outdated query; repeat under slow networking and “react” stays correct. [React](https://react.dev/reference/react/useEffect)

Final — Claude: “Last to arrive doesn’t mean latest.”
View appeal: An instantly visible bug with a satisfying explanation viewers can save and reuse.

7. JavaScript Can’t Count
Format: BOARD
Search: “JavaScript sort numbers wrong”
Opening: “Claude, why does ten come before two?”

- Visual: Price cards snap into order: 1, 10, 2. Cleo physically tilts her head.
- Claude: “Board time.” Metaphor: a librarian alphabetizing number labels.
- Default sort compares string representations, so “10” comes before “2.”
- Fix: sort((a, b) => a - b); the cards rearrange into numeric order. [MDN](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/sort)

Final — Claude: “You hired a librarian to do your accounting.”
View appeal: A broad JavaScript gotcha with a clear visual and a one-line fix.

8. My Birthday Moved
Format: BOARD
Search: “JavaScript date off by one day”
Opening: “Claude, my app says I was born yesterday.”

- Visual: A birthday calendar flips backward when Cleo switches the preview to Los Angeles.
- Claude: “Board time.” Metaphor: a birthday is a calendar square; a timestamp is a clock moment.
- Parsing a date-only string as a Date gives UTC midnight, which can display as the previous day farther west.
- Fix: preserve birthdays as date-only values and format their components without timezone conversion; both previews show the same birthday. [MDN](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date)

Final — Claude: “Your birthday doesn’t need jet lag.”
View appeal: A notorious searchable bug with personal stakes and a memorable explanation.

Top 3 overall:

1. Everyone Is Cleo — Strongest immediate hook, escalating disaster, and readable visual comedy.
2. Three Clicks, One Count — Best fit with your proven React audience, plus a useful takeaway.
3. All Tests Passed — Sharpest reveal and punchline; likely to prompt “we did this at work” comments.

