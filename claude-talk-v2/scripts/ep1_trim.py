"""Re-trim every voice clip from its raw PCM (tighter -40 dB gate, ~60 ms of air kept), then report each clip's
length against its text (words per second) so a clip that is too long or short for its line stands out.
python3 scripts/ep1_trim.py [audio dir]"""
import re, struct, subprocess, sys


def samples(path):
    """The API returns a WAV (RIFF header + data + a trailing C2PA chunk), not bare PCM: keep only the data chunk,
    otherwise the header and metadata decode as a click at the start and a loud burst at the end."""
    b = open(path, "rb").read()
    if b[:4] != b"RIFF":
        return b
    i = 12
    while i < len(b):
        cid, sz = b[i:i + 4], struct.unpack("<I", b[i + 4:i + 8])[0]
        if cid == b"data":
            return b[i + 8:i + 8 + sz]
        i += 8 + sz + (sz & 1)
    raise ValueError(path)


d = sys.argv[1] if len(sys.argv) > 1 else "audio/ep1b"
texts = [l.rstrip("\n").split("\t") for l in open(f"{d}/lines.tsv")]
rows = []
for i, (who, text) in enumerate(texts, 1):
    wav = f"{d}/l{i:02d}.wav"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", "-",
                    "-af", "silenceremove=start_periods=1:start_threshold=-40dB:start_silence=0.06,areverse,"
                           "silenceremove=start_periods=1:start_threshold=-40dB:start_silence=0.06,areverse",
                    "-ar", "48000", wav], input=samples(f"{d}/l{i:02d}.pcm"), check=True)
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav]))
    n = len(re.findall(r"[a-z']+", text.lower()))
    wps = n / dur
    print(f"{i:02d} {who:6s} {dur:5.2f}s {n:2d}w {wps:4.2f}w/s {'' if 1.6 <= wps <= 4.2 or n <= 2 else '<-- CHECK'} | {text}")
    rows.append(f"{i:02d} {who} {dur:.3f}")
open(f"{d}/durs.txt", "w").write("\n".join(rows) + "\n")
