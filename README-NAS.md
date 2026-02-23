# nasopenclaw

OpenClaw for Synology NAS — forked from [phioranex/openclaw-docker](https://github.com/phioranex/openclaw-docker).

Four providers, one repo, one compose file with profiles. Each provider is isolated (separate data dir, separate WhatsApp session). No wizard — configs are pre-baked.

## Requirements

- Synology DSM 7.x with Docker package installed
- docker-compose v1.28.5 (bundled with DSM 7 — profiles supported from v1.28.0 ✅)
- SSH access enabled

## Providers

| Profile | Provider | Port | Auth |
|---------|----------|------|------|
| `a` | Anthropic / Claude | 18790 | API key |
| `o` | OpenAI / Codex | 18791 | OAuth (one-time device flow) |
| `g` | Google / Gemini | 18792 | CLIProxy on RO-WIN (no key needed) |
| `z` | Z.AI / GLM | 18793 | API key |

Only run **one profile at a time** — each has its own WhatsApp session stored in a separate data dir. Running two simultaneously will conflict.

## First-time setup

**1. SSH into the NAS and clone the repo:**
```bash
ssh rohitsoni@ro-nas
cd /volume1/docker
git clone https://github.com/fundinglife/nasopenclaw.git nasopenclaw-repo
cd nasopenclaw-repo
```

**2. Run one-time setup (creates dirs, sets permissions, pulls image):**
```bash
bash scripts/setup-nas.sh
```

**3. Copy your keys into `.env`:**
```bash
cp .env.example .env
nano .env   # or vi .env
```

Fill in:
- `WHATSAPP_NUMBER` — your number in E.164 format e.g. `+12025550123`
- `ANTHROPIC_API_KEY` — if using profile `a`
- `ZAI_API_KEY` — if using profile `z`
- Profile `g` (Gemini) needs no key — Gemini is routed through CLIProxy on RO-WIN (see below)
- Profile `o` (Codex) needs no key here — see OAuth section below

**4. Symlink configs to the data directory:**
```bash
ln -sf /volume1/docker/nasopenclaw-repo/configs /volume1/docker/nasopenclaw/configs
```

**5. Start a provider:**
```bash
docker-compose --profile a up -d   # Claude
docker-compose --profile o up -d   # Codex
docker-compose --profile g up -d   # Gemini
docker-compose --profile z up -d   # Z.AI
```

**6. Scan WhatsApp QR (first run only per provider):**
```bash
docker logs -f nasopenclaw-a   # swap letter for your profile
```
A QR code will appear in the logs. Scan it with WhatsApp → Linked Devices.

## Gemini via CLIProxy (profile g)

Profile `g` routes Gemini through **CLIProxy** running on RO-WIN (192.168.68.165) rather than
using a Gemini API key. CLIProxy uses Gemini CLI OAuth (`familyshareuniversal@gmail.com`) and
exposes an OpenAI-compatible endpoint at `https://aiproxy.rohitsoni.com`.

**Dependency:** RO-WIN must be on and the Cloudflare tunnel must be running. If the NAS can't
reach `aiproxy.rohitsoni.com`, nasopenclaw-g will fail to respond.

**Models available via `/model`:**
- `cliproxy/gemini-2.5-pro` (alias: `pro`) — primary
- `cliproxy/gemini-2.5-flash` (alias: `flash`) — fallback
- `cliproxy/gemini-2.5-flash-lite` (alias: `lite`) — fallback

**If Gemini stops working** (token expired), re-authenticate on RO-WIN:
```powershell
docker exec -it cli-proxy-api ./CLIProxyAPI -login
# Follow the OAuth flow in your browser
# Callback port: 8085
```

## Codex OAuth (profile o — one-time only)

Codex uses OAuth via OpenClaw's built-in onboarding. The config for profile `o` is NOT
mounted from configs/ — it lives in data-o/openclaw.json and is written by onboarding.

```bash
# Run onboarding (only needed if data-o is wiped):
docker run -it --rm \
  -v /volume1/docker/nasopenclaw/data-o:/home/node/.openclaw \
  -v /volume1/docker/nasopenclaw/workspace:/home/node/.openclaw/workspace \
  --env-file /volume1/docker/nasopenclaw-repo/.env \
  ghcr.io/phioranex/openclaw-docker:latest onboard --auth-choice openai-codex

# After onboarding completes, patch allowlist into the generated config:
cat > /tmp/patch_config.py << 'EOF'
import json
with open('/volume1/docker/nasopenclaw/data-o/openclaw.json') as f:
    cfg = json.load(f)
cfg['channels']['whatsapp']['dmPolicy'] = 'allowlist'
cfg['channels']['whatsapp']['allowFrom'] = ['+13019961639']
with open('/volume1/docker/nasopenclaw/data-o/openclaw.json', 'w') as f:
    json.dump(cfg, f, indent=2)
print('done')
EOF
python3 /tmp/patch_config.py
```

## Credentials backup (profile o)

WhatsApp session credentials are precious — re-pairing requires phone access.
Backups live at:
- `/volume1/docker/nasopenclaw/data-o/credentials.bak`  (inside data-o)
- `/volume1/docker/nasopenclaw_creds_backup_o`           (outside data-o, safe if data-o wiped)

To restore: `cp -r /volume1/docker/nasopenclaw_creds_backup_o /volume1/docker/nasopenclaw/data-o/credentials`

## Updating the `all` profile config

Unlike other profiles, `nasopenclaw-all` does NOT mount its config read-only. OpenClaw must be able to write to `openclaw.json` at runtime (plugin state, meta, etc). The config lives in `data-all/openclaw.json`.

`configs/openclaw.all.json` in this repo is the **source of truth**. After changing it, deploy to NAS:

```bash
# On NAS after git pull:
cp /volume1/docker/nasopenclaw/configs/openclaw.all.json /volume1/docker/nasopenclaw/data-all/openclaw.json
chown 1000:1000 /volume1/docker/nasopenclaw/data-all/openclaw.json
chmod 644 /volume1/docker/nasopenclaw/data-all/openclaw.json
docker-compose --profile all down && docker-compose --profile all up -d
```

**WhatsApp credentials** are in `data-all/credentials/` — do NOT wipe this directory. They are shared with `data-o` (same device slot). Backup lives at `/volume1/docker/nasopenclaw_creds_backup_all`.

## Daily commands

```bash
# Start
docker-compose --profile a up -d

# Stop
docker-compose --profile a down

# View logs (including WhatsApp QR on first run)
docker logs -f nasopenclaw-a

# Update image and restart
bash scripts/update.sh
```

## Switching providers

Stop the current one, start the other. Each has its own WhatsApp session so you'll need to re-scan QR if switching to a provider that hasn't been paired yet.

```bash
docker-compose --profile a down
docker-compose --profile g up -d
docker logs -f nasopenclaw-g   # scan QR if first time
```

## DSM Task Scheduler auto-start

To auto-start your default provider on NAS boot:

1. DSM → Control Panel → Task Scheduler → Create → Triggered Task → User-defined script
2. User: `root`, Event: `Boot-up`
3. Run command:
```bash
cd /volume1/docker/nasopenclaw-repo && docker-compose --env-file .env --profile a up -d
```
4. Change `a` to whichever profile you want as default.

## Directory layout on NAS

```
/volume1/docker/
├── nasopenclaw-repo/       ← git clone (this repo)
│   ├── docker-compose.yml
│   ├── .env                (gitignored — your keys)
│   ├── configs/
│   │   ├── openclaw.a.json
│   │   ├── openclaw.o.json
│   │   ├── openclaw.g.json
│   │   ├── openclaw.z.json
│   │   └── openclaw.all.json
│   ├── scripts/
│   └── tools/              ← Python agent tools (run on RO-WIN via SSH)
└── nasopenclaw/            ← runtime data (created by setup-nas.sh)
    ├── data-a/             ← Claude session, memory, WhatsApp
    ├── data-o/             ← Codex session, memory, WhatsApp
    ├── data-g/             ← Gemini session, memory, WhatsApp
    ├── data-z/             ← Z.AI session, memory, WhatsApp
    ├── data-all/           ← All-in-one session (Claude + Gemini)
    └── workspace/          ← shared workspace (all providers)
```

## Permissions fix

If you see `EACCES: permission denied` in container logs:
```bash
sudo chown -R 1000:1000 /volume1/docker/nasopenclaw/data-a
# repeat for data-o, data-g, data-z as needed
```

## Config validation

If a container exits immediately, check for config errors:
```bash
docker logs nasopenclaw-a
# Look for "Invalid config" — fix the relevant configs/openclaw.*.json
```

## Notes on Gemini

Profile `g` uses CLIProxy on RO-WIN (Gemini CLI OAuth via `familyshareuniversal@gmail.com`).
No API key required. See the "Gemini via CLIProxy" section above for re-auth instructions.

The previous `google-gemini-cli-auth` OpenClaw plugin approach was abandoned — it had an
unresolved `client_secret` bug and ToS violation risk. CLIProxy solves both cleanly.

## Files not used by the NAS setup

These files are inherited from the upstream [phioranex/openclaw-docker](https://github.com/phioranex/openclaw-docker) fork and are **not used** in the NAS compose-based workflow. They remain in the repo for upstream compatibility.

| File | Purpose (upstream) | Why unused here |
|------|--------------------|-----------------|
| `README.md` | Upstream Docker image docs | NAS docs are in `README-NAS.md` |
| `install.sh` | One-liner Linux/Mac installer | NAS uses `scripts/setup-nas.sh` + compose profiles |
| `install.ps1` | One-liner Windows installer | NAS uses `scripts/setup-nas.sh` + compose profiles |
| `uninstall.sh` | One-liner Linux/Mac uninstaller | NAS: just `docker-compose --profile X down` |
| `uninstall.ps1` | One-liner Windows uninstaller | NAS: just `docker-compose --profile X down` |
| `Dockerfile` | Builds the Docker image | NAS pulls pre-built image from `ghcr.io` |
| `.github/workflows/` | CI to build and push the image | Only runs on the upstream phioranex repo |
| `.last-openclaw-version` | Tracks upstream release for CI | Only used by the CI workflow above |

## Upstream

- OpenClaw: https://github.com/openclaw/openclaw
- phioranex image: https://github.com/phioranex/openclaw-docker
- OpenClaw docs: https://docs.openclaw.ai
- ClawHub skills: https://github.com/VoltAgent/awesome-openclaw-skills
