import { useState, useRef, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Send, MessageSquare, Zap, User } from 'lucide-react';
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
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
          isUser ? 'bg-sky-600' : 'bg-slate-700'
        }`}
      >
        {isUser ? <User className="w-4 h-4 text-white" /> : <Zap className="w-4 h-4 text-slate-300" />}
      </div>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-sky-600 text-white rounded-tr-sm'
            : 'bg-slate-800 border border-slate-700 text-slate-100 rounded-tl-sm'
        }`}
      >
        {isUser ? (
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="text-sm leading-relaxed prose prose-invert prose-sm max-w-none prose-p:my-2 prose-headings:my-2 prose-ul:my-2 prose-ol:my-2 prose-li:my-0.5 prose-table:my-2">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}
        <p className={`text-xs mt-1.5 ${isUser ? 'text-sky-200' : 'text-slate-500'}`}>
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0">
        <Zap className="w-4 h-4 text-slate-300" />
      </div>
      <div className="bg-slate-800 border border-slate-700 rounded-2xl rounded-tl-sm px-4 py-3">
        <div className="flex gap-1.5 items-center h-5">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="w-2 h-2 rounded-full bg-slate-500 animate-bounce"
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
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <div className="flex-shrink-0 mb-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-sky-500 flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-100">LogiSight Copilot</h1>
            <p className="text-sm text-slate-400">Natural language queries over your normalised freight data</p>
          </div>
          <div className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-emerald-800 bg-emerald-950/40">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs text-emerald-400 font-medium">GPT-4o-mini</span>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-4 pr-1 mb-4 min-h-0">
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        {mutation.isPending && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {messages.length <= 1 && (
        <div className="flex-shrink-0 mb-4">
          <p className="text-xs text-slate-500 mb-2 flex items-center gap-1.5">
            <MessageSquare className="w-3.5 h-3.5" /> Suggested queries
          </p>
          <div className="flex flex-wrap gap-2">
            {STARTERS.map((s) => (
              <button
                key={s}
                onClick={() => send(s)}
                disabled={mutation.isPending}
                className="px-3 py-1.5 rounded-full border border-slate-700 bg-slate-800/60 text-slate-300 text-xs hover:border-sky-700 hover:text-sky-300 transition-colors disabled:opacity-40"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex-shrink-0 border-t border-slate-800 pt-4">
        <div className="flex gap-3 items-end">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={mutation.isPending}
              className="w-full px-4 py-3 pr-12 rounded-xl border border-slate-700 bg-slate-800/60 text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent resize-none transition-shadow disabled:opacity-50"
              placeholder="Ask about your freight data… (Enter to send, Shift+Enter for new line)"
              style={{ minHeight: '48px', maxHeight: '120px' }}
            />
          </div>
          <button
            onClick={() => send()}
            disabled={!input.trim() || mutation.isPending}
            className="w-11 h-11 rounded-xl bg-sky-500 hover:bg-sky-400 disabled:opacity-40 disabled:cursor-not-allowed text-white flex items-center justify-center transition-colors flex-shrink-0"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-xs text-slate-600 mt-2 text-center">
          Queries are scoped strictly to your company data. No cross-tenant access.
        </p>
      </div>
    </div>
  );
}
