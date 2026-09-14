#!/usr/bin/env bash
# Fleet-wide Bot Mode check: identity, protocol injection, routines, peers, managed flag.
#
# Invoke through the `terminal` tool:
#   bash <skill_dir>/scripts/bot_roster_check.sh            # every named profile
#   bash <skill_dir>/scripts/bot_roster_check.sh scout dixie # specific Bots
#
# Read-only: it only runs `hermes ... chat -Q -q` queries and list commands.
set -uo pipefail

HERMES_ROOT="${HERMES_ROOT:-$HOME/.hermes}"
PROFILES_DIR="$HERMES_ROOT/profiles"
QUERY='Reply in exactly 3 lines: (1) which profile you are, (2) one teammate from your roster with its role, (3) the exact heading of your messaging-protocol section.'
TIMEOUT_S="${TIMEOUT_S:-180}"

command -v hermes >/dev/null 2>&1 || { echo "hermes not on PATH" >&2; exit 2; }

if [ "$#" -gt 0 ]; then
  BOTS=("$@")
else
  BOTS=()
  if [ -d "$PROFILES_DIR" ]; then
    while IFS= read -r d; do BOTS+=("$(basename "$d")"); done \
      < <(find "$PROFILES_DIR" -mindepth 1 -maxdepth 1 -type d | sort)
  fi
fi

if [ "${#BOTS[@]}" -eq 0 ]; then
  echo "No named profiles found under $PROFILES_DIR (the default profile is $HERMES_ROOT)."
fi

printf '%-18s %-9s %-10s %s\n' BOT MANAGED PROTOCOL IDENTITY
for bot in "${BOTS[@]:-}"; do
  [ -n "$bot" ] || continue
  pfile="$PROFILES_DIR/$bot/profile.yaml"
  managed="no"
  if [ -f "$pfile" ] && grep -q 'hermes-bots' "$pfile"; then managed="yes"; fi

  out="$(timeout "$TIMEOUT_S" hermes -p "$bot" chat -Q -q "$QUERY" 2>&1)"
  rc=$?
  if [ "$rc" -ne 0 ]; then
    printf '%-18s %-9s %-10s %s\n' "$bot" "$managed" "?" "query failed (rc=$rc)"
    continue
  fi
  proto="no"; case "$out" in *"Messaging other agents"*) proto="yes";; esac
  ident="$(printf '%s' "$out" | tr '\n' ' ' | cut -c1-90)"
  printf '%-18s %-9s %-10s %s\n' "$bot" "$managed" "$proto" "$ident"
  [ "$proto" = "no" ] && echo "    -> no protocol: check session title is exactly 'Bot Chat' and agent.bot_mode_protocol=true"
  if [ "$managed" = "no" ]; then
    echo "    -> profile.yaml lacks the hermes-bots managed flag: Bot Mode has never touched this profile"
  fi
done

echo
echo "== routine ownership (cron jobs named '[bot:<name>] ...') =="
hermes cron list 2>&1 | grep -F '[bot:' || echo "(none)"

echo
echo "== peers =="
hermes peer list 2>&1 | head -20

echo
echo "Reminder: routines need their owning profile's gateway running (gateway ticks the scheduler every 60s)."
