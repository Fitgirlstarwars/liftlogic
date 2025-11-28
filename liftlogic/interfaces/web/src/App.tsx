import React, { useState, useEffect, useRef } from "react";
import {
  Search,
  Activity,
  Cloud,
  Check,
  AlertCircle,
  Loader2,
  Server,
  LogOut,
  Database,
  Settings,
  User as UserIcon,
  UserCheck,
  RefreshCcw,
  Mic,
  MicOff,
  ImageIcon,
  XCircle,
  Zap,
  ChevronRight,
  Link2,
  ShieldCheck,
  Key,
  X,
  ArrowRight,
  ExternalLink,
  Info,
  AlertTriangle,
  Copy,
  Clock,
  RotateCcw,
  Brain,
  Layers,
} from "lucide-react";
import { FaultRecord, ViewMode, AIConfig, DriveUser } from "./types/index";
import {
  identifyFaultFromQuery,
  validateContribution,
} from "./services/geminiService";
import {
  searchLocalKnowledgeBase,
  saveToKnowledgeBase,
  getKnowledgeBase,
  initKnowledgeBase,
  setDatabaseChangeCallback,
} from "./services/knowledgeBase";
import {
  initTokenClient,
  signInWithGoogle,
  getCurrentUserInfo,
  initGapiClient,
  saveUserSession,
  loadUserSession,
  clearUserSession,
  findDatabaseFile,
  readDriveFile,
  updateDriveFile,
  createDriveFile,
} from "./services/driveService";
import {
  initSessionKey,
  encryptData,
  decryptData,
} from "./services/cryptoUtils";
import FaultCard from "./components/FaultCard";
import TroubleshootChat from "./components/TroubleshootChat";
import AdminDashboard from "./components/AdminDashboard";
import LoginScreen from "./components/LoginScreen";

// Default Client ID provided by user
const DEFAULT_CLIENT_ID =
  "266461781785-609pkpmvprdq6c3t6egrn2cis39jamos.apps.googleusercontent.com";
const CLIENT_ID_STORAGE_KEY = "LIFT_LOGIC_CLIENT_ID_OVERRIDE";

function App() {
  const [user, setUser] = useState<DriveUser | null>(null);
  const [isLoading, setLoading] = useState(true);
  const [statusMessage, setStatusMessage] = useState("System Start...");

  // Auth & Config State
  const [authError, setAuthError] = useState<string | null>(null);
  const [showAuthConfig, setShowAuthConfig] = useState(false);
  const [clientId, setClientId] = useState(DEFAULT_CLIENT_ID);

  // Model Selection State for Main UI
  const [quickMode, setQuickMode] = useState<
    "SPEED" | "REASONING" | "CONSENSUS"
  >("SPEED");

  const [view, setView] = useState<ViewMode>("SEARCH");
  const [searchQuery, setSearchQuery] = useState("");
  const [faults, setFaults] = useState<FaultRecord[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const [isListening, setIsListening] = useState(false);

  const [activeFaultForChat, setActiveFaultForChat] = useState<
    FaultRecord | undefined
  >(undefined);
  const [showChat, setShowChat] = useState(false);

  // Default to GOOGLE provider.
  const [aiConfig, setAiConfig] = useState<AIConfig>({
    provider: "GOOGLE",
    model: "gemini-3-pro-preview",
    searchDepth: "STANDARD",
    minSources: 1,
  });

  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState<Date | null>(null);

  // Auto-clean legacy overrides to ensure we use the correct hardcoded ID
  useEffect(() => {
    const stored = localStorage.getItem(CLIENT_ID_STORAGE_KEY);
    if (stored && stored !== DEFAULT_CLIENT_ID) {
      console.log("Clearing legacy Client ID override to enforce new default.");
      localStorage.removeItem(CLIENT_ID_STORAGE_KEY);
      setClientId(DEFAULT_CLIENT_ID);
    }
  }, []);

  const initAuth = async () => {
    setLoading(true);
    setAuthError(null);

    // Safety timeout to prevent infinite loading
    const loadingTimeout = setTimeout(() => {
      console.warn("Auth init timeout - showing login screen");
      setLoading(false);
    }, 10000);

    try {
      // Initialize GAPI and Token Client
      await initGapiClient();
      await initTokenClient(clientId);

      const saved = loadUserSession();
      if (saved) {
        setStatusMessage("Restoring Session...");
        setUser(saved);
        await handlePostLoginInit(saved.id);
        clearTimeout(loadingTimeout);
        return;
      }
    } catch (e) {
      console.error("Auth Init Failed", e);
      // Don't show error immediately on load, wait for user interaction
    }
    clearTimeout(loadingTimeout);
    setLoading(false);
  };

  useEffect(() => {
    initAuth();
  }, [clientId]);

  const handleSaveClientId = (newId: string) => {
    const cleaned = newId.trim();
    if (cleaned === DEFAULT_CLIENT_ID || cleaned === "") {
      localStorage.removeItem(CLIENT_ID_STORAGE_KEY);
      setClientId(DEFAULT_CLIENT_ID);
    } else {
      localStorage.setItem(CLIENT_ID_STORAGE_KEY, cleaned);
      setClientId(cleaned);
    }
    window.location.reload();
  };

  const handleResetClientId = () => {
    localStorage.removeItem(CLIENT_ID_STORAGE_KEY);
    setClientId(DEFAULT_CLIENT_ID);
    window.location.reload();
  };

  const handlePostLoginInit = async (userId: string) => {
    try {
      // Initialize session key based on user ID for encryption
      await initSessionKey(userId);

      // Try to find database only if not guest
      if (userId !== "guest") {
        const fileId = await findDatabaseFile();
        if (fileId) {
          setStatusMessage("Decrypting...");
          const content = await readDriveFile(fileId);
          if (content) {
            const decrypted = await decryptData(content);
            initKnowledgeBase(decrypted);
            setLastSyncTime(new Date());
          }
        } else {
          initKnowledgeBase([]);
        }
      } else {
        // Guest mode init
        initKnowledgeBase([]);
      }

      setLoading(false);
      setDatabaseChangeCallback(performCloudSync);
    } catch (e) {
      console.error("Post Login Init Failed", e);
      // If decryption fails or something major breaks, fallback to empty KB but keep logged in
      initKnowledgeBase([]);
      setLoading(false);
    }
  };

  const handleLogin = async () => {
    try {
      setLoading(true);
      setAuthError(null);
      setStatusMessage("Connecting to Google...");

      if (!clientId) {
        setAuthError("Configuration Error: Client ID missing.");
        setShowAuthConfig(true);
        setLoading(false);
        return;
      }

      const token = await signInWithGoogle();

      const userInfo = await getCurrentUserInfo(token);
      if (!userInfo.emailAddress)
        throw new Error("Could not retrieve user info");

      const driveUser: DriveUser = {
        id: userInfo.emailAddress,
        displayName: userInfo.displayName,
        emailAddress: userInfo.emailAddress,
        photoLink: userInfo.photoLink,
        role: "technician",
        isGuest: false,
      };

      setUser(driveUser);
      saveUserSession(driveUser);
      await handlePostLoginInit(driveUser.id);
    } catch (e: any) {
      console.error("Login failed", e);
      setLoading(false);
      // Show the config modal because usually login fails due to origin mismatch
      setAuthError("Authorization Failed. Please check Connection Settings.");
      setShowAuthConfig(true);
    }
  };

  const handleGuestLogin = () => {
    const guestUser: DriveUser = {
      id: "guest",
      displayName: "Guest Technician",
      emailAddress: "",
      role: "guest",
      isGuest: true,
    };
    setUser(guestUser);
    // No session saving for guest to force explicit choice next time
    handlePostLoginInit("guest");
  };

  const handleLogout = () => {
    setUser(null);
    clearUserSession();
    initKnowledgeBase([]);
    setView("SEARCH");
    setFaults([]);
    window.location.reload();
  };

  const handleLinkGoogle = async () => {
    try {
      await signInWithGoogle();
    } catch (e) {
      console.error("Failed to link Google", e);
    }
  };

  const performCloudSync = async (records: FaultRecord[]) => {
    if (!user || user.isGuest) return;
    try {
      setIsSyncing(true);
      const encrypted = await encryptData(records);
      const fileId = await findDatabaseFile();
      if (fileId) {
        await updateDriveFile(fileId, encrypted);
      } else {
        await createDriveFile(encrypted);
      }
      setLastSyncTime(new Date());
    } catch (e) {
      console.error("Sync Failed", e);
    } finally {
      setIsSyncing(false);
    }
  };

  const switchMode = (mode: "SPEED" | "REASONING" | "CONSENSUS") => {
    setQuickMode(mode);
    if (mode === "SPEED") {
      setAiConfig({
        ...aiConfig,
        model: "gemini-3-pro-preview",
        searchDepth: "STANDARD",
        activeModels: undefined,
      } as any);
    } else if (mode === "REASONING") {
      setAiConfig({
        ...aiConfig,
        model: "gemini-3-pro-preview",
        searchDepth: "DEEP",
        activeModels: undefined,
      } as any);
    } else if (mode === "CONSENSUS") {
      setAiConfig({
        ...aiConfig,
        model: "gemini-3-pro-preview",
        searchDepth: "DEEP",
        activeModels: ["GOOGLE", "OPENAI", "ANTHROPIC"],
      } as any);
    }
  };

  const handleSearch = async (overrideQuery?: string) => {
    const q = overrideQuery || searchQuery;
    if (!q.trim() && !selectedImage) return;

    setIsSearching(true);
    setFaults([]);

    try {
      const localResults = searchLocalKnowledgeBase(q);
      setFaults(localResults);

      if (
        user &&
        (selectedImage || (localResults.length === 0 && navigator.onLine))
      ) {
        const aiResults = await identifyFaultFromQuery(
          q,
          selectedImage,
          aiConfig
        );
        const existingIds = new Set(
          localResults.map((r) => r.code + r.manufacturer)
        );
        const newOnes = aiResults.filter(
          (r) => !existingIds.has(r.code + r.manufacturer)
        );
        setFaults([...localResults, ...newOnes]);
      }
    } catch (e) {
      console.error("Search failed", e);
    } finally {
      setIsSearching(false);
    }
  };

  const toggleVoiceSearch = () => {
    if (isListening) {
      setIsListening(false);
      return;
    }
    if (
      !("webkitSpeechRecognition" in window) &&
      !("SpeechRecognition" in window)
    ) {
      alert("Voice search is not supported in this browser.");
      return;
    }
    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";
    recognition.onstart = () => setIsListening(true);
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setSearchQuery(transcript);
      handleSearch(transcript);
    };
    recognition.onerror = () => setIsListening(false);
    recognition.onend = () => setIsListening(false);
    recognition.start();
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64String = reader.result as string;
        const base64Content = base64String.split(",")[1];
        setSelectedImage(base64Content);
      };
      reader.readAsDataURL(file);
    }
  };

  // --- RENDERING ---

  if (isLoading) {
    return (
      <div className="h-screen w-full flex flex-col items-center justify-center bg-industrial-900 text-white gap-6">
        <div className="relative">
          <div className="w-16 h-16 border-4 border-industrial-700 border-t-safety-500 rounded-full animate-spin"></div>
          <div className="absolute inset-0 flex items-center justify-center">
            <Activity className="w-6 h-6 text-safety-500" />
          </div>
        </div>
        <div className="text-sm font-mono text-industrial-400 animate-pulse">
          {statusMessage}
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <LoginScreen
        onLogin={handleLogin}
        onGuestLogin={handleGuestLogin}
        authError={authError}
        showConfig={showAuthConfig}
        setShowConfig={setShowAuthConfig}
        clientId={clientId}
        setClientId={setClientId}
        handleResetClientId={handleResetClientId}
        handleSaveClientId={handleSaveClientId}
        defaultClientId={DEFAULT_CLIENT_ID}
      />
    );
  }

  return (
    <div className="flex flex-col lg:flex-row h-screen bg-industrial-900 text-white overflow-hidden font-sans selection:bg-blue-500/30">
      {/* Top Header - Fixed full width */}
      <header className="fixed top-0 left-0 right-0 w-full h-14 bg-industrial-900 border-b border-industrial-800 flex items-center px-4 z-50">
        <div className="flex items-center gap-3">
          <Server className="w-6 h-6 text-safety-500" />
          <span className="font-bold font-mono text-xl tracking-tighter">
            <span className="text-safety-500">LIFT</span>
            <span className="text-white">LOGIC</span>
          </span>
        </div>
        <button
          onClick={handleLogout}
          className="absolute right-4 top-1/2 -translate-y-1/2 text-industrial-400 hover:text-white p-2"
        >
          <LogOut className="w-5 h-5" />
        </button>
      </header>
      {/* Spacer for fixed header */}
      <div className="h-14 flex-shrink-0" />

      {/* Mobile Bottom Navigation - Forced Visible */}
      <nav className="fixed bottom-0 left-0 right-0 bg-industrial-900 border-t border-industrial-800 z-40 flex justify-around p-2 pb-safe shadow-xl">
        <button
          onClick={() => setView("SEARCH")}
          className={`flex flex-col items-center p-2 rounded-lg w-20 transition-all ${
            view === "SEARCH"
              ? "text-blue-400 bg-industrial-800"
              : "text-industrial-400"
          }`}
        >
          <Search className="w-6 h-6" />
          <span className="text-[10px] font-bold mt-1">Diagnose</span>
        </button>
        <button
          onClick={() => setView("DATABASE")}
          className={`flex flex-col items-center p-2 rounded-lg w-20 transition-all ${
            view === "DATABASE"
              ? "text-blue-400 bg-industrial-800"
              : "text-industrial-400"
          }`}
        >
          <Database className="w-6 h-6" />
          <span className="text-[10px] font-bold mt-1">Library</span>
        </button>
        <button
          onClick={() => setView("ADMIN")}
          className={`flex flex-col items-center p-2 rounded-lg w-20 transition-all ${
            view === "ADMIN"
              ? "text-purple-400 bg-industrial-800"
              : "text-industrial-400"
          }`}
        >
          <Link2 className="w-6 h-6" />
          <span className="text-[10px] font-bold mt-1">Connect</span>
        </button>
      </nav>

      <main className="flex-1 flex flex-col relative overflow-y-auto pb-20">
        {view === "ADMIN" && (
          <AdminDashboard
            currentAiConfig={aiConfig}
            onUpdateAiConfig={setAiConfig}
            onSync={async () => {
              if (user) await performCloudSync(getKnowledgeBase());
            }}
            onConnectGoogle={handleLinkGoogle}
          />
        )}

        {view === "DATABASE" && (
          <div className="flex-1 p-4 lg:p-8 overflow-y-auto">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
              <Database className="w-6 h-6 text-blue-500" /> Knowledge Base
            </h2>
            <div className="grid gap-4">
              {getKnowledgeBase().map((f) => (
                <FaultCard
                  key={f.id}
                  record={f}
                  onChatRequest={(record) => {
                    setActiveFaultForChat(record);
                    setShowChat(true);
                  }}
                  onAddContribution={async (id, text) => {
                    const record = getKnowledgeBase().find((r) => r.id === id);
                    if (record) {
                      const validation = await validateContribution(
                        record,
                        text,
                        aiConfig
                      );
                      if (!record.communityContributions)
                        record.communityContributions = [];
                      record.communityContributions.push({
                        id: Date.now().toString(),
                        text,
                        author: user?.displayName || "Technician",
                        timestamp: Date.now(),
                        votes: 0,
                        aiAnalysis: validation.analysis,
                        refinedContent: validation.refinedContent,
                        aiStatus: validation.status as any,
                      });
                      await saveToKnowledgeBase(record);
                      setFaults([...faults]);
                    }
                  }}
                  onVoteContribution={async (recId, contribId) => {
                    /* Vote logic same as Search view */
                  }}
                />
              ))}
            </div>
          </div>
        )}

        {view === "SEARCH" && (
          <div className="flex-1 flex flex-col max-w-5xl mx-auto w-full p-4 md:p-8">
            {/* Mode Selector */}
            <div className="flex justify-center gap-2 mb-6">
              <div className="flex bg-industrial-900 border border-industrial-700 p-1.5 rounded-lg gap-1">
                <button
                  onClick={() => switchMode("SPEED")}
                  className={`flex items-center gap-2 px-6 py-2 rounded-md transition-all text-xs font-bold uppercase tracking-wider ${
                    quickMode === "SPEED"
                      ? "bg-industrial-800 border border-safety-500 text-safety-500 shadow-[0_0_15px_rgba(245,158,11,0.15)]"
                      : "text-industrial-500 hover:text-industrial-300 hover:bg-industrial-800/50"
                  }`}
                >
                  <Zap className="w-3.5 h-3.5" /> Speed
                </button>
                <button
                  onClick={() => switchMode("REASONING")}
                  className={`flex items-center gap-2 px-6 py-2 rounded-md transition-all text-xs font-bold uppercase tracking-wider ${
                    quickMode === "REASONING"
                      ? "bg-industrial-800 border border-blue-500 text-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.15)]"
                      : "text-industrial-500 hover:text-industrial-300 hover:bg-industrial-800/50"
                  }`}
                >
                  <Brain className="w-3.5 h-3.5" /> Reasoning
                </button>
                <button
                  onClick={() => switchMode("CONSENSUS")}
                  className={`flex items-center gap-2 px-6 py-2 rounded-md transition-all text-xs font-bold uppercase tracking-wider ${
                    quickMode === "CONSENSUS"
                      ? "bg-industrial-800 border border-purple-500 text-purple-400 shadow-[0_0_15px_rgba(168,85,247,0.15)]"
                      : "text-industrial-500 hover:text-industrial-300 hover:bg-industrial-800/50"
                  }`}
                >
                  <Layers className="w-3.5 h-3.5" /> Consensus
                </button>
              </div>
            </div>

            <div className="flex flex-col gap-4 mb-8">
              <div className="relative group max-w-4xl mx-auto w-full">
                <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none">
                  <Search
                    className={`w-6 h-6 ${
                      isSearching
                        ? "text-safety-500 animate-pulse"
                        : "text-industrial-500"
                    }`}
                  />
                </div>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  placeholder="Enter fault code (e.g. Kone 169)"
                  className="w-full bg-industrial-800/50 border border-industrial-600/50 text-white text-lg rounded-2xl pl-14 pr-40 py-5 focus:outline-none focus:border-industrial-500 focus:ring-1 focus:ring-industrial-500/50 transition-all shadow-2xl placeholder-industrial-600 font-medium"
                />

                <div className="absolute right-2.5 top-2.5 bottom-2.5 flex items-center gap-2">
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className={`p-2.5 rounded-xl transition-colors ${
                      selectedImage
                        ? "bg-purple-600 text-white"
                        : "bg-industrial-800/80 text-industrial-400 hover:text-white hover:bg-industrial-700"
                    }`}
                  >
                    <ImageIcon className="w-5 h-5" />
                  </button>
                  <input
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    accept="image/*"
                    onChange={handleImageUpload}
                  />

                  <button
                    onClick={toggleVoiceSearch}
                    className={`p-2.5 rounded-xl transition-all ${
                      isListening
                        ? "bg-red-500 text-white animate-pulse"
                        : "bg-industrial-800/80 text-industrial-400 hover:text-white hover:bg-industrial-700"
                    }`}
                  >
                    {isListening ? (
                      <Mic className="w-5 h-5" />
                    ) : (
                      <MicOff className="w-5 h-5" />
                    )}
                  </button>

                  <button
                    onClick={() => handleSearch()}
                    disabled={isSearching}
                    className="bg-blue-600 hover:bg-blue-500 text-white py-2.5 px-6 rounded-xl font-bold transition-all disabled:opacity-50 shadow-lg shadow-blue-600/20 hover:shadow-blue-600/40 active:scale-95"
                  >
                    {isSearching ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      "Analyze"
                    )}
                  </button>
                </div>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto">
              {faults.length > 0 ? (
                <div className="space-y-6">
                  {faults.map((f) => (
                    <FaultCard
                      key={f.id}
                      record={f}
                      onChatRequest={(record) => {
                        setActiveFaultForChat(record);
                        setShowChat(true);
                      }}
                      onAddContribution={async (id, text) => {
                        const record = faults.find((r) => r.id === id);
                        if (record) {
                          const validation = await validateContribution(
                            record,
                            text,
                            aiConfig
                          );
                          if (!record.communityContributions)
                            record.communityContributions = [];
                          record.communityContributions.push({
                            id: Date.now().toString(),
                            text,
                            author: user?.displayName || "Technician",
                            timestamp: Date.now(),
                            votes: 0,
                            aiAnalysis: validation.analysis,
                            refinedContent: validation.refinedContent,
                            aiStatus: validation.status as any,
                          });
                          setFaults([...faults]);
                          await saveToKnowledgeBase(record);
                        }
                      }}
                      onVoteContribution={async (recId, contribId) => {
                        const record = faults.find((r) => r.id === recId);
                        if (record && record.communityContributions) {
                          const c = record.communityContributions.find(
                            (c) => c.id === contribId
                          );
                          if (c) {
                            c.votes = (c.votes || 0) + 1;
                            setFaults([...faults]);
                            await saveToKnowledgeBase(record);
                          }
                        }
                      }}
                    />
                  ))}
                </div>
              ) : (
                !isSearching && (
                  <div className="h-full flex flex-col items-center justify-center text-industrial-500 opacity-50">
                    <div className="w-20 h-20 rounded-full bg-industrial-800 border-2 border-industrial-700 flex items-center justify-center mb-4">
                      <Zap className="w-8 h-8 text-industrial-600" />
                    </div>
                    <p>No Exact Matches Found</p>
                    <p className="text-xs max-w-xs text-center mt-2">
                      Try a broader search or ensure the code is correct. You
                      can also create a new record manually.
                    </p>
                  </div>
                )
              )}
              {isSearching && faults.length === 0 && (
                <div className="flex flex-col items-center justify-center py-20">
                  <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4"></div>
                  <div className="text-blue-400 font-bold animate-pulse">
                    Running Deep Research Agent...
                  </div>
                  <div className="text-xs text-industrial-400 mt-2">
                    Connecting via {aiConfig.provider}...
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {showChat && (
          <div className="absolute inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200">
            <div className="w-full max-w-2xl h-[80vh] animate-in zoom-in-95 duration-200">
              <TroubleshootChat
                contextRecord={activeFaultForChat}
                onClose={() => setShowChat(false)}
              />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
