#!/usr/bin/env bash
# Wipe the local netbox-docker NetBox database and prepare it for a fresh build:
#   - tears the stack down and deletes the Postgres volume
#   - brings Postgres up (PostGIS overlay), creates the postgis extension
#     (netbox-pathways' migrations need it BEFORE netbox starts)
#   - starts netbox/worker, waits for health
#   - creates the demo-loader superuser + API token and writes the token to
#     .env (never printed), and deletes the now-invalid .secrets_userkey.pem
#
# DESTRUCTIVE: deletes ALL data in that NetBox instance. Local dev only.
# Usage: tools/reset_netbox.sh [path-to-netbox-docker]
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
DOCKER_DIR="${1:-$HERE/../netbox-docker}"
cd "$DOCKER_DIR"

nbc() { docker compose -f docker-compose.yml -f docker-compose.override.yml \
        -f extensions/postgis-pathways/docker-compose.postgis.yml "$@"; }

source env/postgres.env

echo "== down + remove postgres volume"
nbc down
docker volume rm netbox-docker_netbox-postgres >/dev/null

echo "== postgres up, create postgis extension"
nbc up -d --wait postgres
nbc exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS postgis;" >/dev/null

echo "== netbox up (first boot runs all migrations; can take several minutes)"
nbc up -d netbox netbox-worker >/dev/null 2>&1 || true
for i in $(seq 1 90); do
  state="$(docker inspect -f '{{.State.Health.Status}}' netbox-docker-netbox-1 2>/dev/null || echo none)"
  [ "$state" = "healthy" ] && break
  sleep 10
done
[ "$state" = "healthy" ] || { echo "netbox never became healthy"; exit 1; }
nbc up -d --wait >/dev/null

echo "== token"
TOKEN_FILE="$(mktemp)"; chmod 600 "$TOKEN_FILE"
nbc exec -T netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py shell -c "
from django.contrib.auth import get_user_model
from users.models import Token
U = get_user_model()
u, _ = U.objects.get_or_create(username='demo-loader', defaults={'is_superuser': True, 'is_active': True})
Token.objects.filter(user=u).delete()
t = Token(user=u, description='demo-data loader scripts')
t.save()
print('TOKEN=nbt_' + t.key + '.' + t.token)
" 2>/dev/null | grep '^TOKEN=' | sed 's/^TOKEN=//' > "$TOKEN_FILE"

python3 - "$HERE/.env" "$TOKEN_FILE" <<'PY'
import re, sys
env_path, token_path = sys.argv[1], sys.argv[2]
token = open(token_path).read().strip()
try:
    content = open(env_path).read()
except FileNotFoundError:
    content = "NETBOX_URL=http://localhost:8000\n"
if "NETBOX_TOKEN=" in content:
    content = re.sub(r"NETBOX_TOKEN=.*", f"NETBOX_TOKEN={token}", content)
else:
    content = content.rstrip("\n") + f"\nNETBOX_TOKEN={token}\n"
open(env_path, "w").write(content)
PY
rm -f "$TOKEN_FILE" "$HERE/.secrets_userkey.pem"
echo "== done: empty NetBox ready, .env updated, secrets key removed"
