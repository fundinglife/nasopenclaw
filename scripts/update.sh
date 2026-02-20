#!/bin/bash
# Pull latest image and restart whichever nasopenclaw container is running
DOCKER="/volume1/@appstore/Docker/usr/bin/docker"
COMPOSE_FILE="/volume1/docker/nasopenclaw-repo/docker-compose.yml"
ENV_FILE="/volume1/docker/nasopenclaw-repo/.env"
IMAGE="ghcr.io/phioranex/openclaw-docker:latest"

# Detect which profile is running
RUNNING=""
for p in a o g z; do
    if $DOCKER ps --format '{{.Names}}' | grep -q "nasopenclaw-$p"; then
        RUNNING="$p"
        break
    fi
done

echo "Pulling latest image..."
$DOCKER pull "$IMAGE"

if [ -n "$RUNNING" ]; then
    echo "Restarting profile: $RUNNING"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" --profile "$RUNNING" down
    sleep 2
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" --profile "$RUNNING" up -d
    echo "Done. nasopenclaw-$RUNNING restarted."
else
    echo "No nasopenclaw container was running. Start one with:"
    echo "  docker-compose --profile a up -d   # Claude"
    echo "  docker-compose --profile o up -d   # Codex"
    echo "  docker-compose --profile g up -d   # Gemini"
    echo "  docker-compose --profile z up -d   # Z.AI"
fi
