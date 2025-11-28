
import { FaultRecord } from "../types";

declare var google: any;
declare var gapi: any;

// Scope for User Info, Drive File access, AND Gemini API Access
// We add 'generative-language' to allow using the user's credentials for AI models
const SCOPES = 'https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/cloud-platform';

const USER_STORAGE_KEY = 'LIFT_LOGIC_USER_SESSION';
const DB_FILE_NAME = 'liftlogic_secure_db.lock'; 

let tokenClient: any;
let gapiInited = false;

/**
 * Helper to wait for a global variable (nested supported) to become available.
 * e.g. waitForGlobal('google.accounts.oauth2')
 */
const waitForGlobal = (keyPath: string, timeout = 5000): Promise<void> => {
  return new Promise((resolve) => {
    const check = () => {
        const parts = keyPath.split('.');
        let current: any = window;
        for (const part of parts) {
            current = current?.[part];
            if (current === undefined) return false;
        }
        return true;
    };

    if (check()) {
      resolve();
      return;
    }

    const startTime = Date.now();
    const interval = setInterval(() => {
      if (check()) {
        clearInterval(interval);
        resolve();
      } else if (Date.now() - startTime > timeout) {
        clearInterval(interval);
        console.warn(`Timeout waiting for ${keyPath} to load.`);
        resolve(); 
      }
    }, 100);
  });
};

/**
 * Initialize the Google Identity Services (GIS) Token Client.
 */
export const initTokenClient = async (clientId: string): Promise<void> => {
    await waitForGlobal('google.accounts.oauth2');
    
    return new Promise((resolve) => {
        if (typeof google === 'undefined' || !google.accounts || !google.accounts.oauth2) {
            console.warn("Google Identity Services script failed to load. Auth disabled.");
            resolve();
            return;
        }

        if (!clientId || clientId.includes('YOUR_CLIENT_ID') || clientId === '') {
            console.warn("Google Client ID is not configured.");
            resolve(); 
            return;
        }

        try {
            tokenClient = google.accounts.oauth2.initTokenClient({
                client_id: clientId,
                scope: SCOPES,
                callback: (response: any) => {
                    if (response.error) {
                        console.error("GIS Callback Error:", response);
                    }
                },
            });
            console.log("Token Client Initialized");
            resolve();
        } catch (err) {
            console.error("Error initializing Token Client", err);
            resolve();
        }
    });
};

/**
 * Initialize the GAPI Client (Needed for Drive API calls)
 */
export const initGapiClient = async (): Promise<void> => {
    await waitForGlobal('gapi');

    return new Promise((resolve) => {
        const gapiObj = (window as any).gapi;
        
        if (!gapiObj) {
            console.warn("GAPI script failed to load. Drive Sync disabled.");
            resolve();
            return;
        }
        
        try {
            gapiObj.load('client', async () => {
                try {
                    await gapiObj.client.init({}); 
                    await gapiObj.client.load('drive', 'v3');
                    gapiInited = true;
                    console.log("GAPI Client Initialized");
                    resolve();
                } catch (e) {
                    console.error("Failed to load GAPI client", e);
                    resolve();
                }
            });
        } catch (e) {
            console.error("GAPI Load Crash", e);
            resolve();
        }
    });
}

/**
 * Trigger the Popup to sign in.
 */
export const signInWithGoogle = (): Promise<string> => {
  return new Promise((resolve, reject) => {
    if (!tokenClient) {
        const msg = "Google Services not ready. Please refresh or check internet connection.";
        console.error(msg);
        reject(new Error(msg));
        return;
    }

    try {
        tokenClient.callback = async (resp: any) => {
          if (resp.error !== undefined) {
            reject(resp);
            return;
          }

          // Sync token with GAPI for Drive calls
          if (gapiInited && (window as any).gapi?.client) {
              (window as any).gapi.client.setToken({ access_token: resp.access_token });
          }

          resolve(resp.access_token);
        };

        tokenClient.requestAccessToken({ prompt: 'consent' });
    } catch (e) {
        console.error("Sign In Error", e);
        reject(e);
    }
  });
};

/**
 * Silently refresh the access token (no popup, for session restoration).
 * Returns null if user interaction is required.
 */
export const silentTokenRefresh = (): Promise<string | null> => {
  return new Promise((resolve) => {
    if (!tokenClient) {
        console.log("Token client not ready for silent refresh");
        resolve(null);
        return;
    }

    try {
        tokenClient.callback = async (resp: any) => {
          if (resp.error !== undefined) {
            // Silent refresh failed - user needs to re-authenticate
            console.log("Silent token refresh failed, user interaction required");
            resolve(null);
            return;
          }

          // Sync token with GAPI for Drive calls
          if (gapiInited && (window as any).gapi?.client) {
              (window as any).gapi.client.setToken({ access_token: resp.access_token });
          }

          console.log("Silent token refresh successful");
          resolve(resp.access_token);
        };

        // Request token without consent prompt (silent)
        tokenClient.requestAccessToken({ prompt: '' });
    } catch (e) {
        console.error("Silent refresh error", e);
        resolve(null);
    }
  });
};

/**
 * Returns the current valid OAuth Access Token if available.
 * This allows other services to use the user's credentials for API calls.
 */
export const getAccessToken = (): string | null => {
    if (gapiInited && (window as any).gapi?.client) {
        const tokenObj = (window as any).gapi.client.getToken();
        return tokenObj ? tokenObj.access_token : null;
    }
    return null;
}

export const getCurrentUserInfo = async (accessToken: string): Promise<{ displayName: string, emailAddress: string, photoLink?: string }> => {
  try {
      const response = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
        headers: {
            'Authorization': `Bearer ${accessToken}`
        }
      });
      
      if (!response.ok) throw new Error("Failed to fetch user info");
      
      const data = await response.json();
      return {
          displayName: data.name,
          emailAddress: data.email,
          photoLink: data.picture
      };
  } catch (err) {
      console.error("Error fetching user info:", err);
      return { displayName: 'Unknown Technician', emailAddress: '' };
  }
};

// --- DRIVE API HELPERS ---

export const findDatabaseFile = async (): Promise<string | null> => {
    if (!gapiInited || !(window as any).gapi?.client?.drive) {
        console.warn("GAPI not initialized or Drive API missing. Cannot find database.");
        return null;
    }
    try {
        const response = await (window as any).gapi.client.drive.files.list({
            q: `name = '${DB_FILE_NAME}' and trashed = false`,
            fields: 'files(id, name)',
            spaces: 'drive'
        });
        
        const files = response.result.files;
        if (files && files.length > 0) {
            return files[0].id;
        }
        return null;
    } catch (e) {
        console.error("Error finding file", e);
        return null;
    }
};

export const readDriveFile = async (fileId: string): Promise<string | null> => {
    if (!gapiInited) return null;
    try {
        const response = await (window as any).gapi.client.drive.files.get({
            fileId: fileId,
            alt: 'media'
        });
        return typeof response.body === 'string' ? response.body : response.result;
    } catch (e) {
        console.error("Error reading file", e);
        return null;
    }
};

export const createDriveFile = async (encryptedData: string): Promise<string | null> => {
    if (!gapiInited) return null;
    try {
        const fileMetadata = {
            name: DB_FILE_NAME,
            mimeType: 'text/plain'
        };
        
        const accessToken = (window as any).gapi.client.getToken().access_token;
        const metadataBlob = new Blob([JSON.stringify(fileMetadata)], { type: 'application/json' });
        const contentBlob = new Blob([encryptedData], { type: 'text/plain' });
        
        const form = new FormData();
        form.append('metadata', metadataBlob);
        form.append('file', contentBlob);
        
        const res = await fetch('https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + accessToken },
            body: form
        });
        
        const json = await res.json();
        return json.id;

    } catch (e) {
        console.error("Error creating file", e);
        return null;
    }
};

export const updateDriveFile = async (fileId: string, encryptedData: string): Promise<boolean> => {
    if (!gapiInited) return false;
    try {
        const accessToken = (window as any).gapi.client.getToken().access_token;
        const contentBlob = new Blob([encryptedData], { type: 'text/plain' });
        
        const res = await fetch(`https://www.googleapis.com/upload/drive/v3/files/${fileId}?uploadType=media`, {
            method: 'PATCH',
            headers: { 'Authorization': 'Bearer ' + accessToken, 'Content-Type': 'text/plain' },
            body: contentBlob
        });
        
        return res.ok;
    } catch (e) {
        console.error("Error updating file", e);
        return false;
    }
};

// --- PERSISTENCE HELPERS ---

export const saveUserSession = (user: { displayName: string, emailAddress: string, photoLink?: string, isGuest?: boolean, id: string }) => {
  try {
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
  } catch (e) {
    console.error("Failed to save session", e);
  }
};

export const loadUserSession = () => {
  try {
    const data = localStorage.getItem(USER_STORAGE_KEY);
    return data ? JSON.parse(data) : null;
  } catch (e) {
    return null;
  }
};

export const clearUserSession = () => {
  localStorage.removeItem(USER_STORAGE_KEY);
};
