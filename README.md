# 🪷 DesiCharacters

**Chat with uniquely Desi personalities — powered by AI & built with FastAPI + React.**  
_An open-source experiment in bringing Indian characters to life through AI conversations._

Live - [desicharactersai](https://zuno10.github.io/bahrupiya)

---

## ✨ Overview

DesiCharacters lets you chat with distinct Indian personalities — each with their own tone, humor, and cultural flavor.  
Built with **FastAPI** + **React** and powered by **Gemini AI**, it delivers a smooth, privacy-first chat experience.

It uses a **tiered summarization system** to handle long conversations efficiently — all chat data and summaries are stored locally in the user's browser for privacy.

---

## 🎯 Features

- **💬 Chat with Desi AI characters** — Bollywood-style, techies, neighborhood aunties, and more.  
- **✍️ Customizable personalities** — modify or add new characters via simple prompt files.  
- **🔒 Privacy-first** — chats and summaries are stored only in the browser (LocalStorage) by default.  
- **🧠 Tiered summarization** — Local → Chapter → Global summaries for handling long chats.  
- **⚡ Fast frontend (React + Vite)** and **clean backend (FastAPI)** for modular scaling.  
- **🧱 Modular structure** — separate frontend, backend, and character data for clean maintenance.  

---

## 🧠 Tech Stack

| 🧩 Layer | ⚙️ Tech |
|:--|:--|
| **Frontend** | [React](https://react.dev/), [Vite](https://vitejs.dev/), [TailwindCSS](https://tailwindcss.com/) |
| **Backend** | [FastAPI](https://fastapi.tiangolo.com/), Python |
| **AI** | [Gemini API](https://ai.google.dev/) |
| **Storage** | LocalStorage (privacy-focused) |
| **Development** | Uvicorn, npm |

---

## 📦 Project Highlights
### ⚙️ Backend Highlights
- `main.py`: API Endpoints and backend server.
- `requirements.txt`: Python backend dependencies.
- `characters.json`: Character data or configuration.
- `.env.example`: Environment variable template.

### 🎨 Frontend Highlights
- `src/`: Source code for the UI.
- `public/`: Static assets.
- `vite.config.js`: Vite configuration for frontend bundling.
- `tailwind.config.js`: TailwindCSS setup.


## ⚙️ Setup & Installation

Follow these steps to run DesiCharacters locally.

### 🧰 Prerequisites
- 🐍 Python 3.8+  
- 🧩 Node.js & npm  
- 🔑 A **Gemini API Key** (Get one from [Google AI Studio](https://ai.google.dev/gemini-api/docs/api-key) login and click on Get API Keys) 

### 🪄 1. Clone the Repository
~~~bash
git clone https://github.com/Shrikrishna2000/desicharecters
cd desicharacters
~~~

### 🔐 2. Set up your API Key
Create a file named `.env` inside the `backend/` directory and add your key:
~~~text
# backend/.env
GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
~~~

### 🧠 3. Backend Setup
~~~bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
~~~
🟢 The backend API runs at: **http://localhost:8000**

### 💻 4. Frontend Setup
Open a new terminal:
~~~bash
cd ../frontend
npm install
npm run dev
~~~
🟢 Frontend available at: **http://localhost:5173**

### 🧪 5. API Documentation
Visit **Swagger UI** at:  
👉 **http://localhost:8000/docs**

---

## 🔌 API Endpoints

This project uses standard **REST endpoints** and a **WebSocket** for real-time chat.

| 🔗 Endpoint | 🧭 Method | 📝 Description |
|:--|:--|:--|
| `/chat` | `POST` | _Deprecated — use WebSocket for real-time chat (kept for testing)._ |
| `/summary` | `GET` | Generate conversation summaries using the tiered summarization strategy. |
| `/characters` | `GET` | Retrieve available characters and their metadata. |
| `/ws/{character_id}` | `WEBSOCKET` | Real-time chat with persistent context for the selected character. |

---

## 📸 Screenshots / Demo

_Coming soon — add GIF or screenshot of the chat UI here._  
_(Example: conversation between a Bollywood-style character and the user.)_

---

## 🚀 Future Plans

### 🧩 User Experience
- 📥 Download and 📤 Upload chats (resume past conversations)  
- 📱 Improved mobile responsiveness  

### 🧠 AI Layer
- ⚙️ Optionally switch to **LangChain** for modular LLM pipelines  

### 🎭 Customization
- 🧑‍🎨 In-app UI for creating and editing characters  

### 💾 Persistence
- ☁️ Optional cloud sync (MongoDB / Supabase)  
- 🔒 Default remains **browser-local** for maximum privacy  

---

## 🤝 Contributing

Contributions are welcome!  
If you’d like to add a character, improve the code, or fix a bug — here’s how:

1. 🍴 **Fork** the repository  
2. 🌿 **Create a branch:** `git checkout -b feature/YourFeature`  
3. 💾 **Commit:** `git commit -m "Add YourFeature"`  
4. 🚀 **Push & Open a Pull Request**

---

## 📜 License

🪪 **MIT License © 2025 Shrikrishna Soni**

---

## 💡 Acknowledgements

Special thanks to these amazing tools & frameworks:

- ⚡ **FastAPI** — high-performance backend  
- ⚛️ **React** — dynamic, modern UI  
- 🧠 **Gemini AI API** — powering intelligent conversations and summaries  
- 🎨 **TailwindCSS** — clean, responsive styling  

---
