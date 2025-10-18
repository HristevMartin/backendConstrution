# AI Chat Agent Documentation

## Overview

The AI Chat Agent is a sophisticated tool-calling agent that helps homeowners find suitable tradespeople for their jobs. It uses OpenAI's GPT-4o-mini with function calling to intelligently search your database and provide personalized trader recommendations.

## Features

✅ **Intelligent Trade Recognition** - Understands natural language queries and identifies required trade types
✅ **Smart Trader Search** - Searches your database by trade, location, and radius
✅ **Distance Calculation** - Uses real UK postcode API to calculate accurate distances
✅ **Conversational** - Asks follow-up questions when information is missing
✅ **Structured Responses** - Returns UI-ready JSON with trader suggestions
✅ **Session Management** - Maintains conversation context per job
✅ **British English** - Professional, concise responses tailored for UK market

## API Endpoint

**URL:** `/travel/ai/homeowner-chat`  
**Method:** `POST`  
**Content-Type:** `application/json`

### Request Format

```json
{
  "jobId": "unique-job-identifier",
  "message": "I need an electrician in London",
  "limit": 5
}
```

**Parameters:**
- `jobId` (required): Unique identifier for the job/conversation
- `message` (required): User's natural language query
- `limit` (optional): Maximum number of trader suggestions (default: 5, max: 8)

### Response Format

```json
{
  "ok": true,
  "turnId": "uuid-v4",
  "receivedAt": "2025-10-11T14:30:00.000Z",
  "reply": "I found 3 electricians near you in London...",
  "suggestions": [
    {
      "traderId": "user-id-123",
      "name": "John Smith",
      "trade": "Electrical",
      "city": "London",
      "postcode": "SW1A 1AA",
      "distanceKm": 2.5,
      "experienceYears": 10,
      "verified": true,
      "badges": ["Verified", "CSCS card"],
      "image": "https://..."
    }
  ],
  "nextAction": "SUGGESTIONS_SHOWN",
  "slots": {
    "trade": "Electrical",
    "radiusKm": 15
  }
}
```

**Response Fields:**
- `ok`: Success status
- `turnId`: Unique identifier for this conversation turn
- `receivedAt`: ISO 8601 timestamp
- `reply`: AI's natural language response
- `suggestions`: Array of trader objects (empty if no matches or still gathering info)
- `nextAction`: One of: `"NONE"`, `"SUGGESTIONS_SHOWN"`, `"AWAIT_NOTIFY_SELECTION"`
- `slots`: Extracted/remembered information (trade, radiusKm, etc.)

### Error Responses

```json
{
  "ok": false,
  "error": "Error message"
}
```

**Status Codes:**
- `400` - Bad Request (missing jobId or message)
- `429` - Rate Limited (AI is busy)
- `502` - AI service error
- `500` - Internal server error

## How It Works

### 1. Tool-Calling Architecture

The agent uses OpenAI's function calling to:
1. **get_job_context** - Fetches job details from your database
2. **search_traders** - Performs intelligent trader search
3. **notify_trader** - Prepares notification (actual email sent by UI)

### 2. Conversation Flow

```
User: "I need an electrician in London SW1"
  ↓
AI calls: get_job_context(jobId)
  ↓
AI calls: search_traders(trade="Electrical", postcode="SW1", radiusKm=15, limit=5)
  ↓
AI responds: "I found 3 electricians near you..."
```

### 3. Trade Normalization

The agent understands various trade synonyms:
- "electrician", "electrics" → "Electrical"
- "plumber", "plumbing", "leak" → "Plumbing"
- "carpenter", "joiner" → "Carpentry"
- "roofer", "roof" → "Roofing"
- etc.

### 4. Distance Calculation

Uses your existing `ProjectRecommendationEngine` with the UK Postcodes.io API:
- Real-time coordinate lookup with caching
- Haversine formula for accurate distances
- Fallback to 50 miles for unknown postcodes

### 5. Trader Filtering

Searches traders based on:
- **Trade match**: Primary trade or other services
- **Distance**: Within job radius and trader's service radius
- **Verification**: Certification images or text
- **Recency**: Active within last 90 days (preferred)

Results sorted by distance (closest first).

## Usage Examples

### Example 1: Basic Query

```bash
curl -X POST http://localhost:8080/travel/ai/homeowner-chat \
  -H "Content-Type: application/json" \
  -d '{
    "jobId": "job-123",
    "message": "I need a plumber in Manchester M1",
    "limit": 3
  }'
```

### Example 2: Missing Information

```bash
# User doesn't specify trade
curl -X POST http://localhost:8080/travel/ai/homeowner-chat \
  -H "Content-Type: application/json" \
  -d '{
    "jobId": "job-456",
    "message": "I need help with my house",
    "limit": 5
  }'

# AI will ask: "What type of tradesperson do you need? (e.g., Plumber, Electrician, Carpenter)"
```

### Example 3: Follow-up Message

```bash
# After AI asks for clarification
curl -X POST http://localhost:8080/travel/ai/homeowner-chat \
  -H "Content-Type: application/json" \
  -d '{
    "jobId": "job-456",
    "message": "Electrician",
    "limit": 5
  }'

# AI remembers context and searches for electricians
```

## Allowed Service Categories

- Plumbing
- Electrical
- Carpentry
- Roofing
- Painting
- Gardening
- Heating & Cooling
- Flooring
- Cleaning
- Removals
- Handyman
- Mechanic

## Session Management

Sessions are stored in memory (per `jobId`):
- **Slots**: Remembered information (trade, radiusKm)
- **Last Candidates**: Most recent trader suggestions
- **Updated At**: Last activity timestamp

⚠️ **Note**: Current implementation uses in-memory storage. For production, consider migrating to Redis for:
- Persistence across server restarts
- Distributed deployment support
- Better scalability

## Integration with UI

### 1. Display Suggestions

```javascript
const response = await fetch('/travel/ai/homeowner-chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    jobId: currentJobId,
    message: userInput,
    limit: 5
  })
});

const data = await response.json();

// Display AI response
console.log(data.reply);

// Show trader cards
data.suggestions.forEach(trader => {
  renderTraderCard(trader);
});
```

### 2. Handle User Selection

When user picks a trader:
```javascript
// Use your existing notify endpoint
await fetch(`/travel/jobs/${jobId}/notify-trader`, {
  method: 'POST',
  body: JSON.stringify({ traderId: selectedTraderId })
});
```

## Testing

Run the test suite:

```bash
# Make sure your server is running
python app.py

# In another terminal
python test_chat_agent.py
```

Tests include:
1. Initial query with complete information
2. Request for trader suggestions
3. Missing trade (AI should ask for clarification)
4. Error handling (missing jobId)

## Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...

# MongoDB (already configured in config.py)
MONGO_DB=travelDB
DB_HOST=localhost
DB_PORT=27017
```

### Tuning Parameters

In `chat_agent.py`:

```python
# OpenAI settings
model="gpt-4o-mini"        # Model to use
temperature=0.3            # Lower = more consistent
max_tokens=500            # Response length limit

# Search settings
traders = TraderProject.objects()[:800]  # Max traders to scan
active_after = datetime.utcnow() - timedelta(days=90)  # Active trader window
```

## Troubleshooting

### Issue: "AI is busy" error
**Solution**: OpenAI rate limit reached. Wait a moment or upgrade API tier.

### Issue: No traders found
**Solution**: 
- Check if traders exist in database
- Verify postcode format is correct
- Increase search radius

### Issue: Distance calculation returns None
**Solution**:
- Check postcode is valid UK format
- Ensure Postcodes.io API is accessible
- Check logs for specific error messages

### Issue: Trade not recognized
**Solution**: Add synonym to `_normalise_trade()` function

## Performance Optimization

### 1. Caching
Postcode coordinates are already cached (10,000 max).

### 2. Database Indexing
Ensure indexes on:
```python
# TraderProject
- primaryTrade
- postcode
- updated_at
```

### 3. Trader Limit
Adjust based on your database size:
```python
traders = TraderProject.objects()[:800]  # Tune this number
```

### 4. Batch Processing
For large datasets, consider:
- Pre-filtering by region before distance calculation
- Batch postcode lookups (already implemented in recommendation engine)

## Future Enhancements

### Planned Features
- [ ] Redis session storage
- [ ] Multi-language support
- [ ] Trader availability checking
- [ ] Price estimation
- [ ] Review/rating integration
- [ ] Smart re-ranking based on user preferences
- [ ] A/B testing for different prompts

### Notification System
Currently `notify_trader` is a stub. To implement:

1. Create endpoint: `/travel/jobs/{jobId}/notify-trader`
2. Send email to trader about job
3. Track notification history
4. Implement rate limiting per trader

## Support

For issues or questions:
1. Check logs: `print` statements throughout code
2. Test with `test_chat_agent.py`
3. Verify OpenAI API key is valid
4. Check database connectivity

## License

Part of the homeowner_official_api backend system.

