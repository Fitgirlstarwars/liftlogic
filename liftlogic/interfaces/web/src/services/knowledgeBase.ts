
import { FaultRecord } from "../types";

// In-Memory Cache to avoid constant decryption on every keystroke
// This is the ONLY place data exists in the app.
let MEMORY_CACHE: FaultRecord[] | null = null;

// Callback to trigger Cloud Sync when data changes
let onDatabaseChange: ((records: FaultRecord[]) => Promise<void>) | null = null;

export const setDatabaseChangeCallback = (cb: (records: FaultRecord[]) => Promise<void>) => {
  onDatabaseChange = cb;
};

/**
 * Initializes the KB with data fetched from Cloud (after decryption).
 */
export const initKnowledgeBase = (initialData: FaultRecord[] = []) => {
    MEMORY_CACHE = initialData;
};

/**
 * Returns the full list of records currently in memory.
 */
export const getKnowledgeBase = (): FaultRecord[] => {
    return MEMORY_CACHE || [];
};

/**
 * Searches the in-memory database.
 */
export const searchLocalKnowledgeBase = (query: string): FaultRecord[] => {
    if (!MEMORY_CACHE) return [];
    if (!query) return MEMORY_CACHE;
    const q = query.toLowerCase();
    return MEMORY_CACHE.filter(r => 
        r.code.toLowerCase().includes(q) || 
        r.description.toLowerCase().includes(q) ||
        r.manufacturer.toLowerCase().includes(q) ||
        (r.relatedQueries && r.relatedQueries.some(rq => rq.toLowerCase().includes(q)))
    );
};

/**
 * Saves or updates a record in the local cache and triggers the sync callback.
 */
export const saveToKnowledgeBase = async (record: FaultRecord): Promise<void> => {
    if (!MEMORY_CACHE) MEMORY_CACHE = [];
    
    const index = MEMORY_CACHE.findIndex(r => r.id === record.id);
    if (index >= 0) {
        MEMORY_CACHE[index] = record;
    } else {
        MEMORY_CACHE.push(record);
    }

    if (onDatabaseChange) {
        await onDatabaseChange(MEMORY_CACHE);
    }
};

/**
 * Merges a list of records into the local cache.
 */
export const mergeKnowledgeBase = async (records: FaultRecord[]): Promise<void> => {
    if (!MEMORY_CACHE) MEMORY_CACHE = [];
    
    let changed = false;
    records.forEach(newRecord => {
        const index = MEMORY_CACHE!.findIndex(r => r.id === newRecord.id);
        if (index !== -1) {
            // Update existing
             MEMORY_CACHE![index] = newRecord;
             changed = true;
        } else {
            // Add new
            MEMORY_CACHE!.push(newRecord);
            changed = true;
        }
    });
    
    // Note: merge usually happens during sync/import, so strictly speaking 
    // we might not want to trigger the 'save back to cloud' callback immediately 
    // unless specifically needed, but keeping state consistent is good.
};

/**
 * Removes duplicates based on Manufacturer + Code.
 */
export const deduplicateDatabase = (): number => {
    if (!MEMORY_CACHE) return 0;
    const unique = new Map();
    let removedCount = 0;
    
    MEMORY_CACHE.forEach(r => {
        // Key by Manufacturer + Code to find logical duplicates
        const key = `${r.manufacturer}-${r.code}`.toLowerCase();
        if (!unique.has(key)) {
            unique.set(key, r);
        } else {
            // Keep the one with more contributions/data
            const existing = unique.get(key);
            const existingScore = (existing.communityContributions?.length || 0) + (existing.solutions?.length || 0);
            const currentScore = (r.communityContributions?.length || 0) + (r.solutions?.length || 0);
            
            if (currentScore > existingScore) {
                unique.set(key, r);
            }
            removedCount++;
        }
    });
    
    MEMORY_CACHE = Array.from(unique.values());
    
    if (removedCount > 0 && onDatabaseChange) {
        onDatabaseChange(MEMORY_CACHE);
    }
    return removedCount;
};

/**
 * Exports the database as a JSON file download.
 */
export const exportDatabase = () => {
    if (!MEMORY_CACHE) return;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(MEMORY_CACHE, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", "liftlogic_db_export.json");
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
};

/**
 * Imports a JSON file into the database.
 */
export const importDatabase = (file: File): Promise<void> => {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = async (event) => {
            try {
                const json = JSON.parse(event.target?.result as string);
                if (Array.isArray(json)) {
                    await mergeKnowledgeBase(json);
                    if (onDatabaseChange && MEMORY_CACHE) {
                        await onDatabaseChange(MEMORY_CACHE);
                    }
                    resolve();
                } else {
                    reject(new Error("Invalid format"));
                }
            } catch (e) {
                reject(e);
            }
        };
        reader.readAsText(file);
    });
};

/**
 * Generates JSONL content suitable for Gemini fine-tuning.
 */
export const generateTuningData = (): string | null => {
    if (!MEMORY_CACHE || MEMORY_CACHE.length === 0) return null;
    
    // Convert KB records to Gemini JSONL tuning format
    const lines = MEMORY_CACHE.map(record => {
        // Filter out records with too little info to be useful training data
        if (!record.solutions || record.solutions.length === 0 || record.description.length < 10) return null;

        const system = "You are an expert elevator technician.";
        const user = `Identify the fault: ${record.manufacturer} ${record.code}`;
        const modelResponse = JSON.stringify({
            code: record.code,
            title: record.title,
            description: record.description,
            possibleCauses: record.possibleCauses,
            solutions: record.solutions,
            severity: record.severity
        }); 
        
        return JSON.stringify({
            messages: [
                { role: 'system', content: system },
                { role: 'user', content: user },
                { role: 'model', content: modelResponse }
            ]
        });
    }).filter(l => l !== null);

    return lines.join('\n');
};

/**
 * Exports the tuning dataset as a JSONL file download.
 */
export const exportTuningDataset = () => {
    const data = generateTuningData();
    if (!data) {
        alert("No valid data for tuning.");
        return;
    }
    const dataStr = "data:text/plain;charset=utf-8," + encodeURIComponent(data);
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", "gemini_tuning_dataset.jsonl");
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
};
