#!/usr/bin/env bash

test_mode=0

while getopts "t" opt; do
	case $opt in
	t) test_mode=1 ;;
	*)
		echo "Usage: $0 [-t]" >&2
		exit 1
		;;
	esac
done

shopt -s nullglob
files=(/tmp/aitranscribe_record_v??.txt)
shopt -u nullglob

if ((${#files[@]} == 0)); then
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

if ((test_mode == 1)); then
	echo "Filename: $promptfile"
	echo "Content:"
	cat -- "$promptfile"
else
	cat -- "$promptfile"

	targetfile="${promptfile%.txt}.prompted.txt"
	if [[ -e "$targetfile" ]]; then
		targetfile="${promptfile%.txt}.prompted.$(date +%s).txt"
	fi
	mv -- "$promptfile" "$targetfile"
fi
