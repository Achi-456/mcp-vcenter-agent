# Ubuntu Server Deployment Guide — vCenter AI Admin Stack

## Architecture

```
Your Laptop Browser
       |
http://serverip:80
       |
  [nginx:80]  ← serves dashboard HTML + proxies /api
       |
  [vcenter-api:8000]  ← FastAPI (internal only)
       |
  VMware vCenter (your existing infra)
```

---

## Step 1: Install Docker on Ubuntu Server

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add your user to docker group (no sudo needed)
sudo usermod -aG docker $USER
newgrp docker
```

---

## Step 2: Copy Project Files to Server

From your Windows laptop, use SCP or any SFTP tool:

```bash
# From your Windows laptop (PowerShell or WinSCP)
scp -r "C:\Users\achinthah\Desktop\my\Project\Gayan Ayya\*" ubuntu@<SERVER_IP>:/opt/vcenter-admin/
```

Or SSH into the server and clone/create the directory:

```bash
sudo mkdir -p /opt/vcenter-admin
sudo chown $USER:$USER /opt/vcenter-admin
```

---

## Step 3: Create the .env File on the Server

```bash
cd /opt/vcenter-admin
cp .env.example .env
nano .env
```

Fill in your real values:
```
ANTHROPIC_API_KEY=sk-ant-api03-your-real-key
VCENTER_HOST=core-infra-vc01.dclab.com
VCENTER_USER=administrator@vsphere.local
VCENTER_PASSWORD=your-real-password
VCENTER_PORT=443
```

---

## Step 4: Build and Start (First Time)

```bash
cd /opt/vcenter-admin

# Build the FastAPI image
docker compose build

# Start all services in the background
docker compose up -d
```

---

## Step 5: Verify It's Running

```bash
# Check container status
docker compose ps

# Check API logs
docker compose logs vcenter-api

# Check nginx logs
docker compose logs nginx

# Quick health test
curl http://localhost/api/status
```

---

## Step 6: Access from Your Laptop

Open your browser and navigate to:
```
http://<SERVER_IP>
```

You should see the **vCenter AI Dashboard**. Click **Connect** to link to vCenter, then use the AI chat on the right panel.

---

## Useful Management Commands

```bash
# Stop everything
docker compose down

# Restart after code changes
docker compose build vcenter-api && docker compose up -d

# View live logs
docker compose logs -f

# Update and redeploy
git pull  # or copy new files
docker compose build && docker compose up -d

# Check resource usage
docker stats
```

---

## Testing on Docker Desktop (Windows)

Before deploying to Ubuntu, test locally:

```powershell
# In PowerShell, from the project folder:
cd "C:\Users\achinthah\Desktop\my\Project\Gayan Ayya"

# Copy .env.example to .env and fill in your credentials
copy .env.example .env
notepad .env

# Build and run
docker compose build
docker compose up -d

# Open browser
start http://localhost
```

---

## Firewall (Ubuntu Server)

If using UFW, allow port 80:

```bash
sudo ufw allow 80/tcp
sudo ufw status
```

---

## Auto-Start on Server Reboot

The `restart: unless-stopped` policy in docker-compose.yml means containers restart automatically after a server reboot as long as the Docker daemon is enabled:

```bash
sudo systemctl enable docker
```
