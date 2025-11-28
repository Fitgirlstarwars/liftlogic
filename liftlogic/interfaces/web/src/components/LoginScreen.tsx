import React from 'react';
import { Server, AlertTriangle, ArrowRight, Settings, ShieldCheck, Key, Copy, AlertCircle, RotateCcw, X } from 'lucide-react';

interface LoginScreenProps {
  onLogin: () => void;
  onGuestLogin: () => void;
  authError: string | null;
  showConfig: boolean;
  setShowConfig: (show: boolean) => void;
  clientId: string;
  setClientId: (id: string) => void;
  handleResetClientId: () => void;
  handleSaveClientId: (id: string) => void;
  defaultClientId: string;
}

const LoginScreen: React.FC<LoginScreenProps> = ({
  onLogin,
  onGuestLogin,
  authError,
  showConfig,
  setShowConfig,
  clientId,
  setClientId,
  handleResetClientId,
  handleSaveClientId,
  defaultClientId
}) => {
  return (
    <div className="h-screen w-full flex items-center justify-center bg-industrial-900 text-white relative overflow-hidden">
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden z-0 opacity-20 pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-600/30 rounded-full blur-3xl animate-pulse-slow"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-600/30 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }}></div>
      </div>

      <div className="relative z-10 w-full max-w-sm p-8 bg-industrial-800/80 backdrop-blur-xl border border-industrial-600 rounded-2xl shadow-2xl flex flex-col items-center transition-all">
        <div className="mb-8 p-4 bg-industrial-900 rounded-2xl border border-industrial-700 shadow-inner">
          <Server className="w-12 h-12 text-safety-500" />
        </div>

        <h1 className="text-3xl font-bold text-center mb-2 font-mono tracking-tight">
          <span className="text-safety-500">LIFT</span>
          <span className="text-white">LOGIC</span>
        </h1>
        <p className="text-industrial-400 text-xs mb-8 text-center max-w-[240px]">
          Intelligent Fault Portal
        </p>

        {!showConfig ? (
          <div className="w-full space-y-4 animate-in fade-in zoom-in-95 duration-300">
            {authError && (
              <div className="bg-red-900/50 border border-red-500/50 p-3 rounded-lg text-red-200 text-xs flex items-start gap-2 mb-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold">Connection Failed</div>
                  <div className="opacity-80 mt-1 mb-2">{authError}</div>
                  <button onClick={() => setShowConfig(true)} className="w-full bg-red-800/50 hover:bg-red-800 text-white py-1 rounded border border-red-500/30 font-bold">
                    Troubleshoot
                  </button>
                </div>
              </div>
            )}

            <button
              onClick={onLogin}
              className="w-full py-3.5 px-4 bg-white text-gray-900 font-bold rounded-xl hover:bg-gray-100 transition-all flex items-center justify-center gap-3 shadow-lg shadow-white/5 active:scale-[0.98]"
            >
              <img src="https://www.google.com/favicon.ico" className="w-5 h-5" alt="G" />
              <span>Sign in with Google</span>
            </button>

            <div className="relative flex py-2 items-center">
              <div className="flex-grow border-t border-industrial-700"></div>
              <span className="flex-shrink-0 mx-4 text-industrial-500 text-xs">OR</span>
              <div className="flex-grow border-t border-industrial-700"></div>
            </div>

            <button
              onClick={onGuestLogin}
              className="w-full py-3.5 px-4 bg-industrial-700 text-industrial-300 font-bold rounded-xl hover:bg-industrial-600 hover:text-white transition-all flex items-center justify-center gap-3 shadow-lg active:scale-[0.98]"
            >
              <span>Continue as Guest</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            <p className="text-[10px] text-industrial-500 text-center mt-2">
              Guest mode: Data not synced. Sign in to save your work to Google Drive.
            </p>

            <div className="flex justify-center mt-4">
              <button onClick={() => setShowConfig(true)} className="text-industrial-500 hover:text-white p-2 flex items-center gap-2 text-xs">
                <Settings className="w-3 h-3" /> Connection Settings
              </button>
            </div>
          </div>
        ) : (
          <div className="w-full animate-in fade-in zoom-in-95 duration-300">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Settings className="w-4 h-4" /> Connection Settings
              </h3>
              <button onClick={() => setShowConfig(false)} className="text-industrial-400 hover:text-white"><X className="w-4 h-4" /></button>
            </div>

            <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-1">
              <div className="p-3 bg-yellow-900/20 border border-yellow-700/50 rounded-lg">
                <div className="text-[10px] text-yellow-500 font-bold uppercase mb-1 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" /> Detected Origin
                </div>
                <p className="text-[10px] text-industrial-400 mb-2 leading-relaxed">
                  If you see "Error 400", copy this URL and add it to "Authorized JavaScript origins" in Google Cloud Console.
                </p>
                <div className="bg-black/40 p-2 rounded border border-yellow-900/50 flex items-center justify-between gap-2 mb-1">
                  <code className="text-[10px] text-yellow-100 font-mono break-all leading-tight">{window.location.origin}</code>
                  <button
                    onClick={() => navigator.clipboard.writeText(window.location.origin)}
                    className="text-yellow-500 hover:text-white flex-shrink-0 flex items-center gap-1 bg-yellow-900/30 px-2 py-1 rounded text-[10px]"
                    title="Copy URL"
                  >
                    <Copy className="w-3 h-3" />
                  </button>
                </div>
                <div className="text-[9px] text-red-400 mt-2 flex items-start gap-1">
                  <AlertCircle className="w-3 h-3 flex-shrink-0" />
                  <span><strong>Rule:</strong> No trailing slash (/) at the end.</span>
                </div>
              </div>

              <div className="p-3 bg-industrial-800 border border-industrial-600 rounded-lg">
                <div className="text-[10px] text-blue-400 font-bold uppercase mb-2 flex items-center gap-1">
                  <Key className="w-3 h-3" /> Active Client ID
                </div>
                <div className="relative">
                  <input
                    type="text"
                    value={clientId}
                    onChange={(e) => setClientId(e.target.value)}
                    className="w-full bg-industrial-900 border border-industrial-600 rounded p-2 text-xs text-white font-mono focus:border-blue-500 outline-none pr-8"
                  />
                  {clientId !== defaultClientId && (
                    <button
                      onClick={handleResetClientId}
                      className="absolute right-2 top-2 text-industrial-400 hover:text-white"
                      title="Reset to Default"
                    >
                      <RotateCcw className="w-3 h-3" />
                    </button>
                  )}
                </div>
              </div>

              <button
                onClick={() => handleSaveClientId(clientId)}
                className="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-lg text-xs"
              >
                Save Configuration
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default LoginScreen;
