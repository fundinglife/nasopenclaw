# nasopenclaw — OpenClaw for Synology NAS

> Forked from [phioranex/openclaw-docker](https://github.com/phioranex/openclaw-docker)

OpenClaw Docker deployment adapted for Synology NAS running DSM 7.x with Docker 20.10.x (no Compose v2 plugin). Uses plain `docker run` commands and Synology-native paths.

## Why this fork?

Synology DSM 7 ships Docker 20.10.x with only **docker-compose v1** (standalone binary). OpenClaw's official installer and phioranex's scripts require `docker compose` (v2 plugin) which is not available. This fork replaces all `docker compose` calls with plain `docker run` commands that work on DSM 7 as-is.

## Requirements

- Synology NAS with DSM 7.x
- Docker package installed via Package Center
- SSH access enabled (Control Panel → Terminal & SNMP)

## Install

SSH into your NAS, then:

```bash
curl -fsSL https://raw.githubusercontent.com/fundinglife/nasopenclaw/main/install-nas.sh | bash
```

Or clone and run locally:

```bash
git clone https://github.com/fundinglife/nasopenclaw.git /volume1/docker/nasopenclaw-repo
bash /volume1/docker/nasopenclaw-repo/install-nas.sh
```

The installer will:
1. Create `/volume1/docker/nasopenclaw/data` and `/volume1/docker/nasopenclaw/workspace`
2. Set correct ownership for the container's node user (UID 1000)
3. Pull `ghcr.io/phioranex/openclaw-docker:latest`
4. Write helper scripts to `/volume1/docker/nasopenclaw/scripts/`
5. Run the OpenClaw onboarding wizard
6. Start the gateway

## Data locations

| Path | Purpose |
|------|---------|
| `/volume1/docker/nasopenclaw/data/` | Config, memory, credentials, auth tokens |
| `/volume1/docker/nasopenclaw/workspace/` | Agent workspace (files the agent can read/write) |
| `/volume1/docker/nasopenclaw/scripts/` | Helper scripts |

## Daily use scripts

```bash
# Start gateway
bash /volume1/docker/nasopenclaw/scripts/start.sh

# Stop gateway
bash /volume1/docker/nasopenclaw/scripts/stop.sh

# Run onboarding again (re-configure provider, add channels)
bash /volume1/docker/nasopenclaw/scripts/onboard.sh

# Run any CLI command (replaces "docker compose run --rm openclaw-cli <cmd>")
bash /volume1/docker/nasopenclaw/scripts/cli.sh devices list
bash /volume1/docker/nasopenclaw/scripts/cli.sh devices approve <requestId>
bash /volume1/docker/nasopenclaw/scripts/cli.sh dashboard --no-open

# Pull latest image and restart
bash /volume1/docker/nasopenclaw/scripts/update.sh
```

## DSM Task Scheduler auto-start

To have the gateway start automatically on NAS boot:

1. Open **DSM → Control Panel → Task Scheduler**
2. Click **Create → Triggered Task → User-defined script**
3. Configure:
   - **Task name:** nasopenclaw-gateway
   - **User:** root
   - **Event:** Boot-up
4. In **Task Settings → Run command**, paste:
   ```bash
   bash /volume1/docker/nasopenclaw/scripts/start.sh
   ```
5. Click **OK**

To test without rebooting: select the task and click **Run**.

## Permissions fix

If you see `EACCES: permission denied` errors in container logs:

```bash
sudo chown -R 1000:1000 /volume1/docker/nasopenclaw/data
sudo chown -R 1000:1000 /volume1/docker/nasopenclaw/workspace
```

## Provider authentication (OAuth)

**Codex (ChatGPT Plus OAuth):**
The onboarding wizard handles device flow. When prompted, open the URL in a browser on any device, complete login, then paste the callback URL back into the terminal.

**Gemini CLI OAuth:**
```bash
bash /volume1/docker/nasopenclaw/scripts/cli.sh models auth login --provider google-gemini-cli
```

**GitHub Copilot OAuth:**
During onboarding, select GitHub Copilot → navigate to `github.com/login/device` → enter the code shown.

**Z.AI / GLM (API key):**
Set `ANTHROPIC_API_KEY=<your-zai-key>` and `ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic/v1` when prompted during onboarding, or add to openclaw.json after setup.

## Accessing the dashboard remotely

OpenClaw's Control UI runs on port 18789. To access it securely from outside your network, expose it via a Cloudflare Tunnel (do **not** expose it directly to the internet — leaked gateway tokens give full agent access).

## Updating

```bash
bash /volume1/docker/nasopenclaw/scripts/update.sh
```

The phioranex image auto-builds daily and tracks the latest OpenClaw release.

## Upstream

- **OpenClaw:** https://github.com/openclaw/openclaw
- **phioranex image:** https://github.com/phioranex/openclaw-docker
- **OpenClaw docs:** https://docs.openclaw.ai
- **ClawHub skills:** https://github.com/VoltAgent/awesome-openclaw-skills
