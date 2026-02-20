#!/bin/bash
# nasopenclaw setup — run once on NAS before first docker-compose up
# Creates data dirs, sets ownership for container's node user (UID 1000)
set -e

DOCKER="/volume1/@appstore/Docker/usr/bin/docker"
BASE="/volume1/docker/nasopenclaw"
IMAGE="ghcr.io/phioranex/openclaw-docker:latest"
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo -e "\n${GREEN}nasopenclaw — NAS setup${NC}\n"

# Create all data dirs
for dir in data-a data-o data-g data-z workspace configs; do
    mkdir -p "$BASE/$dir"
    echo "  created $BASE/$dir"
done

# Set ownership to container's node user
chown -R 1000:1000 "$BASE/data-a" "$BASE/data-o" "$BASE/data-g" "$BASE/data-z" "$BASE/workspace" 2>/dev/null \
    || echo -e "${YELLOW}  Warning: chown failed — run as root if you hit permission errors${NC}"

echo ""

# Pull image
echo "Pulling image $IMAGE ..."
$DOCKER pull "$IMAGE"

echo -e "\n${GREEN}Setup complete.${NC}"
echo ""
echo "Next steps:"
echo "  1. cp .env.example .env  and fill in your keys"
echo "  2. Copy configs/ to $BASE/configs/ on the NAS"
echo "     (or symlink: ln -s \$(pwd)/configs $BASE/configs)"
echo "  3. Start a provider:"
echo "     docker-compose --profile a up -d   # Claude"
echo "     docker-compose --profile o up -d   # Codex"
echo "     docker-compose --profile g up -d   # Gemini"
echo "     docker-compose --profile z up -d   # Z.AI"
echo ""
echo "  Ports: a=18790  o=18791  g=18792  z=18793"
echo ""
echo "  On first run each provider will show a WhatsApp QR code."
echo "  View it with: docker logs -f nasopenclaw-a  (or -o/-g/-z)"
