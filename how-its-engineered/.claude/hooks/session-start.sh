#!/bin/bash
# Cloud sessions only: Node deps for rendering, plus the two Python envs the voice pipeline needs.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# render.mjs (Playwright + fonts). Chromium is preinstalled; don't download it.
npm install --no-audit --no-fund

# voice/gemini_tts.py runs from .venv-fish (needs google-genai)
[ -x .venv-fish/bin/python ] || python3 -m venv .venv-fish
.venv-fish/bin/pip install -q --upgrade google-genai

# Whisper alignment env. av 15+ breaks faster-whisper 1.2.x (metadata_errors), so pin a binary av 14.
WHISPER_ENV="$HOME/.whisper"
[ -x "$WHISPER_ENV/bin/python" ] || python3 -m venv "$WHISPER_ENV"
"$WHISPER_ENV/bin/pip" install -q faster-whisper
"$WHISPER_ENV/bin/pip" install -q --only-binary=:all: "av<15"
# prefetch the model (~1.5 GB, cached after the first run)
"$WHISPER_ENV/bin/python" -c "from huggingface_hub import snapshot_download; snapshot_download('Systran/faster-whisper-medium.en')"

echo "export WHISPER_PY=\"$WHISPER_ENV/bin/python\"" >> "$CLAUDE_ENV_FILE"
# render.mjs: the project's Playwright may expect a newer browser build than the one preinstalled here
if [ -x /opt/pw-browsers/chromium ]; then
  echo "export CHROMIUM_PATH=/opt/pw-browsers/chromium" >> "$CLAUDE_ENV_FILE"
fi
