import os
import json
from dotenv import load_dotenv
from typing import List, Dict
from pydantic import BaseModel
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
# LangChain imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage

# Load environment variables
load_dotenv()

app = FastAPI()

origins = [
    "*",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    expose_headers=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
#  Initialize the LangChain LLM
# -----------------------------
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.7,
    google_api_key=os.environ.get("GOOGLE_API_KEY"),
)

# -----------------------------
#  Load characters
# -----------------------------
@app.get("/characters", response_model=List[Dict])
def read_characters():
    with open("characters.json", "r") as f:
        characters = json.load(f)
    return characters

# Store chat sessions per character
conversation_sessions = {}

# -----------------------------
#  Pydantic Model for requests
# -----------------------------
class ChatHistory(BaseModel):
    history: List[Dict[str, str]]
    character_id: str

# -----------------------------
#  Summarization function
# -----------------------------
def summarize_text(text_to_summarize: str) -> str:
    prompt = (
        f"Please create an abstractive summary of the following conversation. "
        "Focus on key topics, decisions, and outcomes. Keep it concise (<=2 sentences).\n\n"
        f"Conversation:\n\n{text_to_summarize}"
    )

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        print("Summary  : ", responce.content)
        return response.content
    except Exception as e:
        print(f"Error during summarization: {e}")
        return "Failed to generate summary."

# -----------------------------
#  REST endpoint for summaries
# -----------------------------
@app.post("/chat/summary")
async def create_chat_summary(data: ChatHistory):
    try:
        formatted_history = "\n".join(
            [f"{m['role']}: {m['parts']}" for m in data.history]
        )
        summary_text = summarize_text(formatted_history)
        return {"summary": summary_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

# -----------------------------
#  WebSocket endpoint for chat
# -----------------------------
@app.websocket("/ws/{character_id}")
async def websocket_endpoint(websocket: WebSocket, character_id: str):
    await websocket.accept()

    if character_id not in conversation_sessions:
        # Load character info
        character_data = next(
            (c for c in read_characters() if c["id"] == character_id), None
        )
        if not character_data:
            await websocket.send_text(
                json.dumps({"role": "system", "parts": "Error: Character not found."})
            )
            await websocket.close()
            return

        base_prompt = f"""
        You are {character_data['name']}.
        Your Visual Description: {character_data['Visual_Description']}
        Your Personality: {character_data['Personality']}
        Roleplay Behavior Examples: {character_data['Roleplay_Examples']}.
        Guidelines:
        1. Stay in character; never break the fourth wall.
        2. Always respond in the user’s language.
        3. Keep responses ≤70 words.
        4. Never reveal you're an AI or language model.
        5. Politely address unethical/harmful inputs; condemn repeated offenses.
        6. Politely refuse inappropriate questions.
        """

        # Start chat history for this character
        conversation_sessions[character_id] = [
            SystemMessage(content=base_prompt.strip())
        ]

        # Initial message
        init_response = llm.invoke(conversation_sessions[character_id])
        await websocket.send_text(
            json.dumps({"role": "assistant", "parts": init_response.content})
        )

    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received raw: {data}")

            # Try to parse JSON safely
            try:
                parsed = json.loads(data)
            except json.JSONDecodeError:
                parsed = {"type": "message", "content": data}
            
            # Handle "resume" messages
            if parsed.get("type") == "resume":
                history = parsed.get("history", [])
                print(f"Resuming conversation for {character_id} with {len(history)} messages")

                # Optional: rebuild session state
                session = conversation_sessions.get(character_id, [])
                for msg in history:
                    if msg["role"] == "user":
                        session.append(HumanMessage(content=msg["parts"]))
                    elif msg["role"] == "assistant":
                        session.append(AIMessage(content=msg["parts"]))
                    elif msg["role"] == "system":
                        session.append(SystemMessage(content=msg["parts"]))

                conversation_sessions[character_id] = session

                await websocket.send_text(
                    json.dumps({
                        "role": "system",
                        "parts": f"✅ Conversation for {character_id} restored ({len(history)} messages)."
                    })
                )
                continue

            # Retrieve chat history
            chat_history = conversation_sessions[character_id]

            # Append user message
            chat_history.append(HumanMessage(content=data))

            # Generate model response
            try:
                response = llm.invoke(chat_history)
                chat_history.append(AIMessage(content=response.content))

                await websocket.send_text(
                    json.dumps({"role": "assistant", "parts": response.content})
                )
                print(f"AI response: {response.content}")

            except Exception as e:
                err_msg = "AI: Sorry, an error occurred. Please try again."
                print(f"Error sending message to AI: {e}")
                await websocket.send_text(
                    json.dumps({"role": "system", "parts": err_msg})
                )

    except WebSocketDisconnect:
        print("WebSocket disconnected.")
    except asyncio.CancelledError:
        # Happens when server stops or websocket task cancelled
        print("WebSocket task cancelled (server shutting down).")
    except Exception as e:
        print(f"WebSocket closed with an unexpected error: {e}")
