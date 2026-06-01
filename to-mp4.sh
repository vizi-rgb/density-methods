#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="$PWD/out"

if [ ! -d "$OUT_DIR" ]; then
  echo "Directory 'out' does not exist. Create it and add subfolders with PNG files."
  exit 1
fi

shopt -s nullglob
subfolders=("$OUT_DIR"/*/)

if [ "${#subfolders[@]}" -eq 0 ]; then
  echo "No subfolders found in '$OUT_DIR'."
  exit 1
fi

created_count=0

for folder in "${subfolders[@]}"; do
  folder_name="$(basename "${folder%/}")"
  output_video="${OUT_DIR}/${folder_name}.mp4"
  frames_file="$(mktemp)"

  find "$folder" -maxdepth 1 -type f \( -name '*.png' -o -name '*.PNG' \) | sort -V | awk '{print "file '\''" $0 "'\''"}' > "$frames_file"

  if [ ! -s "$frames_file" ]; then
    echo "No PNG files found in '$folder'. Skipping."
    rm -f "$frames_file"
    continue
  fi

  if ! ffmpeg -y -r 30 -f concat -safe 0 -i "$frames_file" -c:v libx264 -pix_fmt yuv420p "$output_video"; then
    echo "Failed to create video for '$folder'."
    rm -f "$frames_file"
    continue
  fi

  rm -f "$frames_file"
  created_count=$((created_count + 1))
done

if [ "$created_count" -eq 0 ]; then
  echo "No videos were created."
  exit 1
fi