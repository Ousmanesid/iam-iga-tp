#!/bin/bash
# Script d'attente générique pour vérifier la disponibilité d'un service
# Usage: ./wait-for.sh <host> <port> <timeout_seconds>

set -e

HOST="$1"
PORT="$2"
TIMEOUT="${3:-60}"

echo "⏳ Attente de $HOST:$PORT..."

end=$((SECONDS + TIMEOUT))

while [ $SECONDS -lt $end ]; do
    if nc -z "$HOST" "$PORT" > /dev/null 2>&1; then
        echo "✅ $HOST:$PORT est disponible"
        exit 0
    fi
    sleep 2
done

echo "❌ Timeout: $HOST:$PORT n'est pas disponible après ${TIMEOUT}s"
exit 1

