#!/usr/bin/env bash
# Usage: ./run_task.sh [T05]
# No argument = next unchecked task in progress/PROGRESS.md.
# Prints the prompt to paste into Pi. If PI_CMD is set it also runs: $PI_CMD "<prompt>"
set -euo pipefail
cd "$(dirname "$0")"

task="${1:-}"
if [ -z "$task" ]; then
  line=$(grep -m1 -E '^\| \[ \] T[0-9]+' progress/PROGRESS.md || true)
  task=$(echo "$line" | grep -oE 'T[0-9]+' | head -1 || true)
fi
if [ -z "$task" ]; then echo "All tasks are done (or blocked). See progress/PROGRESS.md"; exit 0; fi

file=$(ls tasks/"$task"-*.md 2>/dev/null | head -1 || true)
if [ -z "$file" ]; then echo "No task file found for $task"; exit 1; fi

prompt="Read AGENTS.md, then do task $task exactly as written in $file. Follow the session protocol in AGENTS.md. Stop when the task is finished."
echo "$prompt"
if [ -n "${PI_CMD:-}" ]; then
  $PI_CMD "$prompt"
fi
