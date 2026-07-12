#!/bin/bash
set -e

if ! pgrep -x tailscaled > /dev/null; then
  tailscaled \
    --tun=userspace-networking \
    --outbound-http-proxy-listen=localhost:1054 \
    --socks5-server=localhost:1055 &
  sleep 3
fi

tailscale up \
  --authkey="${TAILSCALE_AUTH_KEY}" \
  --hostname="cursor-hass-livebox" \
  --advertise-tags=tag:cursor-agent \
  --accept-routes 2>/dev/null || true

export ALL_PROXY=socks5h://localhost:1055/
export HTTP_PROXY=http://localhost:1054/
export HTTPS_PROXY=http://localhost:1054/

if ! grep -q ALL_PROXY ~/.bashrc 2>/dev/null; then
  cat >> ~/.bashrc << 'EOF'
export ALL_PROXY=socks5h://localhost:1055/
export HTTP_PROXY=http://localhost:1054/
export HTTPS_PROXY=http://localhost:1054/
EOF
fi

echo "Tailscale: $(tailscale status --self 2>/dev/null | head -1 || echo 'non connecté')"
