import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { 
  getCharacters, getScenarios, getStyles, createSession 
} from '../api';
import { 
  User, BookOpen, PenTool, Play, AlertCircle, Sparkles, ArrowLeft 
} from 'lucide-react';
import { LucideIcon } from 'lucide-react';

interface Character {
  id: string;
  name: string;
  tagline: string;
}

interface Style {
  profile_id: string;
  name: string;
}

interface Scenario {
  id: string;
  title: string;
  description: string;
  compatible_character_ids: string[];
  user_role_options: Role[];
}

interface Role {
  id: string;
  name: string;
  description: string;
  relationships_options?: { description: string }[];
}

export default function SetupPage() {
  const navigate = useNavigate();

  const [characters, setCharacters] = useState<Character[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [styles, setStyles] = useState<Style[]>([]);
  const [loading, setLoading] = useState(true);

  const [charId, setCharId] = useState('');
  const [profileId, setProfileId] = useState('');
  const [mode, setMode] = useState<'sandbox' | 'scenario'>('sandbox');
  const [scenarioId, setScenarioId] = useState('');
  
  const [userName, setUserName] = useState('');
  const [userDesc, setUserDesc] = useState('');
  const [userRel, setUserRel] = useState('');

  useEffect(() => {
    Promise.all([getCharacters(), getScenarios(), getStyles()])
      .then(([charsData, scnsData, stylesData]) => {
        setCharacters(charsData);
        setScenarios(scnsData);
        setStyles(stylesData);
        
        if (charsData.length > 0) setCharId(charsData[0].id);
        if (stylesData.length > 0) setProfileId(stylesData[0].profile_id);
        
        setLoading(false);
      })
      .catch(err => console.error("Load error:", err));
  }, []);

  const availableScenarios = scenarios.filter(s => 
    s.compatible_character_ids.includes(charId)
  );

  const currentScenario = scenarios.find(s => s.id === scenarioId);

  const handleRoleSelect = (roleId: string) => {
    if (!currentScenario) return;
    const role = currentScenario.user_role_options.find(r => r.id === roleId);
    if (role) {
      const relDesc = role.relationships_options?.[0]?.description || role.description;
      setUserRel(relDesc);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userName || !userDesc || !userRel) {
      alert("Please fill in all persona fields.");
      return;
    }

    const payload = {
      character_id: charId,
      profile_id: profileId,
      scenario_id: mode === 'scenario' ? scenarioId : null,
      user_persona: {
        name: userName,
        description: userDesc,
        relationship: userRel
      }
    };

    try {
      setLoading(true);
      const res = await createSession(payload);
      navigate(`/chat/${res.session_id}`);
    } catch (err) {
      console.error(err);
      alert("Session creation error");
      setLoading(false);
    }
  };

  if (loading) return <div className="p-10 text-center">Loading data...</div>;

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <div className="flex items-center gap-4 mb-8">
        <Link to="/" className="text-zinc-400 hover:text-white transition">
          <ArrowLeft size={24} />
        </Link>
        <h1 className="text-3xl font-bold flex items-center gap-2 text-primary">
          <Sparkles /> New Game
        </h1>
      </div>

      <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-8">
        
        <div className="space-y-6">
          <SectionTitle icon={User} title="1. Choose Partner" />
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">AI Character</label>
              <select 
                className="w-full bg-zinc-800 border border-zinc-700 rounded p-3 focus:border-primary outline-none"
                value={charId}
                onChange={e => setCharId(e.target.value)}
              >
                {characters.map(c => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
              <p className="text-xs text-gray-500 mt-2">
                {characters.find(c => c.id === charId)?.tagline}
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Narrative Style</label>
              <select 
                className="w-full bg-zinc-800 border border-zinc-700 rounded p-3 focus:border-primary outline-none"
                value={profileId}
                onChange={e => setProfileId(e.target.value)}
              >
                {styles.map(s => (
                  <option key={s.profile_id} value={s.profile_id}>{s.name}</option>
                ))}
              </select>
            </div>

            <SectionTitle icon={BookOpen} title="2. Plot" />
            
            <div className="flex gap-4 mb-4">
              <ModeButton active={mode === 'sandbox'} onClick={() => setMode('sandbox')}>
                Sandbox
              </ModeButton>
              <ModeButton active={mode === 'scenario'} onClick={() => setMode('scenario')}>
                Scenario
              </ModeButton>
            </div>

            {mode === 'scenario' ? (
              availableScenarios.length > 0 ? (
                <div className="space-y-4 bg-zinc-800/50 p-4 rounded border border-zinc-700">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Choose Scenario</label>
                    <select 
                      className="w-full bg-zinc-900 border border-zinc-600 rounded p-2"
                      value={scenarioId}
                      onChange={e => setScenarioId(e.target.value)}
                    >
                      <option value="">-- Not selected --</option>
                      {availableScenarios.map(s => (
                        <option key={s.id} value={s.id}>{s.title}</option>
                      ))}
                    </select>
                  </div>
                  
                  {currentScenario && (
                    <div>
                      <p className="text-sm text-gray-300 italic mb-3">{currentScenario.description}</p>
                      
                      <label className="block text-sm text-gray-400 mb-1">Your Role</label>
                      <select 
                        className="w-full bg-zinc-900 border border-zinc-600 rounded p-2"
                        onChange={(e) => handleRoleSelect(e.target.value)}
                        defaultValue=""
                      >
                        <option value="" disabled>-- Choose role --</option>
                        {currentScenario.user_role_options.map(r => (
                          <option key={r.id} value={r.id}>{r.name}</option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-yellow-500 text-sm flex items-center gap-2">
                  <AlertCircle size={16} /> No scenarios available for this character.
                </div>
              )
            ) : (
              <p className="text-sm text-gray-500">Complete freedom of action. No rails, only improvisation.</p>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <SectionTitle icon={PenTool} title="3. Your Character" />
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Name</label>
              <input 
                type="text"
                className="w-full bg-zinc-800 border border-zinc-700 rounded p-3 focus:border-primary outline-none"
                placeholder="What's your name?"
                value={userName}
                onChange={e => setUserName(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Appearance & Personality</label>
              <textarea 
                className="w-full bg-zinc-800 border border-zinc-700 rounded p-3 focus:border-primary outline-none h-32 resize-none"
                placeholder="Tall, with a cyber-eye... Bad temper..."
                value={userDesc}
                onChange={e => setUserDesc(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">
                Relationship with {characters.find(c => c.id === charId)?.name || 'AI'}
              </label>
              <textarea 
                className="w-full bg-zinc-800 border border-zinc-700 rounded p-3 focus:border-primary outline-none h-32 resize-none"
                placeholder="Are we old enemies or best friends? How did we meet?"
                value={userRel}
                onChange={e => setUserRel(e.target.value)}
              />
              {mode === 'scenario' && (
                <p className="text-xs text-blue-400/70 mt-1">
                  *In scenario mode, this field will auto-fill when you select a role, but you can customize it.
                </p>
              )}
            </div>
          </div>
        </div>

        <div className="md:col-span-2 pt-6 border-t border-zinc-800">
          <button 
            type="submit"
            disabled={loading}
            className="w-full bg-primary hover:bg-blue-600 text-white font-bold py-4 rounded-lg flex items-center justify-center gap-2 transition text-lg"
          >
            {loading ? 'Creating world...' : <><Play fill="currentColor" /> Start Game</>}
          </button>
        </div>

      </form>
    </div>
  );
}

interface SectionTitleProps {
  icon: LucideIcon;
  title: string;
}

function SectionTitle({ icon: Icon, title }: SectionTitleProps) {
  return (
    <h2 className="text-xl font-semibold text-gray-200 flex items-center gap-2 border-b border-zinc-700 pb-2">
      <Icon size={20} className="text-primary" /> {title}
    </h2>
  );
}

interface ModeButtonProps {
  active: boolean;
  children: React.ReactNode;
  onClick: () => void;
}

function ModeButton({ active, children, onClick }: ModeButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex-1 py-2 rounded font-medium transition ${
        active 
          ? 'bg-primary text-white shadow-lg shadow-blue-900/50' 
          : 'bg-zinc-800 text-gray-400 hover:bg-zinc-700'
      }`}
    >
      {children}
    </button>
  );
}
