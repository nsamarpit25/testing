window.TIMINGS=[
 {
  "li": 0,
  "pi": 0,
  "say": "The weather server hiccups for one second.",
  "show": "The weather server *hiccups* for one second.",
  "start": 0.0,
  "end": 2.08
 },
 {
  "li": 0,
  "pi": 1,
  "say": "Every app hits retry at the same moment.",
  "show": "Every app hits *retry* at the same moment.",
  "start": 2.4,
  "end": 4.52
 },
 {
  "li": 0,
  "pi": 2,
  "say": "And now it's down for real.",
  "show": "And now it's [down for real.]",
  "start": 4.52,
  "end": 6.36
 },
 {
  "li": 1,
  "pi": 0,
  "say": "Retrying is smart. Most failures are brief: a network blip, a server restarting.",
  "show": "Retrying is *smart.* Most failures are *brief:* a network blip, a server restarting.",
  "start": 7.36,
  "end": 12.3
 },
 {
  "li": 1,
  "pi": 1,
  "say": "Try again, and it often just works.",
  "show": "Try again, and it often just *works.*",
  "start": 12.6,
  "end": 14.3
 },
 {
  "li": 2,
  "pi": 0,
  "say": "But retry instantly, again and again, and each failure turns into more calls.",
  "show": "But retry *instantly,* again and again, and each failure turns into *more calls.*",
  "start": 14.66,
  "end": 19.2
 },
 {
  "li": 2,
  "pi": 1,
  "say": "That's a retry storm.",
  "show": "That's a [retry storm.]",
  "start": 19.48,
  "end": 20.78
 },
 {
  "li": 3,
  "pi": 0,
  "say": "Fix one: cap it. Three attempts, then stop and show an error.",
  "show": "Fix one: [cap it.] *3 attempts,* then stop and show an error.",
  "start": 21.66,
  "end": 25.04
 },
 {
  "li": 4,
  "pi": 0,
  "say": "Fix two: back off. Wait one second, then two, then four.",
  "show": "Fix two: [back off.] Wait *1 second,* then *2,* then *4.*",
  "start": 25.62,
  "end": 29.14
 },
 {
  "li": 4,
  "pi": 1,
  "say": "Each wait gives the server more room to recover.",
  "show": "Each wait gives the server more room to *recover.*",
  "start": 29.14,
  "end": 31.82
 },
 {
  "li": 5,
  "pi": 0,
  "say": "But if every app waits exactly one second, they all come back together.",
  "show": "But if every app waits *exactly* one second, they all come back *together.*",
  "start": 32.48,
  "end": 36.38
 },
 {
  "li": 5,
  "pi": 1,
  "say": "Fix three: jitter. Add a little randomness, and the crowd spreads out.",
  "show": "Fix three: [jitter.] Add a little *randomness,* and the crowd *spreads out.*",
  "start": 37.0,
  "end": 40.76
 },
 {
  "li": 6,
  "pi": 0,
  "say": "Only retry what might fix itself, like a timeout or a five-oh-three. Not a four-oh-four.",
  "show": "Only retry what might fix itself, like a *timeout* or a *503.* Not a *404.*",
  "start": 41.46,
  "end": 47.2
 },
 {
  "li": 6,
  "pi": 1,
  "say": "And retrying a payment can charge twice, unless it's idempotent.",
  "show": "And retrying a payment can *charge twice,* unless it's *idempotent.*",
  "start": 47.78,
  "end": 52.12
 },
 {
  "li": 7,
  "pi": 0,
  "say": "AWS SDKs already retry with backoff by default.",
  "show": "*AWS* SDKs already retry with *backoff* by default.",
  "start": 53.66,
  "end": 56.94
 },
 {
  "li": 8,
  "pi": 0,
  "say": "Haven't seen idempotency? That reel's on my profile.",
  "show": "Haven't seen *idempotency?* That reel's on my profile.",
  "start": 57.5,
  "end": 59.96
 },
 {
  "li": 8,
  "pi": 1,
  "say": "Follow for the rest of the series.",
  "show": "[Follow] for the rest of the series.",
  "start": 60.38,
  "end": 61.58
 }
];
window.WORDS=[[" The", 0.0, 0.34], [" weather", 0.34, 0.58], [" server", 0.58, 0.94], [" hiccups", 0.94, 1.32], [" for", 1.32, 1.56], [" one", 1.56, 1.78], [" second.", 1.78, 2.08], [" Every", 2.4, 2.58], [" app", 2.58, 2.82], [" hits", 2.82, 3.12], [" retry", 3.12, 3.62], [" at", 3.62, 3.84], [" the", 3.84, 3.96], [" same", 3.96, 4.16], [" moment,", 4.16, 4.52], [" and", 4.52, 4.88], [" now", 4.88, 5.12], [" it's", 5.12, 5.52], [" down", 5.52, 5.74], [" for", 5.74, 6.0], [" real.", 6.0, 6.36], [" Retrying", 7.36, 7.76], [" is", 7.76, 8.04], [" smart.", 8.04, 8.5], [" Most", 8.92, 9.12], [" failures", 9.12, 9.42], [" are", 9.42, 9.62], [" brief.", 9.62, 9.9], [" A", 10.3, 10.42], [" network", 10.42, 10.7], [" blip,", 10.7, 10.96], [" a", 11.24, 11.36], [" server", 11.36, 11.64], [" restarting,", 11.64, 12.3], [" try", 12.6, 12.7], [" again,", 12.7, 13.0], [" and", 13.14, 13.26], [" it", 13.26, 13.4], [" often", 13.4, 13.64], [" just", 13.64, 13.9], [" works.", 13.9, 14.3], [" But", 14.66, 14.82], [" retry", 14.82, 15.16], [" instantly,", 15.16, 15.78], [" again", 15.96, 16.26], [" and", 16.26, 16.44], [" again,", 16.44, 16.84], [" and", 16.9, 17.32], [" each", 17.32, 17.5], [" failure", 17.5, 17.86], [" turns", 17.86, 18.2], [" into", 18.2, 18.46], [" more", 18.46, 18.76], [" calls.", 18.76, 19.2], [" That's", 19.48, 19.88], [" a", 19.88, 20.06], [" retry", 20.06, 20.44], [" storm.", 20.44, 20.78], [" Fix", 21.66, 21.76], [" one,", 21.76, 22.06], [" cap", 22.6, 22.7], [" it.", 22.7, 22.94], [" Three", 23.2, 23.42], [" attempts,", 23.42, 23.78], [" then", 23.94, 24.06], [" stop", 24.06, 24.34], [" and", 24.34, 24.54], [" show", 24.54, 24.7], [" an", 24.7, 24.84], [" error.", 24.84, 25.04], [" Fix", 25.62, 25.82], [" two,", 25.82, 26.08], [" back", 26.34, 26.5], [" off.", 26.5, 26.78], [" Wait", 27.24, 27.4], [" one", 27.4, 27.64], [" second,", 27.64, 27.92], [" then", 28.06, 28.18], [" two,", 28.18, 28.46], [" then", 28.72, 28.86], [" four.", 28.86, 29.14], [" Each", 29.14, 29.66], [" wait", 29.66, 29.92], [" gives", 29.92, 30.26], [" the", 30.26, 30.46], [" server", 30.46, 30.72], [" more", 30.72, 31.02], [" room", 31.02, 31.26], [" to", 31.26, 31.46], [" recover.", 31.46, 31.82], [" But", 32.48, 32.62], [" if", 32.62, 32.74], [" every", 32.74, 33.02], [" app", 33.02, 33.26], [" waits", 33.26, 33.6], [" exactly", 33.6, 34.18], [" one", 34.18, 34.44], [" second,", 34.44, 34.78], [" they", 35.0, 35.12], [" all", 35.12, 35.28], [" come", 35.28, 35.52], [" back", 35.52, 35.82], [" together.", 35.82, 36.38], [" Fix", 37.0, 37.12], [" three,", 37.12, 37.44], [" jitter.", 37.82, 38.04], [" Add", 38.42, 38.62], [" a", 38.62, 38.72], [" little", 38.72, 38.94], [" randomness,", 38.94, 39.5], [" and", 39.58, 39.72], [" the", 39.72, 39.86], [" crowd", 39.86, 40.08], [" spreads", 40.08, 40.44], [" out.", 40.44, 40.76], [" Only", 41.46, 41.74], [" retry", 41.74, 42.24], [" what", 42.24, 42.52], [" might", 42.52, 42.98], [" fix", 42.98, 43.36], [" itself,", 43.36, 43.82], [" like", 43.82, 44.34], [" a", 44.34, 44.52], [" timeout", 44.52, 44.76], [" or", 44.76, 45.08], [" a", 45.08, 45.28], [" 503,", 45.28, 45.68], [" not", 46.04, 46.38], [" a", 46.38, 46.66], [" 404.", 46.66, 47.2], [" And", 47.78, 48.04], [" retrying", 48.04, 48.54], [" a", 48.54, 48.72], [" payment", 48.72, 49.0], [" can", 49.0, 49.32], [" charge", 49.32, 49.76], [" twice,", 49.76, 50.28], [" unless", 50.58, 51.06], [" it's", 51.06, 51.64], [" idempotent.", 51.64, 52.12], [" AWS", 53.66, 54.12], [" SDK", 54.12, 54.62], [" is", 54.62, 54.88], [" already", 54.88, 55.28], [" retry", 55.28, 55.72], [" with", 55.72, 55.9], [" back", 55.9, 56.14], [" off", 56.14, 56.36], [" by", 56.36, 56.58], [" default.", 56.58, 56.94], [" Haven't", 57.5, 57.72], [" seen", 57.72, 57.9], [" idempotency?", 57.9, 58.52], [" That", 58.52, 59.0], [" reel's", 59.0, 59.32], [" on", 59.32, 59.4], [" my", 59.4, 59.56], [" profile.", 59.56, 59.96], [" Follow", 60.38, 60.6], [" for", 60.6, 60.76], [" the", 60.76, 60.92], [" rest", 60.92, 61.08], [" of", 61.08, 61.22], [" the", 61.22, 61.34], [" series.", 61.34, 61.58]];
