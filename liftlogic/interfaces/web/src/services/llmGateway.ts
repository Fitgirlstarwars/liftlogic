
import { AIConfig, AIProvider } from "../types";
import { getAccessToken } from "./driveService";

// Standardized Interface for all AI responses
export interface LLMResponse {
  text: string;
  provider: string;
  model: string;
  usage?: { input: number, output: number };
}

/**
 * The Gateway Router.
 * Decides which external API to call based on the user's configuration.
 */
export const generateViaGateway = async (
  prompt: string,
  systemInstruction: string,
  config: AIConfig,
  jsonMode: boolean = false
): Promise<LLMResponse> => {

  switch (config.provider) {
    case 'GOOGLE':
      return await callGoogleGemini(prompt, systemInstruction, config, jsonMode);
    case 'OPENAI':
      return await callOpenAI(prompt, systemInstruction, config, jsonMode);
    case 'ANTHROPIC':
      return await callAnthropic(prompt, systemInstruction, config, jsonMode);
    case 'XAI':
      return await callGrok(prompt, systemInstruction, config, jsonMode);
    default:
      throw new Error("Unknown AI Provider selected");
  }
};

// --- 1. GOOGLE GEMINI (OAUTH ONLY) ---
const callGoogleGemini = async (prompt: string, sys: string, config: AIConfig, jsonMode: boolean): Promise<LLMResponse> => {
  const token = getAccessToken();
  
  if (!token) {
     throw new Error("Authentication Missing: Please sign in with Google to use the AI features.");
  }

  // Construct REST Request
  const model = config.model.includes('gemini') ? config.model : 'gemini-3-pro-preview';
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`;
  
  const body: any = {
    contents: [{ parts: [{ text: prompt }] }],
    systemInstruction: { parts: [{ text: sys }] },
    generationConfig: {
       temperature: 0.2,
       responseMimeType: jsonMode ? "application/json" : "text/plain"
    }
  };

  // Enable Search if Deep Mode
  if (config.searchDepth === 'DEEP') {
     body.tools = [{ googleSearch: {} }];
  }

  const headers: any = { 
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}` 
  };

  const res = await fetch(url, {
     method: 'POST',
     headers,
     body: JSON.stringify(body)
  });

  if (!res.ok) {
     const err = await res.text();
     if (res.status === 401 || res.status === 403) {
         throw new Error("Session Expired: Please refresh the page and sign in again.");
     }
     throw new Error(`Gemini API Error: ${err}`);
  }

  const data = await res.json();
  const text = data.candidates?.[0]?.content?.parts?.[0]?.text || "";

  return {
    text,
    provider: 'Google',
    model: model
  };
};

// --- 2. OPENAI (ChatGPT) ---
const callOpenAI = async (prompt: string, sys: string, config: AIConfig, jsonMode: boolean): Promise<LLMResponse> => {
   if (!config.openaiKey) throw new Error("Please link your OpenAI account in Settings.");

   const res = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${config.openaiKey}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
         model: config.model || "gpt-4-turbo",
         messages: [
            { role: "system", content: sys },
            { role: "user", content: prompt }
         ],
         response_format: jsonMode ? { type: "json_object" } : undefined
      })
   });

   if (!res.ok) {
      const err = await res.text();
      throw new Error(`OpenAI Connection Failed: ${err}`);
   }

   const data = await res.json();
   return {
      text: data.choices[0].message.content,
      provider: 'OpenAI',
      model: data.model
   };
};

// --- 3. ANTHROPIC (Claude) ---
const callAnthropic = async (prompt: string, sys: string, config: AIConfig, jsonMode: boolean): Promise<LLMResponse> => {
   if (!config.anthropicKey) throw new Error("Please link your Anthropic account in Settings.");

   // Simulating request structure
   const res = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
         "x-api-key": config.anthropicKey,
         "anthropic-version": "2023-06-01",
         "content-type": "application/json",
         "dangerously-allow-browser": "true" 
      },
      body: JSON.stringify({
         model: config.model || "claude-3-sonnet-20240229",
         max_tokens: 4096,
         system: sys,
         messages: [{ role: "user", content: prompt }]
      })
   });

   if (!res.ok) {
     const err = await res.text();
     throw new Error(`Claude Connection Failed: ${err}`);
   }

   const data = await res.json();
   return {
     text: data.content[0].text,
     provider: 'Anthropic',
     model: data.model
   };
};

// --- 4. xAI (Grok) ---
const callGrok = async (prompt: string, sys: string, config: AIConfig, jsonMode: boolean): Promise<LLMResponse> => {
    if (!config.xaiKey) throw new Error("Please link your xAI account in Settings.");
 
    const res = await fetch("https://api.x.ai/v1/chat/completions", {
       method: "POST",
       headers: {
         "Authorization": `Bearer ${config.xaiKey}`,
         "Content-Type": "application/json"
       },
       body: JSON.stringify({
          model: "grok-beta",
          messages: [
             { role: "system", content: sys },
             { role: "user", content: prompt }
          ],
          stream: false
       })
    });
 
    if (!res.ok) {
       const err = await res.text();
       throw new Error(`Grok Connection Failed: ${err}`);
    }
 
    const data = await res.json();
    return {
       text: data.choices[0].message.content,
       provider: 'xAI',
       model: 'grok-beta'
    };
 };
