#!/usr/bin/env bash
# Acceptance tests of netbox-tracepath-plugin against this dataset, in a local netbox-docker NetBox.
#
#   - each script is piped into `manage.py shell` inside the NetBox container (nothing is copied in)
#   - a script skips itself, with a [skipped] line, when the plugin or a plugin it needs (netbox-fms,
#     netbox-wdm) is not installed, or when the dataset is not loaded: the dataset itself never needs any of this
#   - PDFs the scripts render go to /tmp/tp-out inside the container
#
# Usage: tests/tracepath/run.sh [path-to-netbox-docker]       (default: ../netbox-docker next to this repository)
#        NETBOX_COMPOSE="docker compose -p other -f other.yml" tests/tracepath/run.sh      (any other Compose setup;
#        the service must be called netbox)
# Exit status is non-zero when a check fails.
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
if [ -n "${NETBOX_COMPOSE:-}" ]; then
  nbc() { $NETBOX_COMPOSE "$@"; }
else
  DOCKER_DIR="${1:-$HERE/../../../netbox-docker}"
  cd "$DOCKER_DIR" || { echo "no netbox-docker at $DOCKER_DIR"; exit 2; }
  nbc() { docker compose -f docker-compose.yml -f docker-compose.override.yml \
          -f extensions/postgis-pathways/docker-compose.postgis.yml "$@"; }
fi

status=0
for name in live_smoke live_scope live_profiles live_render live_wdm live_fms; do
  echo "######## $name"
  out="$(nbc exec -T netbox sh -c "cd /opt/netbox/netbox && python manage.py shell" < "$HERE/$name.py" 2>&1)"
  rc=$?
  if [ "$name" = "live_smoke" ]; then
    # the smoke test prints a line per check; keep what matters
    echo "$out" | grep -E "FAIL|ALL OK|FAILED|Traceback|\[skipped\]" || true
    [ "$(echo "$out" | grep -c '^  ok ')" -gt 0 ] && echo "  ($(echo "$out" | grep -c '^  ok ') checks ok)"
  else
    echo "$out" | grep -vE "^\s*$|loaded config|FutureWarning|warnings.warn|objects imported automatically" | tail -40
  fi
  if [ $rc -ne 0 ] || echo "$out" | grep -qE "FAIL|Traceback"; then status=1; fi
done
exit $status
