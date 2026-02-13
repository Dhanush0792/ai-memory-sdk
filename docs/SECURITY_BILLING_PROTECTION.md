# Gemini Billing Protection Setup

## Overview
This guide ensures you never face unexpected billing charges from Google Gemini API usage.

## ⚠️ Critical: Set Budget Limits BEFORE Deployment

### Step 1: Access Google Cloud Console
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select your project (or create a new one)
3. Navigate to **Billing** → **Budgets & alerts**

### Step 2: Create Budget Alert
1. Click **CREATE BUDGET**
2. Configure:
   - **Name**: `Gemini API Monthly Budget`
   - **Projects**: Select your project
   - **Services**: Select "Generative Language API"
   - **Time range**: Monthly
   - **Budget type**: Specified amount

### Step 3: Set Budget Amount
**Recommended starting budgets:**
- **Development/Testing**: $10-20/month
- **Small production**: $50-100/month
- **Medium production**: $200-500/month

**Set threshold alerts at:**
- 50% of budget
- 75% of budget
- 90% of budget
- 100% of budget

### Step 4: Configure Alert Actions
1. **Email notifications**: Add your email
2. **Pub/Sub notifications** (optional): For automated responses
3. **Programmatic notifications**: Can trigger auto-shutdown

### Step 5: Set Hard Quota Limits
1. Navigate to **APIs & Services** → **Enabled APIs**
2. Find "Generative Language API"
3. Click **Quotas**
4. Set limits:
   - **Requests per day**: Start with 1,000-10,000
   - **Requests per minute**: 60-600 (based on expected load)

## 🛡️ Additional Protection Measures

### Application-Level Rate Limiting
The Memory Infrastructure includes built-in rate limiting:
```env
RATE_LIMIT_REQUESTS=100  # Requests per minute per user
```

### Provider Fallback
Enable automatic fallback to prevent service disruption:
```env
PROVIDER_FALLBACK_ENABLED=true
EXTRACTION_PROVIDER=gemini
# Falls back to OpenAI if Gemini quota exceeded
```

### Monitoring & Alerts
1. **Enable metrics** in `.env`:
   ```env
   METRICS_ENABLED=true
   STRUCTURED_LOGGING=true
   ```

2. **Monitor usage** via:
   - Google Cloud Console → API Dashboard
   - Application metrics endpoint: `/metrics`

### Cost Estimation
**Gemini 1.5 Flash pricing (as of 2024):**
- Input: $0.075 per 1M tokens
- Output: $0.30 per 1M tokens

**Example cost calculation:**
- 10,000 requests/day
- Average 500 tokens input + 200 tokens output per request
- Monthly cost: ~$35-50

## 🚨 Emergency Shutdown Procedure

If you detect unexpected usage:

1. **Immediate**: Disable API key
   ```bash
   # In Google Cloud Console:
   # APIs & Services → Credentials → Delete/Disable key
   ```

2. **Stop application**:
   ```bash
   docker-compose down
   ```

3. **Revoke and rotate keys**:
   - Generate new API key
   - Update `.env` file
   - Never commit the new key

4. **Review logs**:
   ```bash
   # Check application logs for unusual patterns
   docker-compose logs app | grep "gemini"
   ```

## ✅ Pre-Deployment Checklist

Before deploying to production:

- [ ] Budget alerts configured in Google Cloud Console
- [ ] Hard quota limits set
- [ ] Email notifications enabled
- [ ] Application rate limiting configured
- [ ] Monitoring enabled (`METRICS_ENABLED=true`)
- [ ] `.env` file contains valid API key
- [ ] `.env` is in `.gitignore` and NOT committed
- [ ] Tested with low quota limits first
- [ ] Emergency contact list prepared
- [ ] Cost estimation reviewed and approved

## 📊 Monitoring Best Practices

### Daily Checks
- Review API usage in Google Cloud Console
- Check application metrics endpoint
- Monitor error rates

### Weekly Reviews
- Compare actual vs. estimated costs
- Review rate limit effectiveness
- Adjust quotas if needed

### Monthly Audits
- Full cost analysis
- Budget adjustment
- Security review

## 🔗 Resources

- [Google Cloud Billing Documentation](https://cloud.google.com/billing/docs)
- [Gemini API Pricing](https://ai.google.dev/pricing)
- [Budget Alerts Guide](https://cloud.google.com/billing/docs/how-to/budgets)
- [Quota Management](https://cloud.google.com/docs/quota)

## Support

For billing issues:
- Google Cloud Support: https://cloud.google.com/support
- Gemini API Support: https://ai.google.dev/support
