# Deployment Guide

## Live URLs
- **Landing Page:** https://arprofm.com
- **Tech Portal:** https://arprofm.com/app
- **Render Direct:** https://liftlogic.onrender.com

## Account Ownership

| Service | Account | Purpose |
|---------|---------|---------|
| GitHub | fitgirlstarwars@gmail.com | Source code repository |
| Render | fitgirlstarwars@gmail.com | Hosting & deployment |
| Google Cloud | weshobbs85@gmail.com | OAuth & Gemini API |
| Porkbun | weshobbs85@gmail.com | Domain registrar (arprofm.com) |

## Repositories
- **LiftLogic:** https://github.com/Fitgirlstarwars/liftlogic
- **ARPRO Website (archived):** https://github.com/Fitgirlstarwars/arpro-website

## Render Configuration
- **Service Name:** liftlogic
- **Runtime:** Docker
- **Plan:** Free
- **Auto-deploy:** Enabled (on push to main)
- **Health Check:** /health

## DNS Configuration (Porkbun)
| Type | Host | Value |
|------|------|-------|
| A | (root) | 216.24.57.1 |
| CNAME | www | liftlogic.onrender.com |

## Google OAuth Setup
To enable Google Sign-In on production:

1. Go to https://console.cloud.google.com/ (weshobbs85@gmail.com)
2. APIs & Services → Credentials
3. Edit OAuth 2.0 Client ID
4. Add to **Authorized JavaScript origins:**
   - `https://arprofm.com`
5. Add to **Authorized redirect URIs:**
   - `https://arprofm.com`
   - `https://arprofm.com/app`
6. Save

## Deployment Workflow

### Automatic (Recommended)
Push to `main` branch → Render auto-deploys

```bash
git add .
git commit -m "Your changes"
git push origin main
```

### Manual
1. Go to Render Dashboard
2. Click "Manual Deploy" → "Deploy latest commit"

## Environment Variables (Render)
Currently using defaults. Add these in Render Settings → Environment if needed:
- `OAUTH_ENCRYPTION_KEY` - For secure OAuth token storage

## Monitoring
- **Render Logs:** https://dashboard.render.com/ → liftlogic → Logs
- **Health Check:** https://arprofm.com/health

## Troubleshooting

### Cold Starts (Free Tier)
Free tier services sleep after 15 mins of inactivity. First request may take ~30 seconds.

### OAuth Errors
If "redirect_uri_mismatch" appears, add the domain to Google Cloud Console OAuth settings.

### DNS Issues
DNS records are in Porkbun. Propagation can take up to 48 hours globally.
