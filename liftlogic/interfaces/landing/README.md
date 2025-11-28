# ARPRO Website - Netlify Deployment Package

This folder contains a **production-ready** version of the ARPRO Lifts & Escalators website, optimized for Netlify deployment.

## 📁 Folder Structure

```
netlify-deploy/
├── index.html          # Main HTML file (root level - REQUIRED)
├── styles.css          # Main stylesheet
├── script.js           # Main JavaScript file
├── netlify.toml        # Netlify configuration (redirects, headers, caching)
├── README.md           # This file
└── assets/
    ├── animations/     # Lottie animation files
    ├── arprologos/     # Company logos
    ├── css/            # Additional CSS (if needed)
    ├── fonts/          # Founders Grotesk font files
    └── images/         # All website images
```

## ✅ Why This Structure Works

According to **Netlify best practices 2025**:

1. **index.html at root level** - Required for Netlify to serve your site correctly
2. **Organized assets** - All images, fonts, and animations in `/assets` subfolder
3. **netlify.toml** - Configuration file for redirects, headers, and caching
4. **No unnecessary files** - Clean structure with only production files

## 🚀 How to Deploy to Netlify

### Method 1: Drag & Drop (Easiest)

1. Go to [app.netlify.com](https://app.netlify.com)
2. Log into your account
3. Click **"Add new site"** → **"Deploy manually"**
4. **Drag and drop this entire `netlify-deploy` folder**
5. Wait 30 seconds for deployment
6. Your site will be live at `https://your-site-name.netlify.app`

### Method 2: Netlify CLI

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Navigate to this folder
cd /Users/wes/Desktop/ARPROwebsite/netlify-deploy

# Deploy
netlify deploy --prod
```

## 🌐 Custom Domain Setup (liftsmith.xyz)

Your domain is already configured! DNS records:
- **A Record**: `liftsmith.xyz` → `75.2.60.5` (Netlify IP)
- **CNAME**: `www.liftsmith.xyz` → `resplendent-cheesecake-8c8388.netlify.app`

After deploying:
1. Go to **Site settings** → **Domain management**
2. Click **"Add domain"**
3. Enter: `liftsmith.xyz`
4. Netlify will verify and provision SSL certificate (5-20 minutes)

## 📋 What's Included

### ✅ Features
- Responsive design (mobile, tablet, desktop)
- Modern dark theme with WCAG AA accessibility
- Smooth scroll animations
- Contact form with validation
- SEO optimized
- Security headers configured
- Performance optimized

### 📄 Files
- **index.html** (31 KB) - Main website structure
- **styles.css** (33 KB) - All styling
- **script.js** (20 KB) - Interactive functionality
- **assets/** - All images, fonts, logos, animations

## 🔧 Post-Deployment Checklist

After deploying, verify:
- [ ] Site loads at `https://liftsmith.xyz`
- [ ] SSL certificate is active (green padlock 🔒)
- [ ] All images load correctly
- [ ] Navigation works smoothly
- [ ] Contact form validates input
- [ ] Mobile responsive design works
- [ ] Animations play correctly

## 🛠️ Troubleshooting

### Issue: "Page not found" (404)
**Solution**: Make sure you deployed **this folder** (`netlify-deploy`), not the parent folder.

### Issue: Images not loading
**Solution**: Check that the `assets` folder was included in your deployment.

### Issue: SSL not working
**Solution**: Wait 5-20 minutes for Netlify to provision the certificate. Check domain management settings.

### Issue: Contact form not submitting
**Solution**: The form currently simulates submission. To enable real email:
1. Add `netlify` attribute to the `<form>` tag in `index.html`
2. Netlify will automatically handle submissions

## 📞 Contact Information

**Company**: ARPRO Lifts & Escalators
**Email**: info@arpro.com.au
**Phone**: +61 427 661 175
**Website**: https://liftsmith.xyz

---

**✨ Deployment Package Created**: October 23, 2025
**Status**: Production Ready ✅
**Optimized for**: Netlify Static Hosting
