# One-take Gemini TTS voiceover + Whisper-aligned phrase timings.
# usage: .venv-fish/bin/python voice/gemini_tts.py <script.json> <outdir> [--voice Puck] [--reuse] [--vertex]
# needs GEMINI_API_KEY in env (WHISPER_PY optionally points at a python with faster_whisper). Writes raw.wav, timings.json (li, pi, say, show, start, end), voice.wav.
import base64, difflib, json, os, re, subprocess, sys
from pathlib import Path

args = sys.argv[1:]
script, out = Path(args[0]), Path(args[1])
voice = args[args.index('--voice') + 1] if '--voice' in args else 'Puck'
reuse = '--reuse' in args
out.mkdir(parents=True, exist_ok=True)
lines = json.loads(script.read_text())['lines']

STYLE = os.environ.get('TTS_STYLE') or ("confident, energetic tech explainer narrating a short Instagram reel; natural and conversational, "
         "like talking to a friend; slightly fast pace; clear pauses between sentences")

# build one transcript; longer pause before the reveal after "spot the problem?"
parts = []
for li, line in enumerate(lines):
    s = ' '.join(p['say'] for p in line)
    if re.search(r'spot the', s, re.I): s += ' <pause>'
    parts.append(s)
TEXT = '\n'.join(parts)

raw = out / 'raw.wav'
if not (reuse and raw.exists()):
    from google import genai
    from google.genai import types
    if '--vertex' in args:
        # Vertex AI with gcloud application-default credentials: gemini-3.8-flash-tts (only in the 'global' region).
        # 3.x models read a spoken-direction prefix out loud and reject a system instruction, so the style goes in a [bracketed] tag.
        proj = os.environ.get('GOOGLE_CLOUD_PROJECT') or json.load(open(Path.home() / '.config/gcloud/application_default_credentials.json'))['quota_project_id']
        vc = genai.Client(vertexai=True, project=proj, location=os.environ.get('GOOGLE_CLOUD_LOCATION', 'global'),
                          http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1), timeout=300000))
        model = os.environ.get('TTS_MODEL', 'gemini-3.8-flash-tts'); g3 = model.startswith('gemini-3')
        r = vc.models.generate_content(model=model, contents=f'[{STYLE}] {TEXT}' if g3 else f'Read this aloud as a {STYLE}:\n\n{TEXT}',
            config=types.GenerateContentConfig(response_modalities=['AUDIO'], speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)))))
        import wave
        w = wave.open(str(raw), 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
        w.writeframes(r.candidates[0].content.parts[0].inline_data.data); w.close()
        print('generated', raw, '(vertex)')
    else:
      client = genai.Client(http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1), timeout=180000))
      r = client.interactions.create(
          model='gemini-3.8-flash-tts',
          input=[{'type': 'user_input', 'content': [{'type': 'text', 'text': TEXT,
                  'annotations': [{'type': 'speech_metadata', 'style': STYLE}]}]}],
          response_format={'type': 'audio'},
          generation_config={'speech_config': [{'voice': voice}]},
      )
      raw.write_bytes(base64.b64decode(r.output_audio.data))
      print('generated', raw)
    if '--tempo' in args:  # speed the take up (pitch kept) before alignment, so timings match what plays
        sped = out / 'raw_tempo.wav'
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(raw), '-af', f"atempo={args[args.index('--tempo') + 1]}", str(sped)], check=True)
        sped.replace(raw)

# ---- align phrases with whisper word timestamps (separate python env) ----
WHISPER_PY = os.environ.get('WHISPER_PY') or str(Path.home() / 'Developer/reel-builder/.whisper/bin/python')
words = json.loads(subprocess.run([WHISPER_PY, '-c', f'''
import json
from faster_whisper import WhisperModel
m = WhisperModel("medium.en", device="cpu", compute_type="int8")
segs, _ = m.transcribe({str(raw)!r}, word_timestamps=True)
print(json.dumps([[w.word, w.start, w.end] for s in segs for w in s.words]))
'''], capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1])
(out / 'words.json').write_text(json.dumps(words))

NUM = {'50': 'fifty', '10': 'ten', '$50': 'fifty dollars', '1': 'one', '2': 'two', '3': 'three', '10,000,000': 'tenmillion', '4': 'four', '503': 'fiveohthree', '404': 'fourohfour', '5': 'five', '99%': 'ninetyninepercent', '1%': 'onepercent', '5%': 'fivepercent', '25': 'twentyfive', '25%': 'twentyfivepercent', '100': 'hundred', '99': 'ninetynine', '2024': 'twentytwentyfour', '8.5': 'eightandahalf', '8': 'eight', '5.': 'five'}
norm = lambda s: re.sub(r'[^a-z]', '', s.lower())
# char stream from whisper, with the word index of each char
wchars, widx = [], []
for i, (w, a, b) in enumerate(words):
    t = norm(NUM.get(w.strip().strip('.,?!'), w))
    wchars += t; widx += [i] * len(t)
pchars, pspan = [], []
for li, line in enumerate(lines):
    for pi, p in enumerate(line):
        t = norm(p['say']); pspan.append((li, pi, len(pchars), len(pchars) + len(t))); pchars += t
sm = difflib.SequenceMatcher(None, pchars, wchars, autojunk=False)
pmap = {}
for a, b, n in sm.get_matching_blocks():
    for k in range(n): pmap[a + k] = b + k
def near(c, step):
    while c not in pmap and 0 <= c < len(pchars): c += step
    return pmap.get(c)

timings = []
for li, pi, c0, c1 in pspan:
    a, b = near(c0, 1), near(c1 - 1, -1)
    p = lines[li][pi]
    timings.append({'li': li, 'pi': pi, 'say': p['say'], 'show': p['show'],
                    'start': round(words[widx[a]][1], 3), 'end': round(words[widx[b]][2], 3)})
for i in range(1, len(timings)):  # keep monotonic
    timings[i]['start'] = max(timings[i]['start'], timings[i - 1]['end'])
(out / 'timings.json').write_text(json.dumps(timings, indent=1))

# ---- post: gentle polish, loudness -14 LUFS, 2 s tail pad ----
subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(raw), '-af',
                'highpass=f=70,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120,'
                'loudnorm=I=-14:TP=-1.5:LRA=9,apad=pad_dur=2', '-ar', '48000', str(out / 'voice.wav')], check=True)
for t in timings: print(f"{t['li']}.{t['pi']}  {t['start']:6.2f}-{t['end']:6.2f}  {t['say']}")
