import React from 'react';
import { TickerInfo } from '../types';

interface MarketTickerProps {
  tickers: TickerInfo[];
}

const MarketTicker: React.FC<MarketTickerProps> = ({ tickers }) => {
  return (
    <div className="bg-[#0f172a] text-white py-1.5 overflow-hidden whitespace-nowrap border-b border-blue-900/30">
      <div className="inline-block animate-marquee flex items-center gap-8 px-4">
        {tickers.map((ticker, idx) => (
          <div key={idx} className="flex items-center gap-1.5">
            <span className="font-black text-[9px] tracking-tight uppercase text-blue-400">{ticker.symbol}</span>
            <span className="font-mono text-[10px] font-bold">₹{ticker.lastPrice.toLocaleString('en-IN')}</span>
            <span className={`text-[9px] font-black ${ticker.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {ticker.change >= 0 ? '+' : ''}{ticker.changePercent.toFixed(2)}%
            </span>
          </div>
        ))}
        {/* Duplicate for loop */}
        {tickers.map((ticker, idx) => (
          <div key={`dup-${idx}`} className="flex items-center gap-1.5">
            <span className="font-black text-[9px] tracking-tight uppercase text-blue-400">{ticker.symbol}</span>
            <span className="font-mono text-[10px] font-bold">₹{ticker.lastPrice.toLocaleString('en-IN')}</span>
            <span className={`text-[9px] font-black ${ticker.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {ticker.change >= 0 ? '+' : ''}{ticker.changePercent.toFixed(2)}%
            </span>
          </div>
        ))}
      </div>
      <style>{`
        @keyframes marquee {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
        .animate-marquee {
          animation: marquee 20s linear infinite;
        }
      `}</style>
    </div>
  );
};

export default MarketTicker;