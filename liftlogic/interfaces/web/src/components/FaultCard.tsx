import React, { useState } from 'react';
import { FaultRecord, SeverityLevel } from '../types';
import { AlertTriangle, CheckCircle, MessageSquare, Database, CloudLightning, Cpu, Wrench, User, Clock, Plus, Save, X, ShieldAlert, ShieldCheck, Loader2, ThumbsUp, Sparkles, ChevronDown, ChevronUp, Bot, Brain, Shield, Layers } from 'lucide-react';

interface FaultCardProps {
  record: FaultRecord;
  onChatRequest: (record: FaultRecord) => void;
  onAddContribution: (recordId: string, text: string) => void;
  onVoteContribution: (recordId: string, contributionId: string) => void;
}

const SeverityBadge: React.FC<{ level: string }> = ({ level }) => {
  const safeLevel = level || SeverityLevel.MEDIUM;
  
  const colors: Record<string, string> = {
    [SeverityLevel.LOW]: 'bg-blue-900/50 text-blue-200 border-blue-700',
    [SeverityLevel.MEDIUM]: 'bg-yellow-900/50 text-yellow-200 border-yellow-700',
    [SeverityLevel.HIGH]: 'bg-orange-900/50 text-orange-200 border-orange-700',
    [SeverityLevel.CRITICAL]: 'bg-red-900/50 text-red-200 border-red-700',
  };

  const activeColor = colors[safeLevel] || colors[SeverityLevel.MEDIUM];

  return (
    <span className={`px-2 py-1 rounded border text-xs font-bold tracking-wider ${activeColor}`}>
      {safeLevel} SEVERITY
    </span>
  );
};

const SourceBadge: React.FC<{ source: string }> = ({ source }) => {
  // Determine Icon and Color based on source string
  let Icon = Bot;
  let colorClass = "text-industrial-400";

  if (source && source.includes("GPT")) {
     Icon = Brain;
     colorClass = "text-green-400";
  } else if (source && source.includes("Claude")) {
     Icon = Shield;
     colorClass = "text-purple-400";
  } else if (source && source.includes("Gemini")) {
     Icon = Sparkles;
     colorClass = "text-blue-400";
  } else if (source && source.includes("Consensus")) {
     Icon = Layers;
     colorClass = "text-blue-200";
  } else if (source && source.includes("CACHE")) {
     Icon = Database;
     colorClass = "text-industrial-400";
  }

  return (
    <div className={`flex items-center gap-1 text-xs font-bold ${colorClass}`}>
       <Icon className="w-3 h-3" />
       {source || "AI Model"}
    </div>
  );
}

const FaultCard: React.FC<FaultCardProps> = ({ record, onChatRequest, onAddContribution, onVoteContribution }) => {
  const [isAddingNote, setIsAddingNote] = useState(false);
  const [newNote, setNewNote] = useState('');
  const [expandedNotes, setExpandedNotes] = useState<Set<string>>(new Set());
  
  // Consensus Tab State
  // 'master' means the Consolidated View. Other strings are source names from sub-records.
  const [activeTab, setActiveTab] = useState<string>('master');

  // Helper to get the record to display based on the tab
  const getDisplayRecord = () => {
      if (!record.consensusRawData || activeTab === 'master') return record;
      return record.consensusRawData.find(r => r.source === activeTab) || record;
  };

  const displayRecord = getDisplayRecord();
  
  // Safety check in case displayRecord is somehow undefined
  if (!displayRecord) return null;

  const isConsensus = record.source === 'AI Consensus' && record.consensusRawData && record.consensusRawData.length > 0;

  const handleSubmitNote = () => {
    if (newNote.trim()) {
      onAddContribution(record.id, newNote);
      setNewNote('');
      setIsAddingNote(false);
    }
  };

  const toggleNote = (id: string) => {
    const newSet = new Set(expandedNotes);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setExpandedNotes(newSet);
  };

  // Sort contributions: Verified & Higher votes first
  const sortedContributions = [...(record.communityContributions || [])].sort((a, b) => {
    // Priority 1: Verified Status
    const aVerified = a.aiStatus === 'VERIFIED' ? 1 : 0;
    const bVerified = b.aiStatus === 'VERIFIED' ? 1 : 0;
    if (aVerified !== bVerified) return bVerified - aVerified;
    
    // Priority 2: Vote Count
    return (b.votes || 0) - (a.votes || 0);
  });

  const causes = displayRecord.possibleCauses || [];
  const solutions = displayRecord.solutions || [];

  return (
    <div className={`bg-industrial-800/50 backdrop-blur-sm border rounded-xl overflow-hidden shadow-2xl mb-6 transition-all duration-300 group ${isConsensus ? 'border-blue-500/30 shadow-blue-900/10' : 'border-industrial-700/50 hover:border-industrial-600'}`}>
      
      {/* Consensus Tabs Header (Only visible if consensus record) */}
      {isConsensus && record.consensusRawData && (
          <div className="flex border-b border-industrial-700 bg-industrial-900 overflow-x-auto">
             <button
                onClick={() => setActiveTab('master')}
                className={`flex items-center gap-2 px-4 py-3 text-xs font-bold uppercase tracking-wider transition-colors whitespace-nowrap ${activeTab === 'master' ? 'text-white bg-gradient-to-r from-industrial-800 to-industrial-700 border-t-2 border-blue-500' : 'text-industrial-500 hover:text-industrial-300 hover:bg-industrial-800'}`}
             >
                <Layers className="w-4 h-4" />
                <span>Master Analysis</span>
             </button>
             
             {record.consensusRawData.map((subRecord) => {
                 let Icon = Bot;
                 let name = subRecord.source;
                 if (name.includes("GPT")) { Icon = Brain; name = "GPT-5.1"; }
                 if (name.includes("Claude")) { Icon = Shield; name = "Claude"; }
                 if (name.includes("Gemini")) { Icon = Sparkles; name = "Gemini"; }

                 return (
                    <button
                        key={subRecord.source}
                        onClick={() => setActiveTab(subRecord.source)}
                        className={`flex items-center gap-2 px-4 py-3 text-xs font-bold uppercase tracking-wider transition-colors border-l border-industrial-800 whitespace-nowrap ${activeTab === subRecord.source ? 'text-white bg-industrial-800 border-t-2 border-industrial-400' : 'text-industrial-500 hover:text-industrial-300 hover:bg-industrial-800'}`}
                    >
                        <Icon className="w-3 h-3" />
                        <span>{name}</span>
                    </button>
                 );
             })}
          </div>
      )}

      {/* Header */}
      <div className="p-4 md:p-6 border-b border-industrial-700 bg-gradient-to-r from-industrial-800 to-industrial-700 relative">
        
        {/* Active Tab Indicator for clarity */}
        {activeTab !== 'master' && (
            <div className="absolute top-0 left-0 right-0 h-1 bg-industrial-500/30"></div>
        )}

        <div className="flex justify-between items-start">
          <div className="flex items-center gap-3">
            <div className="bg-industrial-600 p-2 rounded-md flex-shrink-0">
              <Cpu className="w-6 h-6 text-safety-400" />
            </div>
            <div>
              <h3 className="text-xl md:text-2xl font-mono font-bold text-white break-all">{displayRecord.code}</h3>
              <div className="flex flex-wrap items-center text-industrial-300 text-sm gap-1 md:gap-2">
                <span className="uppercase tracking-wide">{displayRecord.manufacturer}</span>
                {displayRecord.model && <span>• {displayRecord.model}</span>}
                <span className="hidden md:inline">• {displayRecord.equipmentType}</span>
              </div>
            </div>
          </div>
          <div className="flex flex-col items-end gap-2 flex-shrink-0">
             <SeverityBadge level={displayRecord.severity} />
             <SourceBadge source={displayRecord.source} />
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="p-4 md:p-6 space-y-6">
        
        {/* Description */}
        <div>
          <h4 className="text-industrial-300 uppercase text-xs font-bold mb-2 tracking-wider">Description</h4>
          <p className="text-industrial-100 leading-relaxed whitespace-pre-wrap text-sm md:text-base">{displayRecord.description || "No description available."}</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Causes */}
          <div className="bg-industrial-900/50 p-4 rounded border border-industrial-700/50">
            <h4 className="flex items-center gap-2 text-orange-400 uppercase text-xs font-bold mb-3 tracking-wider">
              <AlertTriangle className="w-4 h-4" /> Possible Causes
            </h4>
            <ul className="space-y-2">
              {causes.length > 0 ? (
                  causes.map((cause, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-industrial-200">
                      <span className="mt-1.5 w-1.5 h-1.5 bg-orange-500 rounded-full flex-shrink-0" />
                      {cause}
                    </li>
                  ))
              ) : (
                  <li className="text-sm text-industrial-500 italic">No specific causes listed.</li>
              )}
            </ul>
          </div>

          {/* Solutions */}
          <div className="bg-industrial-900/50 p-4 rounded border border-industrial-700/50">
            <h4 className="flex items-center gap-2 text-green-400 uppercase text-xs font-bold mb-3 tracking-wider">
              <CheckCircle className="w-4 h-4" /> Recommended Solutions
            </h4>
            <ul className="space-y-2">
              {solutions.length > 0 ? (
                  solutions.map((sol, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-industrial-200">
                      <span className="mt-1 text-green-500 font-mono text-xs flex-shrink-0">{idx + 1}.</span>
                      {sol}
                    </li>
                  ))
              ) : (
                  <li className="text-sm text-industrial-500 italic">No specific solutions listed.</li>
              )}
            </ul>
          </div>
        </div>

        {/* Community/Field Notes Section (Only show on Master to prevent fragmented comments) */}
        {activeTab === 'master' && (
        <div className="bg-industrial-700/30 p-4 rounded border border-industrial-600">
            <div className="flex items-center justify-between mb-4">
                <h4 className="flex items-center gap-2 text-blue-300 uppercase text-xs font-bold tracking-wider">
                    <Wrench className="w-4 h-4" /> Top Technician Fixes
                </h4>
                {!isAddingNote && (
                    <button 
                        onClick={() => setIsAddingNote(true)}
                        className="flex items-center gap-1 text-xs bg-industrial-700 hover:bg-blue-900/50 text-blue-200 px-2 py-1 rounded border border-industrial-500 transition-colors"
                    >
                        <Plus className="w-3 h-3" /> I solved this
                    </button>
                )}
            </div>

            <div className="space-y-3">
                {sortedContributions.length > 0 ? (
                    sortedContributions.map((note, idx) => (
                        <div 
                          key={note.id} 
                          className={`p-3 rounded border transition-all relative ${
                            note.votes > 1 
                              ? 'bg-gradient-to-r from-industrial-800 to-blue-900/20 border-blue-500/50 shadow-lg' 
                              : 'bg-industrial-800 border-industrial-600'
                          }`}
                        >
                            {/* Badge for top solution */}
                            {idx === 0 && note.votes > 0 && (
                              <div className="absolute -top-2 -right-2 bg-safety-500 text-industrial-900 text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1 shadow">
                                <Sparkles className="w-3 h-3" /> Top Fix
                              </div>
                            )}

                            <div className="flex justify-between items-start gap-3">
                                <div className="flex-1">
                                    {/* Refined Content (The "Well Constructed" part) */}
                                    {note.refinedContent ? (
                                      <div className="mb-2">
                                        <div className="flex items-center gap-2 text-xs text-green-400 font-bold mb-1 uppercase tracking-wider">
                                          <ShieldCheck className="w-3 h-3" /> Validated Procedure
                                        </div>
                                        <p className="text-sm text-white whitespace-pre-wrap">{note.refinedContent}</p>
                                        
                                        {/* Raw input toggle */}
                                        <button 
                                          onClick={() => toggleNote(note.id)}
                                          className="mt-2 text-[10px] text-industrial-400 flex items-center gap-1 hover:text-industrial-200"
                                        >
                                          {expandedNotes.has(note.id) ? <ChevronUp className="w-3 h-3"/> : <ChevronDown className="w-3 h-3"/>}
                                          {expandedNotes.has(note.id) ? "Hide original note" : "Show original technician note"}
                                        </button>
                                        
                                        {expandedNotes.has(note.id) && (
                                          <div className="mt-1 p-2 bg-industrial-900/50 rounded border border-industrial-700 text-xs text-industrial-300 italic">
                                            "{note.text}"
                                          </div>
                                        )}
                                      </div>
                                    ) : (
                                      <p className="text-sm text-industrial-100 mb-2 whitespace-pre-wrap">{note.text}</p>
                                    )}
                                    
                                    <div className="flex items-center gap-3 text-[10px] text-industrial-400">
                                        <span className="flex items-center gap-1"><User className="w-3 h-3" /> {note.author}</span>
                                        <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {new Date(note.timestamp).toLocaleDateString()}</span>
                                        {note.aiStatus === 'PENDING' && <span className="flex items-center gap-1 text-safety-400"><Loader2 className="w-3 h-3 animate-spin" /> Analyzing...</span>}
                                        {note.aiStatus === 'CAUTION' && <span className="flex items-center gap-1 text-orange-400"><ShieldAlert className="w-3 h-3" /> Caution</span>}
                                    </div>
                                </div>

                                {/* Voting Mechanism */}
                                <div className="flex flex-col items-center gap-1">
                                  <button 
                                    onClick={() => onVoteContribution(record.id, note.id)}
                                    className="group flex flex-col items-center justify-center p-2 rounded hover:bg-industrial-700 transition-colors"
                                    title="This worked for me"
                                  >
                                    <ThumbsUp className={`w-4 h-4 ${note.votes > 0 ? 'text-blue-400' : 'text-industrial-500'} group-hover:text-blue-300 transition-colors`} />
                                    <span className={`text-xs font-bold ${note.votes > 0 ? 'text-blue-400' : 'text-industrial-500'}`}>
                                      {note.votes || 0}
                                    </span>
                                  </button>
                                </div>
                            </div>
                        </div>
                    ))
                ) : (
                    <div className="text-xs text-industrial-500 italic">No field notes added yet. Be the first to share how you fixed this.</div>
                )}

                {isAddingNote && (
                    <div className="bg-industrial-800 p-3 rounded border border-industrial-500 animate-in fade-in slide-in-from-top-2">
                        <textarea 
                            value={newNote}
                            onChange={(e) => setNewNote(e.target.value)}
                            placeholder="Describe exactly what you did to fix this fault..."
                            className="w-full bg-industrial-900 border border-industrial-600 rounded p-2 text-sm text-white mb-2 focus:border-blue-500 outline-none min-h-[80px]"
                        />
                        <div className="flex justify-end gap-2">
                            <button 
                                onClick={() => setIsAddingNote(false)}
                                className="flex items-center gap-1 px-3 py-1 text-xs text-industrial-400 hover:text-white transition-colors"
                            >
                                <X className="w-3 h-3" /> Cancel
                            </button>
                            <button 
                                onClick={handleSubmitNote}
                                disabled={!newNote.trim()}
                                className="flex items-center gap-1 px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold rounded transition-colors disabled:opacity-50"
                            >
                                <Save className="w-3 h-3" /> Save Fix
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
        )}

        {/* Action Footer */}
        <div className="pt-4 border-t border-industrial-700 flex justify-end">
          <button 
            onClick={() => onChatRequest(record)}
            className="flex items-center gap-2 px-4 py-2 bg-industrial-700 hover:bg-industrial-600 text-white text-sm font-medium rounded transition-colors w-full md:w-auto justify-center"
          >
            <MessageSquare className="w-4 h-4" />
            Troubleshoot with AI
          </button>
        </div>
      </div>
    </div>
  );
};

export default FaultCard;