#!/usr/bin/env bash
# Generic leak check for a public repo: local paths, personal e-mails, stray PDFs.
# Project-specific names are checked by a private pre-push hook that is NOT in the repo.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"
files=$(git ls-files | grep -v '^scripts/sanitize_check.sh$')
fail=0
if echo "$files" | xargs grep -InE '(/Users/|/home/[a-z]|C:\\Users)' ; then
  echo "sanitize: local path found"; fail=1
fi
if echo "$files" | xargs grep -InoE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}' | grep -v 'noreply' ; then
  echo "sanitize: e-mail address found"; fail=1
fi
if echo "$files" | grep -E '\.pdf$' | grep -v '^examples/' ; then
  echo "sanitize: PDF outside examples/"; fail=1
fi
[ "$fail" -eq 0 ] && echo "sanitize: ok"
exit "$fail"
