export interface CandleData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ma20?: number;
  ema50?: number;
  isUp: boolean;
}

export function generateCandleDataset(basePrice: number, count: number = 85): CandleData[] {
  const dataset: CandleData[] = [];
  let price = basePrice * 0.975;
  const now = new Date();

  for (let i = count; i >= 0; i--) {
    const time = new Date(now.getTime() - i * 5 * 60 * 1000);
    const timeStr = time.toTimeString().slice(0, 5);

    // Realistic random walk with slight upward bias
    const changePct = (Math.random() - 0.475) * 0.005;
    const open = Number(price.toFixed(2));
    const close = Number((open * (1 + changePct)).toFixed(2));
    const spread = Math.abs(close - open);
    const volatility = (Math.random() * 0.4 + 0.2) * (spread + open * 0.001);
    
    const high = Number((Math.max(open, close) + volatility).toFixed(2));
    const low = Number((Math.min(open, close) - volatility).toFixed(2));
    const volume = Math.floor(Math.random() * 650 + 150);

    price = close;
    dataset.push({
      time: timeStr,
      open,
      high,
      low,
      close,
      volume,
      isUp: close >= open,
    });
  }

  // Calculate Moving Averages
  for (let i = 0; i < dataset.length; i++) {
    if (i >= 19) {
      const slice = dataset.slice(i - 19, i + 1);
      const sum = slice.reduce((acc, c) => acc + c.close, 0);
      dataset[i].ma20 = Number((sum / 20).toFixed(2));
    }
    if (i >= 49) {
      const slice = dataset.slice(i - 49, i + 1);
      const sum = slice.reduce((acc, c) => acc + c.close, 0);
      dataset[i].ema50 = Number((sum / 50).toFixed(2));
    }
  }

  return dataset;
}

interface ProfessionalChartParams {
  symbol: string;
  basePrice: number;
  overlaySMC?: boolean;
  overlayAI?: boolean;
  activePosition?: {
    side: string;
    entryPrice: number;
    sl?: number;
    tp?: number;
    unrealizedPnl?: number;
  };
  candleCount?: number;
  realCandles?: CandleData[];
  zoomStart?: number;
  zoomEnd?: number;
  isInitialLoad?: boolean;
}

export function getProfessionalChartOption(params: ProfessionalChartParams) {
  const candles = (params.realCandles && params.realCandles.length > 0)
    ? params.realCandles
    : generateCandleDataset(params.basePrice, params.candleCount || 85);

  const times = candles.map(c => c.time);
  
  // ECharts Candlestick format: [open, close, lowest, highest]
  const ohlc: any[] = candles.map(c => [c.open, c.close, c.low, c.high]);

  const volumes: any[] = candles.map(c => ({
    value: c.volume,
    itemStyle: {
      color: c.isUp ? 'rgba(8, 153, 129, 0.45)' : 'rgba(242, 54, 69, 0.45)'
    }
  }));

  const ma20Data: any[] = candles.map(c => c.ma20 ?? null);
  const ema50Data: any[] = candles.map(c => c.ema50 ?? null);

  // Append 8 future time padding slots for right-margin spacing (TradingView style right margin)
  if (candles.length > 0) {
    const lastTimeStr = candles[candles.length - 1].time;
    const parts = lastTimeStr.split(':');
    let h = parseInt(parts[0] || '12', 10);
    let m = parseInt(parts[1] || '00', 10);

    for (let i = 1; i <= 8; i++) {
      m += 5;
      if (m >= 60) {
        h = (h + 1) % 24;
        m = m % 60;
      }
      const futureTime = `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
      times.push(futureTime);
      ohlc.push([null, null, null, null]);
      volumes.push({ value: null, itemStyle: { color: 'transparent' } });
      ma20Data.push(null);
      ema50Data.push(null);
    }
  }

  const markLines: any[] = [];

  if (params.activePosition) {
    let entry = params.activePosition.entryPrice;
    // Scale entry price to match current chart price if mock data is off-scale
    if (Math.abs(entry - params.basePrice) / params.basePrice > 0.15) {
      entry = params.activePosition.side === 'BUY'
        ? Number((params.basePrice * 0.992).toFixed(2))
        : Number((params.basePrice * 1.008).toFixed(2));
    }

    const isBuy = params.activePosition.side === 'BUY';
    const sl = (params.activePosition.sl && Math.abs(params.activePosition.sl - params.basePrice) / params.basePrice < 0.15)
      ? params.activePosition.sl
      : Number((entry * (isBuy ? 0.985 : 1.015)).toFixed(2));

    const tp = (params.activePosition.tp && Math.abs(params.activePosition.tp - params.basePrice) / params.basePrice < 0.15)
      ? params.activePosition.tp
      : Number((entry * (isBuy ? 1.025 : 0.975)).toFixed(2));

    markLines.push({
      name: 'ENTRY',
      yAxis: entry,
      lineStyle: { color: '#3B82F6', width: 2, type: 'solid' },
      label: { 
        formatter: ` ENTRY ${params.activePosition.side} $${entry.toLocaleString()} `, 
        position: 'insideEndTop', 
        color: '#FFFFFF', 
        fontSize: 10,
        fontWeight: 'bold',
        fontFamily: 'JetBrains Mono',
        backgroundColor: '#3B82F6',
        padding: [3, 6],
        borderRadius: 4
      }
    });

    markLines.push({
      name: 'SL',
      yAxis: sl,
      lineStyle: { color: '#EF4444', width: 1.5, type: 'dashed' },
      label: { 
        formatter: ` SL $${sl.toLocaleString()} `, 
        position: 'insideEndTop', 
        color: '#FFFFFF', 
        fontSize: 10,
        fontWeight: 'bold',
        fontFamily: 'JetBrains Mono',
        backgroundColor: '#EF4444',
        padding: [3, 6],
        borderRadius: 4
      }
    });

    markLines.push({
      name: 'TP',
      yAxis: tp,
      lineStyle: { color: '#22C55E', width: 1.5, type: 'dashed' },
      label: { 
        formatter: ` TP $${tp.toLocaleString()} `, 
        position: 'insideEndTop', 
        color: '#FFFFFF', 
        fontSize: 10,
        fontWeight: 'bold',
        fontFamily: 'JetBrains Mono',
        backgroundColor: '#22C55E',
        padding: [3, 6],
        borderRadius: 4
      }
    });
  }

  if (params.overlaySMC) {
    const highLevel = Number((params.basePrice * 1.006).toFixed(2));
    const lowLevel = Number((params.basePrice * 0.992).toFixed(2));
    markLines.push(
      {
        name: 'BOS Breakout',
        yAxis: highLevel,
        lineStyle: { color: '#00F0FF', width: 1, type: 'dashed' },
        label: { 
          formatter: 'BOS (Break of Structure)', 
          position: 'insideStartTop', 
          color: '#00F0FF', 
          fontSize: 9,
          fontFamily: 'JetBrains Mono'
        }
      },
      {
        name: 'Order Block Demand',
        yAxis: lowLevel,
        lineStyle: { color: '#089981', width: 1, type: 'solid' },
        label: { 
          formatter: 'Bullish Demand OB', 
          position: 'insideStartTop', 
          color: '#089981', 
          fontSize: 9,
          fontFamily: 'JetBrains Mono'
        }
      }
    );
  }

  return {
    backgroundColor: '#0E1217',
    animation: false,
    legend: {
      data: [params.symbol, 'MA 20', 'EMA 50', 'Volume'],
      top: 6,
      right: 20,
      textStyle: { color: '#64748B', fontSize: 10, fontFamily: 'JetBrains Mono' },
      icon: 'roundRect',
      itemWidth: 12,
      itemHeight: 6
    },
    grid: [
      { left: '48px', right: '55px', top: '32px', height: '65%' },
      { left: '48px', right: '55px', top: '77%', height: '15%' }
    ],
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        crossStyle: { color: '#4A5568', width: 1, type: 'dashed' }
      },
      backgroundColor: '#161B22',
      borderColor: '#2D3748',
      borderWidth: 1,
      padding: [8, 12],
      textStyle: { color: '#E2E8F0', fontFamily: 'JetBrains Mono', fontSize: 11 },
      formatter: (paramsArray: any[]) => {
        if (!paramsArray || paramsArray.length === 0) return '';
        const cIdx = paramsArray[0].dataIndex;
        const candle = candles[cIdx];
        if (!candle) return '';

        const color = candle.isUp ? '#089981' : '#f23645';
        const changeVal = (candle.close - candle.open).toFixed(2);
        const changePct = (((candle.close - candle.open) / candle.open) * 100).toFixed(2);

        return `
          <div style="font-family: JetBrains Mono; font-size: 11px; min-width: 220px;">
            <div style="display: flex; justify-content: space-between; font-weight: bold; color: ${color}; margin-bottom: 6px; border-b: 1px solid #2D3748; padding-bottom: 4px;">
              <span>${params.symbol} • ${candle.time}</span>
              <span>${candle.isUp ? '+' : ''}${changeVal} (${changePct}%)</span>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px; color: #94a3b8; font-size: 10px;">
              <div>Open: <strong style="color:#e2e8f0">$${candle.open.toLocaleString()}</strong></div>
              <div>Close: <strong style="color:${color}">$${candle.close.toLocaleString()}</strong></div>
              <div>High: <strong style="color:#e2e8f0">$${candle.high.toLocaleString()}</strong></div>
              <div>Low: <strong style="color:#e2e8f0">$${candle.low.toLocaleString()}</strong></div>
            </div>
            <div style="margin-top: 6px; font-size: 10px; color: #64748b; border-t: 1px solid #2D3748; padding-top: 4px;">
              Volume: <strong style="color:#cbd5e1">${candle.volume.toLocaleString()} BTC</strong>
            </div>
          </div>
        `;
      }
    },
    axisPointer: {
      link: [{ xAxisIndex: 'all' }],
      label: { backgroundColor: '#2D3748', fontSize: 10, fontFamily: 'JetBrains Mono' }
    },
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: [0, 1],
        filterMode: 'filter',
        start: params.zoomStart ?? 30,
        end: params.zoomEnd ?? 100
      },
      {
        show: true,
        type: 'slider',
        xAxisIndex: [0, 1],
        bottom: '2px',
        height: 14,
        borderColor: '#2D3748',
        backgroundColor: '#0E1217',
        fillerColor: 'rgba(59, 130, 246, 0.15)',
        handleStyle: { color: '#3B82F6', borderColor: '#60A5FA' },
        textStyle: { color: '#64748B', fontSize: 9, fontFamily: 'JetBrains Mono' },
        filterMode: 'filter',
        start: params.zoomStart ?? 30,
        end: params.zoomEnd ?? 100
      }
    ],
    xAxis: [
      {
        type: 'category',
        data: times,
        gridIndex: 0,
        axisLine: { lineStyle: { color: '#2D3748' } },
        axisTick: { show: false },
        axisLabel: { color: '#64748B', fontSize: 10, fontFamily: 'JetBrains Mono' }
      },
      {
        type: 'category',
        data: times,
        gridIndex: 1,
        axisLine: { lineStyle: { color: '#2D3748' } },
        axisTick: { show: false },
        axisLabel: { show: false }
      }
    ],
    yAxis: [
      {
        scale: true,
        gridIndex: 0,
        position: 'right',
        splitLine: { lineStyle: { color: 'rgba(45, 55, 72, 0.4)', type: 'dashed' } },
        axisLine: { lineStyle: { color: '#2D3748' } },
        axisLabel: { 
          color: '#94A3B8', 
          fontSize: 10, 
          fontFamily: 'JetBrains Mono',
          formatter: (v: number) => `$${v.toLocaleString()}`
        }
      },
      {
        scale: true,
        gridIndex: 1,
        position: 'right',
        splitLine: { show: false },
        axisLine: { show: false },
        axisLabel: { show: false }
      }
    ],
    series: [
      {
        name: params.symbol,
        type: 'candlestick',
        data: ohlc,
        barMaxWidth: 14,
        barMinWidth: 4,
        itemStyle: {
          color: '#089981',
          color0: '#F23645',
          borderColor: '#089981',
          borderColor0: '#F23645',
          borderWidth: 1.2
        },
        markLine: markLines.length > 0 ? {
          symbol: ['none', 'none'],
          data: markLines
        } : undefined
      },
      {
        name: 'MA 20',
        type: 'line',
        data: ma20Data,
        smooth: true,
        showSymbol: false,
        lineStyle: { color: '#3B82F6', width: 1.5, opacity: 0.85 }
      },
      {
        name: 'EMA 50',
        type: 'line',
        data: ema50Data,
        smooth: true,
        showSymbol: false,
        lineStyle: { color: '#F59E0B', width: 1.5, opacity: 0.85 }
      },
      {
        name: 'Volume',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumes,
        barMaxWidth: 12
      }
    ]
  };
}
