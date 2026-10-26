# Running Daedalus for players

This folder holds the live world server stack: the Daedalus server, Redis, Caddy for TLS, and a backup job. It runs
on one host. Staging and live are two copies of the same stack.

Status (2026-10-13):
- The stack is written, `docker compose config` validates, and the shell scripts pass `sh -n`.
- It has not yet been run end to end on a cloud host. That needs a host, which is a spend and needs Richey's yes.
- Sharding (realm or district servers) comes from Astra's shard directory (ADR-065 follow-up).

## What you need
- A Linux VM with Docker. 4 vCPU and 16 GB is a reasonable start for testnet. Size it again from Astra's benchmarks
  before launch.
- A domain name with an A record pointing at the VM, for example `play.<yourdomain>`.
- Ports 80 and 443 open.

## First boot
```
git clone https://github.com/RicheyWorks/Daedalus2 && cd Daedalus2/deploy
cp env.example .env && ./gen-secrets.sh >> .env   # then edit DOMAIN and ACME_EMAIL in .env
docker compose up -d --build
docker compose ps                                    # server shows "healthy" after about 90 s
```
- Caddy fetches the TLS certificate by itself.
- Players connect at `https://<DOMAIN>`. In Unreal, set the DaedalusWorldActor **ServerUrl** to that address.

## Staging next to live
```
cp env.example staging.env   # its own DOMAIN, secrets, memory
docker compose -p daedalus-staging --env-file staging.env up -d --build
```
Try every upgrade on staging first.

## Backups
- The `backup` service writes `backups/daedalus-<UTC>.tar.gz` every 6 h and keeps 14 days. Each archive holds all
  worlds, gates, fleets, ecology and deeds, plus Redis.
- Copy `backups/` off the host every day, for example with `rclone sync backups remote:daedalus-backups`. A backup
  on the same disk is not a backup.
- To restore: `./restore.sh backups/daedalus-<stamp>.tar.gz`. It first saves what is there now.
- Run a restore drill weekly: `./restore-drill.sh`. It starts a throwaway server on the newest backup, checks that
  the worlds are served, and touches nothing live.

## Upgrades and rollback
- Set `DAEDALUS_VERSION=<git sha>` in `.env`, then `docker compose up -d --build`.
- To roll back, set the old tag and run `up -d`. The worlds volume is untouched by an image change. Back up before
  every upgrade.

## Watching it
- `GET /actuator/health` is public and is what the healthcheck uses.
- `/actuator/prometheus` serves metrics. Point an uptime monitor at `https://<DOMAIN>/actuator/health`.
- To see logs: `docker compose logs -f server`.

## Rules
- Testnet only (Sepolia). Mainnet, real money, sales and prices need Richey's explicit yes.
- `.env` holds secrets. It is git-ignored, so never paste it anywhere.
- The deed signer key is a no-funds key that only signs mint vouchers. Set it on the host only.
