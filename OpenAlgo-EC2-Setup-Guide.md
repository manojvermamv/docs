# 📘 OpenAlgo EC2 Production Setup Guide (Automated)

This guide explains how to install, configure, and run OpenAlgo on a fresh AWS EC2 instance with **systemd (background service)**, using `uv` as the Python runtime manager.

---

# 🚀 1. Fresh Server Login (EC2)

```bash
ssh -i your-key.pem ec2-user@<EC2_PUBLIC_IP>
```

---

# 🧹 2. Clean Previous Installations (IMPORTANT)

If you are reinstalling, remove old broken setups:

```bash
sudo systemctl stop openalgo 2>/dev/null
sudo systemctl disable openalgo 2>/dev/null
sudo rm -f /etc/systemd/system/openalgo.service
sudo systemctl daemon-reload
```

Remove old project (if needed):

```bash
rm -rf /home/ec2-user/openalgo
```

Remove broken venv (if exists):

```bash
rm -rf /home/ec2-user/openalgo/.venv
```

---

# 📥 3. Clone OpenAlgo Repository

```bash
cd /home/ec2-user
git clone <YOUR_OPENALGO_REPO_URL> openalgo
cd openalgo
```

---

# 🐍 4. Install uv (Python runtime manager)

```bash
curl -Ls https://astral.sh/uv/install.sh | sh
```

Activate path:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Verify:

```bash
uv --version
```

---

# 📦 5. Setup Project Dependencies (Stable Python 3.11)

Inside project folder:

```bash
cd /home/ec2-user/openalgo
uv python install 3.11
uv venv --python 3.11
uv sync
```

This will:

- Install stable **Python 3.11** (DO NOT use 3.14+ for production yet)
- Create `.venv` tied to Python 3.11
- Install dependencies
- Prepare runtime environment

---

# 🔐 6. Fix Permissions (CRITICAL)

Ensure correct ownership and safe permissions:

```bash
sudo chown -R ec2-user:ec2-user /home/ec2-user/openalgo
chmod -R u+rwX /home/ec2-user/openalgo
```

---

# ⚙️ 7. Configure Environment (.env)

Edit configuration:

```bash
nano .env
```

Update:

```env
FLASK_HOST_IP='0.0.0.0'
FLASK_PORT='5000'

HOST_SERVER='http://<EC2_PUBLIC_IP>:5000'
REDIRECT_URL='http://<EC2_PUBLIC_IP>:5000/<broker>/callback'
```

---

# 🧪 8. Test Run (Manual)

Before systemd setup, test manually:

```bash
cd /home/ec2-user/openalgo
uv run python --version
```

**CRITICAL:** Ensure it says `Python 3.11.x`. If it says `3.14.x`, delete `.venv` and recreate it with `--python 3.11`.

Run the app:

```bash
uv run app.py
```

If working:

- Open browser → `http://<EC2_PUBLIC_IP>:5000`
- Or test via terminal: `curl http://localhost:5000`

**Note:** If the app is listening on `8765` instead of `5000`, verify your `.env` or check if it's a websocket server. 

Verify listening port:

```bash
sudo ss -tulnp | grep 5000
```

Expected:
`LISTEN 0 128 0.0.0.0:5000`

Stop with:

```bash
CTRL + C
```

---

# 🔧 9. Create systemd Service (Background Run)

Create service file:

```bash
sudo nano /etc/systemd/system/openalgo.service
```

Paste:

```ini
[Unit]
Description=OpenAlgo Service
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/openalgo

EnvironmentFile=/home/ec2-user/openalgo/.env
Environment=PYTHONUNBUFFERED=1

ExecStart=/home/ec2-user/.local/bin/uv run app.py

Restart=always
RestartSec=5

KillMode=control-group
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

---

# 🔄 10. Enable & Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable openalgo
sudo systemctl start openalgo
```

---

# 📊 11. Check Status

```bash
sudo systemctl status openalgo
```

Expected:

```text
Active: active (running)
```

---

# 📜 12. View Logs

```bash
journalctl -u openalgo -f
```

---

# ⛔ 13. Stop / Restart Service

Stop:

```bash
sudo systemctl stop openalgo
```

Restart:

```bash
sudo systemctl restart openalgo
```

Disable auto-start:

```bash
sudo systemctl disable openalgo
```

---

# 🌐 14. Access OpenAlgo

Open in browser:

```
http://<EC2_PUBLIC_IP>:5000
```

---

# 🔥 15. Open AWS Security Group Ports

Ensure inbound rules:

| Type | Port | Source    |
| ---- | ---- | --------- |
| HTTP | 5000 | 0.0.0.0/0 |
| SSH  | 22   | Your IP   |

---

# 🧯 16. Troubleshooting

## ❌ uv not found

```bash
export PATH="$HOME/.local/bin:$PATH"
```

---

## ❌ Permission denied (.venv)

```bash
rm -rf .venv
uv sync
```

---

## ❌ systemd fails

```bash
journalctl -u openalgo -n 100 --no-pager
```

---

## ❌ App not accessible / Stability Issues

If you see `RuntimeError: cannot schedule new futures after interpreter shutdown` or the server hangs:

1. **Check Python Version:** `uv run python --version` (Must be 3.11)
2. **Check Ports:** `sudo ss -tulnp | grep LISTEN`
3. **Security group:** Open port 5000 in AWS Console.

---

## 🛠️ Recommended Clean Reinstall (Python 3.11)

If your environment is broken or using Python 3.14:

```bash
# 1. Stop Service
sudo systemctl stop openalgo

# 2. Remove Broken Environment
cd /home/ec2-user/openalgo
rm -rf .venv
rm -rf ~/.local/share/uv/python

# 3. Install Stable Python
uv python install 3.11

# 4. Create Fresh venv
uv venv --python 3.11

# 5. Reinstall Dependencies
uv sync

# 6. Verify & Reload
uv run python --version  # Should be 3.11
sudo systemctl daemon-reload
sudo systemctl start openalgo
```

---

# 🏁 Final Result

After setup:

✔ OpenAlgo runs in background
✔ Auto starts on reboot
✔ Survives SSH disconnect
✔ Accessible via public IP
✔ Production-ready EC2 deployment

---

# 🚀 Production Recommendations

For real production deployment, consider these upgrades:

1. **WSGI Server:** Instead of `uv run app.py`, use **Gunicorn** or **Uvicorn**.
   ```bash
   uv add gunicorn  # or uv add uvicorn
   ```

   **Update `ExecStart` in service file:**

   For Flask (Gunicorn):
   ```ini
   ExecStart=/home/ec2-user/openalgo/.venv/bin/gunicorn -w 2 -b 0.0.0.0:5000 app:app
   ```

   For FastAPI (Uvicorn):
   ```ini
   ExecStart=/home/ec2-user/openalgo/.venv/bin/uvicorn app:app --host 0.0.0.0 --port 5000
   ```

2. **Reverse Proxy:** Use Nginx for SSL (HTTPS) and port forwarding.
3. **Process Groups:** We added `KillMode=control-group` to ensure all child threads (like APScheduler) are killed properly on restart.
4. **Environment Variables:** Use `EnvironmentFile` in systemd to load configurations directly from `.env`.

---

If you want, I can also convert this into:

✅ GitHub-ready README with badges
✅ One-click install shell script (`install.sh`)
✅ Docker deployment version
✅ Fully automated EC2 bootstrap script

Just tell me 👍
