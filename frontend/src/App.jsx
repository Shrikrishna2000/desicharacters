import { useEffect, useState } from 'react';
import Chat from './Chat';
import { useCharacterStore } from './store/characterStore';

function App() {
  const { fetchCharacters, characters, loading, error, selectedCharacter, selectCharacter } = useCharacterStore();
  const [timer, setTimer] = useState(60);
  const [showLoading, setShowLoading] = useState(true);

  // Fetch characters on mount
  useEffect(() => {
    fetchCharacters();
  }, []);

  // Countdown timer logic
  useEffect(() => {
    if (!loading) {
      setShowLoading(false); // Stop showing loading if data arrived
      return;
    }

    setShowLoading(true);
    setTimer(60);
    const interval = setInterval(() => {
      setTimer((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          setShowLoading(false); // Stop showing loading when timer ends
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [loading]);

  // Loading screen with countdown
  if (showLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
        <h2 className="text-2xl font-semibold mb-4">Loading characters...</h2>
        <p className="text-gray-600">Please wait {timer}s</p>
      </div>
    );
  }

  // Error screen
  if (error) {
    return <div className="text-center mt-10 text-red-500">{error}</div>;
  }

  // Character selection screen
  if (!selectedCharacter) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 p-6">
        <h1 className="text-3xl font-bold mb-8">Select a Character</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 w-full max-w-6xl">
          {characters.map((c) => (
            <button
              key={c.id}
              onClick={() => selectCharacter(c)}
              className="bg-white border border-gray-200 hover:border-blue-500 shadow-sm hover:shadow-md transition-all duration-200 rounded-xl p-5 text-left group"
            >
              <h2 className="text-xl font-semibold text-gray-800 group-hover:text-blue-600 mb-2">
                {c.name}
              </h2>
              <div className="text-gray-600 text-sm leading-relaxed mb-4">
                {c.description}
              </div>
              <div className="flex flex-wrap">
                {c.tags && c.tags.map((tag, index) => (
                  <span
                    key={index}
                    className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full mr-2 mb-1"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </button>
          ))}
        </div>
      </div>
    );
  }

  // Show chat when a character is selected
  return <Chat />;
}

export default App;
