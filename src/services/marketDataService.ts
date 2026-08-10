import type { CandleData } from '../utils/chartDataGenerator';
import type { TickerData } from '../types';

const BINANCE_REST_BASE = 'https://api.binance.com/api/v3';

// Map UI symbols (e.g. BTC/USDT) to Binance symbol (e.g. BTCUSDT)
export function toBinanceSymbol(symbol: string): string {
  return symbol.replace('/', '').toUpperCase();
}

// Map UI timeframes to Binance interval strings
export function toBinanceInterval(tf: string): string {
  const map: Record<string, string> = {
    'M1': '1m',
    'M5': '5m',
    'M15': '15m',
    'H1': '1h',
    'H4': '4h',
    'D1': '1d'
  };
  return map[tf] || '5m';
}

/**
 * Fetch REAL historical Kline / Candlestick data directly from Binance API
 */
export async function fetchRealKlines(
  symbol: string, 
  timeframe: string = 'M5', 
  limit: number = 200
): Promise<CandleData[]> {
  try {
    const binanceSymbol = toBinanceSymbol(symbol);
    const interval = toBinanceInterval(timeframe);
    const url = `${BINANCE_REST_BASE}/klines?symbol=${binanceSymbol}&interval=${interval}&limit=${limit}`;

    const res = await fetch(url);
    if (!res.ok) {
      throw new Error(`Binance API error: ${res.statusText}`);
    }

    const rawData: Array<any> = await res.json();

    const candles: CandleData[] = rawData.map((d: any) => {
      const openTime = new Date(d[0]);
      const timeStr = openTime.toTimeString().slice(0, 5);
      const open = parseFloat(d[1]);
      const high = parseFloat(d[2]);
      const low = parseFloat(d[3]);
      const close = parseFloat(d[4]);
      const volume = Math.round(parseFloat(d[5]));

      return {
        time: timeStr,
        open,
        high,
        low,
        close,
        volume,
        isUp: close >= open
      };
    });

    // Calculate Moving Averages on REAL data
    for (let i = 0; i < candles.length; i++) {
      if (i >= 19) {
        const slice = candles.slice(i - 19, i + 1);
        const sum = slice.reduce((acc, c) => acc + c.close, 0);
        candles[i].ma20 = Number((sum / 20).toFixed(2));
      }
      if (i >= 49) {
        const slice = candles.slice(i - 49, i + 1);
        const sum = slice.reduce((acc, c) => acc + c.close, 0);
        candles[i].ema50 = Number((sum / 50).toFixed(2));
      }
    }

    return candles;
  } catch (error) {
    console.error(`Failed to fetch real klines for ${symbol}:`, error);
    return [];
  }
}

/**
 * Fetch REAL 24hr Ticker data from Binance API
 */
export async function fetchReal24hTickers(): Promise<Partial<TickerData>[]> {
  try {
    const targetSymbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'AVAXUSDT', 'LINKUSDT', 'XRPUSDT'];
    const res = await fetch(`${BINANCE_REST_BASE}/ticker/24hr`);
    if (!res.ok) throw new Error(`Binance ticker fetch failed`);

    const allTickers: Array<any> = await res.json();
    const filtered = allTickers.filter((t: any) => targetSymbols.includes(t.symbol));

    return filtered.map((t: any) => {
      const formattedSymbol = t.symbol.replace('USDT', '/USDT');
      return {
        symbol: formattedSymbol,
        price: parseFloat(t.lastPrice),
        change24h: parseFloat(parseFloat(t.priceChangePercent).toFixed(2)),
        high24h: parseFloat(t.highPrice),
        low24h: parseFloat(t.lowPrice),
        volume24h: parseFloat(t.quoteVolume)
      };
    });
  } catch (error) {
    console.error('Failed to fetch real 24h tickers:', error);
    return [];
  }
}

/**
 * Real-time Binance WebSocket Stream for Mini Tickers
 */
export function subscribeBinanceLivePrices(
  onTick: (symbol: string, price: number, change24h: number) => void
): () => void {
  const ws = new WebSocket('wss://stream.binance.com:9443/ws/!miniTicker@arr');

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (Array.isArray(data)) {
        data.forEach((item: any) => {
          if (item.s && item.s.endsWith('USDT')) {
            const symbol = item.s.replace('USDT', '/USDT');
            const price = parseFloat(item.c);
            const open = parseFloat(item.o);
            const change24h = parseFloat((((price - open) / open) * 100).toFixed(2));
            onTick(symbol, price, change24h);
          }
        });
      }
    } catch (err) {
      console.error('Error parsing Binance live WS tick:', err);
    }
  };

  ws.onerror = (err) => {
    console.warn('Binance WebSocket error:', err);
  };

  return () => {
    if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
      ws.close();
    }
  };
}

/**
 * Dynamically update the active candle with sub-second live price tick (TradingView 1:1 style)
 */
export function updateCandlesWithLiveTick(
  candles: CandleData[],
  symbol: string,
  targetSymbol: string,
  newPrice: number
): CandleData[] {
  if (!candles || candles.length === 0 || symbol !== targetSymbol) return candles;

  const updated = [...candles];
  const lastIdx = updated.length - 1;
  const last = { ...updated[lastIdx] };

  last.close = newPrice;
  last.high = Math.max(last.high, newPrice);
  last.low = Math.min(last.low, newPrice);
  last.isUp = last.close >= last.open;

  if (updated.length >= 20) {
    const slice = updated.slice(updated.length - 20, updated.length - 1);
    const sum = slice.reduce((acc, c) => acc + c.close, 0) + last.close;
    last.ma20 = Number((sum / 20).toFixed(2));
  }

  if (updated.length >= 50) {
    const slice = updated.slice(updated.length - 50, updated.length - 1);
    const sum = slice.reduce((acc, c) => acc + c.close, 0) + last.close;
    last.ema50 = Number((sum / 50).toFixed(2));
  }

  updated[lastIdx] = last;
  return updated;
}
