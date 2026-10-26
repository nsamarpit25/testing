# Zack D.-style narrator test: one Gemini TTS take per line, joined with short gaps, so every line's start and end is exact
# (no Whisper). Writes audio/<ep>/l##.wav, voice.wav (48 kHz, -14 LUFS) and lines.json (text, start, end in seconds).
# usage: "<venv with google-genai>/python" scripts/zdf_tts.py <ep> [--voice Puck] [--reuse]
import base64, json, os, subprocess, sys, wave
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
args = sys.argv[1:]
ep = args[0]
voice = args[args.index('--voice') + 1] if '--voice' in args else 'Puck'
out = HERE / 'audio' / ep
out.mkdir(parents=True, exist_ok=True)
LINES = json.load(open(out / 'script.json'))['lines']
GAP, LEAD = 0.12, 0.25
STYLE = ("fast, upbeat male storyteller narrating a short animated Instagram reel, like a friend telling a quick story; "
         "punchy, warm, no pauses inside the line")

for k in os.environ.get('ENV_FILE', str(HERE.parent / '.env')).split(','):
    for ln in open(k):
        if ln.startswith('GEMINI_API_KEY='):
            os.environ.setdefault('GEMINI_API_KEY', ln.split('=', 1)[1].strip().strip('"'))


def tts(text, path):
    from google import genai
    from google.genai import types
    if '--vertex' in args:  # gcloud application-default credentials; the 3.x TTS model only lives in 'global'
        proj = os.environ.get('GOOGLE_CLOUD_PROJECT') or json.load(open(Path.home() / '.config/gcloud/application_default_credentials.json'))['quota_project_id']
        vc = genai.Client(vertexai=True, project=proj, location='global',
                          http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=2), timeout=120000))
        r = vc.models.generate_content(model='gemini-3.8-flash-tts', contents=f'[{STYLE}] {text}',
            config=types.GenerateContentConfig(response_modalities=['AUDIO'], speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)))))
        w = wave.open(str(path), 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
        w.writeframes(r.candidates[0].content.parts[0].inline_data.data); w.close()
        return
    client = genai.Client(http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=2), timeout=120000))
    r = client.interactions.create(
        model='gemini-3.8-flash-tts',
        input=[{'type': 'user_input', 'content': [{'type': 'text', 'text': text,
                'annotations': [{'type': 'speech_metadata', 'style': STYLE}]}]}],
        response_format={'type': 'audio'},
        generation_config={'speech_config': [{'voice': voice}]},
    )
    data = base64.b64decode(r.output_audio.data)
    if data[:4] == b'RIFF':
        path.write_bytes(data)
    else:  # raw 24 kHz mono PCM
        w = wave.open(str(path), 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(data); w.close()


def trimmed(src, dst):  # cut leading and trailing silence so the gaps are ours
    af = 'silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse'
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(src), '-af', af, '-ar', '48000', '-ac', '1', str(dst)], check=True)
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(dst)],
                                capture_output=True, text=True, check=True).stdout)


t, timed, parts = LEAD, [], []
for i, L in enumerate(LINES, 1):
    raw, cut = out / f'l{i:02d}_raw.wav', out / f'l{i:02d}.wav'
    if not ('--reuse' in args and raw.exists()):
        tts(L['say'], raw)
    d = trimmed(raw, cut)
    timed.append({**L, 'start': round(t, 3), 'end': round(t + d, 3)})
    parts.append((cut, t))
    t += d + L.get('gap', GAP)
(out / 'lines.json').write_text(json.dumps(timed, indent=1))

cmd = ['ffmpeg', '-loglevel', 'error', '-y']
for p, _ in parts:
    cmd += ['-i', str(p)]
fl = ''.join(f'[{k}]adelay={int(s * 1000)}:all=1[a{k}];' for k, (_, s) in enumerate(parts))
fl += ''.join(f'[a{k}]' for k in range(len(parts))) + f'amix=inputs={len(parts)}:normalize=0,'
fl += f'highpass=f=70,loudnorm=I=-14:TP=-1.5:LRA=9,apad=whole_dur={t + 0.6:.2f}[o]'
subprocess.run(cmd + ['-filter_complex', fl, '-map', '[o]', '-ar', '48000', str(out / 'voice.wav')], check=True)
for L in timed:
    print(f"{L['start']:5.2f}-{L['end']:5.2f}  {L['say']}")
print('total', round(t, 2))
