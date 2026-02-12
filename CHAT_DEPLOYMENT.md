# Real AI Chat App - Quick Deployment Guide

## Prerequisites

- Docker & Docker Compose
- OpenAI or Anthropic API key
- 2GB RAM minimum

## Quick Start (5 Minutes)

### 1. Configure Environment

```bash
cd C:\Users\Desktop\Projects\memory
cp .env.example .env
```

Edit `.env`:
```bash
# Required
DATABASE_URL=postgresql://memoryuser:memorypass@db:5432/memorydb
REDIS_URL=redis://redis:6379/0
OPENAI_API_KEY=your-key-here

# Optional
EXTRACTION_PROVIDER=openai
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

### 2. Start Services

```bash
docker-compose up -d
```

Wait 30 seconds for services to start.

### 3. Verify Deployment

```bash
# Check health
curl http://localhost:8000/health

# Check metrics
curl http://localhost:8000/metrics
```

### 4. Open Chat Interface

Open browser: `http://localhost:8000/frontend/chat.html`

### 5. Test Chat

Try these messages:
1. "I'm Alex and I work at Microsoft"
2. "I prefer concise explanations"
3. "What do you know about me?"

You should see:
- ✅ Memories ingested (right panel)
- ✅ Context in LLM response
- ✅ Memory panel updates

## Run Integration Tests

```bash
# Activate venv
.venv\Scripts\activate

# Install dependencies
pip install requests

# Run tests
python tests/test_chat_integration.py
```

Expected output:
```
✅ SCENARIO 1 PASSED
✅ SCENARIO 2 PASSED
✅ SCENARIO 3 PASSED
✅ SCENARIO 4 PASSED

🎉 ALL TESTS PASSED!
```

## Troubleshooting

### Chat returns 503
- **Cause**: LLM provider not configured
- **Fix**: Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in `.env`

### No memories ingested
- **Cause**: Extraction provider error
- **Fix**: Check logs: `docker-compose logs app`

### Memory panel empty
- **Cause**: CORS or API error
- **Fix**: Check browser console (F12)

### Rate limit exceeded
- **Cause**: Too many requests
- **Fix**: Wait 1 minute or restart Redis: `docker-compose restart redis`

## Real User Deployment

### Day 1: Soft Launch (2-3 users)

1. Deploy to staging/production
2. Share URL with 2-3 users
3. Monitor metrics: `http://your-domain/metrics`
4. Check logs hourly

### Day 2-7: Full Deployment (5-10 users)

1. Invite remaining users
2. Collect feedback
3. Monitor daily:
   - Total conversations
   - Memories per user
   - Error rate
   - Latency

### Metrics to Track

```bash
# Total chat requests
chat_request_total

# Chat latency
chat_latency_seconds

# Memory operations
memory_ingest_total
memory_retrieve_total

# Errors
chat_error_total
extraction_failure_total
```

## Production Checklist

- [ ] Set strong `SESSION_SECRET`
- [ ] Configure production `CORS_ORIGINS`
- [ ] Enable HTTPS/TLS
- [ ] Set up daily backups
- [ ] Configure monitoring alerts
- [ ] Test multi-instance deployment
- [ ] Run load tests

## Next Steps

1. ✅ Deploy locally
2. ✅ Run integration tests
3. ⏳ Deploy to staging
4. ⏳ Invite 2-3 users (soft launch)
5. ⏳ Monitor for 24 hours
6. ⏳ Full deployment (5-10 users)
7. ⏳ Collect 100+ conversations
8. ⏳ Generate final report

---

**Status**: Ready for deployment  
**Estimated Time**: 5 minutes to first chat  
**Support**: Check logs with `docker-compose logs -f app`
