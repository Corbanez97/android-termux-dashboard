module.exports = {
  apps: [
    {
      name: "dashboard-api",
      cwd: "/data/data/com.termux/files/home/projects/android-termux-dashboard",
      script: "/data/data/com.termux/files/usr/bin/bash",
      args: "-lc '.venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8501'",
      interpreter: "none",
      autorestart: true,
      max_restarts: 20,
      min_uptime: "10s",
      merge_logs: true,
      env: {
        DASHBOARD_AUTO_REFRESH_SECONDS: "15",
        DASHBOARD_HISTORY_LIMIT: "720",
        DASHBOARD_SAMPLE_INTERVAL_SECONDS: "60"
      }
    },
    {
      name: "wol-api",
      cwd: "/data/data/com.termux/files/home/projects/wol",
      script: "/data/data/com.termux/files/usr/bin/bash",
      args: "-lc '.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8502'",
      interpreter: "none",
      autorestart: true,
      max_restarts: 20,
      min_uptime: "10s",
      merge_logs: true
    }
  ]
};
