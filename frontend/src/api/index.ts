const API_BASE = 'https://crispy-chainsaw-pjj55jw9x6c6rv-8000.app.github.dev/api';

// ЕСЛИ С ЛОКАЛЬНОГО ПК, ТО РАСКОММЕНТИРОВАТЬ СТРОЧКУ НИЖЕ, А СТРОЧКУ ВЫШЕ ЗАКОММЕНТИРОВАТЬ
// const API_BASE = 'http://localhost:8000/api';

const getApiKey = (): string => {
  return localStorage.getItem('gemini_api_key') || '';
};

const fetchWithKey = async (url: string, options: RequestInit = {}) => {
  const headers = {
    'Content-Type': 'application/json',
    'X-Gemini-Api-Key': getApiKey(),
    ...options.headers,
  };
  
  const response = await fetch(url, { ...options, headers });
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return response.json();
};

export const getCharacters = () => fetchWithKey(`${API_BASE}/characters`);
export const getScenarios = () => fetchWithKey(`${API_BASE}/scenarios`);
export const getStyles = () => fetchWithKey(`${API_BASE}/styles`);
export const getSessions = () => fetchWithKey(`${API_BASE}/sessions`);

export const createSession = (payload: any) => 
  fetchWithKey(`${API_BASE}/sessions`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });

export const loadSession = (sessionId: string) => 
  fetchWithKey(`${API_BASE}/sessions/${sessionId}`);

export const sendMessage = (sessionId: string, message: string) =>
  fetchWithKey(`${API_BASE}/chat/send`, {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, text: message }),
  });

export const regenerateMessage = (sessionId: string) =>
  fetchWithKey(`${API_BASE}/chat/regenerate`, {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId }),
  });

export const editMessage = (sessionId: string, index: number, newText: string) =>
  fetchWithKey(`${API_BASE}/history/edit`, {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, msg_index: index, new_text: newText }),
  });

export const rewindChat = (sessionId: string, targetIndex: number) =>
  fetchWithKey(`${API_BASE}/history/rewind`, {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, target_index: targetIndex }),
  });
