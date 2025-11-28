
import React, { useEffect, useState } from 'react';
import { AIConfig, AIProvider } from '../types';
import { getAccessToken } from '../services/driveService';
import { Shield, Zap, Database, Save, CheckCircle, PlugZap, Search, Globe, Brain, Key, Lock, ExternalLink, LogIn } from 'lucide-react';

interface AdminDashboardProps {
  currentAiConfig: AIConfig;
  onUpdateAiConfig: (config: AIConfig) => void;
  onSync: () => Promise<void>;
  onConnectGoogle: () => Promise<void>;
}

const AdminDashboard: React.FC<AdminDashboardProps> = ({ currentAiConfig, onUpdateAiConfig, onConnectGoogle }) => {
  const [config, setConfig] = useState<AIConfig>(currentAiConfig);
  const [googleConnected, setGoogleConnected] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    // Check periodically or on mount if we have a token
    const checkToken = () => {
        const token = getAccessToken();
        setGoogleConnected(!!token);
    };
    checkToken();
    // Re-check every second in case auth state changes elsewhere
    const interval = setInterval(checkToken, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleSave = () => {
    onUpdateAiConfig(config);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleGoogleConnect = async () => {
      await onConnectGoogle();
      setGoogleConnected(!!getAccessToken());
  };

  const ProviderCard = ({ 
      id, name, icon: Icon, color, description, isConnected, needsKey 
  }: { 
      id: AIProvider, name: string, icon: any, color: string, description: string, isConnected: boolean, needsKey?: boolean 
  }) => (
    <div className={`relative overflow-hidden rounded-xl border transition-all ${config.provider === id ? `bg-industrial-800 border-${color}-500 shadow-[0_0_20px_rgba(var(--${color}-rgb),0.1)]` : 'bg-industrial-800/50 border-industrial-600 hover:border-industrial-500'}`}>
        {config.provider === id && (
            <div className={`absolute top-0 right-0 p-1 bg-${color}-500 text-industrial-900 text-[10px] font-bold px-2 rounded-bl-lg`}>
                ACTIVE
            </div>
        )}
        
        <div className="p-5">
            <div className="flex items-center gap-3 mb-3">
                <div className={`p-2 rounded-lg bg-${color}-900/30 text-${color}-400`}>
                    <Icon className="w-6 h-6" />
                </div>
                <div>
                    <h4 className="font-bold text-white text-lg">{name}</h4>
                    <p className="text-xs text-industrial-400">{description}</p>
                </div>
            </div>

            <div className="space-y-3">
                {needsKey ? (
                    <div className="relative">
                        <Key className="absolute left-3 top-2.5 w-4 h-4 text-industrial-500" />
                        <input 
                            type="password"
                            value={id === 'OPENAI' ? config.openaiKey : id === 'ANTHROPIC' ? config.anthropicKey : config.xaiKey || ''}
                            onChange={(e) => {
                                const val = e.target.value;
                                if (id === 'OPENAI') setConfig({...config, openaiKey: val});
                                if (id === 'ANTHROPIC') setConfig({...config, anthropicKey: val});
                                if (id === 'XAI') setConfig({...config, xaiKey: val});
                            }}
                            placeholder={`Paste your ${name} API Key`}
                            className="w-full bg-industrial-900 border border-industrial-700 rounded-lg py-2 pl-9 pr-3 text-sm text-white focus:border-blue-500 outline-none"
                        />
                         <div className="text-[10px] text-industrial-500 italic mt-1 ml-1">
                            * Sign to Connect not supported by this provider. Key required.
                        </div>
                    </div>
                ) : (
                    <div className="flex flex-col gap-2">
                        <div className={`flex items-center gap-2 text-sm ${isConnected ? 'text-green-400' : 'text-industrial-500'}`}>
                            {isConnected ? <CheckCircle className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
                            <span>{isConnected ? 'Account Linked via Google OAuth' : 'Not Linked'}</span>
                        </div>
                        {!isConnected && (
                            <button 
                                onClick={handleGoogleConnect}
                                className="flex items-center justify-center gap-2 w-full py-2 bg-blue-600 text-white rounded-lg font-bold text-xs hover:bg-blue-500 transition-colors"
                            >
                                <img src="https://www.google.com/favicon.ico" className="w-3 h-3" alt="G" />
                                Sign to Connect Google AI
                            </button>
                        )}
                    </div>
                )}
            </div>

            <div className="mt-4 pt-4 border-t border-industrial-700/50 flex justify-between items-center">
                <button 
                    onClick={() => setConfig({...config, provider: id})}
                    className={`text-xs font-bold px-3 py-1.5 rounded transition-colors ${config.provider === id ? 'bg-white text-industrial-900' : 'bg-industrial-700 text-industrial-300 hover:text-white'}`}
                >
                    {config.provider === id ? 'Selected' : 'Use this Provider'}
                </button>
                {needsKey && (
                    <a href="#" className="text-[10px] text-industrial-500 hover:text-white flex items-center gap-1">
                        Get Key <ExternalLink className="w-3 h-3" />
                    </a>
                )}
            </div>
        </div>
    </div>
  );

  return (
    <div className="flex-1 p-4 lg:p-8 overflow-y-auto space-y-8">
      
      <div className="flex items-center justify-between">
         <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <PlugZap className="w-6 h-6 text-yellow-400" /> Link AI Accounts
         </h2>
         <button 
            onClick={handleSave}
            className="flex items-center gap-2 bg-green-600 hover:bg-green-500 text-white px-6 py-2 rounded-lg font-bold transition-all shadow-lg shadow-green-900/20"
         >
            {saved ? <CheckCircle className="w-5 h-5" /> : <Save className="w-5 h-5" />}
            {saved ? 'Saved' : 'Save Connections'}
         </button>
      </div>

      <div className="bg-blue-900/10 border border-blue-500/30 p-4 rounded-xl flex items-start gap-3">
          <Globe className="w-6 h-6 text-blue-400 flex-shrink-0 mt-1" />
          <div>
              <h3 className="text-sm font-bold text-white mb-1">Client-Side Deep Research Agent</h3>
              <p className="text-xs text-blue-200/70 leading-relaxed">
                  To perform "30+ site" research without a backend server, we use a recursive agent running in your browser.
                  It uses your connected AI account to perform multiple parallel Google Grounding searches and synthesizes the results.
                  This incurs zero server cost for us and uses your personal quota.
              </p>
          </div>
          <div className="ml-auto flex items-center gap-2">
              <span className="text-xs font-bold text-blue-400 uppercase">Deep Mode</span>
              <button 
                 onClick={() => setConfig({...config, searchDepth: config.searchDepth === 'DEEP' ? 'STANDARD' : 'DEEP'})}
                 className={`w-12 h-6 rounded-full relative transition-colors ${config.searchDepth === 'DEEP' ? 'bg-blue-500' : 'bg-industrial-700'}`}
              >
                 <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-all ${config.searchDepth === 'DEEP' ? 'left-7' : 'left-1'}`} />
              </button>
          </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <ProviderCard 
             id="GOOGLE"
             name="Google Gemini"
             icon={Brain}
             color="blue"
             description="Recommended. Uses your Google Account directly (OAuth). No Key required."
             isConnected={googleConnected}
             needsKey={false}
          />

          <ProviderCard 
             id="OPENAI"
             name="OpenAI (ChatGPT)"
             icon={Zap}
             color="green"
             description="Connect your Plus/Enterprise account via API Key."
             isConnected={!!config.openaiKey}
             needsKey={true}
          />

          <ProviderCard 
             id="ANTHROPIC"
             name="Anthropic (Claude)"
             icon={Shield}
             color="purple"
             description="Excellent for technical manual analysis."
             isConnected={!!config.anthropicKey}
             needsKey={true}
          />

          <ProviderCard 
             id="XAI"
             name="xAI (Grok)"
             icon={Globe}
             color="gray"
             description="Real-time access to X data."
             isConnected={!!config.xaiKey}
             needsKey={true}
          />
      </div>

      <div className="bg-industrial-800 border border-industrial-600 rounded-xl p-6">
          <h3 className="font-bold text-white mb-4">Privacy & Security</h3>
          <ul className="space-y-2 text-sm text-industrial-400">
              <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-green-500" /> API Keys are stored in your browser's Local Storage (AES-256 equivalent).</li>
              <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-green-500" /> Keys are never sent to our servers.</li>
              <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-green-500" /> All AI requests originate from your IP address.</li>
              <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-green-500" /> Google OAuth uses the official 'generative-language' scope.</li>
          </ul>
      </div>

    </div>
  );
};

export default AdminDashboard;
