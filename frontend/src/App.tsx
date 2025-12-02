import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

import HomePage from './pages/HomePage';
import SetupPage from './pages/SetupPage';
import ChatPage from './pages/ChatPage';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-zinc-900 text-gray-100 font-sans">
        <div className="max-w-4xl mx-auto p-4 h-screen flex flex-col">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/setup" element={<SetupPage />} />
            <Route path="/chat/:sessionId" element={<ChatPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
