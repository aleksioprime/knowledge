#!/usr/bin/env bash
# Кто ответил и что вернул: ./check.sh
set -euo pipefail
GW=${GW:-http://localhost:47080}

show() {
  echo "\$ $*"
  curl -s -i "$@" | tr -d '\r' | grep -E '^(HTTP|X-Served-By)|^[\[{]'
  echo
}

show "$GW/api/tasks/1"
show "$GW/api/tasks/1/comments"
