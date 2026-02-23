#!/bin/bash
#
# nasopenclaw - OpenClaw installer for Synology NAS
# Forked from phioranex/openclaw-docker
#
# Designed for:
#   - Synology DSM 7.x
#   - Docker 20.10.x (docker-compose v1, NO compose v2 plugin)
#   - Docker binary at /volume1/@appstore/Docker/usr/bin/docker
#
# Usage (run via SSH on NAS):
#   bash install-nas.sh
#
# Or with options:
#   bash install-nas.sh --skip-onboard
#   bash install-nas.sh --no-start
#

set -e

# ── Config ─────────────────────────────────────────────────────────────────
DOCKER="/volume1/@appstore/Docker/usr/bin/docker"
INSTALL_DIR="/volume1/docker/nasopenclaw"
DATA_DIR="$INSTALL_DIR/data"
WORKSPACE_DIR="$INSTALL_DIR/workspace"
SCRIPTS_DIR="$INSTALL_DIR/scripts"
IMAGE="ghcr.io/phioranex/openclaw-docker:latest"
CONTAINER_NAME="nasopenclaw-gateway"
# Node user UID inside the phioranex image
CONTAINER_UID=1000
CONTAINER_GID=1000
PORT=18789

# ── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

# ── Flags ───────────────────────────────────────────────────────────────────
NO_START=false
SKIP_ONBOARD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-start)    NO_START=true;    shift ;;
        --skip-onboard) SKIP_ONBOARD=true; shift ;;
        --help|-h)
            echo "nasopenclaw installer for Synology NAS"
            echo "Usage: bash install-nas.sh [--no-start] [--skip-onboard]"
            exit 0 ;;
        *) echo -e "${RED}Unknown option: $1${NC}"; exit 1 ;;
    esac
done

# ── Helpers ──────────────────────────────────────────────────────────────────
step()    { echo -e "\n${BLUE}▶${NC} ${BOLD}$1${NC}"; }
ok()      { echo -e "${GREEN}✓${NC} $1"; }
warn()    { echo -e "${YELLOW}⚠${NC} $1"; }
err()     { echo -e "${RED}✗${NC} $1"; }

# ── Banner ───────────────────────────────────────────────────────────────────
echo -e "${RED}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║       nasopenclaw — OpenClaw for Synology NAS            ║"
echo "║       Forked from phioranex/openclaw-docker              ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ── Pre-flight ────────────────────────────────────────────────────────────────
step "Checking Docker..."
if [[ ! -x "$DOCKER" ]]; then
    err "Docker binary not found at $DOCKER"
    echo "Install the Docker package via Synology Package Center first."
    exit 1
fi
ok "Docker found: $($DOCKER --version)"

if ! $DOCKER info &>/dev/null; then
    err "Docker daemon is not running"
    exit 1
fi
ok "Docker daemon is running"

# ── Directories ───────────────────────────────────────────────────────────────
step "Creating directories..."
mkdir -p "$DATA_DIR" "$WORKSPACE_DIR" "$SCRIPTS_DIR"
# Set ownership to container's node user so volumes are writable
chown -R "${CONTAINER_UID}:${CONTAINER_GID}" "$DATA_DIR" "$WORKSPACE_DIR" 2>/dev/null || \
    warn "Could not chown dirs — run as root if permission errors occur"
ok "Created $DATA_DIR"
ok "Created $WORKSPACE_DIR"

# ── Pull image ────────────────────────────────────────────────────────────────
step "Pulling OpenClaw image..."
$DOCKER pull "$IMAGE"
ok "Image pulled: $IMAGE"

# ── Generate scripts ──────────────────────────────────────────────────────────
step "Writing helper scripts to $SCRIPTS_DIR..."

# start.sh
cat > "$SCRIPTS_DIR/start.sh" <<STARTSCRIPT
#!/bin/bash
# Start nasopenclaw gateway
DOCKER="/volume1/@appstore/Docker/usr/bin/docker"
IMAGE="ghcr.io/phioranex/openclaw-docker:latest"
CONTAINER="nasopenclaw-gateway"
DATA_DIR="/volume1/docker/nasopenclaw/data"
WORKSPACE_DIR="/volume1/docker/nasopenclaw/workspace"
PORT=18789

# Remove stale container if exists
\$DOCKER rm -f "\$CONTAINER" 2>/dev/null || true

\$DOCKER run -d \\
  --name "\$CONTAINER" \\
  --restart unless-stopped \\
  -v "\$DATA_DIR:/home/node/.openclaw" \\
  -v "\$WORKSPACE_DIR:/home/node/.openclaw/workspace" \\
  -p "\$PORT:\$PORT" \\
  -e NODE_ENV=production \\
  -e OPENCLAW_SKIP_SERVICE_CHECK=true \\
  "\$IMAGE" gateway

echo "nasopenclaw gateway started on port \$PORT"
STARTSCRIPT

# stop.sh
cat > "$SCRIPTS_DIR/stop.sh" <<STOPSCRIPT
#!/bin/bash
# Stop nasopenclaw gateway
DOCKER="/volume1/@appstore/Docker/usr/bin/docker"
\$DOCKER stop nasopenclaw-gateway 2>/dev/null && echo "Stopped." || echo "Not running."
STOPSCRIPT

# cli.sh — replacement for "docker compose run --rm openclaw-cli <command>"
cat > "$SCRIPTS_DIR/cli.sh" <<CLISCRIPT
#!/bin/bash
# Run an openclaw CLI command
# Usage: bash cli.sh <command> [args...]
# Example: bash cli.sh devices list
#          bash cli.sh devices approve <id>
#          bash cli.sh dashboard --no-open
DOCKER="/volume1/@appstore/Docker/usr/bin/docker"
IMAGE="ghcr.io/phioranex/openclaw-docker:latest"
DATA_DIR="/volume1/docker/nasopenclaw/data"
WORKSPACE_DIR="/volume1/docker/nasopenclaw/workspace"

\$DOCKER run -it --rm \\
  -v "\$DATA_DIR:/home/node/.openclaw" \\
  -v "\$WORKSPACE_DIR:/home/node/.openclaw/workspace" \\
  -e NODE_ENV=production \\
  --entrypoint node \\
  "\$IMAGE" /app/dist/index.js "\$@"
CLISCRIPT

# onboard.sh
cat > "$SCRIPTS_DIR/onboard.sh" <<ONBOARDSCRIPT
#!/bin/bash
# Run OpenClaw onboarding wizard
# Run this once on first install to configure provider, WhatsApp, etc.
DOCKER="/volume1/@appstore/Docker/usr/bin/docker"
IMAGE="ghcr.io/phioranex/openclaw-docker:latest"
DATA_DIR="/volume1/docker/nasopenclaw/data"
WORKSPACE_DIR="/volume1/docker/nasopenclaw/workspace"

\$DOCKER run -it --rm \\
  -v "\$DATA_DIR:/home/node/.openclaw" \\
  -v "\$WORKSPACE_DIR:/home/node/.openclaw/workspace" \\
  -e NODE_ENV=production \\
  "\$IMAGE" onboard
ONBOARDSCRIPT

# update.sh
cat > "$SCRIPTS_DIR/update.sh" <<UPDATESCRIPT
#!/bin/bash
# Pull latest image and restart gateway
DOCKER="/volume1/@appstore/Docker/usr/bin/docker"
IMAGE="ghcr.io/phioranex/openclaw-docker:latest"

echo "Pulling latest image..."
\$DOCKER pull "\$IMAGE"
echo "Restarting gateway..."
bash /volume1/docker/nasopenclaw/scripts/stop.sh
sleep 2
bash /volume1/docker/nasopenclaw/scripts/start.sh
echo "Update complete."
UPDATESCRIPT

chmod +x "$SCRIPTS_DIR"/*.sh
ok "Scripts written to $SCRIPTS_DIR"

# ── Onboarding ────────────────────────────────────────────────────────────────
if [[ "$SKIP_ONBOARD" == "false" ]]; then
    step "Running onboarding wizard..."
    echo -e "${YELLOW}Configure your AI provider, WhatsApp, and channels.${NC}"
    echo -e "${YELLOW}Follow the prompts. You can re-run onboarding later with:${NC}"
    echo -e "  bash $SCRIPTS_DIR/onboard.sh\n"

    if ! $DOCKER run -it --rm \
        -v "$DATA_DIR:/home/node/.openclaw" \
        -v "$WORKSPACE_DIR:/home/node/.openclaw/workspace" \
        -e NODE_ENV=production \
        "$IMAGE" onboard; then
        warn "Onboarding cancelled or failed. Re-run: bash $SCRIPTS_DIR/onboard.sh"
    else
        ok "Onboarding complete!"
    fi
fi

# ── Start gateway ─────────────────────────────────────────────────────────────
if [[ "$NO_START" == "false" ]]; then
    step "Starting gateway..."
    bash "$SCRIPTS_DIR/start.sh"

    echo -n "Waiting for gateway"
    for i in {1..20}; do
        if $DOCKER exec "$CONTAINER_NAME" wget -qO- http://localhost:$PORT/health &>/dev/null 2>&1; then
            echo ""; ok "Gateway is up!"; break
        fi
        echo -n "."; sleep 2
    done
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        nasopenclaw installed successfully!               ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"

NAS_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo -e "\n${BOLD}Dashboard:${NC}    http://${NAS_IP:-<NAS_IP>}:$PORT"
echo -e "${BOLD}Config:${NC}       $DATA_DIR"
echo -e "${BOLD}Workspace:${NC}    $WORKSPACE_DIR"
echo -e "\n${BOLD}Scripts:${NC}"
echo -e "  Start:     bash $SCRIPTS_DIR/start.sh"
echo -e "  Stop:      bash $SCRIPTS_DIR/stop.sh"
echo -e "  CLI:       bash $SCRIPTS_DIR/cli.sh <command>"
echo -e "  Onboard:   bash $SCRIPTS_DIR/onboard.sh"
echo -e "  Update:    bash $SCRIPTS_DIR/update.sh"
echo -e "\n${BOLD}Docs:${NC}         https://docs.openclaw.ai"
echo -e "${YELLOW}See README-NAS.md for DSM Task Scheduler auto-start setup.${NC}\n"
