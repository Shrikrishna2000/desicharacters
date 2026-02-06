# Backend API Documentation

**Base URL:** `http://localhost:8000`  
**Swagger UI:** `http://localhost:8000/docs`

---

## 🏥 Health Check

### Health Status
- **URL:** `/health`
- **Method:** `GET`
- **Response:** `200 OK`
  ```json
  {
    "status": "ok"
  }
  ```

---

## 🎭 Character Management

### 1. List All Characters
Retrieves all available character profiles from the `/prompts` directory.

- **URL:** `/characters`
- **Method:** `GET`
- **Response:** `200 OK`
  ```json
  [
    {
      "id": "dadi",
      "name": "Dadi",
      "version": "v1",
      "Visual_Description": "Petite, weathered frame in a bright floral sari...",
      "Personality": "Chaotic, fun-loving, brutally honest grandma...",
      "Roleplay_Examples": [
        "'Dating app? Arre beta! In our day, ek shy glance was enough!'",
        "'Mindfulness app? Hah! We chased buffaloes in the rain!'"
      ],
      "description": "Dadi is the ultimate roaster-grandma...",
      "tags": ["elder", "chaotic", "fun-loving", "roaster"]
    },
    ...
  ]
  ```

### 2. Get Specific Character
Retrieves details for a single character by ID.

- **URL:** `/characters/{character_id}`
- **Method:** `GET`
- **Path Parameters:**
  - `character_id` (string): Unique character identifier (e.g., `dadi`, `priya`)
- **Response:** `200 OK` - Character object (see structure above)
- **Error Response:** `404 Not Found`
  ```json
  {
    "detail": "Character not found"
  }
  ```

### 3. Generate Character ⭐ NEW
Generates a new AI character profile based on a topic or description using Google Gemini.

- **URL:** `/characters/generate`
- **Method:** `POST`
- **Request Body:**
  ```json
  {
    "topic": "A grumpy old detective who loves cats"
  }
  ```
- **Response:** `200 OK`
  ```json
  {
    "name": "Detective Thomas Blackwood",
    "Visual_Description": "A man in his late 60s with a furrowed brow and salt-and-pepper mustache...",
    "Personality": "Cynical and world-weary, but has a soft spot for cats...",
    "Roleplay_Examples": [
      "User: Good morning, Detective. | Character: Morning. Don't expect me to be cheerful...",
      "User: Can you help find my cat? | Character: A missing cat, huh?..."
    ],
    "description": "Generated from topic: A grumpy old detective who loves cats"
  }
  ```
- **Error Responses:**
  - `400 Bad Request` - Topic is required
  - `500 Internal Server Error` - LLM generation failed

**How it works:**
1. Uses Google Gemini 2.5 Flash to generate a character profile
2. Processes LLM response with robust JSON parsing (handles newlines, escaping, etc.)
3. Maps response to internal schema with proper field names
4. Returns character ready to use in sessions

---

## 💬 Chat Endpoints

### 4. Send Chat Message
Generate an AI reply for a specific session (deprecated - use WebSocket).

- **URL:** `/chat/send`
- **Method:** `POST`
- **Request Body:**
  ```json
  {
    "session_id": "session_123",
    "user_message": "Hello, how are you?"
  }
  ```
- **Response:** `200 OK`
  ```json
  {
    "reply": "I'm doing great! How can I help you?"
  }
  ```
- **Rate Limit:** Per session

### 5. Generate Chat Summary
Creates an abstractive summary of conversation history.

- **URL:** `/chat/summary`
- **Method:** `POST`
- **Request Body:**
  ```json
  {
    "history": [
      {
        "role": "user",
        "parts": "What's your favorite memory?"
      },
      {
        "role": "assistant",
        "parts": "I remember a beautiful sunset in Mumbai..."
      },
      {
        "role": "user",
        "parts": "That sounds amazing!"
      }
    ]
  }
  ```
- **Response:** `200 OK`
  ```json
  {
    "summary": "User and assistant discussed memorable experiences, specifically a beautiful sunset in Mumbai."
  }
  ```
- **Rate Limit:** Global limit for summary generation

---

## 📋 Session Management

### 6. Create Session
Initialize a new conversation session with a character.

- **URL:** `/session/create`
- **Method:** `POST`
- **Request Body:**
  ```json
  {
    "session_id": "session_123",
    "character": {
      "id": "dadi",
      "name": "Dadi",
      "Visual_Description": "...",
      "Personality": "...",
      "Roleplay_Examples": [...]
    },
    "history": []
  }
  ```
- **Response:** `200 OK`
  ```json
  {
    "created": true
  }
  ```

### 7. Get Session
Retrieve a stored session state from Redis.

- **URL:** `/session/{session_id}`
- **Method:** `GET`
- **Path Parameters:**
  - `session_id` (string): Session identifier
- **Response:** `200 OK`
  ```json
  {
    "session_id": "session_123",
    "character": { ... },
    "history": [ ... ],
    "summary": "Conversation summary if available"
  }
  ```
- **Error Response:** `404 Not Found`
  ```json
  {
    "detail": "Session not found"
  }
  ```

### 8. Update Session History
Append new messages to session history.

- **URL:** `/session/{session_id}/update`
- **Method:** `POST`
- **Path Parameters:**
  - `session_id` (string): Session identifier
- **Request Body:**
  ```json
  {
    "history": [
      {
        "role": "user",
        "parts": "New user message"
      },
      {
        "role": "assistant",
        "parts": "AI response"
      }
    ]
  }
  ```
- **Response:** `200 OK`
  ```json
  {
    "updated": true
  }
  ```

### 9. Delete Session
Remove a session completely from storage.

- **URL:** `/session/{session_id}`
- **Method:** `DELETE`
- **Path Parameters:**
  - `session_id` (string): Session identifier
- **Response:** `200 OK`
  ```json
  {
    "deleted": true
  }
  ```

---

## 🔌 WebSocket Endpoint

### 10. Real-time Chat (WebSocket)
Production-ready WebSocket for streaming chat responses with session persistence.

- **URL:** `ws://localhost:8000/ws/chat/{session_id}`
- **Headers (optional):**
  - `x-client-id`: Unique client identifier
  - `x-tab-id`: Browser tab identifier
- **Features:**
  - ✅ Streaming responses (chunks)
  - ✅ Session resume/restore
  - ✅ Heartbeat ping/pong (20s interval)
  - ✅ Idle timeout (120s)
  - ✅ Rate limiting (30 requests/60s)
  - ✅ Input sanitization & jailbreak detection

#### Message Protocol

**Client → Server Messages:**

1. **User Message**
   ```json
   {
     "type": "user_message",
     "content": "Hello, how are you today?"
   }
   ```
   - Plain string also accepted: `"Hello, how are you?"`

2. **Resume/Restore Session**
   ```json
   {
     "type": "resume"
   }
   ```
   - Server responds with last 20 messages from history

3. **Ping (Heartbeat)**
   ```json
   {
     "type": "ping"
   }
   ```

**Server → Client Messages:**

1. **Stream Start**
   ```json
   {
     "type": "assistant_stream_start"
   }
   ```

2. **Stream Chunk** (repeats multiple times)
   ```json
   {
     "type": "assistant_stream_chunk",
     "chunk": "Hello! How can"
   }
   ```

3. **Stream End**
   ```json
   {
     "type": "assistant_stream_end"
   }
   ```

4. **Pong (Heartbeat Response)**
   ```json
   {
     "type": "pong",
     "ts": 1701503858123
   }
   ```

5. **Session Restored**
   ```json
   {
     "type": "restore",
     "payload": {
       "history": [ ... ],
       "summary": "Previous conversation summary"
     }
   }
   ```

6. **Acknowledgement**
   ```json
   {
     "type": "ack",
     "session_id": "session_123"
   }
   ```

7. **Error**
   ```json
   {
     "type": "error",
     "message": "Rate limit exceeded"
   }
   ```

#### WebSocket Example (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat/session_123', [], {
  headers: { 'x-client-id': 'client_abc', 'x-tab-id': 'tab_xyz' }
});

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  
  if (msg.type === 'assistant_stream_start') {
    console.log('Response incoming...');
  } else if (msg.type === 'assistant_stream_chunk') {
    console.log(msg.chunk);  // Print streamed text chunk by chunk
  } else if (msg.type === 'assistant_stream_end') {
    console.log('Response complete');
  } else if (msg.type === 'pong') {
    console.log('Heartbeat received');
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Connection closed');
};

// Send user message
ws.send(JSON.stringify({
  type: 'user_message',
  content: 'Hello there!'
}));

// Resume session after disconnect
setTimeout(() => {
  ws.send(JSON.stringify({ type: 'resume' }));
}, 2000);
```

---

## 🔐 Security & Rate Limiting

- **Rate Limits:**
  - Chat endpoint: Per session
  - Summary endpoint: Global limit
  - WebSocket: 30 requests per 60 seconds per client

- **Input Validation:**
  - User input is sanitized to prevent injection attacks
  - Jailbreak attempts are detected and rejected automatically
  - Special characters are escaped and normalized

- **Idle Timeout:**
  - WebSocket connections close after 120 seconds of inactivity
  - Server sends heartbeat every 20 seconds to keep connection alive

---

## ⚙️ Configuration

**Environment Variables:**
- `GOOGLE_API_KEY`: Gemini API key for LLM operations
- `SECRET_KEY` : Super secret

**Storage:**
- Character prompts: `/app/prompts/*.md` (Markdown files with [visual], [personality], [examples] sections)
- Session storage: Redis (in-memory, for chat history and session state)

**Key Services:**
- LLM: Google Gemini 2.5 Flash
- Framework: FastAPI + LangChain
- Rate Limiter: Per-client/session tracking

---

## 📝 Example Workflows

### Workflow 1: Quick Character Chat (REST only)
```
GET /characters → Browse all characters
GET /characters/{id} → Select one
POST /chat/send → Get single response
```

### Workflow 2: Full Session with WebSocket (Recommended)
```
GET /characters → Get character details
POST /session/create → Initialize session in Redis
WS /ws/chat/{session_id} → Connect WebSocket (persistent)
Send: "Hello!" → Receive streamed response in chunks
Send: "Tell me a story" → Receive streamed response
Send: "What did I say before?" → AI has full context
(Connection persists - no session recreation needed)
```

### Workflow 3: Resume Interrupted Conversation
```
WS /ws/chat/{session_id} → Reconnect to same session
Send: {"type": "resume"} → Receive last 20 messages + summary
Continue chatting...
```

### Workflow 4: AI-Generated Characters
```
POST /characters/generate → Create new character with AI
  Request: {"topic": "A mysterious fortune teller"}
  Response: Full character profile with personality & examples
POST /session/create → Start session with generated character
WS /ws/chat/{session_id} → Begin streaming chat
```

### Workflow 5: Summary Generation
```
POST /chat/summary → Analyze conversation history
  Request: {"history": [...all messages...]}
  Response: {"summary": "Concise summary of key points"}
```

---

## 🐛 Error Handling

All errors follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common Status Codes:**
- `200 OK` - Request successful
- `400 Bad Request` - Invalid input (missing required fields)
- `404 Not Found` - Resource not found (character, session)
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error (check server logs)

**Example Error Responses:**

Rate limit exceeded:
```json
{
  "detail": "Rate limit exceeded. Max 30 requests per 60 seconds."
}
```

Character generation failed:
```json
{
  "detail": "Invalid JSON from LLM: Expecting value at line 2"
}
```

---

## 📊 Data Schema Reference

### Character Object
```json
{
  "id": "string (unique identifier)",
  "name": "string (display name)",
  "version": "string (e.g., 'v1')",
  "Visual_Description": "string (detailed appearance)",
  "Personality": "string (personality traits and behaviors)",
  "Roleplay_Examples": "array of strings (example interactions)",
  "description": "string (brief summary)",
  "tags": "array of strings (e.g., ['friend', 'chaotic', 'fun-loving'])"
}
```

### Message Object
```json
{
  "role": "string ('user', 'assistant', or 'system')",
  "parts": "string (message content)"
}
```

### Session Object
```json
{
  "session_id": "string (unique session identifier)",
  "character": "Character object",
  "history": "array of Message objects",
  "summary": "string (optional, summary of conversation)",
  "created_at": "timestamp",
  "last_updated": "timestamp"
}
```

---

## 🚀 Getting Started

1. **Start the server:**
   ```bash
   uvicorn main:app --reload
   ```

2. **Access Swagger UI:**
   ```
   http://localhost:8000/docs
   ```

3. **Test a simple request:**
   ```bash
   curl http://localhost:8000/health
   ```

4. **Generate a character:**
   ```bash
   curl -X POST http://localhost:8000/characters/generate \
     -H "Content-Type: application/json" \
     -d '{"topic": "A wise monk who loves tea"}'
   ```

5. **Connect WebSocket for chat:**
   ```javascript
   const ws = new WebSocket('ws://localhost:8000/ws/chat/my_session_1');
   ws.onmessage = (e) => console.log(JSON.parse(e.data));
   ws.send(JSON.stringify({type: 'user_message', content: 'Hi!'}));
   ```

---

**Version:** 2.0  
**Last Updated:** December 2, 2025  
**Maintainer:** Backend Team

#### Protocol Details:

**Connection:**
- Upon connection, the server sends an initial greeting from the character.

**Client Messages:**
- **Standard Message:** Send a plain string or JSON.
- **Resume Session:** To restore a previous session context, send:
  ```json
  {
    "type": "resume",
    "history": [
       { "role": "user", "parts": "..." },
       { "role": "assistant", "parts": "..." }
    ]
  }
  ```

**Server Messages:**
- **Format:**
  ```json
  {
    "role": "assistant",
    "parts": "Response text..."
  }
  ```
- **System Messages:** (e.g., errors or status updates)
  ```json
  {
    "role": "system",
    "parts": "Error message..."
  }
  ```
