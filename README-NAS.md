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
| `g` | Google / Gemini | 18792 | API key |
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
- `GEMINI_API_KEY` — if using profile `g`
- `ZAI_API_KEY` — if using profile `z`
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

## Codex OAuth (profile o — one-time only)

Codex uses OAuth rather than an API key. You already did this, but for reference:
```bash
# On the NAS as root:
codex login --device-code
# Opens a URL — visit it in any browser, complete login
# Token saved to /root/.codex/auth.json
# Mounted read-only into the container automatically
```

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
│   │   └── openclaw.z.json
│   └── scripts/
└── nasopenclaw/            ← runtime data (created by setup-nas.sh)
    ├── data-a/             ← Claude session, memory, WhatsApp
    ├── data-o/             ← Codex session, memory, WhatsApp
    ├── data-g/             ← Gemini session, memory, WhatsApp
    ├── data-z/             ← Z.AI session, memory, WhatsApp
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

## Notes on Gemini OAuth

The `google-gemini-cli-auth` plugin has an open bug (missing `client_secret`) as of Feb 2026. Profile `g` uses an API key instead. Get a free key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) — free tier is 1000 requests/day, 60 RPM.

## Upstream

- OpenClaw: https://github.com/openclaw/openclaw
- phioranex image: https://github.com/phioranex/openclaw-docker
- OpenClaw docs: https://docs.openclaw.ai
- ClawHub skills: https://github.com/VoltAgent/awesome-openclaw-skills
