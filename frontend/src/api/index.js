import axios from 'axios';

// Базовый URL FastAPI сервера
const API = axios.create({
  baseURL: 'https://crispy-chainsaw-pjj55jw9x6c6rv-8000.app.github.dev/api',
  // ЕСЛИ ВЫ С ЛОКАЛЬНОГО СЕРВЕРА, РАСКОММЕНТИРУЙТЕ СЛЕДУЮЩУЮ СТРОКУ, А НАВЕРХУ ЗАКОММЕНТИРУЙТЕ:
  // baseURL: 'http://localhost:8000/api',
});

// АВТОМАТИЧЕСКОЕ ДОБАВЛЕНИЕ КЛЮЧА
API.interceptors.request.use((config) => {
  const apiKey = localStorage.getItem('gemini_api_key');
  if (apiKey) {
    config.headers['X-Gemini-API-Key'] = apiKey;
  }
  return config;
});

// --- Static Data ---
export const getCharacters = () => API.get('/characters').then(res => res.data);
export const getScenarios = () => API.get('/scenarios').then(res => res.data);
export const getStyles = () => API.get('/styles').then(res => res.data);

// --- Sessions ---
export const getSessions = () => API.get('/sessions').then(res => res.data);
export const loadSession = (id) => API.get(`/sessions/${id}`).then(res => res.data);

// createData: { character_id, profile_id, user_persona: {...}, scenario_id? }
export const createSession = (createData) => API.post('/sessions', createData).then(res => res.data);

// --- Chat ---
export const sendMessage = (sessionId, text) => API.post('/chat/send', { session_id: sessionId, text }).then(res => res.data);
export const regenerateMessage = (sessionId) => API.post('/chat/regenerate', { session_id: sessionId }).then(res => res.data);

// --- History ---
export const editMessage = (sessionId, index, newText) => API.post('/history/edit', { session_id: sessionId, msg_index: index, new_text: newText });
export const rewindChat = (sessionId, targetIndex) => API.post('/history/rewind', { session_id: sessionId, target_index: targetIndex });
export const swipeMessage = (sessionId, index, newText) => API.post('/history/swipe', { session_id: sessionId, msg_index: index, new_content: newText });

export default API;