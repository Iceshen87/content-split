# ✂️ ContentSplit — AI Content Repurposer API

Turn one blog post into Twitter threads, LinkedIn posts, NOSTR notes, email newsletters, video scripts, and summaries with a single API call.

## 🚀 Quick Start

```bash
pip install fastapi uvicorn httpx
python app.py
# → http://localhost:8080
# → http://localhost:8080/docs (Swagger UI)
```

## 📡 API

### Sign Up (Free)
```bash
curl -X POST http://localhost:8080/api/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com"}'
```

### Repurpose Content
```bash
curl -X POST http://localhost:8080/api/repurpose \
  -H "X-API-Key: cs_your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Your long blog post here...",
    "targets": ["twitter_thread", "linkedin", "email_newsletter"],
    "tone": "professional"
  }'
```

### Check Usage
```bash
curl http://localhost:8080/api/usage -H "X-API-Key: cs_your_key"
```

## 🎯 Platforms

| Platform | Output |
|----------|--------|
| `twitter_thread` | Numbered thread (2-20 tweets) |
| `linkedin` | Professional post with engagement hook |
| `nostr` | Concise note with hashtags |
| `email_newsletter` | Subject + intro + takeaways + CTA |
| `video_script` | 60s script with B-roll suggestions |
| `summary` | 2-3 sentence summary |

## 💰 Pricing

| Plan | Price | Requests/mo | Platforms |
|------|-------|-------------|-----------|
| Free | $0 | 50 | 3 |
| Starter | $9 | 500 | All 6 |
| Pro | $29 | 5,000 | All 6 |
| Enterprise | $99 | 50,000 | All 6 |

## 🔧 AI Backends

Set one of these env vars for AI-powered generation:
- `OPENAI_API_KEY` — Uses GPT-4o-mini
- `ANTHROPIC_API_KEY` — Uses Claude 3 Haiku

Without either, falls back to rule-based extraction (still useful, just less polished).

## 🐳 Docker

```bash
docker build -t contentsplit .
docker run -p 8080:8080 -e OPENAI_API_KEY=sk-... contentsplit
```

## License

MIT
