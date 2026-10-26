**1. Deleted 84,000 Users**
- Format: CLASSIC
- Searchable keyword: sql delete without where clause rollback
- Opening line: "Claude, why did my query to delete my test account just say '84,302 rows affected'?"
- Beats:
  - Visual: Cleo frozen at her desk; terminal shows a terrifyingly large number; Slack pings start popping up on her secondary monitor.
  - Escalation 1: Claude notes she forgot the `WHERE` clause. Cleo tries to hit Ctrl+Z in the terminal.
  - Escalation 2: Customer support messages her: "Why is the CEO's account gone?" Cleo asks about the automated daily backups.
  - Twist: Claude reveals the backup script was written by Cleo six months ago—it just successfully backed up the newly empty database, overwriting yesterday's.
- Final line: Claude: "On the bright side, our database queries are now running 100% faster."
- Why it should get views: Dropping prod / forgetting the `WHERE` clause is the ultimate universal developer nightmare, matching the high-stakes energy of the API key and useEffect episodes.

**2. The "Quick" npm Audit Fix**
- Format: CLASSIC
- Searchable keyword: npm audit fix force broke my app
- Opening line: "Claude, I just ran `npm audit fix --force` to clear one tiny security warning, and now the app won't even boot."
- Beats:
  - Visual: Cleo’s screen is a waterfall of bright red terminal errors that keeps scrolling down onto her desk.
  - Escalation 1: To fix one low-severity warning, `--force` downgraded React by three major versions.
  - Escalation 2: Cleo tries to revert, realizes she didn't commit her morning's work first. Now she has 142 vulnerabilities instead of 1.
  - Twist: Claude checks what the original security warning was actually for—a regex vulnerability in a testing library that isn't even shipped to production.
- Final line: Claude: "Good news: the hackers can't exploit the app if the app doesn't exist."
- Why it should get views: Every JS developer has been burned by the trap of `npm audit fix --force`, making it instantly shareable.

**3. The Friday 4:59 PM Deploy**
- Format: CLASSIC
- Searchable keyword: git revert hotfix production down
- Opening line: "Claude, I just pushed a one-line typo fix so I could leave early, and the entire checkout page went blank."
- Beats:
  - Visual: Warm Friday sunset outside the window; Cleo has her backpack on one shoulder, coat half on, staring in horror at a red Datadog dashboard.
  - Escalation 1: The "typo" was actually a load-bearing misspelled variable name used across 14 backend microservices.
  - Escalation 2: She pushes a hotfix, which triggers a 25-minute CI/CD pipeline build because the Docker cache just expired.
  - Twist: Her boss messages in `#general`: "Whoever is still online, great job locking down the checkout page for the scheduled 5 PM maintenance window!"
- Final line: Claude: "Take the credit, close the laptop, and run."
- Why it should get views: "Never deploy on a Friday" is top-tier dev culture lore with built-in ticking-clock tension.

**4. The Haunted Cron Job**
- Format: CLASSIC
- Searchable keyword: crontab syntax every minute instead of once a day
- Opening line: "Claude, why did our server just send the 'Happy Birthday' discount code to users 1,400 times today?"
- Beats:
  - Visual: Cleo’s phone on the desk is vibrating continuously off the table from automated alert texts.
  - Escalation 1: Cleo put `* 9 * * *` in the crontab thinking it meant 9:00 AM once a day, instead of *every single minute* during the 9 AM hour.
  - Escalation 2: Worse, the 5% discount code she generated stacks. Users are combining them.
  - Twist: Finance messages her: sales volume is up 800% this morning, except the company now owes customers $12 to take the product.
- Final line: Claude: "Technically, you just solved user acquisition."
- Why it should get views: Cron syntax is notoriously confusing, and runaway automation loops (like your top-performing `useEffect` episode) always perform well.

**5. React State Is One Step Behind**
- Format: BOARD
- Searchable keyword: react useState not updating immediately console log
- Opening line: "Claude, React is broken—I just called `setCount(5)`, and the very next line logs `count` as `4`."
- Beats:
  - Visual: Claude pulls down a glowing 3D whiteboard showing a restaurant table and a waiter holding a notepad.
  - Metaphor: "Board time." Calling `setCount` isn't teleporting food onto the table; it's handing an order to the waiter. Your `console.log` is looking at the table before the waiter even walks to the kitchen (the next render).
  - The Fix: Cleo either uses the new value directly in a variable before setting it, or checks it on the next render. She updates the code; the UI and logs sync up.
- Final line: Claude: "Stop yelling at the waiter while he's still holding the pen."
- Why it should get views: This is arguably the #1 most googled React question by beginners and intermediates, following the proven success of your `useEffect` video.

**6. Git Rebase vs. Merge**
- Format: BOARD
- Searchable keyword: git rebase vs merge difference explained
- Opening line: "Claude, the senior dev told me to rebase my branch instead of merging, and I'm too afraid to press Enter."
- Beats:
  - Visual: On the 3D board, Claude draws two notebooks—one with messy taped-in pages, one looking brand new.
  - Metaphor: "Board time." `git merge` is stapling your messy rough draft notes onto the end of the main book—accurate history, ugly to read. `git rebase` is pretending you waited until everyone else finished writing the book, and then wrote your chapters cleanly at the very end.
  - The Fix: Cleo runs `git pull --rebase origin main`. The commit graph on her screen straightens into a clean single line.
- Final line: Claude: "Rebase: lying about when you started your work, professionally."
- Why it should get views: Git anxiety is huge, and `rebase vs merge` is an evergreen search term that developers constantly need a visual refresher on.

**7. Why `0.1 + 0.2 !== 0.3`**
- Format: BOARD
- Searchable keyword: 0.1 + 0.2 !== 0.3 javascript floating point fix
- Opening line: "Claude, why is my shopping cart saying a 10-cent item plus a 20-cent item equals `0.30000000000000004` dollars?"
- Beats:
  - Visual: Claude brings out the board showing a pie cut into 3 pieces and a calculator displaying `0.3333333`.
  - Metaphor: "Board time." In base-10, you can't write 1/3 cleanly—it's `0.3333...` forever, so you eventually round it. Computers work in base-2 (binary), where `0.1` is an infinite repeating fraction. When you add two rounded binary numbers, the tiny leftover crumbs add up at the end.
  - The Fix: Never do money math in decimals; store everything in cents as whole integers (`10 + 20 = 30`), then divide by 100 at display time. Cleo changes it; the cart shows `$0.30`.
- Final line: Claude: "Computers are great at math, until they have to make change for a dollar."
- Why it should get views: Every programmer hits this bizarre bug eventually, and the "store money in cents" fix is a concrete, high-save-value takeaway.

**8. `z-index: 999999` Still Behind**
- Format: BOARD
- Searchable keyword: css z-index not working stacking context
- Opening line: "Claude, I set my modal's `z-index` to nine million and it's still hiding behind the navbar."
- Beats:
  - Visual: Cleo aggressively typing more `9`s into her CSS file; Claude pulls down the board showing two glass elevators (Floor 1 and Floor 2).
  - Metaphor: "Board time." Stacking Contexts. Your modal is inside a parent div on Floor 1 (`z-index: 1`), and the navbar is on Floor 2 (`z-index: 2`). Being 9 million millimeters tall inside the Floor 1 elevator still never puts you above Floor 2.
  - The Fix: Move the modal outside the parent div (or fix the parent's `z-index`/`transform`). Cleo moves the component to the root; the modal pops to the front with just `z-index: 10`.
- Final line: Claude: "You can delete the other eight nines now."
- Why it should get views: Typing `z-index: 999999` out of frustration is a universal dev meme, and explaining "stacking context" simply will get massive bookmarks/saves.

***

**TOP 3 OVERALL RANKING**

1. **Deleted 84,000 Users (CLASSIC)** — High-stakes production disasters with big numbers (like your 45k DB reads and 40k emails) are your proven best performers on the channel.
2. **React State Is One Step Behind (BOARD)** — Directly taps into the exact same React audience that made your `useEffect` video #1, solving a daily frustration with a sticky metaphor.
3. **`z-index: 999999` Still Behind (BOARD)** — The opening hook of typing `999999` is universally relatable across all web devs, and the "elevator floor" metaphor makes for a great 3D visual that gets saves.