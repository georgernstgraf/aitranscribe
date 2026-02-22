#!/usr/bin/env bash

shopt -s nullglob
files=(/tmp/aitranscribe_record_v??.txt)
shopt -u nullglob

if (( ${#files[@]} == 0 )); then
    echo "There is no prompt available"
    exit 1
fi

promptfile="${files[0]}"
for candidate in "${files[@]}"; do
    if [[ "$candidate" -ot "$promptfile" ]]; then
        promptfile="$candidate"
    fi
done

if [[ ! -r "$promptfile" ]]; then
    echo "The prompt file is not readable: $promptfile"
    exit 1
fi

cat -- "$promptfile"

targetfile="${promptfile%.txt}.prompted.txt"
if [[ -e "$targetfile" ]]; then
    targetfile="${promptfile%.txt}.prompted.$(date +%s).txt"
fi

mv -- "$promptfile" "$targetfile"