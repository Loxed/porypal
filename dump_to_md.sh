#!/bin/bash

ROOT="${1:-.}"
OUT="$ROOT/porypal_dump.md"
> "$OUT"

EXTENSIONS=("py" "yaml" "yml" "json" "sh")
EXCLUDE_DIRS=(".venv" "__pycache__" ".git" "build" "dist")

find "$ROOT" -type f | sort | while read -r file; do
    rel="${file#$ROOT/}"

    # Skip excluded dirs
    skip=false
    for dir in "${EXCLUDE_DIRS[@]}"; do
        if [[ "$rel" == *"$dir"* ]]; then
            skip=true; break
        fi
    done
    $skip && continue

    # Skip this script and the output file
    [[ "$rel" == "dump_to_md.sh" || "$rel" == "porypal_dump.md" ]] && continue

    # Check extension
    ext="${file##*.}"
    match=false
    for e in "${EXTENSIONS[@]}"; do
        [[ "$ext" == "$e" ]] && match=true && break
    done
    $match || continue

    [[ "$ext" == "py" ]] && lang="python" || lang="$ext"

    echo "# $rel" >> "$OUT"
    echo '```'"$lang" >> "$OUT"
    cat "$file" >> "$OUT"
    echo '```' >> "$OUT"
    echo "" >> "$OUT"
    echo "----" >> "$OUT"
    echo "" >> "$OUT"
done

echo "Written to $OUT"