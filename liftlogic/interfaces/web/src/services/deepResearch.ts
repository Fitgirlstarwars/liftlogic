
import { AIConfig, FaultRecord, EquipmentType, SeverityLevel } from "../types";
import { v4 as uuidv4 } from 'uuid';
import { generateViaGateway } from "./llmGateway";

/**
 * THE DEEP RESEARCH AGENT
 * 
 * Instead of one query, this agent:
 * 1. Analyzes the query to identify 3-4 distinct research angles.
 * 2. Fires parallel "Google Grounded" requests for each angle via the User's OAuth.
 * 3. Synthesizes the results into a massive, verified report.
 * 
 * This effectively "searches 30+ sites" by proxy of Google's index.
 */
export const performDeepResearch = async (
    query: string, 
    config: AIConfig
): Promise<FaultRecord | null> => {
    
    // Step 1: Planning Phase
    // Ask the AI how to research this.
    const planPrompt = `
    I need to research the elevator/escalator fault: "${query}".
    Generate 4 distinct, specific search queries to find the manual, the specific fault code meaning, electrical causes, and mechanical fixes.
    Return ONLY a JSON array of strings.
    Example: ["Otis Gen2 Error 404 manual", "Otis Gen2 drive fault electrical check", "elevator door lock mechanical adjustment guide"]
    `;

    let searchQueries: string[] = [];
    try {
        const planResponse = await generateViaGateway(planPrompt, "You are a research planner.", config, true);
        const cleanJson = planResponse.text.replace(/```json/g, '').replace(/```/g, '').trim();
        searchQueries = JSON.parse(cleanJson);
    } catch (e) {
        console.warn("Planning failed, falling back to basic search", e);
        searchQueries = [`${query} elevator fault manual`, `${query} troubleshooting guide`];
    }

    // Step 2: Parallel Execution (The "Web Crawl" Simulation)
    // We fire requests for all queries simultaneously. 
    // Since we use the User's OAuth, we usually have a decent quota.
    
    const researchPromises = searchQueries.map(q => 
        generateViaGateway(
            `Research this strictly using Google Search tools: "${q}". Extract technical facts about causes and solutions. Be verbose.`,
            "You are a field researcher. Use Google Search to find technical details.",
            { ...config, searchDepth: 'DEEP' } // Force Grounding
        )
    );

    const results = await Promise.all(researchPromises);
    const aggregatedKnowledge = results.map(r => r.text).join("\n\n---\n\n");

    // Step 3: Synthesis Phase
    // Compile all the messy search notes into the strict JSON format.
    const synthesisPrompt = `
    Review these research notes from multiple web sources regarding fault "${query}":

    ${aggregatedKnowledge.substring(0, 20000)} ... [truncated if too long]

    Based ONLY on this research:
    1. Identify the Equipment Manufacturer and Model.
    2. Define the exact Fault Code and Title.
    3. List specific Possible Causes.
    4. List Step-by-Step Solutions.
    
    Return a VALID JSON object matching this schema:
    {
        "code": "string",
        "title": "string",
        "manufacturer": "string",
        "model": "string",
        "equipmentType": "ELEVATOR" | "ESCALATOR",
        "description": "string",
        "possibleCauses": ["string"],
        "solutions": ["string"],
        "severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    }
    `;

    try {
        const finalResponse = await generateViaGateway(synthesisPrompt, "You are a Technical Editor.", config, true);
        const cleanFinal = finalResponse.text.replace(/```json/g, '').replace(/```/g, '').trim();
        const data = JSON.parse(cleanFinal);

        return {
            ...data,
            id: uuidv4(),
            lastUpdated: new Date().toISOString(),
            source: `Deep Research (${config.provider})`,
            consensusRawData: [] 
        };
    } catch (e) {
        console.error("Synthesis failed", e);
        return null;
    }
};
