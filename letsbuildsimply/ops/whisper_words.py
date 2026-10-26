"""whisper_words.py <in.wav>... : faster-whisper large-v3 word timestamps -> <in>.words.json"""
import json, sys
from faster_whisper import WhisperModel
m = WhisperModel("large-v3", device="cuda", compute_type="float16")
for f in sys.argv[1:]:
    segs, _ = m.transcribe(f, language="en", word_timestamps=True, beam_size=5, vad_filter=False)
    words = [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3), "p": round(w.probability, 3)} for s in segs for w in s.words]
    json.dump(words, open(f.rsplit('.', 1)[0] + '.words.json', 'w'))
    print(f, len(words), ' '.join(x['w'] for x in words))
