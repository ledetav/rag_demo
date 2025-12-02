import React, { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { 
  ArrowLeft, Send, RefreshCw, Edit2, Trash2, 
  Bot, User as UserIcon, Loader2 
} from 'lucide-react';
import { LucideIcon } from 'lucide-react';

import { 
  loadSession, sendMessage, regenerateMessage, 
  editMessage, rewindChat 
} from '../api';

interface Message {
  role: 'user' | 'ai';
  content: string;
  index: number;
  isEditing?: boolean;
  editDraft?: string;
}

interface Meta {
  character_id?: string;
  scenario_state?: {
    current_step: number;
  };
}

export default function ChatPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadChat();
  }, [sessionId]);

  const loadChat = async () => {
    if (!sessionId) return;
    try {
      setLoading(true);
      const data = await loadSession(sessionId);
      const formatted = (data.full_history || []).map((m: Message) => ({ ...m, isEditing: false }));
      setMessages(formatted);
      setMeta(data.meta || {});
    } catch (err) {
      console.error("Failed to load session", err);
    } finally {
      setLoading(false);
      scrollToBottom();
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  
  useEffect(() => {
    scrollToBottom();
  }, [messages, generating]);

  const handleSend = async () => {
    if (!input.trim() || generating || !sessionId) return;

    const text = input;
    setInput('');
    setGenerating(true);

    const tempUserMsg: Message = { 
      role: 'user', 
      content: text, 
      index: messages.length 
    };
    setMessages(prev => [...prev, tempUserMsg]);

    try {
      const res = await sendMessage(sessionId, text);
      const aiMsg: Message = {
        role: 'ai',
        content: res.response,
        index: messages.length + 1
      };
      setMessages(prev => [...prev, aiMsg]);
    } catch (err) {
      console.error(err);
      alert("Error sending message");
    } finally {
      setGenerating(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      handleSend();
    }
  };

  const toggleEdit = (index: number) => {
    setMessages(prev => prev.map((msg, i) => 
      i === index ? { ...msg, isEditing: !msg.isEditing, editDraft: msg.content } : msg
    ));
  };

  const saveEdit = async (index: number, newText: string) => {
    if (!sessionId) return;
    setMessages(prev => prev.map((msg, i) => 
      i === index ? { ...msg, content: newText, isEditing: false } : msg
    ));
    
    try {
      await editMessage(sessionId, index, newText);
    } catch (err) {
      console.error("Edit failed", err);
      alert("Failed to save edit on server");
    }
  };

  const handleRegenerate = async () => {
    if (generating || !sessionId) return;
    
    const lastMsg = messages[messages.length - 1];
    if (lastMsg.role !== 'ai') return;

    setMessages(prev => prev.slice(0, -1));
    setGenerating(true);

    try {
      const res = await regenerateMessage(sessionId);
      const newAiMsg: Message = {
        role: 'ai',
        content: res.response,
        index: messages.length - 1
      };
      setMessages(prev => [...prev, newAiMsg]);
    } catch (err) {
      console.error(err);
      loadChat(); 
    } finally {
      setGenerating(false);
    }
  };

  const handleRewind = async (index: number) => {
    if (!window.confirm("Are you sure? This will delete this message and everything after it.") || !sessionId) return;
    
    const targetIndexForBackend = index - 1; 

    try {
      await rewindChat(sessionId, targetIndexForBackend);
      setMessages(prev => prev.slice(0, index));
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-zinc-900 text-zinc-500">
        <Loader2 className="animate-spin mr-2" /> Loading history...
      </div>
    );
  }

  const charName = meta?.character_id || "AI Companion";

  return (
    <div className="flex flex-col h-screen bg-zinc-900 text-zinc-100">
      <header className="flex items-center gap-4 p-4 border-b border-zinc-800 bg-zinc-900/95 backdrop-blur z-10">
        <Link to="/" className="text-zinc-400 hover:text-white transition">
          <ArrowLeft />
        </Link>
        <div>
          <h1 className="font-bold text-lg">{charName}</h1>
          <p className="text-xs text-zinc-500 flex items-center gap-1">
             {meta?.scenario_state ? "Scenario Mode" : "Sandbox Mode"}
             {meta?.scenario_state?.current_step && meta.scenario_state.current_step > 0 && ` • Act ${meta.scenario_state.current_step}`}
          </p>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-4 space-y-6 custom-scrollbar">
        {messages.map((msg, idx) => (
          <MessageItem 
            key={idx} 
            msg={msg} 
            index={idx}
            isLast={idx === messages.length - 1}
            onEdit={toggleEdit}
            onSave={saveEdit}
            onRewind={handleRewind}
            onRegenerate={handleRegenerate}
          />
        ))}
        
        {generating && (
          <div className="flex gap-3 max-w-[85%]">
            <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center shrink-0">
               <Bot size={18} className="text-primary animate-pulse" />
            </div>
            <div className="bg-zinc-800/50 p-4 rounded-2xl rounded-tl-none flex items-center gap-2 text-zinc-400 text-sm">
              <Loader2 className="animate-spin" size={16} /> Writing...
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 bg-zinc-900 border-t border-zinc-800">
        <div className="max-w-4xl mx-auto relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Write your action... (Ctrl+Enter to send)"
            className="w-full bg-zinc-800 border-zinc-700 rounded-xl p-4 pr-14 outline-none focus:border-primary/50 focus:bg-zinc-750 transition resize-none min-h-[60px] max-h-[200px]"
            rows={2}
          />
          <button 
            onClick={handleSend}
            disabled={!input.trim() || generating}
            className="absolute right-3 bottom-3 p-2 bg-primary text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}

interface MessageItemProps {
  msg: Message;
  index: number;
  isLast: boolean;
  onEdit: (index: number) => void;
  onSave: (index: number, text: string) => void;
  onRewind: (index: number) => void;
  onRegenerate: () => void;
}

function MessageItem({ msg, index, isLast, onEdit, onSave, onRewind, onRegenerate }: MessageItemProps) {
  const isUser = msg.role === 'user';
  
  if (msg.isEditing) {
    return (
      <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
         <div className="w-full max-w-2xl">
            <textarea 
               defaultValue={msg.content}
               className="w-full bg-zinc-900 border border-zinc-600 rounded p-3 text-sm focus:border-primary outline-none"
               rows={4}
               id={`edit-${index}`}
            />
            <div className="flex justify-end gap-2 mt-2">
              <button 
                onClick={() => onEdit(index)}
                className="text-xs px-3 py-1 text-zinc-400 hover:text-white"
              >
                Cancel
              </button>
              <button 
                onClick={() => {
                   const el = document.getElementById(`edit-${index}`) as HTMLTextAreaElement;
                   if (el) onSave(index, el.value);
                }}
                className="text-xs px-3 py-1 bg-green-700 text-white rounded hover:bg-green-600"
              >
                Save
              </button>
            </div>
         </div>
      </div>
    )
  }

  return (
    <div className={`group flex gap-4 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
        isUser ? 'bg-zinc-700' : 'bg-indigo-900/50'
      }`}>
        {isUser ? <UserIcon size={20} className="text-zinc-300" /> : <Bot size={20} className="text-indigo-300" />}
      </div>

      <div className={`relative max-w-[85%] md:max-w-[70%] rounded-2xl p-4 text-sm leading-relaxed ${
        isUser 
          ? 'bg-zinc-700/50 text-zinc-100 rounded-tr-none' 
          : 'bg-zinc-800/80 text-zinc-200 rounded-tl-none shadow-sm'
      }`}>
        
        <div className="prose prose-invert prose-sm max-w-none">
          <ReactMarkdown
            components={{
              em: ({node, ...props}) => <span className="text-blue-300/90 not-italic font-normal" {...props} />,
              p: ({node, ...props}) => <p className="mb-2 last:mb-0" {...props} />
            }}
          >
            {msg.content}
          </ReactMarkdown>
        </div>

        <div className={`absolute top-2 ${isUser ? '-left-10' : '-right-10'} opacity-0 group-hover:opacity-100 transition flex flex-col gap-1`}>
          <ActionButton onClick={() => onEdit(index)} icon={Edit2} title="Edit" />
          <ActionButton onClick={() => onRewind(index)} icon={Trash2} title="Delete & Rewind" color="text-red-400 hover:text-red-300" />
          {!isUser && isLast && (
            <ActionButton onClick={onRegenerate} icon={RefreshCw} title="Regenerate" />
          )}
        </div>
      </div>
    </div>
  );
}

interface ActionButtonProps {
  onClick: () => void;
  icon: LucideIcon;
  title: string;
  color?: string;
}

function ActionButton({ onClick, icon: Icon, title, color = "text-zinc-500 hover:text-white" }: ActionButtonProps) {
  return (
    <button 
      onClick={onClick}
      className={`p-1.5 rounded-full hover:bg-zinc-800 transition ${color}`}
      title={title}
    >
      <Icon size={14} />
    </button>
  );
}
