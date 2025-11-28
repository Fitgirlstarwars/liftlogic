
import { GoogleGenAI, Type, Schema } from "@google/genai";
import { FaultRecord, EquipmentType, SeverityLevel, AIConfig } from "../types";
import { v4 as uuidv4 } from 'uuid';
import { getAccessToken } from "./driveService";
import { generateViaGateway } from "./llmGateway";
import { performDeepResearch } from "./deepResearch";

const CUSTOM_KEY_STORAGE = 'LIFT_LOGIC_CUSTOM_API_KEY';

export const getCustomApiKey = (): string | null => {
  return localStorage.getItem(CUSTOM_KEY_STORAGE);
};

export const setCustomApiKey = (key: string) => {
  if (!key) localStorage.removeItem(CUSTOM_KEY_STORAGE);
  else localStorage.setItem(CUSTOM_KEY_STORAGE, key.trim());
};

const cleanJsonOutput = (text: string): string => {
  let clean = text.replace(/```json/g, '').replace(/```/g, '').trim();
  const startObj = clean.indexOf('{');
  const startArr = clean.indexOf('[');
  const isArray = (startArr !== -1 && (startObj === -1 || startArr < startObj));

  if (isArray) {
    const end = clean.lastIndexOf(']');
    if (startArr !== -1 && end !== -1) clean = clean.substring(startArr, end + 1);
  } else {
    const end = clean.lastIndexOf('}');
    if (startObj !== -1 && end !== -1) clean = clean.substring(startObj, end + 1);
  }
  return clean;
};

/**
 * Expand equipment type shortcuts in query
 * L = Lift/Elevator, E = Escalator
 * Example: "KONE L F505" -> "KONE Elevator F505"
 */
const expandQueryShortcuts = (query: string): string => {
  // Match patterns like "BRAND L CODE" or "BRAND E CODE"
  // Case insensitive, handles spaces
  return query
    .replace(/\b([A-Za-z]+)\s+L\s+/gi, '$1 Elevator ')
    .replace(/\b([A-Za-z]+)\s+E\s+/gi, '$1 Escalator ')
    // Also handle standalone L/E at start
    .replace(/^L\s+/i, 'Elevator ')
    .replace(/^E\s+/i, 'Escalator ');
};

// --- CORE EXPORTS ---

export const identifyFaultFromQuery = async (
    query: string,
    imageBase64?: string | null,
    config?: AIConfig
): Promise<FaultRecord[]> => {

    // Expand shortcuts: "KONE L F505" -> "KONE Elevator F505"
    const expandedQuery = expandQueryShortcuts(query);

    // 1. Check for Deep Research Mode
    if (config?.searchDepth === 'DEEP') {
        const deepResult = await performDeepResearch(expandedQuery, config || { provider: 'GOOGLE', model: 'gemini-3-pro-preview', searchDepth: 'DEEP', minSources: 3 });
        return deepResult ? [deepResult] : [];
    }

    // 2. Standard Search via Gateway (Supports all providers)
    // If there is an image, we MUST use Gemini (other providers via generic gateway might not support image yet in this demo)

    const prompt = `
    Analyze this query: "${expandedQuery}". 
    Extract technical elevator/escalator fault information.
    Return JSON matching: { code, title, manufacturer, model, equipmentType, description, possibleCauses[], solutions[], severity }.
    If uncertain, return { "code": "UNKNOWN" ... }.
    `;

    try {
        const response = await generateViaGateway(
            prompt,
            "You are an expert Elevator Technician.",
            config || { provider: 'GOOGLE', model: 'gemini-3-pro-preview', searchDepth: 'STANDARD', minSources: 1 },
            true
        );
        
        const cleanText = cleanJsonOutput(response.text);
        const data = JSON.parse(cleanText);

        if (data.code === "UNKNOWN") return [];

        return [{
            ...data,
            id: uuidv4(),
            lastUpdated: new Date().toISOString(),
            source: `${response.provider} (${response.model})`,
            severity: data.severity || SeverityLevel.MEDIUM
        }];

    } catch (e) {
        console.error("Standard Identification Failed", e);
        return [];
    }
};

export const validateContribution = async (
  record: FaultRecord,
  contribution: string,
  config?: AIConfig
): Promise<{ analysis: string; status: 'VERIFIED' | 'CAUTION' | 'UNCERTAIN'; refinedContent: string; joke: string }> => {
    
    const prompt = `
    Context: Fault ${record.code} (${record.manufacturer}). 
    Technician Note: "${contribution}".
    Verify technical accuracy. Rewrite for clarity. Assess safety risks.
    Output JSON: { analysis, status (VERIFIED/CAUTION/UNCERTAIN), refinedContent, joke }.
    `;

    try {
        const response = await generateViaGateway(
            prompt,
            "You are a Senior Technical Validator.",
            config || { provider: 'GOOGLE', model: 'gemini-3-pro-preview', searchDepth: 'STANDARD', minSources: 1 },
            true
        );

        const data = JSON.parse(cleanJsonOutput(response.text));
        return {
            analysis: data.analysis || "Checked via AI",
            status: data.status || "UNCERTAIN",
            refinedContent: data.refinedContent || contribution,
            joke: data.joke || "Going up!"
        };
    } catch (e) {
        return { 
          analysis: "Validation unavailable.", 
          status: "UNCERTAIN", 
          refinedContent: contribution,
          joke: "Why did the elevator stop? It needed a break." 
        };
    }
};

/**
 * Uploads a file directly to Google AI Studio via OAuth.
 * Strict: Requires Token. No fallback to Process Env.
 */
export const uploadToGemini = async (file: File): Promise<{ uri: string; state: string }> => {
  const TOKEN = getAccessToken();
  
  if (!TOKEN) throw new Error("Authentication required. Please sign in with Google.");
  
  try {
    const metadata = { file: { displayName: file.name } };
    const headers: any = {
        'Authorization': `Bearer ${TOKEN}`,
        'X-Goog-Upload-Protocol': 'resumable',
        'X-Goog-Upload-Command': 'start',
        'X-Goog-Upload-Header-Content-Length': file.size.toString(),
        'X-Goog-Upload-Header-Content-Type': file.type,
    };

    const initRes = await fetch(`https://generativelanguage.googleapis.com/upload/v1beta/files?key=NO_KEY_NEEDED`, {
       method: 'POST',
       headers: { 
          'Authorization': `Bearer ${TOKEN}`,
          'Content-Type': 'application/json' 
       },
       body: JSON.stringify(metadata)
    });

    if (!initRes.ok) throw new Error("Upload Init Failed");
    
    const uploadUrl = initRes.headers.get('X-Goog-Upload-URL');
    if (!uploadUrl) throw new Error("No upload URL received");

    const uploadRes = await fetch(uploadUrl, {
        method: 'POST',
        headers: { 
           'Authorization': `Bearer ${TOKEN}`,
           'X-Goog-Upload-Offset': '0',
           'X-Goog-Upload-Command': 'upload, finalize'
        },
        body: file
    });

    if (!uploadRes.ok) throw new Error("Upload Failed");
    const result = await uploadRes.json();
    return { uri: result.file.uri, state: result.file.state };

  } catch (e) {
    console.error("Upload error", e);
    throw e;
  }
};
export const streamTroubleshootingHelp = async function* (
    history: { role: string; parts: { text: string }[] }[], 
    newMessage: string,
    context?: FaultRecord
) {
    // Note: Streaming requires the gateway, but streaming support varies.
    // For this implementation, we will use a direct call if Google is the provider to support streaming,
    // otherwise we might need to buffer.
    
    const TOKEN = getAccessToken();
    if (!TOKEN) throw new Error("Authentication required");

    const model = 'gemini-3-pro-preview';
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:streamGenerateContent?alt=sse`;

    const body = {
        contents: [...history, { role: 'user', parts: [{ text: newMessage }] }],
        systemInstruction: { parts: [{ text: "You are an expert field technician." }] }
    };

    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${TOKEN}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
    });

    const reader = response.body?.getReader();
    if (!reader) return;

    const decoder = new TextDecoder();
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        
        // Parse SSE format (simple parsing for demo)
        const lines = chunk.split('\n');
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                try {
                    const json = JSON.parse(line.substring(6));
                    const text = json.candidates?.[0]?.content?.parts?.[0]?.text;
                    if (text) yield { text };
                } catch (e) { /* ignore parse error */ }
            }
        }
    }
};
