# Topic list — How It's Engineered

Source: the "Who's gonna tell vibe coders about…" list (110 items, original order).
Workflow per topic: script + hook options → approval → voice (Gemini Puck) → video.html → preview → render → cover → caption.
Status: ✅ posted / ⏰ scheduled (IST) / 🎬 made, not posted / 📝 planned / blank = open.

## Next up: ranking after 09 Kubernetes (2026-10-17)

Scored 1–5 on **Arc** (follows Docker → Kubernetes), **Pain** (relatable for beginners) and **Visual** (works in the diorama style).

| Rank | Topic | Arc · Pain · Visual | Pain | Metaphor | Hook | Anchor |
|---|---|---|---|---|---|---|
| 1 | Service Discovery (#9) | 5 · 3 · 5 | The address changes and every call goes nowhere | Phone contacts: tap the name, not the number | "Kubernetes just moved your app to a new server, and every other service is still calling the old address." | Kubernetes Services + DNS, Consul, Netflix Eureka |
| 2 | Health Checks (#56–57, wildcard) | 5 · 4 · 5 | App is "running" but frozen, and nothing restarts it | Nurse checking a pulse (alive?) + shop's Open/Closed sign (ready?) | "Your app froze at 3 AM, and something restarted it before anyone woke up. How did it know?" | Kubernetes liveness and readiness probes |
| 3 | Circuit Breakers (#10) | 4 · 5 · 5 | One broken feature takes the whole app down | Fuse box tripping | "The reviews section broke, and it took your entire shopping app down with it." | Netflix Hystrix, Resilience4j |
| 4 | Retries (#12) | 3 · 5 · 4 | Blind retries make things worse | Redialling a busy line | "Your payment failed, so your app tried again. Now you've been charged twice." | AWS SDKs retry automatically |
| 5 | Timeouts (#11) | 3 · 5 · 4 | A spinner that never ends | Hanging up on hold music | "Your app isn't loading. It's waiting, and it'll wait forever unless you tell it not to." | Browsers, HTTP clients, databases |
| 6 | Message Queues (#15) | 2 · 5 · 5 | Receiver offline, but the message isn't lost | WhatsApp grey ticks as the hook object, post office as the explanation | "You texted a friend whose phone is off. One grey tick. So where is that message right now?" | RabbitMQ, Amazon SQS (don't claim WhatsApp internals) |
| 7 | Exponential Backoff (#13) | 2 · 3 · 4 | Server comes back and the retry stampede knocks it down | Shop reopening after a power cut: crowd jams the door vs people returning after 1, 2, 4 min | "Your server came back online, and every app in the world knocked it straight back out." | AWS: exponential backoff with jitter |
| 8 | Pub/Sub (#16) | 2 · 4 · 5 | One post must reach millions | Radio tower (or school announcement speaker) | "A creator posts once, and millions of phones buzz. Who sent all those notifications?" | Google Cloud Pub/Sub, Redis Pub/Sub |
| 9 | Canary Releases (#53, wildcard) | 4 · 4 · 4 | Shipping a bug to everyone at once | Food taster before the banquet | "You shipped a bug, and only a handful of users ever saw it." | Kubernetes rolling updates, Argo Rollouts (pays off CI/CD) |
| 10 | Event-Driven Architecture (#17) | 1 · 3 · 4 | Services keep asking "anything new?" | Doorbell vs checking the door every minute | "Your order shipped, and your email, tracking page and reward points all updated at once. Nobody asked them to." | Apache Kafka, AWS EventBridge (best after Queues + Pub/Sub) |

**Hooks stand alone:** each reel opens with its own hook. Don't tie a reel's opening to the previous reel's last line, and don't open with "last time".

**Made:** Service Discovery (10), Health Checks (11), Elevator Safety (12, a general-engineering one-off), Circuit Breakers (13; the first upload was deleted, re-cut 1 s shorter for a re-upload) Elevator Fail-Safe (14, a remake of 12 with a new world and script), Timeouts (15) and Retries (16, with Exponential Backoff and jitter folded in). 15 and 16 each have a vibe-coder ending variant too.

**Order from here:** take the topics in list order (no random picks). #18 Distributed Transactions is the first Three.js reel (our render(t) page with a real 3D world; the earlier Remotion version was dropped). A Feature Flags script + voice is parked in `videos/feature-flags-draft/`.

**Pick for next (25 Oct):** #37 Pessimistic Locking, then #38 Distributed Locks. #34 CAP Theorem, #35 Eventual Consistency and #36 Optimistic Locking are built (24 Oct), passed an Argon fact check on 25 Oct, and are scheduled as live posts.

## All 110

| # | Topic | Status | Hook angle | Analogy / objects |
|---|---|---|---|---|
| 1 | Rate Limiting | ✅ | Why an app says "too many requests" | Turnstile / bouncer |
| 2 | Caching | ✅ | Why the second load is instant | Sticky notes on the desk |
| 3 | Load Balancing | ✅ | How Netflix survives 10M people pressing Play | Supermarket lanes, router arm, server row |
| 4 | Reverse Proxies | ✅ | The bouncer in front of every big website | Hotel reception desk |
| 5 | API Gateways | ✅ | One front door for 100 services | Airport check-in counter |
| 6 | CI/CD | ✅ | How code ships 50 times a day without breaking | Factory assembly line with inspectors |
| 7 | Docker | ✅ | "Works on my machine" solved | Shipping containers |
| 8 | Kubernetes | ✅ | Who restarts your app when it crashes | Port crane managing containers |
| 9 | Service Discovery | ✅ | How services find each other | Building directory board |
| 10 | Circuit Breakers | ✅ | Why one broken service doesn't crash the app | Home fuse box tripping |
| 11 | Timeouts | ✅ | Why waiting forever is the worst option | Hanging up on hold music |
| 12 | Retries | ✅ | Why apps try again (and when they shouldn't) | Redialling a busy line |
| 13 | Exponential Backoff | ✅ | Why apps wait 1s, 2s, 4s, 8s | Knocking on a door, politely |
| 14 | Idempotency | ✅ | You tapped Pay twice — why one charge? | Coins, vault, key ID, elevator button |
| 15 | Message Queues | ✅ | How WhatsApp delivers when your friend's phone is off | Post office holding letters |
| 16 | Pub/Sub | ✅ | One post, a million followers notified | Radio broadcast tower |
| 17 | Event-Driven Architecture | ✅ | Services that react instead of ask | Doorbell vs checking the door |
| 18 | Distributed Transactions | ✅ | Booking flight + hotel: both or neither | Vault with two keys |
| 19 | Saga Pattern | ✅ | Undoing a multi-step order | Cancelling a trip step by step |
| 20 | Dead Letter Queues | ✅ | Where failed messages go | Lost-and-found box |
| 21 | Cron Jobs | ✅ | How apps run tasks at 3 AM | Wall of alarm clocks |
| 22 | WebSockets | ✅ | Live chat without refreshing | Open phone line vs letters |
| 23 | Long Polling | ✅ | The hack before real-time existed | "Are we there yet?" on repeat |
| 24 | Server-Sent Events | ✅ | How ChatGPT streams words to you | Typewriter / ticker tape |
| 25 | Database Indexing | ✅ | 1 row in a billion in milliseconds | Book index vs reading every page |
| 26 | Query Optimization | ✅ | Same answer, 1000× faster | Shortest route on a map |
| 27 | N+1 Queries | ✅ | Why your app makes 101 queries instead of 1 | 100 trips to the shop for 100 items |
| 28 | Connection Pooling | ✅ | Why apps don't open a new DB connection per request | Taxi rank vs calling a new cab |
| 29 | Read Replicas | ✅ | Why reads are cheap at scale | Many cashiers, one stock room |
| 30 | Sharding | ✅ | When one database isn't enough | Library split A–M / N–Z buildings |
| 31 | Partitioning | ✅ | How tables stay fast after years | Monthly folders in a filing cabinet |
| 32 | Replication | ✅ | Why your data survives a dead server | Photocopies in different safes |
| 33 | Leader Election | ✅ | What happens when the boss server dies | Class picking a new monitor |
| 34 | CAP Theorem | ✅ | You can't have all three | Two bank branches, phone line cut |
| 35 | Eventual Consistency | ✅ | Why your like count jumps around | Gossip spreading through a town |
| 36 | Optimistic Locking | ✅ | Edit freely, check at save time | Google Docs version check |
| 37 | Pessimistic Locking | 🎬 | Lock it before anyone else touches it | Library book checked out |
| 38 | Distributed Locks | 🎬 | Only one worker runs the job | Talking stick |
| 39 | Race Conditions | 🎬 | Two people book the last seat | Two hands grabbing one ticket |
| 40 | Deadlocks | | Two processes waiting on each other forever | Two cars at a narrow bridge |
| 41 | Memory Leaks | | Why your app slows down over days | Tap left running into a sink |
| 42 | Garbage Collection | | Who cleans up your app's memory | Cleaning crew sweeping the room |
| 43 | Thread Safety | | Why two threads corrupt one counter | Two people writing on one whiteboard |
| 44 | Backpressure | | Telling a fast sender to slow down | Water hose into a full bucket |
| 45 | Autoscaling | | Surviving a Black Friday spike | Restaurant calling in extra chefs |
| 46 | Horizontal Scaling | | More machines, not bigger ones | Fleet of vans |
| 47 | Vertical Scaling | | Just buy a bigger server? | One giant truck |
| 48 | CDN | | Why YouTube loads instantly in every country | Local warehouses vs one factory |
| 49 | Edge Caching | | Your request never reaches the real server | Vending machine on every corner |
| 50 | Cache Invalidation | | The hardest problem in CS | Stale menu board |
| 51 | Feature Flags | 📝 | Shipping code that's switched off | Light switches per room |
| 52 | Blue-Green Deployment | | Updating with zero downtime | Two stages, swap the spotlight |
| 53 | Canary Releases | ✅ | Test on 1% before everyone | Canary in a coal mine |
| 54 | Rolling Deployments | | Replace servers one at a time | Changing a train's carriages while it runs |
| 55 | Rollbacks | | The undo button for production | Time machine / rewind |
| 56 | Health Checks | ✅ | How a system knows a server died | ECG monitor |
| 57 | Liveness & Readiness Probes | ✅ | Alive isn't the same as ready | Restaurant open vs kitchen ready |
| 58 | Monitoring | | How engineers know before you do | Car dashboard |
| 59 | Logging | | The diary every server keeps | Ship's logbook |
| 60 | Distributed Tracing | | Following one request through 20 services | Parcel tracking |
| 61 | Metrics | | Numbers that tell you something's wrong | Fitness tracker |
| 62 | Alerts | | Why engineers get paged at 3 AM | Smoke alarm |
| 63 | SLOs | | "99.9% uptime" actually means… | Train punctuality target |
| 64 | SLIs | | What you actually measure | Speedometer reading |
| 65 | Error Budgets | | Permission to fail, on purpose | Monthly spending allowance |
| 66 | Observability | | Asking questions you didn't plan for | Black box flight recorder |
| 67 | Secrets Management | | Where API keys should live | Bank vault vs sticky note |
| 68 | IAM | | Who's allowed to do what | Hotel key cards per floor |
| 69 | OAuth | | "Sign in with Google" without sharing your password | Valet key |
| 70 | JWT Rotation | | Why tokens expire and refresh | Wristband that changes colour daily |
| 71 | TLS | | How the padlock works | Locked box and key exchange |
| 72 | Encryption at Rest | | Stolen hard drive, unreadable data | Safe in a vault |
| 73 | Encryption in Transit | | Nobody can read it on the way | Armoured truck |
| 74 | WAF | | Firewall that reads every request | Airport security scanner |
| 75 | DDoS Protection | | Surviving a flood of fake traffic | Crowd control barriers |
| 76 | CORS | | That annoying browser error, explained | Building security checking IDs |
| 77 | CSRF | | A site tricks your browser into acting for you | Forged signature on a cheque |
| 78 | SQL Injection | | One quote mark that deletes a database | Form field that rewrites the order |
| 79 | SSRF | | Tricking a server into calling inside its own network | Receptionist fooled into opening the back office |
| 80 | Database Migrations | | Changing a database while it's live | Renovating a shop while it's open |
| 81 | Schema Versioning | | Old app, new database, still works | Edition numbers on a manual |
| 82 | Disaster Recovery | | What happens if a whole data center burns down | Fire drill + backup building |
| 83 | Backups | | The only thing between you and losing everything | Spare keys in a safe |
| 84 | Failover | | Switching to the backup in seconds | Backup generator kicking in |
| 85 | Multi-Region Deployment | | Same app, running on 3 continents | Franchise branches worldwide |
| 86 | Chaos Engineering | | Netflix breaks its own servers on purpose | Fire drill with real smoke |
| 87 | Cost Optimization | | Why the cloud bill was $40,000 | Lights left on in an empty office |
| 88 | Cold Starts | | Why the first request is slow | Car engine on a winter morning |
| 89 | Serverless Limits | | What "serverless" can't do | Rented room with a checkout time |
| 90 | Latency | | Why 100 ms feels slow | Echo across a canyon |
| 91 | Throughput | | How much, not how fast | Highway lanes |
| 92 | P99 Latency | | Why averages lie | Slowest person in the checkout queue |
| 93 | Tail Latency | | One slow server ruins everything | Waiting for the last friend to arrive |
| 94 | Network Partitions | | When servers can't talk but are still alive | Bridge collapses between two towns |
| 95 | Clock Skew | | Why servers can't trust their own clocks | Two watches showing different times |
| 96 | DNS | | What happens when you type google.com | Phone contacts / phone book |
| 97 | TCP vs UDP | | Reliable vs fast | Registered post vs shouting |
| 98 | HTTP/2 & HTTP/3 | | Why the web got faster | Single lane → multi-lane highway |
| 99 | gRPC | | How services talk super fast | Speed dial |
| 100 | Webhooks | | How Stripe tells your app "paid" | Callback phone number |
| 101 | API Versioning | | Changing an API without breaking apps | Plug adapters |
| 102 | Semantic Versioning | | What 2.4.1 actually means | Book edition / reprint / typo fix |
| 103 | Infrastructure as Code | | Servers built from a recipe | Recipe card vs cooking from memory |
| 104 | Terraform | | One file creates your whole cloud | Architect's blueprint |
| 105 | Helm Charts | | App installer for Kubernetes | Flat-pack furniture kit |
| 106 | Build Caching | | Why rebuilds take 5s instead of 5 min | Pre-chopped ingredients |
| 107 | Dependency Hell | | Why installing one package breaks three | Tangled extension cords |
| 108 | Production Incidents | | What happens when a big app goes down | Fire station alarm |
| 109 | On-Call | | The engineer who wakes up at 3 AM | Doctor on call with a pager |
| 110 | Postmortems | | Learning from outages without blame | Flight crash investigation |
