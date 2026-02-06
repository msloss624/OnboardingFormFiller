# Deploying RFI AutoFiller to Azure

## What you'll end up with
A URL like `https://rfi-autofiller.azurewebsites.net` that you open in a browser.
No local install needed. Just bookmark it.

---

## Option A: Azure App Service (Recommended — simplest)

**Cost:** ~$13/month (B1 plan) or free tier available
**Time:** ~15 minutes

### Step 1: Create a GitHub repo
1. Go to github.com → New repository
2. Name: `rfi-autofiller`, Private
3. Push this entire folder to it:
   ```bash
   cd rfi-autofiller
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/rfi-autofiller.git
   git push -u origin main
   ```

### Step 2: Create Azure resources
Go to [Azure Portal](https://portal.azure.com):

1. **Create a Resource Group**
   - Search "Resource groups" → Create
   - Name: `rfi-autofiller-rg`
   - Region: East US (or closest to you)

2. **Create a Web App**
   - Search "App Services" → Create → Web App
   - Name: `rfi-autofiller` (this becomes your URL)
   - Resource Group: `rfi-autofiller-rg`
   - Publish: **Docker Container**
   - OS: **Linux**
   - Region: same as above
   - Pricing: **B1** ($13/mo) or **F1** (free, limited)
   - Click Next until Docker tab

3. **Docker tab**
   - Options: Single Container
   - Image Source: GitHub Actions (or you can build locally)
   - Skip this for now, we'll configure deployment next

   OR simpler: choose **Code** instead of Docker:
   - Runtime stack: **Python 3.11**
   - Startup command: `pip install -r requirements.txt && streamlit run app.py --server.port 8000 --server.address 0.0.0.0 --server.headless true`

### Step 3: Set environment variables
In the Azure Portal → your App Service → **Configuration** → **Application settings**:

Add these:
| Name | Value |
|------|-------|
| `HUBSPOT_API_KEY` | Your HubSpot private app token |
| `FIREFLIES_API_KEY` | Your Fireflies API key |
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `WEBSITES_PORT` | `8501` |

Click **Save**.

### Step 4: Deploy from GitHub
In Azure Portal → your App Service → **Deployment Center**:
1. Source: **GitHub**
2. Sign in to GitHub
3. Select your repo: `rfi-autofiller`
4. Branch: `main`
5. Azure will create a GitHub Actions workflow automatically
6. Click Save

Every time you push to `main`, it auto-deploys.

### Step 5: Visit your app
Go to: `https://rfi-autofiller.azurewebsites.net`

---

## Option B: Azure Container Apps (more robust, slightly more setup)

Better if you want auto-scaling or plan to add more services later.

### Step 1: Build & push Docker image
```bash
# Install Azure CLI if needed
# brew install azure-cli  (Mac)
# winget install Microsoft.AzureCLI  (Windows)

az login
az acr create --resource-group rfi-autofiller-rg --name rfiautofilleracr --sku Basic
az acr login --name rfiautofilleracr

docker build -t rfiautofilleracr.azurecr.io/rfi-autofiller:latest .
docker push rfiautofilleracr.azurecr.io/rfi-autofiller:latest
```

### Step 2: Create Container App
```bash
az containerapp create \
  --name rfi-autofiller \
  --resource-group rfi-autofiller-rg \
  --image rfiautofilleracr.azurecr.io/rfi-autofiller:latest \
  --target-port 8501 \
  --ingress external \
  --env-vars \
    HUBSPOT_API_KEY=your_key \
    FIREFLIES_API_KEY=your_key \
    ANTHROPIC_API_KEY=your_key
```

---

## Troubleshooting

**App won't start?**
- Check Logs: App Service → Log stream
- Make sure WEBSITES_PORT=8501 is set
- Make sure all 3 API keys are set in Configuration

**Slow first load?**
- Streamlit cold-starts can take 10-15 seconds
- B1 plan keeps the app warm; F1 (free) will sleep after inactivity

**Need to update?**
- Just push to GitHub. Auto-deploys in ~2 minutes.
