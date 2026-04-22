# Android Termux Dashboard

A structured FastAPI dashboard for a Termux-hosted Android device, developed locally and deployed over SSH.

## Project layout

```text
android-termux-dashboard/
├─ app.py
├─ ecosystem.config.cjs
├─ requirements.txt
├─ dashboard/
│  ├─ main.py
│  ├─ config.py
│  ├─ utils.py
│  ├─ services/
│  ├─ static/
│  └─ templates/
└─ scripts/
   ├─ ensure-services.sh
   ├─ deploy.sh
   └─ deploy.ps1
```

## What it tracks

- Device telemetry: battery, memory, storage, load, Wi-Fi, telephony, connectivity checks
- Service state: every PM2 process plus `sshd`
- Persistent uptime history: samples are written to `data/uptime-log.jsonl`
- Service bootstrap helper: `scripts/ensure-services.sh`

## Local workflow

Edit the project locally in:

```text
android-termux-dashboard/
```

Then deploy it to the device with either:

```bash
./scripts/deploy.sh
```

or on Windows:

```powershell
.\scripts\deploy.ps1
```

Both scripts:

- send the project to `android-termux`
- install Python dependencies on the device
- make shell scripts executable
- reload the PM2 ecosystem
- save the PM2 process list for reboot restore

## SSH setup

The deploy scripts assume you can SSH using the alias:

```text
android-termux
```

Example `~/.ssh/config` entry on your local machine:

```sshconfig
Host android-termux
    HostName [IP_ADDRESS]
    Port 8022
    User u0_a258
    IdentityFile ~/.ssh/id_ed25519
```

Adjust `HostName`, `Port`, `User`, and `IdentityFile` to match your device.

Quick checks:

```bash
ssh android-termux
```

```bash
scp README.md android-termux:~/README.test
```

## Deploying locally

### Bash

From the project root:

```bash
cd android-termux-dashboard
./scripts/deploy.sh
```

Optional environment overrides:

```bash
REMOTE_HOST=android-termux REMOTE_DIR=projects/android-termux-dashboard ./scripts/deploy.sh
```

### PowerShell

From the project root:

```powershell
cd .\android-termux-dashboard
.\scripts\deploy.ps1
```

Optional parameters:

```powershell
.\scripts\deploy.ps1 -RemoteHost android-termux -RemoteDir projects/android-termux-dashboard
```

## Device-side commands

Useful commands once deployed:

```sh
cd ~/projects/android-termux-dashboard
./scripts/ensure-services.sh
pm2 logs dashboard-api
pm2 logs wol-api
pm2 save
sv status /data/data/com.termux/files/usr/var/service/sshd
```

## Boot persistence

Termux boot can call `scripts/ensure-services.sh` so PM2 resurrects and reloads both APIs after a reboot.

Expected boot helpers on the device:

`~/.termux/boot/start-apis`

```sh
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
/data/data/com.termux/files/home/projects/android-termux-dashboard/scripts/ensure-services.sh
```

`~/.termux/boot/start-sshd`

```sh
#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
sv up /data/data/com.termux/files/usr/var/service/sshd >/dev/null 2>&1 || sshd
```

## Adding PM2 services

The dashboard reads PM2 services dynamically from `pm2 jlist`, so any PM2 app that is online will appear automatically.

To add a service to the managed ecosystem in this repo:

1. Edit `ecosystem.config.cjs`.
2. Add another entry to `apps`.
3. Deploy with `./scripts/deploy.sh` or `.\scripts\deploy.ps1`.

Example:

```js
{
  name: "my-api",
  cwd: "/data/data/com.termux/files/home/projects/my-api",
  script: "/data/data/com.termux/files/usr/bin/bash",
  args: "-lc '.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8600'",
  interpreter: "none",
  autorestart: true,
  max_restarts: 20,
  min_uptime: "10s",
  merge_logs: true
}
```

If you start a PM2 service outside this ecosystem file, it will still be visible in the dashboard, but `scripts/ensure-services.sh` will not manage it unless it is in `ecosystem.config.cjs`.

## Adding runit services

The dashboard currently includes explicit uptime tracking for `sshd`, which is managed by Termux runit.

If you want to add more runit services, extend `dashboard/services/runtime.py` with another collector similar to `get_sshd_service()`.

Typical Termux runit service location:

```text
/data/data/com.termux/files/usr/var/service/<service-name>
```

Useful commands:

```sh
sv status /data/data/com.termux/files/usr/var/service/<service-name>
sv up /data/data/com.termux/files/usr/var/service/<service-name>
sv down /data/data/com.termux/files/usr/var/service/<service-name>
```

To surface a new runit service in the dashboard:

1. Add a function in `dashboard/services/runtime.py` that inspects its PID and uptime.
2. Append that service to `collect_service_status()`.
3. Deploy the project again.
