# Deploying AI Memory SDK Frontend to Netlify

This guide walks you through deploying the frontend to Netlify.

## Quick Start (Recommended)

### Method 1: GitHub Integration (Best for Production)

1. **Go to Netlify Dashboard**
   - Visit [https://app.netlify.com](https://app.netlify.com)
   - Sign in or create an account

2. **Import from GitHub**
   - Click "Add new site" → "Import an existing project"
   - Choose "GitHub" as the provider
   - Authorize Netlify to access your GitHub account
   - Select repository: `Dhanush0792/ai-memory-sdk`

3. **Configure Build Settings**
   - **Base directory**: (leave empty)
   - **Build command**: (leave empty or `echo 'Static site'`)
   - **Publish directory**: `frontend`
   - Click "Deploy site"

4. **Wait for Deployment**
   - Netlify will automatically deploy your site
   - You'll get a URL like: `https://random-name-123.netlify.app`

5. **Configure Custom Domain** (Optional)
   - Go to "Domain settings"
   - Click "Add custom domain"
   - Follow DNS configuration instructions

---

### Method 2: Netlify CLI (For Testing)

1. **Install Netlify CLI**
   ```bash
   npm install -g netlify-cli
   ```

2. **Login to Netlify**
   ```bash
   netlify login
   ```

3. **Deploy from Project Root**
   ```bash
   cd c:\Users\Desktop\Projects\memory
   netlify deploy --dir=frontend --prod
   ```

4. **Follow Prompts**
   - Choose "Create & configure a new site"
   - Select your team
   - Enter site name (e.g., `ai-memory-sdk`)

---

### Method 3: Drag and Drop (Quick Test)

1. **Prepare Frontend Folder**
   - Navigate to `c:\Users\Desktop\Projects\memory\frontend`

2. **Deploy**
   - Go to [https://app.netlify.com/drop](https://app.netlify.com/drop)
   - Drag the `frontend` folder into the browser
   - Netlify deploys immediately

---

## Post-Deployment Steps

### 1. Update Backend CORS Settings

Your backend on Render needs to allow requests from the Netlify domain:

1. Go to your Render dashboard
2. Select your backend service
3. Go to "Environment" tab
4. Update `CORS_ORIGINS` to include your Netlify URL:
   ```
   CORS_ORIGINS=https://your-site.netlify.app,https://ai-memory-sdk.onrender.com
   ```
5. Save and redeploy

### 2. Test the Deployment

1. **Visit your Netlify URL**
   - Landing page should load correctly
   - All animations should work
   - Links should function properly

2. **Test Chat Interface**
   - Navigate to `/chat.html`
   - Verify it connects to the backend API

3. **Check Browser Console**
   - Open DevTools (F12)
   - Look for any errors
   - Verify all assets load correctly

### 3. Configure Environment Variables (If Needed)

If your frontend needs environment variables:

1. Go to Netlify dashboard
2. Select your site
3. Go to "Site settings" → "Environment variables"
4. Add variables like:
   - `API_URL`: `https://ai-memory-sdk.onrender.com`

---

## Custom Domain Setup (Optional)

1. **Add Domain in Netlify**
   - Go to "Domain settings"
   - Click "Add custom domain"
   - Enter your domain (e.g., `aimemory.com`)

2. **Configure DNS**
   - Add DNS records as shown by Netlify
   - For Netlify DNS: Point nameservers to Netlify
   - For external DNS: Add A record or CNAME

3. **Enable HTTPS**
   - Netlify automatically provisions SSL certificate
   - Usually takes a few minutes

---

## Continuous Deployment

With GitHub integration, Netlify automatically:
- ✅ Deploys on every push to `main` branch
- ✅ Creates deploy previews for pull requests
- ✅ Keeps deployment history
- ✅ Allows instant rollbacks

---

## Troubleshooting

### Issue: 404 on Page Refresh
**Solution**: The `_redirects` file should handle this. Verify it exists in `frontend/_redirects`

### Issue: Assets Not Loading
**Solution**: Check that paths in HTML are relative (e.g., `static/css/style.css` not `/static/css/style.css`)

### Issue: CORS Errors
**Solution**: Update `CORS_ORIGINS` on your Render backend to include the Netlify URL

### Issue: Build Fails
**Solution**: Since this is a static site, there's no build step. Ensure "Publish directory" is set to `frontend`

---

## Monitoring and Analytics

### Enable Netlify Analytics (Optional)
1. Go to your site dashboard
2. Click "Analytics" tab
3. Enable analytics ($9/month)
4. Get real-time traffic insights

### Use Lighthouse for Performance
```bash
# Install Lighthouse
npm install -g lighthouse

# Run audit
lighthouse https://your-site.netlify.app --view
```

---

## Cost

- **Free Tier**: 100GB bandwidth/month, 300 build minutes/month
- **Sufficient for**: Most small to medium projects
- **Upgrade**: Pro plan at $19/month if needed

---

## Next Steps

1. ✅ Deploy to Netlify using one of the methods above
2. ✅ Update backend CORS settings
3. ✅ Test the deployment thoroughly
4. ✅ (Optional) Configure custom domain
5. ✅ (Optional) Enable analytics

---

## Support

- **Netlify Docs**: [https://docs.netlify.com](https://docs.netlify.com)
- **Netlify Community**: [https://answers.netlify.com](https://answers.netlify.com)
- **Status Page**: [https://www.netlifystatus.com](https://www.netlifystatus.com)
