# Vacation Planner API

The Vacation Planner API is a backend system built with FastAPI that helps users plan and manage their trips, including AI-generated itineraries powered by Claude.


## Features

Users can:

- Register and log into the platform

- Create and manage trips (destination, days, budget, travel style)

- Generate personalized itineraries using AI, based on their trip details

- Retrieve and update previously generated itineraries

- Securely access all protected routes using JWT authentication

- AI agent that can decide which tool or service to use based on the user’s request.

- Convert speech into text and use it as trip input and return travel plans as spoken responses.

---
## Project structure 
 
```
app/
  agents/travel_agent.py          LangGraph agent class (compiled once)
  api/routes/                     auth, users, trips, itinerary, voice
  core/lifespan_db.py             Database class: engine, sessions, checkpointer
  mcp_tools/
    provider.py                   loads MCP tools for the agent
    servers/travel_server.py      MCP server exposing weather + route tools
  services/
    itinerary.py                  ItineraryService (stream, parse, save)
    voice/                        speech-to-text, trip extraction, text-to-speech
  tools/                          weather, maps, RAG, pricing, trip details
scripts/check_mcp.py              checks that the MCP tools respond
```
---
### 1. Create a Virtual Environment and Install Dependencies

```bash

uv venv

source .venv/bin/activate        # Linux/Mac

.venv\Scripts\activate           # Windows

uv sync

```

### 2. Configure Environment Variables

Copy the example env file and fill in your values:

```bash

cp .env.example .env

```

Required variables:

```env

DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/vacation_planner

SECRET_KEY=your_jwt_secret_key

ALGORITHM=HS256

TOKEN_EXPIRE_MINUTES=60

ANTHROPIC_API_KEY=your_anthropic_api_key

MODEL_NAME=claude-haiku-4-5

MAX_TOKEN=4000

```

### 3. Create the Database

```sql

CREATE DATABASE vacation_planner;

```

### 4. Run Migrations

```bash

alembic upgrade head

```
### 5. Process Documents
```bash

uv run python -m app.rag.processors   

```
### 6. Start the Server

```bash

uv run uvicorn main:app --reload --host 127.0.0.1 --port 8080

```

API documentation is available at `http://127.0.0.1:8080/docs` once the server is running.

---
## API Endpoints
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | No | Create a new account. |
| POST | `/auth/login` | No | Authenticate a user and return a JWT token. |
| GET | `/users/me` | Yes | Retrieve the current user's profile. |
| POST | `/trips` | Yes | Create a new trip. |
| GET | `/trips` | Yes | List all trips for the authenticated user. |
| GET | `/trips/{trip_id}` | Yes | Retrieve details for a specific trip. |
| PUT | `/trips/{trip_id}` | Yes | Update an existing trip. |
| DELETE | `/trips/{trip_id}` | Admin | Delete a trip (admin only). |
| POST | `/voice/trip` | Yes | Create a trip from a spoken request (audio upload). |
| POST | `/itineraries` | Yes | Generate an itinerary for a trip. Body: `{"trip_id": "<uuid>"}`. Streams progress as SSE. |
| GET | `/itineraries/{trip_id}` | Yes | Retrieve a previously generated itinerary. |
| GET | `/itineraries/{trip_id}/audio` | Yes | Hear the itinerary as a short spoken summary (MP3). |


## LLM Integration

Itineraries are generated using [Claude Haiku](https://www.anthropic.com/claude) (`claude-haiku-4-5`) via the Anthropic API, using **structured outputs** and **strict tool use** to guarantee schema-valid responses.

### How it works
 
- **One agent, built once.** `TravelAgent` (`app/agents/travel_agent.py`) is
  created in the application `lifespan` and reused by every request. The graph,
  the LLM client and the system prompt are not rebuilt per request.
- **Per-request context stays safe.** `user_id` and the database session are
  passed through the LangGraph `config`, and tools read them from there. The
  model can never choose or change the user identity.
- **Each run is a fresh conversation.** The checkpoint `thread_id` is unique per
  run, so regenerating an itinerary does not inherit old messages.
- **Service layer.** `ItineraryService` (`app/services/itinerary.py`) runs the
  agent, converts graph chunks into SSE events, validates the final answer and
  saves it.
- **Tool errors do not crash the stream.** Tool failures are returned to the
  model as messages so it can retry or continue.

### Prompt Design


The prompt template and system prompt are versioned in the MLflow prompt registry (`app/utils/prompt_registry.py`) rather than hardcoded, so prompt iterations can be tracked and rolled back independently of code changes.

### Tools available to the agent
 
| Tool | Source | Purpose |
|------|--------|---------|
| `get_trip_details` | local | Loads the trip (destination, days, budget, style) for the authenticated user. |
| `search_travel_knowledge` | local | RAG retrieval over the ingested corpus (local guides + Wikivoyage), filtered by destination/country. |
| `cost_calculation` | local | Rough per-day, per-traveler cost estimate. |
| `get_weather` | **MCP** | Current weather for the destination (Open-Meteo). |
| `find_places_or_route` | **MCP** | Driving distance and travel time between two places (Nominatim + OSRM). |
 
### SSE events
 
| Event | Data | When |
|-------|------|------|
| `tool_started` | `{"tool": "<name>"}` | A tool is called (announced once per tool). |
| `tool_result` | `{"tool": "<name>", "result_preview": "<first 200 chars>"}` | A tool returned. |
| `message_chunk` | `{"text": "<partial text>"}` | Incremental text from the model. |
| `finished` | `{"itinerary_id", "trip_id", ...itinerary}` | The itinerary was validated and saved. |
| `error` | `{"detail": "<message>"}` | Something failed. Nothing is saved. |
 
Example request:
 
```bash
curl -N -X POST http://localhost:8000/itineraries \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"trip_id": "<trip_id>"}'
```
 
### Output validation
 
The model's answer is extracted (a fenced ```json block, falling back to the
outermost `{...}`), then validated against the `ItineraryContent` schema before
anything is saved. Invalid output produces an `error` event instead of a bad
record.
 
---
 
## Voice Input: Speak a Trip
 
`POST /voice/trip` turns a spoken request into a saved trip. The transcript is
only an internal step: the result is a trip, not text.
 
```
audio file → faster-whisper → Claude extracts fields → TripReq validation → trip saved
```
 
1. **Speech-to-text** uses `faster-whisper`, which is free and runs on the CPU
   (no GPU needed). The model is downloaded once on first start, then works offline.
2. **Extraction.** Claude returns only what the user actually said
   (`destination`, `days`, `budget`, `trip_style`). Anything not said stays empty.
   Nothing is guessed.
3. **Validation.** All four fields are required and are checked with the same
   `TripReq` rules as the normal `POST /trips` route.
Example (PowerShell, use `curl.exe`):
 
```bash
curl.exe -X POST http://localhost:8000/voice/trip \
  -H "Authorization: Bearer $TOKEN" \
  -F "audio=@request.mp3;type=audio/mpeg"
```
 
Say, for example: *"I want a five day relaxed trip to Zanzibar with a budget of 1500."*
 
If something was not said, the API answers `422` so the client can ask again:
 
```json
{"detail": {"message": "Please mention the missing details", "missing_fields": ["budget"]}}
```
 
Notes:
- The budget must be a **number** ("1500"). Words like "medium" are not accepted because the budget is stored as a number.
- Audio is processed in memory and is never saved to disk.
- Limits: 10 MB by default. Types: mp3, wav, webm, mp4/m4a, ogg.
---
 
## Spoken Itinerary: Listen to the Plan
 
`GET /itineraries/{trip_id}/audio` returns an MP3 with a short spoken summary
(about 30 to 60 seconds) of the saved itinerary.
 
```
saved itinerary → Claude writes a short spoken script → gTTS → MP3
```
 
The full itinerary is not read aloud, because JSON and long lists sound bad.
Claude first rewrites it as natural sentences, using only facts from the itinerary.
 
Save and play it (PowerShell):
 
```bash
cd $env:USERPROFILE\Downloads
curl.exe -H "Authorization: Bearer $TOKEN" http://localhost:8000/itineraries/<trip_id>/audio --output plan.mp3
start plan.mp3
```
 
In a browser, a plain `<audio src>` cannot send the token header, so fetch the file first:
 
```javascript
const res = await fetch(`${API_URL}/itineraries/${tripId}/audio`, {
  headers: { Authorization: `Bearer ${token}` },
});
const audio = new Audio(URL.createObjectURL(await res.blob()));
audio.play();
```
 
Swagger UI can only download the file, it cannot play audio inline.
 
---
 
## MCP (Model Context Protocol)
 
The weather and route tools are served by an MCP server
(`app/mcp_tools/servers/travel_server.py`) and loaded into the agent through
`MCPToolProvider`. The tool logic stays in `app/tools/`, MCP only exposes it in a
standard way.
 
- **Allowlist.** Only tools named in the allowlist reach the agent
  (`get_weather`, `find_places_or_route`).
- **Fallback.** If the MCP server cannot start, the app logs the error and uses
  the same tools locally, so itinerary generation keeps working.
- **Transport.** `stdio` (the server runs as a subprocess of the app).
Check that the MCP tools respond:
 
```bash
uv run python -m scripts.check_mcp
```
 
At startup the log shows `MCP tools loaded: ['get_weather', 'find_places_or_route']`.
 
### Adding another MCP server
 
1. Create a new server file in `app/mcp_tools/servers/` (for example calendar or bookings).
2. Add it to `build_server_config()` in `provider.py`.
3. Add its tool names to the allowlist in `main.py`.
Tools that change data (create a calendar event, make a booking) should ask the
user for confirmation before they run.
 
### Itinerary Generation: LangGraph Agent + Streaming

The itinerary endpoint no longer makes a single blocking LLM call. It runs
a LangGraph agent that reasons over multiple tools and streams progress to
the client in real time via Server-Sent Events (SSE).

### Known limitations

- Cost estimates from `cost_calculation` are rough and not currently
  validated against the trip's actual budget.
- The model's final JSON is extracted from mixed prose + tool narration
  via regex (fenced ```json block, falling back to outermost `{...}`),
  since the agent narrates between tool calls rather than emitting only JSON.
- Speech accuracy depends on the model size and the language. Test with your real audio