import { useEffect, useState, useRef, useCallback } from "react";
import Markdown from "react-markdown";
import { useCharacterStore } from "./store/characterStore";

// Constants for hierarchical summarization
const CHUNK_SIZE = 7;      // messages per chunk
const CHUNKS_PER_CHAPTER = 10;
const CHAPTERS_PER_GLOBAL = 10;

// BASE API URL
const BASE_URL = "http://127.0.0.1:8000";
function MessageBubble({ msg }) {
  const isUser = msg.role === "user";
  const isSummary = msg.role === "summary";
  const isSystem = msg.role === "system";

  const baseClass = isUser
    ? "bg-blue-500 text-white self-end"
    : isSummary
    ? msg.summaryType === "chunk"
      ? "bg-yellow-100 text-gray-800 self-center"
      : msg.summaryType === "chapter"
      ? "bg-orange-100 text-gray-800 self-center"
      : "bg-green-100 text-gray-800 self-center" // global
    : isSystem
    ? "bg-red-100 text-gray-800 self-center"
    : "bg-gray-300 text-gray-800 self-start";

  if (msg.removed) return null; // hide old rolled-up summaries

  return (
    <div className={`my-1 p-2 rounded-lg max-w-sm ${baseClass}`}>
      <Markdown>{msg.parts}</Markdown>
    </div>
  );
}

function Chat() {
  const {
    selectedCharacter,
    selectCharacter,
    addMessage,
    getMessages,
  } = useCharacterStore();

  const characterId = selectedCharacter?.id;

  const [inputMessage, setInputMessage] = useState("");
  const [status, setStatus] = useState("Disconnected");
  const [messages, setMessages] = useState([]);

  const ws = useRef(null);
  const summarizingRef = useRef(false);

  // Hydrate messages from store
  useEffect(() => {
    if (!characterId) return;
    setMessages(getMessages(characterId) || []);
  }, [characterId, getMessages]);

  // Keep messages in sync with store
  useEffect(() => {
    if (!characterId) return;
    const interval = setInterval(() => {
      setMessages(getMessages(characterId) || []);
    }, 300); // short polling, could switch to Zustand subscribe
    return () => clearInterval(interval);
  }, [characterId, getMessages]);

  // WebSocket connection
  useEffect(() => {
    if (!characterId) return;

    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }

    ws.current = new WebSocket(`${BASE_URL}/ws/${characterId}`);

    ws.current.onopen = () => {
      setStatus("Connected");
      const history = getMessages(characterId);
      ws.current.send(JSON.stringify({ type: "resume", history }));
    };


    ws.current.onmessage = (event) => {
      let parsed;
      try {
        parsed = JSON.parse(event.data);
      } catch {
        parsed = { role: "assistant", parts: String(event.data) };
      }

      const incoming = {
        role: parsed.role || "assistant",
        parts: parsed.parts?.trim() || "",
      };

      addMessage(characterId, incoming);
      triggerSummaryIfNeeded([...getMessages(characterId), incoming]);
    };

    ws.current.onclose = () => setStatus("Disconnected");
    ws.current.onerror = (err) => {
      console.error("WebSocket error", err);
      setStatus("Error");
    };

    return () => ws.current?.close();
  }, [characterId, addMessage, getMessages]);

  // Hierarchical summarization
  const triggerSummaryIfNeeded = useCallback(
    async (allMessages) => {
      if (summarizingRef.current) return;
      summarizingRef.current = true;

      try {
        // 1️⃣ Chunk summarization
        const rawMessages = allMessages.filter(
          (m) => m.role === "user" || m.role === "assistant"
        );

        const lastChunkStart =
          Math.floor(rawMessages.length / CHUNK_SIZE) * CHUNK_SIZE;
        const lastChunk = rawMessages.slice(lastChunkStart);

        if (lastChunk.length === CHUNK_SIZE) {
          const res = await fetch(`${BASE_URL}/chat/summary`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ history: lastChunk, character_id: characterId }),
          });
          if (res.ok) {
            const data = await res.json();
            const chunkSummary = {
              role: "summary",
              summaryType: "chunk",
              index: Math.floor(rawMessages.length / CHUNK_SIZE),
              parts: data.summary?.trim() || "No summary.",
            };
            addMessage(characterId, chunkSummary);
          }
        }

        // 2️⃣ Chapter roll-up
        const chunkSummaries = allMessages.filter(
          (m) => m.role === "summary" && m.summaryType === "chunk"
        );

        if (chunkSummaries.length >= CHUNKS_PER_CHAPTER) {
          const chapterChunks = chunkSummaries.slice(0, CHUNKS_PER_CHAPTER);
          const res = await fetch(`${BASE_URL}/chat/summary`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              history: chapterChunks.map((c) => ({ role: "summary", parts: c.parts })),
              character_id: characterId,
            }),
          });
          if (res.ok) {
            const data = await res.json();
            const chapterSummary = {
              role: "summary",
              summaryType: "chapter",
              index: Math.floor(chunkSummaries[0].index / CHUNKS_PER_CHAPTER),
              parts: data.summary?.trim() || "No summary.",
            };
            addMessage(characterId, chapterSummary);

            // Mark old chunks as removed
            chapterChunks.forEach((c) =>
              addMessage(characterId, { ...c, removed: true })
            );
          }
        }

        // 3️⃣ Global roll-up
        const chapterSummaries = allMessages.filter(
          (m) => m.role === "summary" && m.summaryType === "chapter"
        );

        if (chapterSummaries.length >= CHAPTERS_PER_GLOBAL) {
          const chaptersToRoll = chapterSummaries.slice(0, CHAPTERS_PER_GLOBAL);
          const res = await fetch(`${BASE_URL}/chat/summary`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              history: chaptersToRoll.map((c) => ({ role: "summary", parts: c.parts })),
              character_id: characterId,
            }),
          });
          if (res.ok) {
            const data = await res.json();
            const globalSummary = {
              role: "summary",
              summaryType: "global",
              parts: data.summary?.trim() || "No summary.",
            };
            addMessage(characterId, globalSummary);

            // Mark old chapters as removed
            chaptersToRoll.forEach((c) =>
              addMessage(characterId, { ...c, removed: true })
            );
          }
        }
      } catch (err) {
        console.error("Hierarchical summarization error:", err);
      } finally {
        summarizingRef.current = false;
      }
    },
    [characterId, addMessage]
  );

  const sendMessage = () => {
    if (!inputMessage.trim() || !ws.current) return;
    if (ws.current.readyState !== WebSocket.OPEN) return;

    const userMsg = { role: "user", parts: inputMessage.trim() };
    addMessage(characterId, userMsg);
    triggerSummaryIfNeeded([...getMessages(characterId), userMsg]);

    ws.current.send(inputMessage.trim());
    setInputMessage("");
  };

  return (
    <div className="flex flex-col h-screen bg-gray-100 p-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-3xl font-bold text-gray-800">
          Chat with {selectedCharacter?.name}
        </h1>
        <button
          onClick={() => selectCharacter(null)}
          className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600"
        >
          Change Character
        </button>
      </div>

      {/* Status */}
      <p className="text-center text-sm text-gray-600 mb-4">
        Connection Status:{" "}
        <strong
          className={status === "Connected" ? "text-green-500" : "text-red-500"}
        >
          {status}
        </strong>
      </p>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 bg-white rounded-lg shadow-md mb-4 flex flex-col-reverse">
        {[...messages].reverse().map((msg, i) => (
          <MessageBubble key={i} msg={msg} />
        ))}
      </div>

      {/* Input */}
      <div className="flex items-center space-x-2">
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          className="flex-1 p-3 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Type your message..."
        />
        <button
          onClick={sendMessage}
          className="bg-blue-500 text-white p-3 rounded-full hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          ➤
        </button>
      </div>
    </div>
  );
}

export default Chat;
