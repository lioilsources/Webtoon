#!/usr/bin/env bash
# Deploy from the Mac to JODA: ~/deploy/Webtoon/{backend,deploy,rules,data,media}. Idempotent: secrets, tunnel and DNS
# are created only once; .env and cloudflared creds stay on JODA.
#   deploy/deploy.sh          # code, rules, stories, media, compose up
# The database lives only on JODA (the Mac uses it over the LAN), so there is nothing to copy.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
JODA=${JODA:-joda}
HOSTNAME_API=webtoon-api.ol1n.com

ssh "$JODA" 'mkdir -p ~/deploy/Webtoon/data ~/deploy/Webtoon/media && mkdir -p -m 700 ~/deploy/Webtoon/voice-data ~/deploy/Webtoon/secrets'
rsync -a --delete --exclude .env --exclude 'cloudflared/*.json' --exclude cloudflared/config.yml \
  "$ROOT/deploy" "$JODA":deploy/Webtoon/
rsync -a --delete --exclude /backend/media/ --exclude /backend/.env "$ROOT/backend" "$JODA":deploy/Webtoon/
rsync -a --delete "$ROOT/rules" "$JODA":deploy/Webtoon/
rsync -a "$ROOT/data/gamebooks" "$ROOT/data/stories" "$JODA":deploy/Webtoon/data/
rsync -a "$ROOT/backend/media/" "$JODA":deploy/Webtoon/media/

ssh "$JODA" HOSTNAME_API="$HOSTNAME_API" bash -s <<'REMOTE'
set -euo pipefail
cd ~/deploy/Webtoon/deploy
if [ ! -f .env ]; then
  printf 'POSTGRES_PASSWORD=%s\nSTUDIO_TOKEN=%s\n' "$(openssl rand -hex 24)" "$(openssl rand -hex 32)" > .env
  chmod 600 .env
  echo "created .env"
fi
# Player voice secrets: added once, never printed (docs/voice-backend.md).
for k in VOICE_DATA_KEY VOICE_WORKER_TOKEN; do
  grep -q "^$k=" .env || { printf '%s=%s\n' "$k" "$(openssl rand -hex 32)" >> .env; echo "added $k to .env"; }
done
if [ ! -f cloudflared/config.yml ]; then
  # --config /dev/null: never fall back to ~/.cloudflared/config.yml (another tunnel).
  cf() { cloudflared tunnel --config /dev/null --origincert ~/.cloudflared/cert.pem "$@" 2>/dev/null; }
  tunnel_id() { cf list -o json | python3 -c \
    'import sys,json;print(next((t["id"] for t in json.load(sys.stdin) if t["name"]=="webtoon"),""))'; }
  ID=$(tunnel_id)
  [ -n "$ID" ] || { cf create webtoon >/dev/null; ID=$(tunnel_id); }
  [ -n "$ID" ] || { echo "tunnel webtoon not created" >&2; exit 1; }
  install -m 644 ~/.cloudflared/"$ID".json cloudflared/"$ID".json
  sed "s/<TUNNEL-ID>/$ID/g" cloudflared/config.yml.example > cloudflared/config.yml
  cf route dns "$ID" "$HOSTNAME_API"
  echo "tunnel webtoon = $ID"
fi
docker compose up -d --build db webtoon
REMOTE

ssh "$JODA" 'cd ~/deploy/Webtoon/deploy && docker compose up -d && docker compose ps --format "{{.Name}} {{.Status}}"'
