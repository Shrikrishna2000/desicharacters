import { create } from 'zustand';

const LOCAL_STORAGE_KEY = 'chatHistories';
const BASE_URL = "http://127.0.0.1:8000";

export const useCharacterStore = create((set, get) => ({
  characters: [],
  selectedCharacter: null,
  loading: false,
  error: null,

  chatHistories: typeof window !== "undefined"
    ? JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEY) || '{}')
    : {},

  fetchCharacters: async () => {
    set({ loading: true, error: null });

    let attempts = 0;
    const maxAttempts = 6;
    let success = false;
    let data = [];

    while (attempts < maxAttempts && !success) {
      try {
        const res = await fetch(`${BASE_URL}/characters`);
        if (!res.ok) throw new Error(`Error ${res.status}`);
        data = await res.json();
        success = true;
      } catch (err) {
        console.error(`Attempt ${attempts + 1} failed:`, err);
        attempts++;
        // Wait 1 second before retrying
        await new Promise((r) => setTimeout(r, 10000));
      }
    }

    if (success) {
      set({ characters: data, loading: false });
    } else {
      set({ error: `Failed to fetch characters after ${maxAttempts} attempts`, loading: false });
    }
  },

  selectCharacter: (character) => set({ selectedCharacter: character }),

  addMessage: (characterId, message) => {
    const { chatHistories } = get();
    const updatedHistory = chatHistories[characterId]
      ? [...chatHistories[characterId], message]
      : [message];
    const newHistories = { ...chatHistories, [characterId]: updatedHistory };
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(newHistories));
    set({ chatHistories: newHistories });
  },

  getMessages: (characterId) => {
    const { chatHistories } = get();
    return chatHistories[characterId] || [];
  },

  clearChat: (characterId) => {
    const { chatHistories } = get();
    const newHistories = { ...chatHistories, [characterId]: [] };
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(newHistories));
    set({ chatHistories: newHistories });
  },
}));
