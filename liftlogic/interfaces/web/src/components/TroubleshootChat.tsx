import React, { useState, useRef, useEffect } from 'react';
import { FaultRecord, ChatMessage } from '../types';
import { streamTroubleshootingHelp } from '../services/geminiService';
import { Send, Bot, User, X, AlertCircle } from 'lucide-react';

interface TroubleshootChatProps {
  contextRecord?: FaultRecord;
  onClose: () => void;
}

const TroubleshootChat: React.FC<TroubleshootChatProps> = ({ contextRecord, onClose }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'init',
      role: 'model',
      text: contextRecord 
        ? `I see you're working on ${contextRecord.manufacturer} fault ${contextRecord.code}. I've reviewed the standard solutions. How can I help you apply them or troubleshoot further? Please obey all safety protocols.` 
        : "I'm ready to help you troubleshoot. Describe the equipment behavior or symptoms.",
      timestamp: Date.now()
    }
  ]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      text: input,
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsStreaming(true);

    try {
      // Format history for API
      const history = messages.map(m => ({
        role: m.role,
        parts: [{ text: m.text }]
      }));

      const stream = await streamTroubleshootingHelp(history, userMsg.text, contextRecord);
      
      let fullResponse = "";
      const responseId = (Date.now() + 1).toString();
      
      // Add placeholder for AI response
      setMessages(prev => [...prev, {
        id: responseId,
        role: 'model',
        text: '',
        timestamp: Date.now()
      }]);

      for await (const chunk of stream) {
        // Use chunk.text property instead of chunk.text() method which is deprecated
        if (chunk.text) {
            fullResponse += chunk.text;
            setMessages(prev => prev.map(m => m.id === responseId ? { ...m, text: fullResponse } : m));
        }
      }

    } catch (error) {
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'model',
        text: "I encountered an error connecting to the expert system. Please try again.",
        timestamp: Date.now()
      }]);
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-industrial-800 rounded-lg border border-industrial-600 overflow-hidden shadow-2xl">
      {/* Header */}
      <div className="bg-industrial-700 p-4 flex justify-between items-center border-b border-industrial-600">
        <div className="flex items-center gap-3">
          <div className="bg-safety-500 p-1.5 rounded text-industrial-900">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-white">Field Assistant AI</h3>
            <p className="text-xs text-industrial-300">Gemini 3 Pro • Safety Mode Active</p>
          </div>
        </div>
        <button onClick={onClose} className="text-industrial-400 hover:text-white transition-colors">
          <X className="w-6 h-6" />
        </button>
      </div>

      {/* Context Banner */}
      {contextRecord && (
        <div className="bg-industrial-900/50 p-2 px-4 border-b border-industrial-700 flex items-center gap-2 text-xs text-safety-400">
          <AlertCircle className="w-3 h-3" />
          <span>Context: {contextRecord.manufacturer} Error {contextRecord.code}</span>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-lg p-3 ${
              msg.role === 'user' 
                ? 'bg-industrial-600 text-white rounded-br-none' 
                : 'bg-industrial-700 text-industrial-100 rounded-bl-none border border-industrial-600'
            }`}>
              <div className="text-sm whitespace-pre-wrap">{msg.text}</div>
            </div>
          </div>
        ))}
        {isStreaming && (
            <div className="flex justify-start">
                <div className="bg-industrial-700 p-3 rounded-lg rounded-bl-none border border-industrial-600">
                   <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-industrial-400 rounded-full animate-bounce" style={{ animationDelay: '0s'}}></div>
                        <div className="w-2 h-2 bg-industrial-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s'}}></div>
                        <div className="w-2 h-2 bg-industrial-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s'}}></div>
                   </div>
                </div>
            </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 bg-industrial-700 border-t border-industrial-600">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask about voltage readings, mechanical adjustments..."
            className="flex-1 bg-industrial-900 border border-industrial-600 rounded px-4 py-2 text-white placeholder-industrial-500 focus:outline-none focus:border-safety-500 focus:ring-1 focus:ring-safety-500"
            disabled={isStreaming}
          />
          <button
            onClick={handleSend}
            disabled={isStreaming || !input.trim()}
            className="bg-safety-500 hover:bg-safety-600 disabled:bg-industrial-600 text-industrial-900 font-bold px-4 rounded flex items-center justify-center transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default TroubleshootChat;