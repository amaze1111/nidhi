import React, { useState, useEffect, useCallback, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import 'katex/dist/katex.min.css';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { StockRecommendation, MarketOutlook, GroundingSource, TickerInfo, ChatMessage } from './types';
import { fetchDailyRecommendations, fetchRealTimeMarketData, handleMarketQuery } from './services/geminiService';
import StockCard from './components/StockCard';
import MarketTicker from './components/MarketTicker';

declare global {
  interface Window {
    Telegram: {
      WebApp: any;
    };
  }
}

const App: React.FC = () => {
  const [recommendations, setRecommendations] = useState<StockRecommendation[]>([]);
  const [outlook, setOutlook] = useState<MarketOutlook | null>(null);
  const [sources, setSources] = useState<GroundingSource[]>([]);
  const [tickers, setTickers] = useState<TickerInfo[]>([]);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [queryLoading, setQueryLoading] = useState(false);
  const [marketStatus, setMarketStatus] = useState<{ label: string, color: string }>({ label: '---', color: 'text-slate-400' });
  const [lastAnalysisDate, setLastAnalysisDate] = useState<string>('');

  const chatEndRef = useRef<HTMLDivElement>(null);

  const getMarketState = useCallback(() => {
    const d = new Date();
    const utc = d.getTime() + (d.getTimezoneOffset() * 60000);
    const ist = new Date(utc + (3600000 * 5.5));
    const day = ist.getDay();
    const hours = ist.getHours();
    const mins = ist.getMinutes();
    const timeVal = hours * 100 + mins;

    if (day === 0 || day === 6) return { label: 'CLOSED', color: 'text-rose-500' };
    if (timeVal >= 915 && timeVal <= 1530) return { label: 'LIVE', color: 'text-emerald-500' };
    return { label: 'CLOSED', color: 'text-slate-400' };
  }, []);

  useEffect(() => {
    const updateStatus = () => setMarketStatus(getMarketState());
    updateStatus();
    const interval = setInterval(updateStatus, 30000);
    return () => clearInterval(interval);
  }, [getMarketState]);

  useEffect(() => {
    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.ready();
      window.Telegram.WebApp.expand();
    }
  }, []);

  useEffect(() => {
    if (chatHistory.length > 0) {
      chatEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [chatHistory]);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [tickerData, recData] = await Promise.all([
        fetchRealTimeMarketData(['NIFTY 50', 'BANK NIFTY', 'RELIANCE', 'TCS']),
        fetchDailyRecommendations()
      ]);
      setTickers(tickerData);
      setRecommendations(recData.data.recommendations || []);
      setOutlook(recData.data.outlook);
      setSources(recData.sources);
      setLastAnalysisDate(recData.fetchedAt);

      if (!recData.data.recommendations?.length) {
        setError("Signals unavailable right now.");
      }
    } catch (error) {
      console.error(error);
      setError("Sync failed.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleAction = async (symbol: string, actionType: 'logic' | 'targets' | 'alternatives') => {
    if (queryLoading) return;
    setQueryLoading(true);
    const queryMap: Record<string, string> = {
      logic: `Analyze ${symbol} for INTRADAY trading only. Ignore long-term views. Explain 'Why' with key intraday levels, vwap, and catalysts. Use structured markdown (bullet points, bold text).`,
      targets: `Intraday targets for ${symbol}`,
      alternatives: `Intraday sector alts for ${symbol}`
    };
    const displayMap: Record<string, string> = {
      logic: `Why ${symbol}?`,
      targets: `Targets for ${symbol}`,
      alternatives: `Sector alts for ${symbol}`
    };

    const prompt = queryMap[actionType];
    const displayText = displayMap[actionType];

    setChatHistory(prev => [...prev, { role: 'user', text: displayText, timestamp: new Date().toLocaleTimeString() }]);
    try {
      const response = await handleMarketQuery(prompt);
      setChatHistory(prev => [...prev, { role: 'model', text: response, timestamp: new Date().toLocaleTimeString() }]);
    } catch {
      setChatHistory(prev => [...prev, { role: 'model', text: "Error.", timestamp: '' }]);
    } finally {
      setQueryLoading(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || queryLoading) return;
    const userQuery = query;
    setQuery('');
    setQueryLoading(true);
    setChatHistory(prev => [...prev, { role: 'user', text: userQuery, timestamp: new Date().toLocaleTimeString() }]);
    try {
      const response = await handleMarketQuery(userQuery);
      setChatHistory(prev => [...prev, { role: 'model', text: response, timestamp: new Date().toLocaleTimeString() }]);
    } catch {
      setChatHistory(prev => [...prev, { role: 'model', text: "Service error.", timestamp: '' }]);
    } finally {
      setQueryLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-white">
        <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mb-4"></div>
        <p className="text-[10px] font-black uppercase tracking-widest text-slate-300">Syncing Alpha...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-slate-50">
      {/* COMPACT STICKY HEADER */}
      <div className="sticky top-0 z-[100] bg-white border-b border-slate-100">
        <MarketTicker tickers={tickers} />
        <header className="flex justify-between items-center px-3 py-1.5">
          <div className="flex flex-col">
            <h1 className="text-[11px] font-black text-slate-900 tracking-tighter uppercase leading-none">ALPHA TRADER</h1>
            <span className="text-[7px] font-bold text-slate-400 uppercase leading-none mt-0.5">{lastAnalysisDate}</span>
          </div>
          <div className="flex gap-2 items-center">
            <span className={`text-[9px] font-black tracking-widest ${marketStatus.color}`}>{marketStatus.label}</span>
            <button onClick={loadData} className="bg-blue-600 text-white text-[8px] font-black uppercase px-2 py-1 rounded shadow-sm active:scale-95">Sync</button>
          </div>
        </header>
      </div>

      {/* MAIN CONTENT */}
      <main className="flex-1 p-2 space-y-3 pb-[180px]">
        {error && (
          <div className="bg-rose-50 border border-rose-100 rounded-lg p-2 text-center">
            <p className="text-rose-600 text-[9px] font-bold">{error}</p>
          </div>
        )}

        {outlook && !error && (
          <section className="bg-white rounded-lg p-2.5 shadow-sm border border-slate-100">
            <div className="flex items-center gap-1.5 mb-1">
              <span className="text-[10px]">📈</span>
              <h2 className="text-[9px] font-black text-slate-800 uppercase tracking-tight">Market: {outlook.sentiment}</h2>
            </div>
            <p className="text-[9px] text-slate-500 leading-tight italic">"{outlook.summary}"</p>
          </section>
        )}

        <section>
          <h3 className="text-[8px] font-black text-slate-400 uppercase tracking-[0.2em] mb-2 px-1">Top Recommendations</h3>
          {/* GRID LAYOUT: 3 Cards per row to fit everything at once */}
          <div className="grid grid-cols-3 gap-1.5">
            {recommendations.length > 0 ? (
              recommendations.map((rec, idx) => (
                <StockCard key={idx} recommendation={rec} onAction={handleAction} />
              ))
            ) : !error && (
              <div className="col-span-3 py-6 text-center bg-white rounded-lg border border-dashed border-slate-200">
                <p className="text-[9px] text-slate-400 font-bold uppercase tracking-widest">Waiting for signals...</p>
              </div>
            )}
          </div>
        </section>

        <section className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
          <div className="px-3 py-1.5 border-b border-slate-50 bg-slate-50/50 flex justify-between items-center">
            <h3 className="text-[8px] font-black text-slate-500 uppercase tracking-widest">Alpha Analyst</h3>
            {queryLoading && <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-ping"></div>}
          </div>

          <div className="p-3 flex flex-col gap-3 min-h-[120px]">
            {chatHistory.length === 0 ? (
              <div className="text-center py-6 opacity-30">
                <p className="text-[9px] text-slate-400 font-black uppercase tracking-[0.2em]">Deep-dive logic here</p>
              </div>
            ) : (
              chatHistory.map((msg, i) => (
                <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                  <div className={`max-w-[90%] rounded-xl px-3 py-2 text-[11px] leading-snug shadow-sm overflow-hidden ${msg.role === 'user'
                    ? 'bg-blue-600 text-white rounded-tr-none font-bold'
                    : 'bg-slate-50 text-slate-800 rounded-tl-none border border-slate-200'
                    }`}>
                    {msg.role === 'user' ? (
                      msg.text
                    ) : (
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm, remarkMath]}
                        rehypePlugins={[rehypeKatex]}
                        components={{
                          p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
                          strong: ({ node, ...props }) => <strong className="font-black text-slate-900" {...props} />,
                          ul: ({ node, ...props }) => <ul className="list-disc ml-4 mb-2 space-y-1" {...props} />,
                          ol: ({ node, ...props }) => <ol className="list-decimal ml-4 mb-2 space-y-1" {...props} />,
                          li: ({ node, ...props }) => <li className="pl-1" {...props} />,
                          h1: ({ node, ...props }) => <h1 className="text-[12px] font-black uppercase tracking-widest mb-2 mt-4 text-blue-600" {...props} />,
                          h2: ({ node, ...props }) => <h2 className="text-[11px] font-black uppercase tracking-wide mb-2 mt-3 text-slate-700" {...props} />,
                          h3: ({ node, ...props }) => <h3 className="text-[10px] font-bold uppercase mb-1 mt-2 text-slate-600" {...props} />,
                          table: ({ node, ...props }) => <div className="overflow-x-auto mb-2"><table className="min-w-full divide-y divide-slate-200 border border-slate-200 rounded" {...props} /></div>,
                          th: ({ node, ...props }) => <th className="px-2 py-1 bg-slate-100 text-[9px] font-bold text-slate-500 uppercase tracking-wider text-left" {...props} />,
                          td: ({ node, ...props }) => <td className="px-2 py-1 whitespace-nowrap text-[10px] text-slate-700 border-b border-slate-100" {...props} />,
                          blockquote: ({ node, ...props }) => <blockquote className="border-l-2 border-blue-500 pl-2 italic text-slate-500 my-2" {...props} />,
                          code: ({ node, ...props }) => <code className="bg-slate-100 rounded px-1 py-0.5 font-mono text-[9px] text-pink-600" {...props} />
                        }}
                      >
                        {msg.text}
                      </ReactMarkdown>
                    )}
                  </div>
                </div>
              ))
            )}
            {queryLoading && (
              <div className="flex flex-col items-start fade-in">
                <div className="bg-slate-50 text-slate-500 rounded-lg rounded-tl-none border border-slate-200 px-3 py-2 shadow-sm">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                    <span className="text-[10px] font-bold uppercase tracking-wide">Analysing...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
        </section>
      </main>

      {/* INPUT AREA */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-slate-100 p-2 pb-6 z-[110] shadow-[0_-10px_30px_rgba(0,0,0,0.05)]">
        <div className="max-w-md mx-auto">
          <form onSubmit={handleSendMessage} className="flex gap-1.5">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask for logic..."
              className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 text-[12px] font-bold outline-none placeholder:text-slate-300"
            />
            <button
              type="submit"
              disabled={queryLoading || !query.trim()}
              className="bg-blue-600 text-white px-5 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest disabled:opacity-50 active:scale-95 shadow-md shadow-blue-100"
            >
              Ask
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default App;