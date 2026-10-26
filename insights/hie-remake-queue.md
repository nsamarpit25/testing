# HIE ember remakes: upload queue

These post as auto trial reels, at least 30 minutes apart. Covers show the topic only. Captions open with a keyword line.

| # | Reel | Status | Link |
|---|------|--------|------|
| 1 | Docker (08-docker-v2) | posted 2026-10-21 01:24 IST, with the old subtitle cover | https://www.instagram.com/reel/DeuoSE4iFmj/ |
| 2 | Kubernetes (09-kubernetes-v2) | posted 2026-10-21 01:57 IST, title-only cover | https://www.instagram.com/reel/DeusEvgCfo1/ |
| 3 | Reverse proxies (05-reverse-proxies-v2) | posted 2026-10-21 02:30 IST; deleted by Sam ~09:48 (nginx bug), B replaces it | https://www.instagram.com/reel/Deuv8O2DG8g/ |
| 4 | Rate limiting (01-rate-limiting-v2) | posted 2026-10-21 03:05 IST | https://www.instagram.com/reel/Deuz-jtD7GN/ |
| 5 | Load balancing (04-load-balancing-v2) | posted 2026-10-21 03:40 IST | https://www.instagram.com/reel/Deu389jCI7v/ |
| 6 | Health checks (11-health-checks-v2) | posted 2026-10-21 04:15 IST | https://www.instagram.com/reel/Deu77PfkquT/ |
| 7 | Idempotency (03-idempotency-v2) | posted 2026-10-21 04:50 IST | https://www.instagram.com/reel/DevACd5n0hc/ |
| 8 | Caching | todo | |
| 9 | API gateways | todo | |
| 10 | Service discovery | todo | |
| 11 | CI/CD | todo | |
| 12 | Circuit breakers | todo | |
| 13 | Distributed transactions (21), version A: the original render | todo, new SEO caption | |
| 14 | Distributed transactions (21), version B: 1.1x faster cut | rendered: media/21-distributed-transactions/21-distributed-transactions-fast.mp4 (50s); needs final review and caption | |
| 15 | Canary releases, remade in ember style | last | |

## Change of plan (2026-10-21 ~02:40 IST, from Sam)
After Idempotency, stop the remake queue (rows 8-15 wait) and make the next new topics from TOPICS.md in list order: #19 Saga Pattern, #20 Dead Letter Queues. New topics can get variants (a different hook / first line, or a faster cut), and weak posted reels can get a re-post variant. Pick by early stats.

| # | Reel | Status | Link |
|---|------|--------|------|
| N1 | Saga pattern (19-saga-pattern) | posted 2026-10-21 05:25 IST | https://www.instagram.com/reel/DevEBHCEzQv/ |
| N2 | Dead letter queues (20-dead-letter-queues) | posted 2026-10-21 06:00 IST | https://www.instagram.com/reel/DevH-HaDygZ/ |

## Variants (my picks, overnight 2026-10-21)

| # | Variant | What changed | Status | Link |
|---|---|---|---|---|
| V1 | Saga B (19-saga-pattern-b) | new spoken hook "Your flight and hotel are paid for. Then the car booking fails. Who gets your money back?"; caption opens with that story hook | posted 2026-10-21 06:35 IST | https://www.instagram.com/reel/DevL9S8CCb7/ |
| V2 | Kubernetes B (09-kubernetes-v2b) | spoken hook back to the original's "Your app crashed at 3 AM. By the time you woke up…"; story caption + comment question + broad hashtags (like the 16.8k original) | posted 2026-10-21 07:10 IST | https://www.instagram.com/reel/DevP_yLjBjp/ |
| V3 | Docker B (08-docker-v2b) | spoken hook back to the original's "Your code works perfectly on your laptop. You put it on a server, and it crashes."; story caption + comment question + broad hashtags | posted 2026-10-21 07:45 IST | https://www.instagram.com/reel/DevT_PBgJZY/ |
| V4 | Reverse proxies B (05-reverse-proxies-b) | curiosity hook "Your app has ten servers, and bots can't find a single one…"; fixed nginx proxy_pass (v2 shows invalid `proxy_pass api;`); clearer forward-vs-reverse ending with you → proxy → website path | posted 2026-10-21 08:20 IST | https://www.instagram.com/reel/DevYDm4jtwu/ |
| V5 | Load balancing B (04-load-balancing-b) | hook "A hundred thousand people opened your app at once. It didn't even slow down. How?" (original's "Ten million…" got 228); story caption + comment question | posted 2026-10-21 08:55 IST | https://www.instagram.com/reel/DevcEv4gqn3/ |
| V6 | Health checks B (11-health-checks-b) | spoken hook back to the original's "Your app froze at 3 AM…" (2.6k original); 3:00 AM tag; story caption + comment question | posted 2026-10-21 09:30 IST | https://www.instagram.com/reel/Devf-dXjxew/ |
| V7 | Idempotency B (03-idempotency-b) | hook back to the original's "You tapped Pay twice on bad Wi-Fi. So why weren't you charged twice?"; bigger labels; elevator-button panel for the analogy | posted 2026-10-21 10:05 IST | https://www.instagram.com/reel/DevkAnzDIbu/ |
| N3 | Cron jobs (21-cron-jobs), new topic #21 | "3 a.m. Nobody's awake, and your app just emailed ten thousand people their receipts. Who pressed the button?" alarm clock → server → inboxes; two servers = two receipts | posted 2026-10-21 10:40 IST | https://www.instagram.com/reel/Devn_rdFG6z/ |
| N4 | WebSockets (22-websockets), new topic #22 | "Your friend hit send, and it popped up on your phone instantly. You never refreshed. So how did your app know?" friend phone → server → your phone; request/reply hangs up, WebSocket cable stays open; crowd of phones fills server memory; drop + reconnect | script (Codex fixes applied), voice, video.html, caption done; PC down, so rendered on the Mac (Sam OK'd, tools/remake/bin/rr_mac.sh); Codex PASS (ws1, 1st round); posted 2026-10-21 11:15 IST | https://www.instagram.com/reel/Devr_8Ej1Y-/ |
| V8 | Dead letter queues B (20-dead-letter-queues-b) | hook "One broken order just jammed your whole order line…" (DLQ got 204 views, 11 shares); tighter, higher hook frame; story caption + comment question; RabbitMQ beat remapped (whisper: RobinMQ) | rendered on the Mac; Codex PASS (dlqb1, 1st round); posted 2026-10-21 11:50 IST | https://www.instagram.com/reel/DevwH0gCQ0_/ |
| N5 | Long polling (23-long-polling), new topic #23 | "Your app asked the server for new messages, and the server didn't answer for thirty seconds. On purpose. Why?" same world as WebSockets; server face shows a hold timer; plain polling = 4 wasted trips; held → answered instantly → asks again; time limit → "nothing yet"; are-we-there-yet replay; Telegram getUpdates anchor | rendered on the Mac; Codex PASS (lp1, 1st round); posted 12:25 IST as trial | https://www.instagram.com/reel/Dev0IAUgYr0/ |
| N6 | Server-sent events (24-server-sent-events), new topic #24 | "You asked an AI chatbot a question, and the answer appeared word by word…" AI server → phone; answer streams in 2-word chunks; no-streaming version = blank screen then all at once; EventSource card with data: lines; send-back blocked → new request; news-ticker replay; OpenAI API + browser EventSource anchors | rendered on the Mac; Codex PASS (sse1, 1st round); 13:00 post failed (internet down); reposted 13:21 IST LIVE (Sam: new topics go live) | https://www.instagram.com/reel/Dev6eHQk3he/ |
| N7 | Database indexing (25-database-indexing), new topic #25 | phone-book index; full scan vs index lookup; CREATE INDEX card; writes cost a little more | rendered on the Mac; Codex PASS (idx2, 2nd round); to post LIVE ~13:35 IST (needs Sam's OK for the command) | |
| N8 | Query optimization (26-query-optimization), new topic #26 | "Your orders page takes nine seconds to load…" phone + DB; crate flood, thrown away; better SELECT … LIMIT 10; shopping list; EXPLAIN plan | rendered on the Mac; Codex PASS (qo2, 2nd round); ready, to post LIVE (needs Sam's OK for the live command) | |
| N9 | N+1 queries (27-n-plus-one), new topic #27 | "One page. 101 trips to your database…" counter to 101; one name per trip; 1 + N card; fix = all names in one trip (2) or one JOIN (1) | rendered on the Mac; Codex PASS (np1, 1st round); ready, to post LIVE (needs Sam's OK for the live command) | |
| V9 | Caching v2 (02-caching-v2) | "Your app takes two seconds to load its data…" phone/server/DB/cache sticky note; stale $20 vs $25; expire or clear | rendered on the Mac; Codex PASS (cv1); posted 14:10 IST as trial | https://www.instagram.com/reel/DewAKkNCNjm/ |
| V10 | Message queues v2 (17-message-queues-v2) | "You texted a friend whose phone is dead. One grey tick…" queue slots; delivered/confirmed/removed; checkout rush → worker at own pace; post office | rendered on the Mac; Codex PASS (mq2, 2nd round); posted 14:45 IST as trial | https://www.instagram.com/reel/DewEIruCZVw/ |
| V11 | Circuit breakers v2 (13-circuit-breakers-v2) | "Your whole shop just went down because the reviews got slow…" server waiting slots; breaker closed → counts slow → open → skip reviews → test requests → resume | script PASS after 3 Codex rounds; rendered on the Mac; Codex PASS (cb1); posted 15:20 IST as trial | https://www.instagram.com/reel/DewIIVAEkEx/ |
| V12 | Service discovery v2 (10-service-discovery-v2) | "Every payment in your app failed at 2:05 PM. Nobody changed a single line of code." app/server A/server B/payments block; restart → old address; contacts card; directory lookup | rendered on the Mac; Codex PASS (sd1, 1st round); posted 15:55 IST as trial | https://www.instagram.com/reel/DewMOf9FK3B/ |
| V13 | API gateways v2 (06-api-gateways-v2) | "A stranger saw everyone's food orders in your app, without even logging in." phone → orders direct leak; each service checks itself; gateway front door; blocked; orders still checks whose; routing + slow down | rendered on the Mac; Codex PASS (gw1, 1st round); posted 16:30 IST as trial | https://www.instagram.com/reel/DewQD2ekj6b/ |
| V14 | CI/CD v2 (07-ci-cd-v2) | "You changed one letter in your code. Two minutes later, your whole app was down." code → belt → users; stations rise: build fails/stops, login test fails/stops, good change approved → users; typo caught at TEST | rendered on the Mac; Codex PASS (ci1, 1st round); posted 17:30 IST as trial | https://www.instagram.com/reel/DewW9a6CNof/ |
| V15 | Retries v2 (16-retries-v2) | "The weather server stopped answering for one second. Then thousands of apps tried again at the same moment…" 8 app phones + server load meter; storm waves; stop after 3; backoff 1/2/4 s; jitter spread | rendered on the Mac; Codex PASS (rt1, 1st round); posted 18:30 IST as trial | https://www.instagram.com/reel/Dewd6RjFaG6/ |

- From 13:00 on 2026-10-21 (Sam): new topics are posted live; variants of existing topics go up as trials.
- From 16:45 on 2026-10-21 (Sam): 1 hour between trial posts, 3 hours between live posts.

## Made live / deleted (2026-10-21, Sam)
- Deleted (trials): Canary copies Deugt-XE6nY + DeuiOdulfWH, Saga A DevEBHCEzQv, Kubernetes v2 DeusEvgCfo1. Earlier: Reverse proxies v2 + originals of Rate limiting, Load balancing, Idempotency.
- Made live ~10:55, all three at once: Rate limiting v2 (Deuz-jtD7GN), Saga B (DevL9S8CCb7), Canary (Deuh_3nD3Z_). Next time, space make-lives 30-45 min apart.
- Pending: delete Docker v2 (DeuoSE4iFmj) once Docker B passes it; delete DLQ A (DevH-HaDygZ) once DLQ B passes it; delete the Reverse proxies original and make B live once B passes 1,872; pick the Load balancing / Health checks / Idempotency v2-vs-B winners tonight.
