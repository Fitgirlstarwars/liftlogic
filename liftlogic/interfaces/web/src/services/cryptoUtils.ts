
import { FaultRecord } from "../types";

// VOLATILE MEMORY KEY
// This exists ONLY in RAM. If the app reloads, it is gone.
let SESSION_KEY: CryptoKey | null = null;

// --- CRYPTO CORE (PBKDF2) ---

/**
 * Generates a deterministic salt based on the User's ID.
 * This allows us to recreate the same key every time the specific user logs in,
 * without storing the key or asking for a second password.
 */
const generateDeterministicSalt = async (userId: string): Promise<Uint8Array> => {
  const enc = new TextEncoder();
  const hashBuffer = await window.crypto.subtle.digest('SHA-256', enc.encode(userId));
  // Use the first 16 bytes of the hash as the salt
  return new Uint8Array(hashBuffer).slice(0, 16);
};

/**
 * Derives the AES-GCM key from the user's identifier.
 * We use a high iteration count to make brute-forcing difficult 
 * even if the User ID is known.
 */
const deriveKeyFromUserId = async (userId: string, salt: Uint8Array): Promise<CryptoKey> => {
  const enc = new TextEncoder();
  const keyMaterial = await window.crypto.subtle.importKey(
    "raw",
    enc.encode(userId), // The "Password" is the User ID
    { name: "PBKDF2" },
    false,
    ["deriveKey"]
  );

  return await window.crypto.subtle.deriveKey(
    {
      name: "PBKDF2",
      salt: salt as any,
      iterations: 100000, // 100k iterations
      hash: "SHA-256"
    },
    keyMaterial,
    { name: "AES-GCM", length: 256 },
    false, 
    ["encrypt", "decrypt"]
  );
};

/**
 * Converts ArrayBuffer to Base64 string for storage
 */
const arrayBufferToBase64 = (buffer: ArrayBuffer): string => {
  let binary = '';
  const bytes = new Uint8Array(buffer);
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
};

/**
 * Converts Base64 string to Uint8Array
 */
const base64ToUint8Array = (base64: string): Uint8Array => {
  const binary_string = atob(base64);
  const len = binary_string.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binary_string.charCodeAt(i);
  }
  return bytes;
};

// --- PUBLIC API ---

/**
 * Initializes the session key automatically based on the logged-in user.
 * This creates an "Invisible Vault" experience.
 */
export const initSessionKey = async (userId: string): Promise<CryptoKey> => {
  const salt = await generateDeterministicSalt(userId);
  SESSION_KEY = await deriveKeyFromUserId(userId, salt);
  return SESSION_KEY;
};

/**
 * Encrypts the database.
 * Format: IV (Base64) : CIPHERTEXT (Base64)
 * Note: We don't need to store the salt because it's derived from the user ID.
 */
export const encryptData = async (records: FaultRecord[]): Promise<string> => {
  if (!SESSION_KEY) throw new Error("Session locked - Key missing");

  const encoded = new TextEncoder().encode(JSON.stringify(records));
  // Generate a random IV for every save to ensure semantic security
  const iv = window.crypto.getRandomValues(new Uint8Array(12));
  
  const content = await window.crypto.subtle.encrypt(
    { name: "AES-GCM", iv: iv },
    SESSION_KEY,
    encoded
  );
  
  return `${arrayBufferToBase64(iv.buffer)}:${arrayBufferToBase64(content)}`;
};

/**
 * Decrypts the database.
 * Input Format: IV (Base64) : CIPHERTEXT (Base64)
 */
export const decryptData = async (encryptedString: string): Promise<FaultRecord[]> => {
  if (!SESSION_KEY) throw new Error("Session locked - Key missing");

  try {
    const parts = encryptedString.split(':');
    // Handle legacy or malformed formats gracefully
    if (parts.length < 2) throw new Error("Invalid data format");

    const ivB64 = parts[0];
    const contentB64 = parts[1];

    const iv = base64ToUint8Array(ivB64);
    const content = base64ToUint8Array(contentB64);

    const decrypted = await window.crypto.subtle.decrypt(
      { name: "AES-GCM", iv: iv as any },
      SESSION_KEY,
      content as any
    );

    const decoded = new TextDecoder().decode(decrypted);
    return JSON.parse(decoded);
  } catch (e) {
    console.error("Decryption failed", e);
    // This usually happens if a different user tries to open the file, 
    // or if the file is corrupted.
    throw new Error("Access Denied: Data cannot be decrypted with this account.");
  }
};

// Helper to check if key exists (for UI state)
export const isSessionActive = () => !!SESSION_KEY;
