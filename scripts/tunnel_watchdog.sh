#!/usr/bin/env bash
# Health-checks the Cloudflare quick tunnel for PharmSFAO and forces a restart if it's
# dead or unreachable. cloudflared itself is kept alive by the
# com.pharmasfo.cloudflared launchd job (KeepAlive=true) — this script just detects
# a broken tunnel (process alive but not actually serving traffic, which happens
# often with quick tunnels) and kills it so launchd relaunches a fresh one.
# Safe to run repeatedly (e.g. every couple of minutes from launchd) — a no-op when healthy.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
URL_FILE="$REPO_ROOT/TUNNEL_URL.txt"
WATCHDOG_LOG="$REPO_ROOT/tunnel_watchdog.log"
CLOUDFLARED_LOG="$REPO_ROOT/.cloudflared_tunnel.log"
CF_MATCH="cloudflared tunnel --url http://localhost:8000"
MAX_LOG_BYTES=2000000

log() { echo "$(date -u +'%Y-%m-%dT%H:%M:%SZ') $1" >> "$WATCHDOG_LOG"; }

trim_log_if_huge() {
    [ -f "$CLOUDFLARED_LOG" ] || return 0
    local size
    size=$(wc -c < "$CLOUDFLARED_LOG" 2>/dev/null || echo 0)
    if [ "${size:-0}" -gt "$MAX_LOG_BYTES" ]; then
        tail -n 500 "$CLOUDFLARED_LOG" > "$CLOUDFLARED_LOG.tmp" && mv "$CLOUDFLARED_LOG.tmp" "$CLOUDFLARED_LOG"
        log "Trimmed oversized cloudflared log"
    fi
}

latest_url_in_log() {
    [ -f "$CLOUDFLARED_LOG" ] || return 1
    grep -o 'https://[a-zA-Z0-9.-]*\.trycloudflare\.com' "$CLOUDFLARED_LOG" | tail -1
}

is_healthy() {
    local url="$1"
    [ -z "$url" ] && return 1
    local code
    code=$(curl -s -o /dev/null -m 8 -w '%{http_code}' "$url/login/" 2>/dev/null || echo "000")
    [ "$code" = "200" ]
}

write_url_file() {
    local url="$1" note="$2"
    {
        echo "$url"
        echo "# last checked: $(date -u +'%Y-%m-%dT%H:%M:%SZ') UTC ($note)"
    } > "$URL_FILE"
}

trim_log_if_huge

candidate_url="$(latest_url_in_log || true)"

if is_healthy "$candidate_url"; then
    write_url_file "$candidate_url" "healthy"
    log "OK: $candidate_url"
    exit 0
fi

log "Unhealthy or missing tunnel (latest known: ${candidate_url:-none}) — cycling cloudflared"
pkill -f "$CF_MATCH" 2>/dev/null || true

# launchd's KeepAlive relaunches cloudflared within ~1s; wait for a fresh URL to
# appear after the kill, then confirm it actually serves traffic.
before_lines=$(wc -l < "$CLOUDFLARED_LOG" 2>/dev/null || echo 0)
new_url=""
for _ in $(seq 1 30); do
    sleep 1
    new_url=$(tail -n +"$((before_lines + 1))" "$CLOUDFLARED_LOG" 2>/dev/null | grep -o 'https://[a-zA-Z0-9.-]*\.trycloudflare\.com' | tail -1)
    [ -n "$new_url" ] && break
done

if [ -z "$new_url" ]; then
    log "ERROR: no new tunnel URL appeared within 30s of restart"
    exit 1
fi

sleep 6
if is_healthy "$new_url"; then
    write_url_file "$new_url" "healthy after restart"
    log "Recovered: $new_url"
else
    write_url_file "$new_url" "UNCONFIRMED — will re-check next run"
    log "New URL $new_url not confirmed healthy yet; will re-check next run"
fi
