import { useState, useRef, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import { copilotQuery } from '../api/client';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

const STARTERS = [
  'Which forwarder had the most anomalies this month?',
  'What is our total invoice vs quoted amount in 2026?',
  'Show all invoices with unexpected charges in Q1',
  'Which charge type has the highest average variance?',
  'Which forwarder has been most consistent with their quotes?',
  'What was our total overpayment on BAF charges last quarter?',
];

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';
  return (
    <div className={`flex gap-4 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <div
        className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm ${
          isUser ? 'bg-primary text-on-primary' : 'bg-surface-container-high text-on-surface'
        }`}
      >
        <span className="material-symbols-outlined text-[20px]">{isUser ? 'person' : 'smart_toy'}</span>
      </div>
      <div
        className={`max-w-[80%] rounded-3xl px-6 py-4 shadow-sm ${
          isUser
            ? 'bg-primary text-on-primary rounded-tr-sm'
            : 'bg-surface-container-lowest text-on-surface rounded-tl-sm border border-surface-container'
        }`}
      >
        {isUser ? (
          <p className="font-body-md text-body-md leading-relaxed whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="font-body-md text-body-md leading-relaxed prose prose-sm max-w-none prose-p:my-2 prose-headings:my-2 prose-ul:my-2 prose-ol:my-2 prose-li:my-0.5 prose-table:my-2 prose-th:bg-surface-container-low prose-td:border-b prose-td:border-surface-container">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}
        <p className={`font-label-sm text-label-sm mt-2 opacity-70 ${isUser ? 'text-on-primary' : 'text-on-surface-variant'}`}>
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex gap-4">
      <div className="w-10 h-10 rounded-full bg-surface-container-high text-on-surface flex items-center justify-center flex-shrink-0 shadow-sm">
        <span className="material-symbols-outlined text-[20px]">smart_toy</span>
      </div>
      <div className="bg-surface-container-lowest border border-surface-container rounded-3xl rounded-tl-sm px-6 py-4 shadow-sm">
        <div className="flex gap-1.5 items-center h-6">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="w-2.5 h-2.5 rounded-full bg-primary/40 animate-bounce"
              style={{ animationDelay: `${i * 150}ms` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export function Copilot() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '0',
      role: 'assistant',
      content:
        "Hello! I'm LogiSight Copilot. Ask me anything about your freight data — anomalies, cost breakdowns, forwarder performance, and more. All your data is normalised to your Charge Master, so my answers are precise.",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const mutation = useMutation({
    mutationFn: (question: string) => copilotQuery(question),
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'assistant',
          content: data.answer,
          timestamp: new Date(),
        },
      ]);
    },
    onError: () => {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'assistant',
          content: 'Sorry, I encountered an error processing your request. Please try again.',
          timestamp: new Date(),
        },
      ]);
    },
  });

  const send = (text?: string) => {
    const q = (text ?? input).trim();
    if (!q || mutation.isPending) return;
    setInput('');
    setMessages((prev) => [
      ...prev,
      { id: Date.now().toString(), role: 'user', content: q, timestamp: new Date() },
    ]);
    mutation.mutate(q);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="absolute inset-0 flex flex-col px-12 md:px-16 pt-8 pb-8 overflow-hidden bg-surface z-20">
      <div className="flex-shrink-0 mb-6">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-surface-container-lowest border border-surface-container shadow-sm flex items-center justify-center">
            <span className="material-symbols-outlined text-primary text-[24px]">smart_toy</span>
          </div>
          <div>
            <h1 className="font-display-lg-mobile text-display-lg-mobile text-on-surface tracking-tight leading-none mb-1">Copilot</h1>
            <p className="font-body-md text-body-md text-on-surface-variant">Natural language queries over your normalised freight data</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-6 pr-2 mb-4 custom-scrollbar">
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        {mutation.isPending && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {messages.length <= 1 && (
        <div className="flex-shrink-0 mb-6 bg-surface-container-lowest p-6 rounded-3xl border border-surface-container transition-all">
          <div className={`flex items-center justify-between ${showSuggestions ? 'mb-4' : ''}`}>
            <p className="font-label-sm text-label-sm text-on-surface-variant flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px]">lightbulb</span> Suggested queries
            </p>
            <button
              onClick={() => setShowSuggestions(!showSuggestions)}
              className="text-on-surface-variant hover:bg-surface-container p-1 rounded-full flex items-center justify-center transition-colors"
              title={showSuggestions ? "Hide suggestions" : "Show suggestions"}
            >
              <span className="material-symbols-outlined text-[20px]">
                {showSuggestions ? 'expand_less' : 'expand_more'}
              </span>
            </button>
          </div>
          {showSuggestions && (
            <div className="flex flex-wrap gap-2 animate-in fade-in slide-in-from-top-2 duration-300">
            {STARTERS.map((s) => (
              <button
                key={s}
                onClick={() => send(s)}
                disabled={mutation.isPending}
                className="px-4 py-2 rounded-full border border-surface-container-high bg-surface hover:bg-surface-container-high text-on-surface font-label-sm text-label-sm transition-colors disabled:opacity-40"
              >
                {s}
              </button>
            ))}
            </div>
          )}
        </div>
      )}

      <div className="flex-shrink-0 pt-2 w-full mt-auto">
        <div className="bg-surface-container-lowest rounded-3xl p-2 border border-surface-container shadow-sm focus-within:border-primary focus-within:shadow-md transition-all">
        <div className="flex gap-2 items-end">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={mutation.isPending}
              className="w-full px-4 py-3 bg-transparent text-on-surface placeholder:text-on-surface-variant font-body-md focus:outline-none resize-none transition-shadow disabled:opacity-50"
              placeholder="Ask about your freight data… (Enter to send, Shift+Enter for new line)"
              style={{ minHeight: '48px', maxHeight: '120px' }}
            />
          </div>
          <button
            onClick={() => send()}
            disabled={!input.trim() || mutation.isPending}
            className="w-12 h-12 mb-1 mr-1 rounded-2xl bg-primary hover:bg-on-surface disabled:opacity-40 disabled:bg-surface-container-highest disabled:text-on-surface-variant text-on-primary flex items-center justify-center transition-colors flex-shrink-0"
          >
            <span className="material-symbols-outlined text-[20px] ml-1">send</span>
          </button>
        </div>
      </div>
        <p className="font-label-sm text-label-sm text-on-surface-variant mt-2 mb-1 text-center">
          Queries are scoped strictly to your company data. No cross-tenant access.
        </p>
      </div>
    </div>
  );
}
