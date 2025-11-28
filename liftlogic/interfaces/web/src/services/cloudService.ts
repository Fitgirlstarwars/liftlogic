import { FaultRecord } from "../types";

/**
 * SEAMLESS CLOUD BRIDGE SERVICE
 * 
 * This service communicates with a Google Apps Script Web App deployed by the Admin.
 * This allows ANY user to save data to the Admin's Google Drive without logging in.
 * 
 * --- GOOGLE APPS SCRIPT CODE (COPY & DEPLOY THIS) ---
 * 
 * function doGet(e) {
 *   const file = getDbFile();
 *   return ContentService.createTextOutput(file.getBlob().getDataAsString())
 *     .setMimeType(ContentService.MimeType.JSON);
 * }
 * 
 * function doPost(e) {
 *   // Use a lock to prevent race conditions during concurrent writes
 *   const lock = LockService.getScriptLock();
 *   lock.tryLock(10000);
 *   
 *   try {
 *     const file = getDbFile();
 *     // Handle potential empty file
 *     const content = file.getBlob().getDataAsString();
 *     const currentData = content ? JSON.parse(content) : [];
 *     
 *     // The post body will be the JSON record
 *     const newRecord = JSON.parse(e.postData.contents);
 *     
 *     // Deduplicate: Check if ID exists
 *     const index = currentData.findIndex(r => r.id === newRecord.id);
 *     
 *     if (index >= 0) {
 *       // Update existing
 *       currentData[index] = newRecord;
 *     } else {
 *       // Add new
 *       currentData.push(newRecord);
 *     }
 *     
 *     file.setContent(JSON.stringify(currentData, null, 2));
 *     
 *     return ContentService.createTextOutput(JSON.stringify({status: "success", action: index >= 0 ? "updated" : "created"}))
 *       .setMimeType(ContentService.MimeType.JSON);
 *       
 *   } catch (err) {
 *     return ContentService.createTextOutput(JSON.stringify({status: "error", message: err.toString()}))
 *       .setMimeType(ContentService.MimeType.JSON);
 *   } finally {
 *     lock.releaseLock();
 *   }
 * }
 * 
 * function getDbFile() {
 *   const fileName = "liftlogic_db.json";
 *   const files = DriveApp.getFilesByName(fileName);
 *   if (files.hasNext()) return files.next();
 *   return DriveApp.createFile(fileName, "[]", MimeType.PLAIN_TEXT);
 * }
 * 
 * ----------------------------------------------------
 */

/**
 * Fetches the entire database from the Admin's Cloud Bridge.
 */
export const fetchCloudDatabase = async (bridgeUrl: string): Promise<FaultRecord[]> => {
    try {
        const response = await fetch(bridgeUrl, {
            method: 'GET',
            redirect: 'follow' // Essential for Google Scripts
        });
        
        if (!response.ok) throw new Error("Bridge unavailable");
        
        const data = await response.json();
        return Array.isArray(data) ? data : [];
    } catch (error) {
        console.error("Cloud Bridge Fetch Error:", error);
        throw error;
    }
};

/**
 * Pushes a single record to the Cloud Bridge.
 * This is "Fire and Forget" - we don't strictly wait for it to finish in the UI.
 */
export const pushRecordToCloud = async (bridgeUrl: string, record: FaultRecord): Promise<boolean> => {
    try {
        // We use text/plain to avoid CORS Preflight (OPTIONS) checks which GAS doesn't handle well.
        // The Apps Script doPost parses the content regardless.
        const response = await fetch(bridgeUrl, {
            method: 'POST',
            redirect: 'follow',
            headers: {
                'Content-Type': 'text/plain;charset=utf-8', 
            },
            body: JSON.stringify(record)
        });

        const result = await response.json();
        return result.status === 'success';
    } catch (error) {
        console.error("Cloud Bridge Push Error:", error);
        return false;
    }
};