# Deploying Onboarding Form Filler

## Current Production Setup

- **URL:** https://onboardingformfiller.azurewebsites.net
- **Hosting:** Azure App Service (B1 Linux, Python 3.11)
- **Region:** Canada Central
- **Resource Group:** Sales_Automations
- **Deploy method:** GitHub Actions with OIDC (push to `main`)

---

## How Deployment Works

1. Push to `main` branch
2. GitHub Actions workflow triggers automatically
3. Builds frontend (Node 22) into `backend/static/`
4. Packages backend (Python 3.11)
5. Deploys via OIDC to Azure App Service
6. Takes ~10 minutes total (build ~1 min, deploy ~9 min)

No manual steps needed. Just push code.

---

## Azure Resources

| Resource | Name | Purpose |
|----------|------|---------|
| App Service Plan | OnboardingFormFiller-plan | B1 Linux (~$13/mo) |
| App Service | OnboardingFormFiller | Hosts the app |
| Storage Account | onboardingffstorage | Excel exports (container: `exports`) |
| App Registration | OnboardingFormFiller | SSO + Graph API email |
| Service Principal | OnboardingFormFiller-GitHubDeploy | OIDC for GitHub Actions |

All resources are in the `Sales_Automations` resource group (canadacentral).

---

## Environment Variables (Azure App Service)

Set in Azure Portal > App Service > Configuration > Application settings:

| Name | Value |
|------|-------|
| `HUBSPOT_API_KEY` | HubSpot Private App token |
| `FIREFLIES_API_KEY` | Fireflies.ai API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `DATABASE_URL` | `sqlite+aiosqlite:////home/onboarding.db` |
| `BLOB_CONNECTION_STRING` | Azure Blob connection string |
| `AZURE_AD_TENANT_ID` | `a9f513ef-aa6e-44ab-8d9e-2aa8794e2fca` |
| `AZURE_AD_CLIENT_ID` | `c90b1890-870e-47c4-8b89-75b07a5adb1e` |
| `AZURE_AD_AUDIENCE` | `c90b1890-870e-47c4-8b89-75b07a5adb1e` |
| `GRAPH_CLIENT_ID` | Same app registration client ID |
| `GRAPH_TENANT_ID` | Same tenant ID |
| `GRAPH_CLIENT_SECRET` | Client secret (Certificates & secrets) |
| `GRAPH_SEND_FROM_EMAIL` | `info@belltec.com` |
| `ONBOARDING_TEAM_EMAIL` | Distribution list email |

**Note:** Changing env vars triggers a container swap (~1 min downtime).

---

## Graph API Email Setup

The app sends emails via Microsoft Graph API (client credentials flow).

### Prerequisites
1. `Mail.Send` **application permission** on the app registration
2. **Admin consent** granted (requires Global Administrator)
3. **Client secret** generated under Certificates & secrets
4. Optionally: Application Access Policy to restrict sending to specific mailboxes

### Grant admin consent (CLI)
```bash
az ad app permission admin-consent --id c90b1890-870e-47c4-8b89-75b07a5adb1e
```

### Grant admin consent (Portal)
App registrations > OnboardingFormFiller > API permissions > Grant admin consent

Without `GRAPH_CLIENT_SECRET`, the app runs in dry-run mode (logs email payload, doesn't send).

---

## Troubleshooting

**App won't start?**
- Check logs: App Service > Log stream
- Verify all required env vars are set

**Deploy stuck?**
- Check GitHub Actions tab for build errors
- OIDC deploy is reliable; if issues, check service principal hasn't expired

**Database issues?**
- SQLite lives at `/home/onboarding.db` (persistent across restarts)
- `/home` is the only persistent directory on App Service
- Migrations run automatically on startup

**Email not sending?**
- Check `GRAPH_CLIENT_SECRET` is set (otherwise dry-run mode)
- Verify `Mail.Send` permission has admin consent
- Check app logs for Graph API error details
