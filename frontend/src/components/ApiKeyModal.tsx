import React, { useState, useEffect } from 'react';
import { Key, Save, X, Eye, EyeOff } from 'lucide-react';

interface ApiKeyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function ApiKeyModal({ isOpen, onClose }: ApiKeyModalProps) {
  const [key, setKey] = useState('');
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setKey(localStorage.getItem('gemini_api_key') || '');
    }
  }, [isOpen]);

  const handleSave = () => {
    if (key.trim()) {
      localStorage.setItem('gemini_api_key', key.trim());
    } else {
      localStorage.removeItem('gemini_api_key');
    }
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <div className="bg-zinc-900 border border-zinc-700 p-6 rounded-2xl w-full max-w-md shadow-2xl">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Key className="text-yellow-500" /> API Settings
          </h2>
          <button onClick={onClose} className="text-zinc-500 hover:text-white transition">
            <X size={24} />
          </button>
        </div>

        <p className="text-sm text-zinc-400 mb-4">
          Enter your personal Google Gemini API Key. It will be stored locally in your browser and sent securely with requests.
        </p>

        <div className="relative mb-6">
          <input
            type={show ? "text" : "password"}
            className="w-full bg-zinc-950 border border-zinc-700 rounded-lg p-3 pr-12 focus:border-yellow-500 outline-none text-white font-mono"
            placeholder="AIzaSy..."
            value={key}
            onChange={(e) => setKey(e.target.value)}
          />
          <button 
            type="button"
            onClick={() => setShow(!show)}
            className="absolute right-3 top-3.5 text-zinc-500 hover:text-zinc-300"
          >
            {show ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>

        <div className="flex justify-end gap-3">
          <button 
            onClick={onClose}
            className="px-4 py-2 text-zinc-400 hover:text-white transition"
          >
            Cancel
          </button>
          <button 
            onClick={handleSave}
            className="px-6 py-2 bg-yellow-600 hover:bg-yellow-500 text-white font-semibold rounded-lg flex items-center gap-2 transition"
          >
            <Save size={18} /> Save Key
          </button>
        </div>
      </div>
    </div>
  );
}
