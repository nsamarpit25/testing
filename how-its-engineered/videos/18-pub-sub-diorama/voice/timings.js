window.TIMINGS=[
 {
  "li": 0,
  "pi": 0,
  "say": "Your checkout froze for eight seconds.",
  "show": "Your *checkout* froze for [8 seconds.]",
  "start": 0.0,
  "end": 2.22
 },
 {
  "li": 0,
  "pi": 1,
  "say": "Not on the payment.",
  "show": "Not on the *payment.*",
  "start": 2.56,
  "end": 3.28
 },
 {
  "li": 0,
  "pi": 2,
  "say": "On the receipt email.",
  "show": "On the *receipt email.*",
  "start": 3.44,
  "end": 4.58
 },
 {
  "li": 1,
  "pi": 0,
  "say": "After every order, checkout calls email, then the warehouse, then rewards. One by one.",
  "show": "After every order, checkout calls *email,* then the *warehouse,* then *rewards.* [One by one.]",
  "start": 5.3,
  "end": 11.08
 },
 {
  "li": 1,
  "pi": 1,
  "say": "Email slow? Checkout waits.",
  "show": "Email *slow?* Checkout [waits.]",
  "start": 11.62,
  "end": 13.38
 },
 {
  "li": 1,
  "pi": 2,
  "say": "Email down? The order fails.",
  "show": "Email *down?* The order [fails.]",
  "start": 13.84,
  "end": 15.64
 },
 {
  "li": 2,
  "pi": 0,
  "say": "The fix? Don't call them. Announce it.",
  "show": "The fix? Don't *call* them. [Announce it.]",
  "start": 16.44,
  "end": 19.1
 },
 {
  "li": 2,
  "pi": 1,
  "say": "That's pub sub.",
  "show": "That's [Pub/Sub.]",
  "start": 19.6,
  "end": 20.48
 },
 {
  "li": 3,
  "pi": 0,
  "say": "Like subscribing to a channel: the creator uploads once, and every subscriber gets it.",
  "show": "Like *subscribing* to a channel: the creator uploads [once,] and *every subscriber* gets it.",
  "start": 21.24,
  "end": 26.28
 },
 {
  "li": 4,
  "pi": 0,
  "say": "Step one: publish.",
  "show": "Step one: [publish.]",
  "start": 26.28,
  "end": 27.96
 },
 {
  "li": 4,
  "pi": 1,
  "say": "Checkout sends one message, order placed, to a topic. And it's done.",
  "show": "Checkout sends *one message,* order placed, to a *topic.* And it's [done.]",
  "start": 28.8,
  "end": 32.9
 },
 {
  "li": 5,
  "pi": 0,
  "say": "Step two: subscribe.",
  "show": "Step two: [subscribe.]",
  "start": 33.82,
  "end": 35.1
 },
 {
  "li": 5,
  "pi": 1,
  "say": "Email, warehouse and rewards each subscribe to that topic.",
  "show": "*Email,* *warehouse* and *rewards* each subscribe to that *topic.*",
  "start": 36.0,
  "end": 39.22
 },
 {
  "li": 6,
  "pi": 0,
  "say": "Step three: deliver.",
  "show": "Step three: [deliver.]",
  "start": 39.86,
  "end": 41.1
 },
 {
  "li": 6,
  "pi": 1,
  "say": "Each one gets its own copy.",
  "show": "Each one gets its *own copy.*",
  "start": 41.88,
  "end": 43.5
 },
 {
  "li": 6,
  "pi": 2,
  "say": "Email slow? Only email waits.",
  "show": "Email slow? [Only email] waits.",
  "start": 44.08,
  "end": 46.32
 },
 {
  "li": 7,
  "pi": 0,
  "say": "Need text messages too? Add a subscriber.",
  "show": "Need *text messages* too? [Add a subscriber.]",
  "start": 47.14,
  "end": 49.66
 },
 {
  "li": 7,
  "pi": 1,
  "say": "Checkout never changes. It doesn't even know who's listening.",
  "show": "Checkout *never changes.* It doesn't even know [who's listening.]",
  "start": 50.38,
  "end": 53.4
 },
 {
  "li": 8,
  "pi": 0,
  "say": "So that frozen checkout? Done the moment the order is saved.",
  "show": "So that *frozen checkout?* Done the moment the order is [saved.]",
  "start": 54.24,
  "end": 57.44
 },
 {
  "li": 9,
  "pi": 0,
  "say": "Google Cloud Pub Sub and Kafka both work like this.",
  "show": "*Google Cloud Pub/Sub* and *Kafka* both work like this.",
  "start": 58.2,
  "end": 61.02
 },
 {
  "li": 10,
  "pi": 0,
  "say": "Seen one slow service take down a whole app? That reel's on my profile.",
  "show": "Seen one slow service take down a *whole app?* That reel's on my profile.",
  "start": 61.66,
  "end": 65.16
 },
 {
  "li": 10,
  "pi": 1,
  "say": "Follow for the rest of the series.",
  "show": "[Follow] for the rest of the series.",
  "start": 65.6,
  "end": 66.86
 }
];
window.WORDS=[[" Your", 0.0, 0.38], [" checkout", 0.38, 0.78], [" froze", 0.78, 1.14], [" for", 1.14, 1.38], [" 8", 1.38, 1.74], [" seconds.", 1.74, 2.22], [" Not", 2.56, 2.74], [" on", 2.74, 2.88], [" the", 2.88, 3.02], [" payment,", 3.02, 3.28], [" on", 3.44, 3.72], [" the", 3.72, 3.84], [" receipt", 3.84, 4.2], [" email.", 4.2, 4.58], [" After", 5.3, 5.56], [" every", 5.56, 6.04], [" order,", 6.04, 6.38], [" checkout", 6.72, 6.88], [" calls", 6.88, 7.2], [" email,", 7.2, 7.66], [" then", 7.98, 8.2], [" the", 8.2, 8.36], [" warehouse,", 8.36, 8.66], [" then", 9.12, 9.32], [" rewards.", 9.32, 9.76], [" One", 10.36, 10.5], [" by", 10.5, 10.64], [" one.", 10.64, 11.08], [" Email", 11.62, 11.84], [" slow,", 11.84, 12.28], [" checkout", 12.68, 12.92], [" waits.", 12.92, 13.38], [" Email", 13.84, 14.04], [" down,", 14.04, 14.5], [" the", 14.82, 14.98], [" order", 14.98, 15.22], [" fails.", 15.22, 15.64], [" The", 16.44, 16.56], [" fix?", 16.56, 16.82], [" Don't", 17.3, 17.64], [" call", 17.64, 17.86], [" them,", 17.86, 18.1], [" announce", 18.44, 18.72], [" it.", 18.72, 19.1], [" That's", 19.6, 20.06], [" PubSop.", 20.06, 20.48], [" Like", 21.24, 21.46], [" subscribing", 21.46, 21.94], [" to", 21.94, 22.16], [" a", 22.16, 22.34], [" channel,", 22.34, 22.56], [" the", 22.94, 23.16], [" creator", 23.16, 23.42], [" uploads", 23.42, 23.98], [" once", 23.98, 24.26], [" and", 24.26, 24.58], [" every", 24.58, 25.06], [" subscriber", 25.06, 25.58], [" gets", 25.58, 25.88], [" it.", 25.88, 26.28], [" Step", 26.28, 26.84], [" one,", 26.84, 27.18], [" publish.", 27.66, 27.96], [" Checkout", 28.8, 28.94], [" sends", 28.94, 29.18], [" one", 29.18, 29.52], [" message,", 29.52, 29.94], [" order", 30.34, 30.46], [" placed,", 30.46, 30.94], [" to", 30.98, 31.4], [" a", 31.4, 31.58], [" topic.", 31.58, 31.92], [" And", 32.34, 32.46], [" it's", 32.46, 32.68], [" done.", 32.68, 32.9], [" Step", 33.82, 33.98], [" two,", 33.98, 34.4], [" subscribe.", 34.74, 35.1], [" Email,", 36.0, 36.26], [" warehouse,", 36.52, 36.76], [" and", 37.02, 37.12], [" rewards", 37.12, 37.5], [" each", 37.5, 38.0], [" subscribe", 38.0, 38.46], [" to", 38.46, 38.68], [" that", 38.68, 38.82], [" topic.", 38.82, 39.22], [" Step", 39.86, 40.0], [" three,", 40.0, 40.34], [" deliver.", 40.8, 41.1], [" Each", 41.88, 42.04], [" one", 42.04, 42.28], [" gets", 42.28, 42.5], [" its", 42.5, 42.68], [" own", 42.68, 43.04], [" copy.", 43.04, 43.5], [" Email", 44.08, 44.3], [" slow,", 44.3, 44.7], [" only", 45.2, 45.5], [" email", 45.5, 45.92], [" waits.", 45.92, 46.32], [" Need", 47.14, 47.32], [" text", 47.32, 47.66], [" messages", 47.66, 48.0], [" too?", 48.0, 48.38], [" Add", 48.8, 49.1], [" a", 49.1, 49.24], [" subscriber.", 49.24, 49.66], [" Checkout", 50.38, 50.8], [" never", 50.8, 51.2], [" changes.", 51.2, 51.7], [" It", 52.06, 52.2], [" doesn't", 52.2, 52.38], [" even", 52.38, 52.56], [" know", 52.56, 52.78], [" who's", 52.78, 53.06], [" listening.", 53.06, 53.4], [" So", 54.24, 54.32], [" that", 54.32, 54.48], [" frozen", 54.48, 54.8], [" checkout?", 54.8, 55.2], [" Done", 55.76, 55.9], [" the", 55.9, 56.1], [" moment", 56.1, 56.42], [" the", 56.42, 56.7], [" order", 56.7, 56.88], [" is", 56.88, 57.06], [" saved.", 57.06, 57.44], [" Google", 58.2, 58.38], [" Cloud", 58.38, 58.66], [" PubSub", 58.66, 59.16], [" and", 59.16, 59.4], [" Kafka", 59.4, 59.76], [" both", 59.76, 60.12], [" work", 60.12, 60.42], [" like", 60.42, 60.58], [" this.", 60.58, 61.02], [" Seen", 61.66, 61.78], [" one", 61.78, 61.98], [" slow", 61.98, 62.18], [" service", 62.18, 62.52], [" tick", 62.52, 62.7], [" down", 62.7, 62.86], [" a", 62.86, 62.98], [" whole", 62.98, 63.08], [" app?", 63.08, 63.4], [" That", 63.9, 64.1], [" reel's", 64.1, 64.44], [" on", 64.44, 64.58], [" my", 64.58, 64.76], [" profile.", 64.76, 65.16], [" Follow", 65.6, 65.78], [" for", 65.78, 65.98], [" the", 65.98, 66.16], [" rest", 66.16, 66.32], [" of", 66.32, 66.5], [" the", 66.5, 66.6], [" series.", 66.6, 66.86]];
