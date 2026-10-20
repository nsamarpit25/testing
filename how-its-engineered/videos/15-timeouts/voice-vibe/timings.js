window.TIMINGS=[
 {
  "li": 0,
  "pi": 0,
  "say": "This little capsule is your app asking a server for the weather.",
  "show": "This little capsule is your app asking a server for the *weather.*",
  "start": 0.0,
  "end": 3.3
 },
 {
  "li": 0,
  "pi": 1,
  "say": "It leaves. And nothing comes back.",
  "show": "It leaves. And [nothing comes back.]",
  "start": 3.66,
  "end": 5.56
 },
 {
  "li": 0,
  "pi": 2,
  "say": "So how long should your app keep waiting?",
  "show": "So how long should your app keep *waiting?*",
  "start": 5.98,
  "end": 7.86
 },
 {
  "li": 1,
  "pi": 0,
  "say": "By default, it might wait forever.",
  "show": "By default, it might wait [forever.]",
  "start": 8.52,
  "end": 10.3
 },
 {
  "li": 1,
  "pi": 1,
  "say": "Python's requests library won't time out unless you pass a timeout.",
  "show": "Python's *requests* library won't time out unless you pass a *timeout.*",
  "start": 10.88,
  "end": 14.06
 },
 {
  "li": 1,
  "pi": 2,
  "say": "And Go's default client? Same story.",
  "show": "And *Go's* default client? Same story.",
  "start": 14.46,
  "end": 16.6
 },
 {
  "li": 2,
  "pi": 0,
  "say": "And waiting isn't free.",
  "show": "And waiting [isn't free.]",
  "start": 17.18,
  "end": 18.32
 },
 {
  "li": 2,
  "pi": 1,
  "say": "That call holds a thread while the spinner spins, and every request stuck behind it holds another.",
  "show": "That call holds a *thread* while the spinner spins, and every request stuck behind it holds *another.*",
  "start": 18.78,
  "end": 23.84
 },
 {
  "li": 3,
  "pi": 0,
  "say": "A timeout is a deadline: the longest you'll wait before calling it a failure.",
  "show": "A [timeout] is a *deadline:* the longest you'll wait before calling it a *failure.*",
  "start": 24.56,
  "end": 28.3
 },
 {
  "li": 4,
  "pi": 0,
  "say": "Pass timeout equals three, and after three seconds, you stop waiting.",
  "show": "Pass *timeout=3,* and after *3 seconds,* you stop waiting.",
  "start": 28.3,
  "end": 32.4
 },
 {
  "li": 5,
  "pi": 0,
  "say": "Now the slow call is a failure your code can handle.",
  "show": "Now the slow call is a failure your code can [handle.]",
  "start": 33.18,
  "end": 35.78
 },
 {
  "li": 5,
  "pi": 1,
  "say": "Show a clear error, or use a fallback, like the forecast you saved earlier.",
  "show": "Show a clear *error,* or use a *fallback,* like the forecast you saved earlier.",
  "start": 36.2,
  "end": 39.8
 },
 {
  "li": 6,
  "pi": 0,
  "say": "The spinner stops. The thread is freed. Your user knows what happened.",
  "show": "The spinner *stops.* The thread is *freed.* Your user knows what happened.",
  "start": 40.34,
  "end": 44.0
 },
 {
  "li": 7,
  "pi": 0,
  "say": "Haven't seen circuit breakers? That reel's on my profile.",
  "show": "Haven't seen *circuit breakers?* That reel's on my profile.",
  "start": 44.8,
  "end": 47.48
 },
 {
  "li": 7,
  "pi": 1,
  "say": "If you're a vibe coder, follow for the system design your AI skipped.",
  "show": "If you're a *vibe coder,* [follow] for the system design your AI *skipped.*",
  "start": 47.94,
  "end": 50.96
 }
];
window.WORDS=[[" This", 0.0, 0.52], [" little", 0.52, 0.76], [" capsule", 0.76, 1.2], [" is", 1.2, 1.46], [" your", 1.46, 1.6], [" app", 1.6, 1.92], [" asking", 1.92, 2.32], [" a", 2.32, 2.5], [" server", 2.5, 2.74], [" for", 2.74, 2.94], [" the", 2.94, 3.1], [" weather.", 3.1, 3.3], [" It", 3.66, 3.8], [" leaves,", 3.8, 4.16], [" and", 4.44, 4.64], [" nothing", 4.64, 4.9], [" comes", 4.9, 5.18], [" back.", 5.18, 5.56], [" So", 5.98, 6.18], [" how", 6.18, 6.42], [" long", 6.42, 6.66], [" should", 6.66, 6.88], [" your", 6.88, 7.04], [" app", 7.04, 7.24], [" keep", 7.24, 7.54], [" waiting?", 7.54, 7.86], [" By", 8.52, 8.66], [" default,", 8.66, 9.12], [" it", 9.4, 9.5], [" might", 9.5, 9.72], [" wait", 9.72, 9.92], [" forever.", 9.92, 10.3], [" Python's", 10.88, 11.32], [" request", 11.32, 11.52], [" library", 11.52, 11.98], [" won't", 11.98, 12.4], [" timeout", 12.4, 12.66], [" unless", 12.66, 13.14], [" you", 13.14, 13.34], [" pass", 13.34, 13.54], [" a", 13.54, 13.76], [" timeout,", 13.76, 14.06], [" and", 14.46, 14.74], [" Go's", 14.74, 15.04], [" default", 15.04, 15.3], [" client?", 15.3, 15.64], [" Same", 16.06, 16.2], [" story.", 16.2, 16.6], [" And", 17.18, 17.34], [" waiting", 17.34, 17.6], [" isn't", 17.6, 18.0], [" free.", 18.0, 18.32], [" That", 18.78, 19.0], [" call", 19.0, 19.28], [" holds", 19.28, 19.58], [" a", 19.58, 19.74], [" thread", 19.74, 19.96], [" while", 19.96, 20.26], [" the", 20.26, 20.42], [" spinner", 20.42, 20.66], [" spins,", 20.66, 21.14], [" and", 21.22, 21.68], [" every", 21.68, 22.0], [" request", 22.0, 22.38], [" stuck", 22.38, 22.62], [" behind", 22.62, 22.98], [" it", 22.98, 23.2], [" holds", 23.2, 23.46], [" another.", 23.46, 23.84], [" A", 24.56, 24.8], [" timeout", 24.8, 25.04], [" is", 25.04, 25.28], [" a", 25.28, 25.5], [" deadline,", 25.5, 25.84], [" the", 26.04, 26.3], [" longest", 26.3, 26.6], [" you'll", 26.6, 26.88], [" wait", 26.88, 27.04], [" before", 27.04, 27.28], [" calling", 27.28, 27.62], [" it", 27.62, 27.82], [" a", 27.82, 27.98], [" failure.", 27.98, 28.3], [" Pass", 28.3, 29.22], [" timeout", 29.22, 29.58], [" equals", 29.58, 29.96], [" three,", 29.96, 30.32], [" and", 30.58, 30.68], [" after", 30.68, 30.88], [" three", 30.88, 31.18], [" seconds,", 31.18, 31.58], [" you", 31.7, 31.78], [" stop", 31.78, 32.06], [" waiting.", 32.06, 32.4], [" Now", 33.18, 33.28], [" the", 33.28, 33.5], [" slow", 33.5, 33.68], [" call", 33.68, 33.92], [" is", 33.92, 34.14], [" a", 34.14, 34.28], [" failure", 34.28, 34.6], [" your", 34.6, 34.94], [" code", 34.94, 35.18], [" can", 35.18, 35.38], [" handle.", 35.38, 35.78], [" Show", 36.2, 36.34], [" a", 36.34, 36.52], [" clear", 36.52, 36.66], [" error,", 36.66, 37.02], [" or", 37.26, 37.44], [" use", 37.44, 37.66], [" a", 37.66, 37.8], [" fallback,", 37.8, 38.22], [" like", 38.34, 38.5], [" the", 38.5, 38.7], [" forecast", 38.7, 39.0], [" you", 39.0, 39.2], [" saved", 39.2, 39.42], [" earlier.", 39.42, 39.8], [" The", 40.34, 40.46], [" spinner", 40.46, 40.68], [" stops,", 40.68, 41.12], [" the", 41.46, 41.6], [" thread", 41.6, 41.78], [" is", 41.78, 41.96], [" freed,", 41.96, 42.24], [" your", 42.6, 42.74], [" user", 42.74, 43.06], [" knows", 43.06, 43.34], [" what", 43.34, 43.54], [" happened.", 43.54, 44.0], [" Haven't", 44.8, 45.04], [" seen", 45.04, 45.2], [" circuit", 45.2, 45.5], [" breakers?", 45.5, 45.92], [" That", 46.28, 46.52], [" reel's", 46.52, 46.84], [" on", 46.84, 46.92], [" my", 46.92, 47.08], [" profile.", 47.08, 47.48], [" If", 47.94, 48.04], [" you're", 48.04, 48.22], [" a", 48.22, 48.36], [" vibe", 48.36, 48.5], [" coder,", 48.5, 48.8], [" follow", 49.12, 49.26], [" for", 49.26, 49.44], [" the", 49.44, 49.58], [" system", 49.58, 49.84], [" design", 49.84, 50.2], [" your", 50.2, 50.38], [" AI", 50.38, 50.62], [" skipped.", 50.62, 50.96]];
