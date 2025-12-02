import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { loadSession, getCharacters } from '../api';
import { PlusCircle, MessageSquare, Key } from 'lucide-react';
import ApiKeyModal from '../components/ApiKeyModal';

interface Session {
  id: string;
  user_name: string;
  character_name?: string;
  character_id: string;
  msg_count: number;
  summary?: string;
  persona_name?: string;
}

export default function HomePage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isKeyModalOpen, setKeyModalOpen] = useState(false);

  useEffect(() => {
    const loadSessions = async () => {
      const localSessionIds = JSON.parse(localStorage.getItem('session_ids') || '[]');
      const characters = await getCharacters();
      
      const sessionPromises = localSessionIds.map((id: string) => 
        loadSession(id).then(data => {
          const char = characters.find((c: any) => c.id === data.meta?.character_id);
          return {
            id,
            user_name: data.title || `${data.meta?.user_persona?.name || 'User'} x ${char?.name || 'AI'}`,
            character_name: char?.name || data.meta?.character_id || 'AI',
            character_id: data.meta?.character_id || '',
            persona_name: data.meta?.user_persona?.name || 'User',
            msg_count: data.msg_count || 0,
            summary: data.summary || 'Start of a new journey...'
          };
        }).catch(() => null)
      );
      
      const results = await Promise.all(sessionPromises);
      setSessions(results.filter(Boolean) as Session[]);
    };
    
    loadSessions();
  }, []);

  return (
    <div className="w-full mx-auto py-10 px-4 md:px-8">
      <div className="fixed top-4 right-4 z-50">
        <button 
          onClick={() => setKeyModalOpen(true)}
          className="flex items-center gap-2 text-zinc-500 hover:text-yellow-500 transition text-sm bg-zinc-900/50 px-3 py-1.5 rounded-full border border-zinc-800 hover:border-yellow-500/50"
        >
          <Key size={16} />
          <span>API Key</span>
        </button>
      </div>

      <div className="text-center mb-10">
        <h1 className="text-4xl font-bold text-primary mb-2">Roleplay Engine</h1>
        <p className="text-zinc-500 mb-6">Choose your story</p>
        <Link 
          to="/setup" 
          className="inline-flex items-center gap-2 bg-primary hover:bg-blue-600 text-white px-8 py-4 rounded-xl font-bold text-lg transition shadow-lg shadow-blue-900/20"
        >
          <PlusCircle size={24} />
          New Adventure
        </Link>
      </div>
      
      <div className="max-w-7xl mx-auto">
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-zinc-400 border-b border-zinc-800 pb-2 mb-4">
            Recent Sessions
          </h2>
          
          {sessions.length === 0 ? (
            <div className="text-center py-10 bg-zinc-800/50 rounded-lg border border-zinc-700/50 border-dashed">
              <p className="text-zinc-500">No saved stories yet.</p>
            </div>
          ) : (
            <div className="grid gap-3">
              {sessions.map(s => (
                <Link 
                  key={s.id} 
                  to={`/chat/${s.id}`}
                  className="group block bg-zinc-800 p-5 rounded-xl border border-zinc-700 hover:border-primary/50 hover:bg-zinc-750 transition"
                >
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <div className="text-lg font-semibold text-zinc-100 mb-1">
                        {s.user_name}
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <span className="text-blue-400">{s.persona_name}</span>
                        <span className="text-zinc-600">x</span>
                        <span className="text-purple-400">{s.character_name}</span>
                      </div>
                    </div>
                    <span className="text-xs text-zinc-500 bg-zinc-900 px-2 py-1 rounded">
                      {s.msg_count} msgs
                    </span>
                  </div>
                  
                  <p className="text-sm text-zinc-400 line-clamp-2 mt-2">
                    {s.summary || "Start of a new journey..."}
                  </p>
                  
                  <div className="mt-3 flex items-center gap-2 text-xs text-zinc-600 font-mono">
                    <MessageSquare size={12} />
                    ID: {s.id.substring(0, 15)}...
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      <ApiKeyModal 
        isOpen={isKeyModalOpen} 
        onClose={() => setKeyModalOpen(false)} 
      />
    </div>
  );
}
