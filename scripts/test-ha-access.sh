#!/bin/bash
set -e

source ~/.bashrc 2>/dev/null || true

# Tailscale IPs (tailnet tail4c7c90.ts.net)
# Prod Pi187  : 100.91.212.24  (homeassistant.tail4c7c90.ts.net)
# Eyguians    : 100.86.161.106  (homeassistant-eyg.tail4c7c90.ts.net)
# Cam         : 100.107.146.38

declare -A HA_URLS=(
  [PROD]="http://100.91.212.24:8123"
  [EYG]="http://100.86.161.106:8123"
  [CAM]="http://100.107.146.38:8123"
)

declare -A HA_TOKENS=(
  [PROD]="${HA_TOKEN_PROD:-${HA_TOKEN_ROQUEFORT:-}}"
  [EYG]="${HA_TOKEN_EYG:-}"
  [CAM]="${HA_TOKEN_CAM:-}"
)

for site in PROD EYG CAM; do
  url="${HA_URLS[$site]}"
  token="${HA_TOKENS[$site]}"

  if [ -z "$token" ]; then
    echo "⚠ $site ($url) : token manquant (HA_TOKEN_${site})"
    continue
  fi

  code=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $token" \
    "$url/api/")
  echo "$site ($url) → HTTP $code"
done
