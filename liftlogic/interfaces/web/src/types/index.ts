
export enum EquipmentType {
  ELEVATOR = 'ELEVATOR',
  ESCALATOR = 'ESCALATOR',
  UNKNOWN = 'UNKNOWN'
}

export enum SeverityLevel {
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL'
}

export type AIProvider = 'GOOGLE' | 'OPENAI' | 'ANTHROPIC' | 'XAI';

export interface AIConfig {
  provider: AIProvider;
  model: string; 
  searchDepth: 'STANDARD' | 'DEEP'; 
  minSources: number;
  safetyMode?: string;
  // Provider Specific Credentials (Stored Locally Only)
  openaiKey?: string;
  anthropicKey?: string;
  xaiKey?: string;
}

export interface CommunityContribution {
  id: string;
  text: string; 
  refinedContent?: string; 
  author: string;
  timestamp: number;
  votes: number; 
  aiAnalysis?: string; 
  aiStatus?: 'PENDING' | 'VERIFIED' | 'CAUTION' | 'UNCERTAIN'; 
}

export interface FaultRecord {
  id: string;
  code: string;
  title: string;
  manufacturer: string;
  model?: string; 
  equipmentType: EquipmentType;
  description: string;
  possibleCauses: string[];
  solutions: string[];
  severity: SeverityLevel;
  lastUpdated: string;
  source: string; 
  communityContributions?: CommunityContribution[];
  relatedQueries?: string[]; 
  consensusRawData?: FaultRecord[]; 
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'model';
  text: string;
  timestamp: number;
}

export interface DriveUser {
  id: string;
  displayName: string;
  emailAddress: string;
  role: string;
  photoLink?: string;
  isGuest?: boolean;
}

export type ViewMode = 'SEARCH' | 'TROUBLESHOOT' | 'DATABASE' | 'ADMIN';
