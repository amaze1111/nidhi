import React, { useState } from 'react';
import { StockRecommendation } from '../types';

interface StockCardProps {
  recommendation: StockRecommendation;
  onAction: (symbol: string, actionType: 'logic' | 'targets' | 'alternatives') => void;
}

const StockCard: React.FC<StockCardProps> = ({ recommendation, onAction }) => {
  const [viewed, setViewed] = useState(false);
  const isBuy = recommendation.type.toUpperCase() === 'BUY';

  const handleAnalysisClick = () => {
    onAction(recommendation.symbol, 'logic');
    setViewed(true);
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full">
      <div className={`h-1 w-full ${isBuy ? 'bg-emerald-500' : 'bg-rose-500'}`} />
      <div className="p-1.5 flex flex-col flex-1 justify-between gap-1">
        <div>
          <h3 className="text-[10px] font-black text-slate-900 truncate uppercase leading-tight mb-0.5">{recommendation.symbol}</h3>
          <span className={`inline-block px-1 rounded-[3px] text-[7px] font-black uppercase mb-1 ${isBuy ? 'text-emerald-600 bg-emerald-50' : 'text-rose-600 bg-rose-50'
            }`}>
            {recommendation.type}
          </span>
        </div>

        <div className="space-y-0.5">
          <div className="flex justify-between items-center text-[9px] font-bold">
            <span className="text-slate-400 text-[6px] uppercase">ENT</span>
            <span className="text-slate-800">₹{recommendation.entryPrice}</span>
          </div>
          <div className="flex justify-between items-center text-[9px] font-bold">
            <span className="text-slate-400 text-[6px] uppercase">TGT</span>
            <span className="text-emerald-600">₹{recommendation.targetPrice}</span>
          </div>
        </div>

        {recommendation.allocationPercent && (
          <div className="bg-slate-50 border border-slate-100 rounded p-1.5 my-1">
            <div className="flex justify-between items-center text-[7px] text-slate-400 font-bold uppercase tracking-wider mb-1">
              <span>Alloc: {recommendation.allocationPercent}%</span>
              <span>Est. Gain</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[9px] font-black text-slate-800">
                ₹{(10000 * recommendation.allocationPercent / 100).toLocaleString('en-IN')}
              </span>
              <span className="text-[10px] font-black text-emerald-600">
                +₹{((recommendation.targetPrice - recommendation.entryPrice) * (10000 * recommendation.allocationPercent / 100 / recommendation.entryPrice)).toFixed(0)}
              </span>
            </div>
          </div>
        )}

        <div className="mt-auto">
          <button
            onClick={handleAnalysisClick}
            className={`w-full py-1.5 rounded text-[9px] font-bold uppercase tracking-wider shadow-sm transition-colors ${viewed
                ? 'bg-slate-800 text-slate-200'
                : 'bg-blue-600 text-white hover:bg-blue-700 active:scale-95'
              }`}
          >
            {viewed ? 'Viewed' : 'View Analysis'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default StockCard;