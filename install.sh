#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"

if [[ -z "${PYTHON_BIN:-}" ]]; then
  if command -v python3.11 >/dev/null 2>&1; then
    PYTHON_BIN="python3.11"
  else
    PYTHON_BIN="python3"
  fi
fi

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python >=3.11,<3.13 required. Set PYTHON_BIN=/path/to/python if needed." >&2
  exit 1
fi

"${PYTHON_BIN}" -c 'import sys; raise SystemExit(0 if (3, 11) <= sys.version_info < (3, 13) else 1)' \
  || { echo "Python >=3.11,<3.13 required. Found: $(${PYTHON_BIN} --version)" >&2; exit 1; }

"${PYTHON_BIN}" -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/python" -m pip install -U pip
"${VENV_DIR}/bin/python" -m pip install -e "${ROOT_DIR}[test]"

for tool in xcrun adb ffmpeg ffprobe screencapture; do
  if ! command -v "${tool}" >/dev/null 2>&1; then
    echo "WARN: ${tool} not found. The related backend or verification will be unavailable." >&2
  fi
done

cat <<EOF

Install complete.

macOS Screen Recording:
  Add this Python binary to System Settings > Privacy & Security > Screen Recording:
    ${VENV_DIR}/bin/python

Claude Code registration:
  claude mcp add --scope user --transport stdio video_capture -- ${ROOT_DIR}/bin/video-capture-mcp

Codex registration (~/.codex/config.toml):
  [mcp_servers.video_capture]
  command = "${ROOT_DIR}/bin/video-capture-mcp"
  args = []

EOF
