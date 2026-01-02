import { GoogleGenAI, Type } from "@google/genai";
import { StockRecommendation, MarketOutlook, TickerInfo } from "../types";

const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

const RECOMMENDATION_SCHEMA = {
  type: Type.OBJECT,
  properties: {
    recommendations: {
      type: Type.ARRAY,
      items: {
        type: Type.OBJECT,
        properties: {
          symbol: { type: Type.STRING },
          companyName: { type: Type.STRING },
          type: { type: Type.STRING },
          entryPrice: { type: Type.NUMBER },
          targetPrice: { type: Type.NUMBER },
          stopLoss: { type: Type.NUMBER },
          expectedReturn: { type: Type.STRING },
          rationale: { type: Type.STRING },
          timeframe: { type: Type.STRING },
          riskLevel: { type: Type.STRING },
          telegramSignal: { type: Type.STRING },
          allocationPercent: { type: Type.NUMBER }
        },
        required: ["symbol", "companyName", "type", "entryPrice", "targetPrice", "stopLoss", "rationale", "expectedReturn", "telegramSignal", "allocationPercent"]
      }
    },
    outlook: {
      type: Type.OBJECT,
      properties: {
        sentiment: { type: Type.STRING },
        niftyLevel: { type: Type.STRING },
        bankNiftyLevel: { type: Type.STRING },
        keyEvents: { type: Type.ARRAY, items: { type: Type.STRING } },
        summary: { type: Type.STRING }
      },
      required: ["sentiment", "summary"]
    }
  },
  required: ["recommendations", "outlook"]
};

const getIST = () => {
  const d = new Date();
  const utc = d.getTime() + (d.getTimezoneOffset() * 60000);
  return new Date(utc + (3600000 * 5.5));
};

export const fetchDailyRecommendations = async (): Promise<{
  data: { recommendations: StockRecommendation[]; outlook: MarketOutlook };
  sources: any[];
  fetchedAt: string;
}> => {
  const ist = getIST();
  const todayStr = ist.toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

  // Broader search scope to ensure we get results even on weekends/early mornings
  const prompt = `SEARCH FOR RECENT NSE/BSE TRADING RECOMMENDATIONS AND TOP PICKS.
  CURRENT DATE: ${todayStr}.
  
  INSTRUCTIONS:
  1. Find 3 high-conviction intraday picks from top Indian financial news (Moneycontrol, ET, CNBC TV18).
  2. If today's picks are not yet published, use the most recent ones from the last 24-48 hours.
  3. Ensure prices are current.
  4. Suggest a capital allocation split (%) for a ₹10,000 investment across these 3 picks (total 100%).
  5. Return valid JSON following the schema.`;

  try {
    const response = await ai.models.generateContent({
      model: "gemini-3-flash-preview",
      contents: prompt,
      config: {
        tools: [{ googleSearch: {} }],
        responseMimeType: "application/json",
        responseSchema: RECOMMENDATION_SCHEMA,
      },
    });

    const result = JSON.parse(response.text || "{}");
    const sources = response.candidates?.[0]?.groundingMetadata?.groundingChunks || [];

    return { data: result, sources, fetchedAt: todayStr };
  } catch (error) {
    console.error("Gemini API Error:", error);
    throw error;
  }
};

export const handleMarketQuery = async (query: string): Promise<string> => {
  const ist = getIST();
  const prompt = `User Query: "${query}". Context: INTRADAY TRADING ONLY. Ignore long-term investment views. Current Date: ${ist.toDateString()}. 
  MANDATORY: Use Search. Focus on latest Indian Market session. Be concise.`;

  try {
    const response = await ai.models.generateContent({
      model: "gemini-3-flash-preview",
      contents: prompt,
      config: { tools: [{ googleSearch: {} }] },
    });
    return response.text || "No data found.";
  } catch (error) {
    return "Market feed error.";
  }
};

export const fetchRealTimeMarketData = async (symbols: string[]): Promise<TickerInfo[]> => {
  const prompt = `Current NSE Prices for: ${symbols.join(", ")}. Date: Today. JSON format.`;
  try {
    const response = await ai.models.generateContent({
      model: "gemini-3-flash-preview",
      contents: prompt,
      config: {
        tools: [{ googleSearch: {} }],
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.ARRAY,
          items: {
            type: Type.OBJECT,
            properties: {
              symbol: { type: Type.STRING },
              lastPrice: { type: Type.NUMBER },
              change: { type: Type.NUMBER },
              changePercent: { type: Type.NUMBER },
              volume: { type: Type.STRING },
              bid: { type: Type.NUMBER },
              ask: { type: Type.NUMBER }
            },
            required: ["symbol", "lastPrice", "change", "changePercent", "volume", "bid", "ask"]
          }
        },
      },
    });
    return JSON.parse(response.text || "[]");
  } catch {
    return [];
  }
};