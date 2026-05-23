#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="$PWD/out"
FRAMES_FILE="/tmp/frames.txt"
OUTPUT_VIDEO="out.mp4"

if [ $# -gt 1 ]; then
  echo "Usage: $0 [output.mp4]" >&2
  exit 1
fi

if [ $# -eq 1 ]; then
  if [ -z "$1" ]; then
    echo "Output filename cannot be empty." >&2
    exit 1
  fi
  OUTPUT_VIDEO="$1"
fi

if [ ! -d "$OUT_DIR" ]; then
  echo "Directory 'out' does not exist. Create it and add PNG files."
  exit 1
fi

find "$OUT_DIR" -maxdepth 1 -type f -name '*.png' | sort -V | awk '{print "file '\''" $0 "'\''"}' > "$FRAMES_FILE"

if [ ! -s "$FRAMES_FILE" ]; then
  echo "No PNG files found in '$OUT_DIR'."
  exit 1
fi

ffmpeg -r 30 -f concat -safe 0 -i "$FRAMES_FILE" -c:v libx264 -pix_fmt yuv420p "$OUTPUT_VIDEO"