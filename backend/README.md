# AI Memory SDK - Backend

FastAPI-based backend providing JSON APIs for AI memory management.

## Overview

This backend exposes RESTful JSON APIs for:
- Memory storage and retrieval (facts, preferences, events)
- AI-powered memory extraction from conversations
- Chat with memory context injection
- GDPR compliance (data export/deletion)
- Authentication and rate limiting

**Deployed on**: Render  
**API Documentation**: Available at `/docs` (Swagger UI)

## Memory Contract v1

AI Memory SDK v1 defines a **frozen, stable memory schema** that will not change within v1. This contract guarantees predictability and allows you to build production systems with confidence.

### Supported Memory Types

| Type | Description | Use Case |
|------|-------------|----------|
| `preference` | User preferences and settings | "Prefers dark mode", "Uses metric units" |
| `fact` | Factual information about the user | "Works in fintech", "Lives in San Francisco" |
| `event` | Time-bound events or actions | "Completed onboarding on 2026-02-01" |
| `system` | System-generated metadata | "Account created", "Last login timestamp" |

**v1 Guarantee**: These four types are frozen. No new types will be added in v1. Breaking changes will only occur in v2 (if introduced).

### Required Fields

Every memory **MUST** have these fields:

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `id` | UUID (string) | Unique memory identifier | Auto-generated |
| `owner_id` | string | Tenant identifier (from API key) | Auto-derived, max 255 chars |
| `user_id` | string | Customer-provided user identifier | Required, max 255 chars |
| `type` | enum | Memory type | Must be: fact, preference, event, or system |
| `content` | string | Human-readable memory content | Required, max 10,000 chars |
| `confidence` | float | Confidence score (0.0-1.0) | Default: 1.0 |
| `created_at` | timestamp | Creation timestamp | Auto-generated (UTC) |
| `updated_at` | timestamp | Last update timestamp | Auto-updated (UTC) |
| `is_deleted` | boolean | Soft delete flag | Default: false |

### Optional Fields

These fields are optional but supported:

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `key` | string | Structured key for the memory | Optional, max 255 chars |
| `value` | JSON | Typed value (string, number, boolean, object) | Optional, JSON-serializable |
| `importance` | integer | Importance score (1-5) | Optional, 1=low, 5=critical |
| `metadata` | JSON | Additional metadata | Optional, max 5KB, max 5 levels deep |
| `ttl_seconds` | integer | Time-to-live in seconds | Optional, auto-calculates `expires_at` |
| `expires_at` | timestamp | Expiration timestamp | Optional, can be set directly or via TTL |
| `ingestion_mode` | enum | How memory was created | Default: "explicit", options: explicit, rules |

### Field Validation Rules

**Enforced at API and database level:**

1. **owner_id**: ALWAYS derived from API key. Never trusted from request body.
2. **user_id**: NEVER used as tenant boundary. Only `owner_id` isolates data.
3. **type**: Must be one of the four supported types. Invalid types return `400 Bad Request`.
4. **confidence**: Must be between 0.0 and 1.0 (inclusive).
5. **importance**: If provided, must be between 1 and 5 (inclusive).
6. **ingestion_mode**: Must be "explicit" or "rules". Invalid modes return `400 Bad Request`.
7. **content**: Cannot be empty. Max 10,000 characters.
8. **metadata**: Max 5KB JSON. Max 5 levels of nesting.

### What Will Never Change (v1 Stability Guarantee)

**Guaranteed stable in v1:**
- The four memory types (fact, preference, event, system)
- Required field names and types
- `owner_id` as the tenant boundary
- `user_id` as customer-provided identifier
- Validation rules for confidence, importance, and content length
- Soft delete behavior (is_deleted flag)
- TTL expiration logic

**Backward compatible changes allowed:**
- Adding new optional fields (will not break existing code)
- Adding new indexes for performance
- Extending metadata size limits (upward only)

**Breaking changes (v2 only):**
- Changing required field types
- Removing fields
- Changing validation rules to be more restrictive
- Changing the meaning of existing fields

## Ingestion Modes

AI Memory SDK v1 supports **two ingestion modes** for creating memories. The mode is specified via the `ingestion_mode` field when creating a memory.

### Supported Modes

#### 1. Explicit Mode (Default)

**When to use**: Manual memory creation by your application.

**Behavior**:
- You explicitly provide all memory fields
- No automatic processing or inference
- Full control over what gets stored
- Recommended for most use cases

**Example**:
```json
{
  "user_id": "user_123",
  "content": "User prefers dark mode",
  "type": "preference",
  "key": "ui_theme",
  "value": "dark",
  "ingestion_mode": "explicit"
}
```

**Pros**:
- ✅ Predictable and deterministic
- ✅ No LLM costs
- ✅ Full control over data
- ✅ Fast and reliable

**Cons**:
- ❌ Requires manual extraction logic
- ❌ No automatic inference

#### 2. Rules Mode (Optional)

**When to use**: Deterministic extraction from structured data.

**Behavior**:
- Apply predefined rules to extract memories
- Deterministic (same input = same output)
- No LLM required
- Useful for parsing structured formats

**Example**:
```json
{
  "user_id": "user_123",
  "content": "preference:theme=dark",
  "type": "preference",
  "ingestion_mode": "rules"
}
```

**Pros**:
- ✅ Deterministic extraction
- ✅ No LLM costs
- ✅ Faster than LLM-based extraction

**Cons**:
- ❌ Limited to predefined patterns
- ❌ Requires structured input format

### Explicitly NOT Supported (v1)

The following ingestion modes are **NOT supported** in v1:

- ❌ **Automatic fetching**: No background data scraping
- ❌ **Implicit ingestion**: No automatic memory creation without explicit API calls
- ❌ **LLM-based extraction by default**: Use `/api/v1/memory/extract` endpoint explicitly if needed

### API Behavior

**Valid request** (explicit mode, default):
```bash
curl -X POST https://your-api.com/api/v1/memory \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"user_id": "user_123", "content": "Test", "type": "fact"}'
```
→ Returns `200 OK`

**Valid request** (rules mode):
```bash
curl -X POST https://your-api.com/api/v1/memory \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"user_id": "user_123", "content": "Test", "type": "fact", "ingestion_mode": "rules"}'
```
→ Returns `200 OK`

**Invalid request** (unsupported mode):
```bash
curl -X POST https://your-api.com/api/v1/memory \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"user_id": "user_123", "content": "Test", "type": "fact", "ingestion_mode": "automatic"}'
```
→ Returns `400 Bad Request` with error: "Invalid ingestion_mode. Must be one of: explicit, rules"

### Cost and Safety Implications

| Mode | LLM Cost | Deterministic | Safety | Speed |
|------|----------|---------------|--------|-------|
| explicit | None | ✅ Yes | ✅ High | ✅ Fast |
| rules | None | ✅ Yes | ✅ High | ✅ Fast |
| ~~automatic~~ | ❌ Not supported | - | - | - |

## 5-Minute Quick Start

This is the **canonical, copy-paste-ready** example to get started with AI Memory SDK. Follow these exact steps.

### Prerequisites

- Python 3.11+ installed
- PostgreSQL database running
- Backend server running locally or deployed

### Step 1: Generate an API Key

Run this command to generate your first API key:

```bash
python backend/scripts/generate_api_key.py my_customer_001 --rate-limit 60
```

**Expected output:**
```
API KEY GENERATED SUCCESSFULLY
API Key (SAVE THIS - IT WILL NOT BE SHOWN AGAIN):
  aimsk_live_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0

Key ID:
  550e8400-e29b-41d4-a716-446655440000

Owner ID:
  my_customer_001

Rate Limit:
  60 requests/minute
```

**⚠️ CRITICAL**: Copy the API key now. It will not be shown again.

### Step 2: Store a Memory

Replace `YOUR_API_KEY` with the key from Step 1:

```bash
curl -X POST http://localhost:10000/api/v1/memory \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "content": "User prefers dark mode and works in fintech",
    "type": "preference",
    "key": "ui_theme",
    "value": "dark",
    "importance": 4
  }'
```

**Expected output:**
```json
{
  "id": "mem_abc123def456",
  "owner_id": "my_customer_001",
  "user_id": "user_123",
  "content": "User prefers dark mode and works in fintech",
  "type": "preference",
  "key": "ui_theme",
  "value": "dark",
  "confidence": 1.0,
  "importance": 4,
  "metadata": {},
  "created_at": "2026-02-04T12:00:00Z",
  "updated_at": "2026-02-04T12:00:00Z",
  "expires_at": null,
  "ttl_seconds": null,
  "is_deleted": false,
  "ingestion_mode": "explicit"
}
```

### Step 3: Retrieve Context

Get relevant memories for a user:

```bash
curl -X GET "http://localhost:10000/api/v1/memory?user_id=user_123&limit=5" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Expected output:**
```json
[
  {
    "id": "mem_abc123def456",
    "owner_id": "my_customer_001",
    "user_id": "user_123",
    "content": "User prefers dark mode and works in fintech",
    "type": "preference",
    "key": "ui_theme",
    "value": "dark",
    "confidence": 1.0,
    "importance": 4,
    "created_at": "2026-02-04T12:00:00Z"
  }
]
```

### Step 4: Inject into LLM Prompt

Use the retrieved memories in your LLM prompts:

```python
import requests
import openai

# Step 1: Retrieve memories
API_KEY = "aimsk_live_..."  # Your API key from Step 1
response = requests.get(
    "http://localhost:10000/api/v1/memory",
    params={"user_id": "user_123", "limit": 5},
    headers={"Authorization": f"Bearer {API_KEY}"}
)
memories = response.json()

# Step 2: Build context from memories
context_lines = []
for mem in memories:
    context_lines.append(f"- {mem['content']}")
context = "\n".join(context_lines)

# Step 3: Inject into LLM system prompt
system_prompt = f"""You are a helpful assistant.

User Context:
{context}

Use this context to personalize your responses."""

# Step 4: Send to OpenAI (or any LLM)
client = openai.OpenAI()
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "What theme should I use for the UI?"}
    ]
)

print(response.choices[0].message.content)
# Expected: "Based on your preferences, I recommend using dark mode..."
```

**That's it!** You now have:
- ✅ API key generated
- ✅ Memory stored
- ✅ Context retrieved
- ✅ LLM prompt personalized

## Memory Lifecycle

AI Memory SDK v1 provides lightweight lifecycle controls for managing memory over time.

### Time-to-Live (TTL)

Memories can automatically expire after a specified duration.

**Set TTL when creating a memory:**
```bash
curl -X POST http://localhost:10000/api/v1/memory \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "user_id": "user_123",
    "content": "Temporary session data",
    "type": "event",
    "ttl_seconds": 3600
  }'
```

**Behavior:**
- `expires_at` is automatically calculated as `created_at + ttl_seconds`
- Expired memories are **excluded from retrieval** automatically
- Expired memories are **not deleted** from the database (for audit trail)
- You can query expired memories separately if needed

**Example**: A memory with `ttl_seconds: 3600` (1 hour) will not be returned by `/api/v1/memory` after 1 hour.

### Soft Delete

Soft delete marks a memory as deleted without removing it from the database.

**Soft delete a memory:**
```bash
curl -X DELETE http://localhost:10000/api/v1/memory/mem_abc123/soft?user_id=user_123 \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Behavior:**
- Sets `is_deleted = TRUE`
- Sets `updated_at = NOW()`
- Memory is **excluded from retrieval** automatically
- Memory remains in database for audit trail
- Soft-deleted memories are **not reversible** in v1

**Hard delete vs Soft delete:**
- **Soft delete** (`/api/v1/memory/{id}/soft`): Sets flag, keeps data
- **Hard delete** (`/api/v1/memory/{id}`): Permanently removes from database

### Importance Scoring

Assign importance levels (1-5) to prioritize memories.

**Set importance when creating:**
```bash
curl -X POST http://localhost:10000/api/v1/memory \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "user_id": "user_123",
    "content": "Critical security preference",
    "type": "preference",
    "importance": 5
  }'
```

**Importance levels:**
- `1`: Low priority (e.g., minor preferences)
- `2-3`: Medium priority (e.g., general facts)
- `4`: High priority (e.g., important preferences)
- `5`: Critical (e.g., security settings, legal requirements)

**Use case**: Filter or sort memories by importance in your application logic.

### Owner-Scoped Memory Stats

Get statistics about memories for a specific user:

```bash
curl -X GET "http://localhost:10000/api/v1/memory/stats?user_id=user_123" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Expected output:**
```json
{
  "total": 42,
  "deleted": 5,
  "expired": 3,
  "by_type": {
    "preference": 15,
    "fact": 20,
    "event": 7
  },
  "by_importance": {
    "1": 10,
    "2": 15,
    "3": 10,
    "4": 5,
    "5": 2
  },
  "oldest": "2026-01-01T00:00:00Z",
  "newest": "2026-02-04T12:00:00Z"
}
```

**Stats are scoped by:**
- `owner_id` (from API key) - tenant isolation
- `user_id` (from query parameter) - user-specific stats

## Quick Start (API-First)

### What This API Is

AI Memory SDK provides persistent memory storage for AI applications. Store facts, preferences, and events, then retrieve relevant context to inject into your LLM prompts. This enables AI systems to remember users across sessions without bloating context windows.

### Authentication

All API endpoints require an API key for authentication.

**API Key Format:** `aimsk_live_<32_char_random>`

**Required Header:**
```
Authorization: Bearer aimsk_live_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

**How It Works:**
1. Each API key is associated with an `owner_id` (your customer/app identifier)
2. All memory operations are automatically scoped to the `owner_id` from your API key
3. You cannot access another owner's data
4. Invalid or revoked keys return `401 Unauthorized`

**Getting an API Key:**
API keys are generated server-side using the CLI tool:
```bash
python backend/scripts/generate_api_key.py your_owner_id --rate-limit 60
```

**Security:**
- API keys are hashed (SHA-256) before storage
- Keys are never stored in plaintext
- Keys are returned only once during generation
- Store keys securely (environment variables, secrets manager)
- Never commit keys to version control
- Never expose keys in frontend code

## API Key Management

### Generating Keys

Use the CLI script to generate new API keys:

```bash
# Basic usage
python backend/scripts/generate_api_key.py customer_123

# With custom rate limit
python backend/scripts/generate_api_key.py customer_456 --rate-limit 120

# With metadata
python backend/scripts/generate_api_key.py customer_789 --rate-limit 300 --metadata '{"plan": "pro"}'
```

**Output:**
```
API KEY GENERATED SUCCESSFULLY
API Key (SAVE THIS - IT WILL NOT BE SHOWN AGAIN):
  aimsk_live_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6

Key ID:
  550e8400-e29b-41d4-a716-446655440000

Owner ID:
  customer_123

Rate Limit:
  60 requests/minute
```

**⚠️ CRITICAL:** The plaintext key is shown ONLY ONCE. Store it immediately.

### Listing Keys

View all keys for an owner:

```bash
python backend/scripts/list_api_keys.py customer_123
```

### Revoking Keys

Revoke a compromised or unused key:

```bash
python backend/scripts/revoke_api_key.py 550e8400-e29b-41d4-a716-446655440000
```

Revoked keys:
- Cannot be used for authentication
- Return `401 Unauthorized`
- Are preserved in the database for audit trail
- Cannot be un-revoked (generate a new key instead)

## Rate Limiting

### Per-Key Limits

Each API key has a configurable rate limit (requests per minute).

**Default:** 60 requests/minute

**Headers in Every Response:**
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1706985600
```

**On Rate Limit Exceeded (429):**
```json
{
  "detail": "Rate limit exceeded"
}
```

**Response Headers:**
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1706985660
Retry-After: 15
```

### Rate Limit Algorithm

Uses **token bucket** algorithm:
- Tokens = allowed requests
- Bucket capacity = rate limit per minute
- Tokens refill continuously (rate_limit / 60 per second)
- Each request consumes 1 token
- Request blocked if no tokens available

**Example:**
- Rate limit: 60 requests/minute
- Refill rate: 1 token/second
- Burst: Can make 60 requests instantly, then 1/second

### Handling Rate Limits

**Best Practices:**
1. Monitor `X-RateLimit-Remaining` header
2. Implement exponential backoff on 429
3. Use `Retry-After` header value
4. Cache responses when possible
5. Batch operations if supported

**Example (Python):**
```python
import time
import requests

def make_request_with_retry(url, headers, data, max_retries=3):
    for attempt in range(max_retries):
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited. Retrying after {retry_after}s...")
            time.sleep(retry_after)
            continue
        
        return response
    
    raise Exception("Max retries exceeded")
```

## Security Best Practices

### API Key Safety

**DO:**
- ✅ Store keys in environment variables
- ✅ Use secrets managers (AWS Secrets Manager, HashiCorp Vault)
- ✅ Rotate keys periodically
- ✅ Use different keys for dev/staging/production
- ✅ Revoke keys immediately if compromised
- ✅ Monitor key usage via `last_used_at`

**DON'T:**
- ❌ Commit keys to Git
- ❌ Hardcode keys in source code
- ❌ Expose keys in frontend JavaScript
- ❌ Share keys between customers
- ❌ Log API keys
- ❌ Send keys in URLs or query parameters

### Data Isolation

- All memory is scoped by `owner_id` from the API key
- You cannot access another owner's data
- Enforced at the database query level
- No shared global memory

### Error Messages

All authentication failures return the same generic message:
```json
{
  "detail": "Authentication required"
}
```

This prevents information leakage about:
- Whether a key exists
- Whether a key is revoked
- Key format validity



### Add Memory

Store a new memory for a user:

```bash
curl -X POST https://ai-memory-sdk.onrender.com/api/v1/memory \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "content": "User prefers dark mode and works in fintech",
    "memory_type": "preference",
    "metadata": {
      "source": "settings",
      "confidence": "high"
    }
  }'
```

**Response:**
```json
{
  "memory_id": "mem_abc123",
  "user_id": "user_123",
  "content": "User prefers dark mode and works in fintech",
  "created_at": "2026-02-03T12:00:00Z"
}
```

### Retrieve Context

Get relevant memories for a user based on a query:

```bash
curl -X POST https://ai-memory-sdk.onrender.com/api/v1/memory/context \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "query": "What are the user preferences?",
    "limit": 5
  }'
```

**Response:**
```json
{
  "memories": [
    {
      "content": "User prefers dark mode and works in fintech",
      "memory_type": "preference",
      "created_at": "2026-02-03T12:00:00Z",
      "relevance_score": 0.95
    }
  ],
  "context_summary": "User prefers dark mode. Works in fintech industry."
}
```

### How to Use Returned Context in an LLM Prompt

Inject the `context_summary` into your LLM system prompt:

```python
context = api_response["context_summary"]
system_prompt = f"""You are a helpful assistant.

User Context:
{context}

Use this context to personalize your responses."""

# Send to OpenAI, Anthropic, etc.
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
)
```

### Example: Remembering User Preferences

**Scenario:** A user expresses a preference, you store it, then retrieve it later to personalize responses.

1. **User says:** "I prefer concise explanations"
2. **Store the preference:**
   ```bash
   curl -X POST https://ai-memory-sdk.onrender.com/api/v1/memory \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "user_123",
       "content": "Prefers concise explanations",
       "memory_type": "preference"
     }'
   ```
3. **Later, retrieve context:**
   ```bash
   curl -X POST https://ai-memory-sdk.onrender.com/api/v1/memory/context \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "user_123",
       "query": "How should I respond to this user?"
     }'
   ```
4. **Inject into LLM prompt:**
   - The API returns: `"User prefers concise explanations"`
   - Add this to your system prompt
   - Your LLM now personalizes responses automatically

## API Contract & Stability

All `/api/v1/*` endpoints are considered **stable**.

- **Backward compatibility is guaranteed** within `/api/v1`
- Existing endpoints will not change request/response schemas
- New optional fields may be added, but required fields will not change
- Breaking changes will only occur in `/api/v2` (if introduced in the future)

This means you can safely build production applications against `/api/v1` endpoints without fear of breaking changes.

## Common Use Cases

### 1. Remembering User Preferences Across Sessions

- **Problem**: Users expect AI assistants to remember their preferences without repeating themselves
- **How this API helps**: Store preferences once, retrieve them in every subsequent conversation
- **Example**: User mentions "I prefer metric units" → Store as memory → Future responses automatically use metric
- **Benefit**: Reduces user friction and improves personalization without manual configuration
- **Implementation**: Call `/api/v1/memory` on preference detection, inject context from `/api/v1/memory/context` into every prompt

### 2. Long-Term Memory for AI Assistants

- **Problem**: LLMs have no memory between sessions; context windows are limited and expensive
- **How this API helps**: Persistent storage of facts, events, and context across unlimited conversations
- **Example**: AI remembers user's job, family details, ongoing projects across weeks or months
- **Benefit**: Enables truly stateful AI experiences without bloating prompts with full conversation history
- **Implementation**: Extract memories during conversations, retrieve relevant subset based on current query
- **Cost savings**: Store 1000s of facts, only inject the 5-10 most relevant into each prompt

### 3. Context Recall Without Bloating Prompt Size

- **Problem**: Including full conversation history in every prompt is expensive and hits token limits
- **How this API helps**: Semantic retrieval returns only relevant memories for the current context
- **Example**: User asks about their preferences → API returns only preference-related memories, not everything
- **Benefit**: Maintain rich context while keeping prompts small and costs low
- **Implementation**: Use `/api/v1/memory/context` with a query parameter to get targeted memory retrieval
- **Result**: Pay for 500 tokens of context instead of 5000 tokens of full history

## API Health & Failure Model

### Health Check

The `/health` endpoint indicates whether the API is running and can connect to the database.

- **200 OK**: API is healthy and database is accessible
- **503 Service Unavailable**: API is running but cannot connect to the database

Use this endpoint for monitoring, load balancer health checks, and uptime verification.

### Database Unavailability

If the PostgreSQL database is unavailable:

- All `/api/v1/*` endpoints will return **503 Service Unavailable**
- The API will not cache or queue requests
- Requests will fail immediately with a clear error message
- Once the database is restored, the API will resume normal operation automatically

### Common HTTP Error Codes

- **401 Unauthorized**: Missing or invalid `Authorization` header / API key
- **400 Bad Request**: Invalid request body, missing required fields, or malformed JSON
- **404 Not Found**: Requested resource (e.g., memory_id) does not exist
- **429 Too Many Requests**: Rate limit exceeded (if rate limiting is enabled)
- **500 Internal Server Error**: Unexpected server error (check logs for details)
- **503 Service Unavailable**: Database connection failed or service is temporarily down


## Running Locally

### Prerequisites
- Python 3.11.9
- PostgreSQL database

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Initialize database:
```bash
python -c "from api.database import Database; db = Database(); db.init_schema()"
```

4. Run the server:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 10000
```

The API will be available at `http://localhost:10000`

## Environment Variables

See `.env.example` for all required environment variables:

- `DATABASE_URL` - PostgreSQL connection string (required)
- `ENCRYPTION_KEY` - Fernet encryption key for memory data (required)
- `API_KEY` - API authentication key (required)
- `OPENAI_API_KEY` - OpenAI API key for LLM features (optional)
- `CORS_ORIGINS` - Allowed CORS origins (comma-separated, see below)

### CORS Configuration

The backend uses environment-driven CORS configuration to control which frontend origins can access the API.

**Environment Variable**: `CORS_ORIGINS`

**Format**: Comma-separated list of allowed origins

**Examples**:
```bash
# Single origin
CORS_ORIGINS=https://ai-memory-sdk.netlify.app

# Multiple origins (production + staging)
CORS_ORIGINS=https://ai-memory-sdk.netlify.app,https://ai-memory-sdk-staging.netlify.app

# Local development
CORS_ORIGINS=http://localhost:8080,http://localhost:3000
```

**Important Security Notes**:
- ⚠️ **Never use `*` (wildcard) in production** - This allows any website to access your API
- Always specify exact origins including protocol (`https://`)
- Update this when deploying to new domains
- Missing or empty `CORS_ORIGINS` will block all cross-origin requests (secure by default)
- Whitespace around commas is automatically trimmed

## API Endpoints

### Core Endpoints
- `GET /` - Status check (returns JSON)
- `GET /health` - Health check
- `GET /docs` - Swagger API documentation

### Memory Management
- `POST /api/v1/memory` - Add memory
- `GET /api/v1/memory` - List memories
- `DELETE /api/v1/memory/{memory_id}` - Delete memory
- `GET /api/v1/memory/stats` - Get memory statistics

### Chat
- `POST /api/v1/chat` - Chat with memory context

### GDPR
- `GET /api/v1/gdpr/export` - Export user data
- `DELETE /api/v1/gdpr/delete` - Delete all user data

## Deployment (Render)

The backend is configured for Render deployment:

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: Defined in `Procfile`
- **Python Version**: Specified in `runtime.txt`
- **Environment Variables**: Set in Render dashboard (see below)

### Required Production Environment Variables

The following environment variables **must be set** in the Render dashboard for production deployment:

- `API_KEY` - API authentication key (required)
- `OPENAI_API_KEY` - OpenAI API key for LLM features (required for memory extraction and chat)
- `DATABASE_URL` - PostgreSQL connection string (required)
- `CORS_ORIGINS` - Allowed CORS origins, comma-separated (required, e.g., `https://ai-memory-sdk.netlify.app`)
- `ENCRYPTION_KEY` - Fernet encryption key for memory data (required)

All variables must be configured before deployment. Missing variables will cause the service to fail at startup.

## Architecture

```
backend/
├── api/
│   ├── main.py              # FastAPI app entry point
│   ├── routes.py            # API route definitions
│   ├── database.py          # Database operations
│   ├── auth.py              # Authentication
│   ├── encryption.py        # Data encryption
│   ├── rate_limiter.py      # Rate limiting
│   ├── context_injection.py # Memory context injection
│   └── services/
│       ├── chat_service.py      # Chat logic
│       ├── llm_client.py        # LLM integration
│       └── memory_extractor.py  # Memory extraction
├── requirements.txt         # Python dependencies
├── runtime.txt             # Python version
├── Procfile                # Render start command
└── .env.example            # Environment template
```

## Notes

- **Backend does NOT serve frontend files** - Frontend is deployed separately on Netlify
- All endpoints return JSON (no HTML)
- CORS is configured to allow frontend access
- Rate limiting is enabled by default
