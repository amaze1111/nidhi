
export interface StockRecommendation {
  symbol: string;
  companyName: string;
  type: 'BUY' | 'SELL';
  entryPrice: number;
  targetPrice: number;
  stopLoss: number;
  expectedReturn: string;
  rationale: string;
  timeframe: string;
  riskLevel: 'Low' | 'Medium' | 'High';
  telegramSignal: string; // New field for formatted telegram text
  allocationPercent: number; // Suggested allocation of total capital
}

export interface TickerInfo {
  symbol: string;
  lastPrice: number;
  change: number;
  changePercent: number;
  volume: string;
  bid: number;
  ask: number;
  lastUpdated: string;
}

export interface MarketOutlook {
  sentiment: string;
  niftyLevel: string;
  bankNiftyLevel: string;
  keyEvents: string[];
  summary: string;
}

export interface GroundingSource {
  web: {
    uri: string;
    title: string;
  };
}

export interface ChatMessage {
  role: 'user' | 'model';
  text: string;
  timestamp: string;
}
