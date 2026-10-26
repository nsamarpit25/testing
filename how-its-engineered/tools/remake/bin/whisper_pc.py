#!/usr/bin/env python3
"""Stand-in for a local faster-whisper python (WHISPER_PY): runs the `-c` code on the PC instead of the Mac.

voice/gemini_tts.py calls `$WHISPER_PY -c "<code that transcribes /local/raw.wav>"`. This copies every local .wav the
code names to the PC, swaps in the remote paths, runs it with ~/hie-whisper/bin/python there and prints its stdout.
usage: WHISPER_PY=tools/remake/bin/whisper_pc.py zsh tools/remake/bin/tts.sh <dir>
"""
import os, re, subprocess, sys

PC = os.environ.get('HIE_PC', 'sam@192.168.0.113')
SSH = ['-o', 'BatchMode=yes', '-i', os.path.expanduser('~/.ssh/id_ed25519')]
if os.environ.get('HIE_SSH_CONFIG'):  # AWS box when the PC is off: HIE_PC=hieb HIE_SSH_CONFIG=tools/remake/out/aws/ssh_config
    SSH = ['-o', 'BatchMode=yes', '-F', os.environ['HIE_SSH_CONFIG']]
code = sys.argv[sys.argv.index('-c') + 1]
for i, p in enumerate(sorted(set(re.findall(r"'([^']+\.wav)'", code)))):
    rp = f'/tmp/hie_whisper_{os.getpid()}_{i}.wav'
    subprocess.run(['scp', '-q', *SSH, os.path.abspath(p), f'{PC}:{rp}'], check=True)
    code = code.replace(f"'{p}'", f"'{rp}'")
r = subprocess.run(['ssh', *SSH, PC, '~/hie-whisper/bin/python - ; rm -f /tmp/hie_whisper_%d_*.wav' % os.getpid()],
                   input=code, capture_output=True, text=True)
sys.stderr.write(r.stderr[-2000:])
sys.stdout.write(r.stdout)
sys.exit(r.returncode)
