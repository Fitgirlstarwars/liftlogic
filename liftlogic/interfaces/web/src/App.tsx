import React, { useState, useEffect, useRef, useCallback } from "react";
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
  CheckCircle,
  Lock,
  Unlock,
} from "lucide-react";

// ============ RECOGNIZED TERMS FOR SMART FILTERS ============
const RECOGNIZED_MANUFACTURERS = [
  { id: "kone", name: "KONE", aliases: ["kone", "Kone", "KONE"] },
  { id: "otis", name: "OTIS", aliases: ["otis", "Otis", "OTIS"] },
  { id: "schindler", name: "Schindler", aliases: ["schindler", "Schindler", "SCHINDLER"] },
  { id: "thyssenkrupp", name: "ThyssenKrupp", aliases: ["thyssenkrupp", "ThyssenKrupp", "thyssen", "TK", "tk"] },
  { id: "mitsubishi", name: "Mitsubishi", aliases: ["mitsubishi", "Mitsubishi", "MITSUBISHI", "MELCO", "melco"] },
  { id: "fujitec", name: "Fujitec", aliases: ["fujitec", "Fujitec", "FUJITEC"] },
  { id: "hyundai", name: "Hyundai", aliases: ["hyundai", "Hyundai", "HYUNDAI"] },
  { id: "hitachi", name: "Hitachi", aliases: ["hitachi", "Hitachi", "HITACHI"] },
  { id: "toshiba", name: "Toshiba", aliases: ["toshiba", "Toshiba", "TOSHIBA"] },
];

const RECOGNIZED_EQUIPMENT = [
  { id: "elevator", name: "Elevator", aliases: ["elevator", "Elevator", "ELEVATOR", "lift", "Lift", "LIFT", "L", "l"] },
  { id: "escalator", name: "Escalator", aliases: ["escalator", "Escalator", "ESCALATOR", "E", "e"] },
];

interface SearchFilter {
  type: "manufacturer" | "equipment";
  id: string;
  name: string;
  locked: boolean;
}

const FILTER_STORAGE_KEY = "LIFT_LOGIC_LOCKED_FILTERS";
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

  // Progressive Research Depth State
  const [researchDepth, setResearchDepth] = useState<"quick" | "deep" | "verified">("quick");
  const [isDeepening, setIsDeepening] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [lastSearchQuery, setLastSearchQuery] = useState("");

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

  // Smart Filter State
  const [activeFilters, setActiveFilters] = useState<SearchFilter[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestionMatches, setSuggestionMatches] = useState<
    Array<{ type: "manufacturer" | "equipment"; id: string; name: string }>
  >([]);
  const suggestionsRef = useRef<HTMLDivElement>(null);

  // Load locked filters from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(FILTER_STORAGE_KEY);
      if (stored) {
        const lockedFilters: SearchFilter[] = JSON.parse(stored);
        setActiveFilters(lockedFilters.filter((f) => f.locked));
      }
    } catch (e) {
      console.error("Failed to load locked filters:", e);
    }
  }, []);

  // Save locked filters to localStorage when they change
  useEffect(() => {
    const lockedFilters = activeFilters.filter((f) => f.locked);
    if (lockedFilters.length > 0) {
      localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(lockedFilters));
    } else {
      localStorage.removeItem(FILTER_STORAGE_KEY);
    }
  }, [activeFilters]);

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target as Node)
      ) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Detect recognized terms as user types
  const detectRecognizedTerms = useCallback((input: string) => {
    const words = input.split(/\s+/);
    const lastWord = words[words.length - 1]?.toLowerCase();

    if (!lastWord || lastWord.length < 1) {
      setSuggestionMatches([]);
      setShowSuggestions(false);
      return;
    }

    const matches: Array<{ type: "manufacturer" | "equipment"; id: string; name: string }> = [];

    // Check manufacturers
    for (const mfr of RECOGNIZED_MANUFACTURERS) {
      if (mfr.aliases.some((alias) => alias.toLowerCase().startsWith(lastWord))) {
        matches.push({ type: "manufacturer", id: mfr.id, name: mfr.name });
      }
    }

    // Check equipment
    for (const eq of RECOGNIZED_EQUIPMENT) {
      if (eq.aliases.some((alias) => alias.toLowerCase().startsWith(lastWord))) {
        matches.push({ type: "equipment", id: eq.id, name: eq.name });
      }
    }

    // Filter out already active filters
    const filtered = matches.filter(
      (m) => !activeFilters.some((f) => f.id === m.id && f.type === m.type)
    );

    setSuggestionMatches(filtered);
    setShowSuggestions(filtered.length > 0);
  }, [activeFilters]);

  // Handle selecting a suggestion
  const handleSelectSuggestion = (match: { type: "manufacturer" | "equipment"; id: string; name: string }) => {
    // Add as unlocked filter
    setActiveFilters((prev) => [
      ...prev,
      { type: match.type, id: match.id, name: match.name, locked: false },
    ]);

    // Remove the matched word from search query
    const words = searchQuery.split(/\s+/);
    words.pop(); // Remove the partial match
    setSearchQuery(words.join(" ") + (words.length > 0 ? " " : ""));

    setShowSuggestions(false);
    setSuggestionMatches([]);
  };

  // Toggle filter lock
  const toggleFilterLock = (filterId: string, filterType: string) => {
    setActiveFilters((prev) =>
      prev.map((f) =>
        f.id === filterId && f.type === filterType ? { ...f, locked: !f.locked } : f
      )
    );
  };

  // Remove a filter
  const removeFilter = (filterId: string, filterType: string) => {
    setActiveFilters((prev) =>
      prev.filter((f) => !(f.id === filterId && f.type === filterType))
    );
  };

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

  // Go Deeper: Run deep multi-angle research on current results
  const handleGoDeeper = async () => {
    if (!lastSearchQuery.trim() || !user) return;

    setIsDeepening(true);
    try {
      const deepConfig = {
        ...aiConfig,
        searchDepth: "DEEP" as const,
      };
      const deepResults = await identifyFaultFromQuery(
        lastSearchQuery,
        selectedImage,
        deepConfig
      );

      // Merge with existing, prioritizing deep results
      const existingIds = new Set(faults.map((r) => r.code + r.manufacturer));
      const newOnes = deepResults.filter(
        (r) => !existingIds.has(r.code + r.manufacturer)
      );

      // Update existing results with deeper info, add new ones
      const enhanced = faults.map(f => {
        const deepMatch = deepResults.find(d => d.code === f.code && d.manufacturer === f.manufacturer);
        if (deepMatch) {
          return {
            ...f,
            ...deepMatch,
            source: "Deep Research",
          };
        }
        return f;
      });

      setFaults([...enhanced, ...newOnes]);
      setResearchDepth("deep");
    } catch (e) {
      console.error("Deep research failed", e);
    } finally {
      setIsDeepening(false);
    }
  };

  // Verify: Run adversarial verification pass
  const handleVerify = async () => {
    if (faults.length === 0 || !user) return;

    setIsVerifying(true);
    try {
      const { generateViaGateway } = await import("./services/llmGateway");

      // Verify each fault
      const verifiedFaults = await Promise.all(
        faults.map(async (fault) => {
          const verifyPrompt = `
You are a senior elevator engineer reviewing this diagnosis. Be critical and thorough.

Fault: ${fault.code} - ${fault.title}
Manufacturer: ${fault.manufacturer}
Description: ${fault.description}
Causes: ${fault.possibleCauses?.join(", ")}
Solutions: ${fault.solutions?.join(", ")}

Review for:
1. Technical accuracy
2. Missing safety warnings
3. Common misdiagnoses for this code
4. Additional steps that might be needed

Return JSON: { "confidence": 0-100, "warnings": ["string"], "additionalSteps": ["string"], "verified": true }`;

          try {
            const response = await generateViaGateway(
              verifyPrompt,
              "You are a QA engineer for elevator diagnostics.",
              aiConfig,
              true
            );
            const cleanJson = response.text.replace(/\`\`\`json/g, '').replace(/\`\`\`/g, '').trim();
            const verification = JSON.parse(cleanJson);

            return {
              ...fault,
              source: `Verified (${verification.confidence}% confidence)`,
              solutions: [
                ...fault.solutions,
                ...(verification.additionalSteps || []),
              ],
              communityContributions: [
                ...(fault.communityContributions || []),
                ...(verification.warnings || []).map((w: string, i: number) => ({
                  id: `verify-${Date.now()}-${i}`,
                  text: `⚠️ ${w}`,
                  author: "AI Verification",
                  timestamp: Date.now(),
                  votes: 0,
                  aiStatus: "CAUTION" as const,
                })),
              ],
            };
          } catch {
            return fault;
          }
        })
      );

      setFaults(verifiedFaults);
      setResearchDepth("verified");
    } catch (e) {
      console.error("Verification failed", e);
    } finally {
      setIsVerifying(false);
    }
  };

  const handleSearch = async (overrideQuery?: string) => {
    const rawQuery = overrideQuery || searchQuery;
    if (!rawQuery.trim() && !selectedImage && activeFilters.length === 0) return;

    // Build full query with active filters prepended
    const filterParts: string[] = [];
    const manufacturerFilter = activeFilters.find((f) => f.type === "manufacturer");
    const equipmentFilter = activeFilters.find((f) => f.type === "equipment");

    if (manufacturerFilter) filterParts.push(manufacturerFilter.name);
    if (equipmentFilter) filterParts.push(equipmentFilter.name);

    const q = [...filterParts, rawQuery.trim()].filter(Boolean).join(" ");
    if (!q && !selectedImage) return;

    setIsSearching(true);
    setFaults([]);
    setResearchDepth("quick");
    setLastSearchQuery(q);

    // Clear unlocked filters after search (locked ones persist)
    setActiveFilters((prev) => prev.filter((f) => f.locked));

    try {
      const localResults = searchLocalKnowledgeBase(q);
      setFaults(localResults);

      // Always use quick/standard config for initial search
      const quickConfig = {
        ...aiConfig,
        searchDepth: "STANDARD" as const,
      };

      if (
        user &&
        (selectedImage || (localResults.length === 0 && navigator.onLine))
      ) {
        const aiResults = await identifyFaultFromQuery(
          q,
          selectedImage,
          quickConfig
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
      <header className="fixed top-0 left-0 right-0 w-full h-14 bg-industrial-900 border-b border-industrial-800 flex items-center justify-between px-4 z-50">
        <div className="flex items-center gap-3">
          <Server className="w-6 h-6 text-safety-500" />
          <span className="font-bold font-mono text-xl tracking-tighter">
            <span className="text-safety-500">LIFT</span>
            <span className="text-white">LOGIC</span>
          </span>
        </div>

        {/* User Profile & Sync Status */}
        <div className="flex items-center gap-3">
          {/* Sync Status Indicator */}
          {!user.isGuest && (
            <div className="flex items-center gap-2">
              {isSyncing ? (
                <div className="flex items-center gap-1.5 text-xs text-blue-400">
                  <RefreshCcw className="w-3.5 h-3.5 animate-spin" />
                  <span className="hidden sm:inline">Syncing...</span>
                </div>
              ) : lastSyncTime ? (
                <div className="flex items-center gap-1.5 text-xs text-green-500" title={`Last sync: ${lastSyncTime.toLocaleTimeString()}`}>
                  <Cloud className="w-3.5 h-3.5" />
                  <Check className="w-3 h-3" />
                </div>
              ) : (
                <div className="flex items-center gap-1.5 text-xs text-industrial-500" title="Not synced">
                  <Cloud className="w-3.5 h-3.5" />
                </div>
              )}
            </div>
          )}

          {/* User Profile */}
          <div className="flex items-center gap-2">
            {user.photoLink ? (
              <img
                src={user.photoLink}
                alt={user.displayName}
                className="w-8 h-8 rounded-full border-2 border-industrial-700"
              />
            ) : (
              <div className="w-8 h-8 rounded-full bg-industrial-700 flex items-center justify-center">
                {user.isGuest ? (
                  <UserIcon className="w-4 h-4 text-industrial-400" />
                ) : (
                  <UserCheck className="w-4 h-4 text-safety-500" />
                )}
              </div>
            )}
            <div className="hidden sm:flex flex-col">
              <span className="text-xs font-medium text-white leading-tight truncate max-w-[120px]">
                {user.displayName}
              </span>
              {user.isGuest ? (
                <span className="text-[10px] text-yellow-500">Guest Mode</span>
              ) : (
                <span className="text-[10px] text-industrial-500 truncate max-w-[120px]">
                  {user.emailAddress}
                </span>
              )}
            </div>
          </div>

          {/* Logout Button */}
          <button
            onClick={handleLogout}
            className="text-industrial-400 hover:text-white p-2 ml-1"
            title="Sign out"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </div>
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
            <div className="flex flex-col gap-4 mb-8">
              {/* Active Filter Chips */}
              {activeFilters.length > 0 && (
                <div className="flex flex-wrap gap-2 max-w-4xl mx-auto w-full justify-center">
                  {activeFilters.map((filter) => (
                    <div
                      key={`${filter.type}-${filter.id}`}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                        filter.type === "manufacturer"
                          ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
                          : "bg-purple-600/20 text-purple-400 border border-purple-500/30"
                      }`}
                    >
                      <span>{filter.name}</span>
                      <button
                        onClick={() => toggleFilterLock(filter.id, filter.type)}
                        className={`p-0.5 rounded transition-colors ${
                          filter.locked
                            ? "text-yellow-400 hover:text-yellow-300"
                            : "text-industrial-500 hover:text-industrial-400"
                        }`}
                        title={filter.locked ? "Unlock (won't persist)" : "Lock (will persist)"}
                      >
                        {filter.locked ? (
                          <Lock className="w-3.5 h-3.5" />
                        ) : (
                          <Unlock className="w-3.5 h-3.5" />
                        )}
                      </button>
                      <button
                        onClick={() => removeFilter(filter.id, filter.type)}
                        className="p-0.5 text-industrial-500 hover:text-red-400 transition-colors"
                        title="Remove filter"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <div className="relative group max-w-4xl mx-auto w-full" ref={suggestionsRef}>
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
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    detectRecognizedTerms(e.target.value);
                  }}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  placeholder={activeFilters.length > 0 ? "Enter fault code..." : "Try: KONE L F505 · Otis E 169"}
                  className="w-full bg-industrial-800/50 border border-industrial-600/50 text-white text-base md:text-lg rounded-2xl pl-14 pr-36 md:pr-44 py-4 md:py-5 focus:outline-none focus:border-industrial-500 focus:ring-1 focus:ring-industrial-500/50 transition-all shadow-2xl placeholder-industrial-600 font-medium"
                />

                {/* Autocomplete Dropdown */}
                {showSuggestions && suggestionMatches.length > 0 && (
                  <div className="absolute z-50 w-full mt-2 bg-industrial-800 border border-industrial-600/50 rounded-xl shadow-2xl overflow-hidden">
                    <div className="px-3 py-2 text-xs text-industrial-500 border-b border-industrial-700">
                      Recognized terms — click to add as filter
                    </div>
                    {suggestionMatches.map((match) => (
                      <button
                        key={`${match.type}-${match.id}`}
                        onClick={() => handleSelectSuggestion(match)}
                        className="w-full px-4 py-3 flex items-center gap-3 hover:bg-industrial-700/50 transition-colors text-left"
                      >
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-medium ${
                            match.type === "manufacturer"
                              ? "bg-blue-600/20 text-blue-400"
                              : "bg-purple-600/20 text-purple-400"
                          }`}
                        >
                          {match.type === "manufacturer" ? "MFR" : "TYPE"}
                        </span>
                        <span className="text-white font-medium">{match.name}</span>
                      </button>
                    ))}
                  </div>
                )}

                <div className="absolute right-2 md:right-2.5 top-2 md:top-2.5 bottom-2 md:bottom-2.5 flex items-center gap-1.5 md:gap-2">
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className={`p-2 md:p-2.5 rounded-lg md:rounded-xl transition-colors ${
                      selectedImage
                        ? "bg-purple-600 text-white"
                        : "bg-industrial-800/80 text-industrial-400 hover:text-white hover:bg-industrial-700"
                    }`}
                  >
                    <ImageIcon className="w-4 h-4 md:w-5 md:h-5" />
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
                    className={`p-2 md:p-2.5 rounded-lg md:rounded-xl transition-all ${
                      isListening
                        ? "bg-red-500 text-white animate-pulse"
                        : "bg-industrial-800/80 text-industrial-400 hover:text-white hover:bg-industrial-700"
                    }`}
                  >
                    {isListening ? (
                      <Mic className="w-4 h-4 md:w-5 md:h-5" />
                    ) : (
                      <MicOff className="w-4 h-4 md:w-5 md:h-5" />
                    )}
                  </button>

                  <button
                    onClick={() => handleSearch()}
                    disabled={isSearching}
                    className="bg-blue-600 hover:bg-blue-500 text-white py-2 md:py-2.5 px-4 md:px-6 rounded-lg md:rounded-xl font-bold text-sm md:text-base transition-all disabled:opacity-50 shadow-lg shadow-blue-600/20 hover:shadow-blue-600/40 active:scale-95"
                  >
                    {isSearching ? (
                      <Loader2 className="w-4 h-4 md:w-5 md:h-5 animate-spin" />
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

                  {/* Progressive Research Actions */}
                  {user && !isSearching && (
                    <div className="flex flex-col items-center gap-3 pt-6 pb-4 border-t border-industrial-800">
                      {/* Research Depth Indicator */}
                      <div className="flex items-center gap-2 text-xs text-industrial-500">
                        <div className={`w-2 h-2 rounded-full ${researchDepth === "quick" ? "bg-safety-500" : "bg-industrial-600"}`} />
                        <span className={researchDepth === "quick" ? "text-industrial-400" : "text-industrial-600"}>Quick</span>
                        <div className="w-8 h-px bg-industrial-700" />
                        <div className={`w-2 h-2 rounded-full ${researchDepth === "deep" ? "bg-blue-500" : "bg-industrial-600"}`} />
                        <span className={researchDepth === "deep" ? "text-industrial-400" : "text-industrial-600"}>Deep</span>
                        <div className="w-8 h-px bg-industrial-700" />
                        <div className={`w-2 h-2 rounded-full ${researchDepth === "verified" ? "bg-green-500" : "bg-industrial-600"}`} />
                        <span className={researchDepth === "verified" ? "text-industrial-400" : "text-industrial-600"}>Verified</span>
                      </div>

                      {/* Action Buttons */}
                      <div className="flex gap-3">
                        {researchDepth === "quick" && (
                          <button
                            onClick={handleGoDeeper}
                            disabled={isDeepening}
                            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600/20 border border-blue-500/50 text-blue-400 rounded-lg text-sm font-medium hover:bg-blue-600/30 transition-all disabled:opacity-50"
                          >
                            {isDeepening ? (
                              <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Researching...
                              </>
                            ) : (
                              <>
                                <Brain className="w-4 h-4" />
                                Go Deeper
                              </>
                            )}
                          </button>
                        )}

                        {researchDepth === "deep" && (
                          <button
                            onClick={handleVerify}
                            disabled={isVerifying}
                            className="flex items-center gap-2 px-4 py-2.5 bg-green-600/20 border border-green-500/50 text-green-400 rounded-lg text-sm font-medium hover:bg-green-600/30 transition-all disabled:opacity-50"
                          >
                            {isVerifying ? (
                              <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Verifying...
                              </>
                            ) : (
                              <>
                                <CheckCircle className="w-4 h-4" />
                                Verify Results
                              </>
                            )}
                          </button>
                        )}

                        {researchDepth === "verified" && (
                          <div className="flex items-center gap-2 px-4 py-2.5 bg-green-600/10 border border-green-500/30 text-green-400 rounded-lg text-sm">
                            <CheckCircle className="w-4 h-4" />
                            Results Verified
                          </div>
                        )}
                      </div>

                      {/* Helper Text */}
                      <p className="text-xs text-industrial-600 text-center max-w-md">
                        {researchDepth === "quick" && "Want more detail? Go Deeper runs multi-angle research."}
                        {researchDepth === "deep" && "Verify runs a critical review to catch errors and add safety notes."}
                        {researchDepth === "verified" && "Results have been cross-checked for accuracy."}
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                !isSearching && (
                  <div className="h-full flex flex-col items-center justify-center text-industrial-500">
                    <div className="w-20 h-20 rounded-full bg-industrial-800 border-2 border-industrial-700 flex items-center justify-center mb-4 opacity-50">
                      <Search className="w-8 h-8 text-industrial-600" />
                    </div>
                    <p className="opacity-50">Enter a fault code to begin</p>
                    <p className="text-xs max-w-xs text-center mt-2 opacity-50">
                      Search returns quick results first. You can then go deeper
                      or verify for more thorough analysis.
                    </p>
                    <p className="text-xs text-industrial-600 mt-3">
                      Try: <span className="text-industrial-500">"KONE L F505"</span> · <span className="text-industrial-500">"Otis E 169"</span> · <span className="text-industrial-500">"Schindler door fault"</span>
                    </p>
                    <p className="text-[10px] text-industrial-700 mt-1">
                      L = Lift/Elevator · E = Escalator
                    </p>

                    {/* How it works */}
                    <div className="mt-8 max-w-sm text-center space-y-3">
                      <p className="text-xs text-industrial-600 uppercase tracking-wider font-medium mb-4">How it works</p>
                      <div className="flex items-center justify-center gap-3 text-xs text-industrial-600">
                        <div className="flex flex-col items-center gap-1">
                          <div className="w-8 h-8 rounded-full bg-safety-500/20 flex items-center justify-center">
                            <Zap className="w-4 h-4 text-safety-500" />
                          </div>
                          <span>Quick</span>
                        </div>
                        <ChevronRight className="w-4 h-4 text-industrial-700" />
                        <div className="flex flex-col items-center gap-1">
                          <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center">
                            <Brain className="w-4 h-4 text-blue-400" />
                          </div>
                          <span>Deep</span>
                        </div>
                        <ChevronRight className="w-4 h-4 text-industrial-700" />
                        <div className="flex flex-col items-center gap-1">
                          <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center">
                            <CheckCircle className="w-4 h-4 text-green-400" />
                          </div>
                          <span>Verify</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )
              )}
              {isSearching && faults.length === 0 && (
                <div className="flex flex-col items-center justify-center py-20">
                  <div className="w-12 h-12 border-4 border-safety-500 border-t-transparent rounded-full animate-spin mb-4"></div>
                  <div className="text-safety-500 font-bold animate-pulse">
                    Searching...
                  </div>
                  <div className="text-xs text-industrial-400 mt-2">
                    Checking local database and AI
                  </div>
                </div>
              )}

              {isDeepening && (
                <div className="flex flex-col items-center justify-center py-20">
                  <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4"></div>
                  <div className="text-blue-400 font-bold animate-pulse">
                    Running Deep Research...
                  </div>
                  <div className="text-xs text-industrial-400 mt-2">
                    Analyzing from multiple angles
                  </div>
                </div>
              )}

              {isVerifying && (
                <div className="flex flex-col items-center justify-center py-20">
                  <div className="w-12 h-12 border-4 border-green-500 border-t-transparent rounded-full animate-spin mb-4"></div>
                  <div className="text-green-400 font-bold animate-pulse">
                    Verifying Results...
                  </div>
                  <div className="text-xs text-industrial-400 mt-2">
                    Cross-checking for accuracy
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
