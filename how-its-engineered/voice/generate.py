"""Young custom B voice: Chatterbox cloned from zac.wav, phrase by phrase.

usage: .venv/bin/python voice/generate.py <script.json> <outdir> [--device mps|cpu] [--seed N] [--redo 3.1,5.0]
script.json: {"lines": [["phrase" | {"say": "...", "show": "caption markup"}, ...], ...]}
--redo regenerates only those phrases (line.phrase) with a new seed and rebuilds the rest from the saved takes.
writes <outdir>/raw.wav, <outdir>/timings.json, <outdir>/voice.wav (post-processed)
"""
import json, subprocess, sys, time
from pathlib import Path
import numpy as np, soundfile as sf, torch
from chatterbox.tts import ChatterboxTTS

REF = str(Path(__file__).with_name("zac.wav"))
POST = ("aresample=24000,asetrate=24000*1.07,aresample=44100,atempo=1/1.07,highpass=f=90,"
        "equalizer=f=250:t=q:w=1:g=-2,equalizer=f=5000:t=q:w=1.2:g=2.5,"
        "acompressor=threshold=-20dB:ratio=3:makeup=2,loudnorm=I=-14:TP=-1,apad=pad_dur=2")

def trim(w, sr):
    i = np.where(np.abs(w) > 0.01)[0]
    return w[max(i[0] - int(.01 * sr), 0):i[-1] + int(.05 * sr)]

def gap_after(text, is_last):
    if "spot the" in text.lower(): return 0.9
    if text.endswith("..."): return 0.45
    return 0.55 if is_last else 0.3

def main():
    script, outdir = sys.argv[1], Path(sys.argv[2])
    device = sys.argv[sys.argv.index("--device") + 1] if "--device" in sys.argv else ("mps" if torch.backends.mps.is_available() else "cpu")
    outdir.mkdir(parents=True, exist_ok=True)
    lines = json.load(open(script))["lines"]

    t0 = time.time()
    m = ChatterboxTTS.from_pretrained(device=device)
    sr = m.sr
    t_load = time.time() - t0
    print(f"loaded on {device} in {t_load:.1f}s", flush=True)

    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 1234
    redo = set(sys.argv[sys.argv.index("--redo") + 1].split(",")) if "--redo" in sys.argv else None
    takes = outdir / "takes"; takes.mkdir(exist_ok=True)
    out, tim, t = [], [], 0.0
    t1 = time.time()
    for li, phs in enumerate(lines):
        for pi, item in enumerate(phs):
            p = item if isinstance(item, str) else item["say"]
            show = item if isinstance(item, str) else item.get("show", p)
            f = takes / f"{li:02d}_{pi:02d}.wav"
            if f.exists() and (redo is None and "--fresh" not in sys.argv or redo is not None and f"{li}.{pi}" not in redo):
                w, _ = sf.read(f, dtype="float32")
            else:
                torch.manual_seed(seed + li * 100 + pi)
                w = trim(m.generate(p, audio_prompt_path=REF, exaggeration=0.6, cfg_weight=0.3).squeeze(0).cpu().numpy(), sr)
                sf.write(f, w, sr)
            g = gap_after(p, pi == len(phs) - 1)
            tim.append({"li": li, "pi": pi, "say": p, "show": show, "start": round(t, 3), "end": round(t + len(w) / sr, 3)})
            out += [w, np.zeros(int(g * sr), dtype=w.dtype)]
            t += len(w) / sr + g
            print(f"  {li}.{pi} {len(w)/sr:4.1f}s  {p}", flush=True)
    t_gen = time.time() - t1

    sf.write(outdir / "raw.wav", np.concatenate(out), sr)
    json.dump(tim, open(outdir / "timings.json", "w"), indent=1)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(outdir / "raw.wav"), "-af", POST, "-ar", "44100", str(outdir / "voice.wav")], check=True)
    print(f"done: {t:.1f}s of audio | load {t_load:.1f}s + generate {t_gen:.1f}s = {t_load + t_gen:.1f}s", flush=True)

if __name__ == "__main__":
    main()
