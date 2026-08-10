import React, { useState, useEffect } from 'react';
import { useTerminal } from '../../context/TerminalContext';
import ReactECharts from 'echarts-for-react';
import { fetchRealKlines } from '../../services/marketDataService';
import { type CandleData } from '../../utils/chartDataGenerator';
import { Play, Pause, RotateCcw, X, Sparkles, CheckCircle2, ShieldCheck } from 'lucide-react';

export const TradeReplayModal: React.FC = () => {
  const { replayModalOpen, replayPositionId, setReplayModalOpen, positions } = useTerminal();

  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState<number>(1);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [realCandles, setRealCandles] = useState<CandleData[]>([]);
  const [timeframe, setTimeframe] = useState<'M1' | 'M5' | 'M15' | 'H1'>('M5');

  const activePosition = positions.find(p => p.id === replayPositionId) || positions[0];

  // Fetch real Binance Candlestick Klines for the active position symbol
  useEffect(() => {
    if (replayModalOpen && activePosition) {
      fetchRealKlines(activePosition.symbol, timeframe, 120).then(data => {
        if (data.length > 0) {
          setRealCandles(data);
        }
      });
    }
  }, [replayModalOpen, activePosition?.symbol, timeframe]);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    if (isPlaying && activePosition && currentStepIndex < activePosition.timeline.length - 1) {
      timer = setTimeout(() => {
        setCurrentStepIndex(prev => prev + 1);
      }, 2000 / speed);
    } else if (currentStepIndex >= (activePosition?.timeline.length || 0) - 1) {
      setIsPlaying(false);
    }
    return () => clearTimeout(timer);
  }, [isPlaying, currentStepIndex, speed, activePosition]);

  if (!replayModalOpen || !activePosition) return null;

  const currentTimelineStep = activePosition.timeline[currentStepIndex] || activePosition.timeline[0];

  // Professional TradingView-Style Candlestick (OHLCV) Replay Chart Option
  const getReplayChartOption = () => {
    // Show candles up to current replay step index
    const totalCandles = realCandles.length > 0 ? realCandles.length : 60;
    const stepRatio = Math.min(1.0, (currentStepIndex + 1) / activePosition.timeline.length);
    const visibleCount = Math.max(15, Math.floor(totalCandles * stepRatio));
    
    const visibleCandles = realCandles.slice(0, visibleCount);

    const times = visibleCandles.map(c => c.time);
    const ohlc = visibleCandles.map(c => [c.open, c.close, c.low, c.high]);
    const volumes = visibleCandles.map(c => ({
      value: c.volume,
      itemStyle: {
        color: c.isUp ? 'rgba(34, 197, 94, 0.45)' : 'rgba(239, 68, 68, 0.45)'
      }
    }));

    return {
      backgroundColor: '#151A21',
      animation: true,
      animationDuration: 300,
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        backgroundColor: '#1B222C',
        borderColor: '#2C3643',
        textStyle: { color: '#F5F7FA', fontFamily: 'JetBrains Mono', fontSize: 11 }
      },
      grid: [
        { left: '6%', right: '5%', top: '10%', height: '58%' },
        { left: '6%', right: '5%', top: '72%', height: '18%' }
      ],
      xAxis: [
        {
          type: 'category',
          data: times,
          axisLine: { lineStyle: { color: '#2C3643' } },
          axisLabel: { color: '#8A99AD', fontSize: 10 }
        },
        {
          type: 'category',
          gridIndex: 1,
          data: times,
          axisLine: { lineStyle: { color: '#2C3643' } },
          axisLabel: { show: false }
        }
      ],
      yAxis: [
        {
          scale: true,
          splitLine: { lineStyle: { color: '#242D39', type: 'dashed' } },
          axisLabel: { color: '#8A99AD', fontSize: 10 }
        },
        {
          scale: true,
          gridIndex: 1,
          splitLine: { show: false },
          axisLabel: { show: false }
        }
      ],
      series: [
        {
          name: `${activePosition.symbol} Candles`,
          type: 'candlestick',
          data: ohlc,
          itemStyle: {
            color: '#22C55E',
            color0: '#EF4444',
            borderColor: '#22C55E',
            borderColor0: '#EF4444',
            borderWidth: 1.5
          },
          markLine: {
            symbol: ['none', 'none'],
            data: [
              {
                name: 'ENTRY PRICE',
                yAxis: activePosition.entryPrice,
                lineStyle: { color: '#3B82F6', type: 'solid', width: 2 },
                label: { formatter: `ENTRY $${activePosition.entryPrice}`, position: 'end', color: '#3B82F6', fontSize: 10 }
              },
              {
                name: 'STOP LOSS',
                yAxis: activePosition.sl,
                lineStyle: { color: '#EF4444', type: 'dashed', width: 1.5 },
                label: { formatter: `SL $${activePosition.sl}`, position: 'end', color: '#EF4444', fontSize: 10 }
              },
              {
                name: 'TAKE PROFIT',
                yAxis: activePosition.tp1,
                lineStyle: { color: '#22C55E', type: 'dashed', width: 1.5 },
                label: { formatter: `TP $${activePosition.tp1}`, position: 'end', color: '#22C55E', fontSize: 10 }
              }
            ]
          }
        },
        {
          name: 'Volume',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: volumes
        }
      ]
    };
  };

  return (
    <div className="fixed inset-0 bg-black/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
      <div className="bg-apex-bgSecondary border border-apex-border rounded-panel w-full max-w-5xl overflow-hidden font-mono shadow-2xl flex flex-col max-h-[92vh]">
        {/* Header */}
        <div className="p-3 bg-apex-surface border-b border-apex-border flex items-center justify-between">
          <div className="flex items-center space-x-2 font-bold text-sm text-apex-text">
            <Play className="w-4 h-4 text-apex-accent fill-apex-accent" />
            <span>TRADE ANIMATED EVENT REPLAY: {activePosition.symbol} ({activePosition.account})</span>
            <span className="bg-apex-accent/15 border border-apex-accent/40 text-apex-accent text-[10px] px-2 py-0.5 rounded font-bold">
              PROP {activePosition.leverage}X LEVERAGE
            </span>
          </div>

          <button 
            onClick={() => setReplayModalOpen(false)}
            className="p-1 rounded-md text-apex-muted hover:text-apex-text transition-apex"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-3 overflow-y-auto flex-1">
          {/* Controls Bar */}
          <div className="p-3 workstation-panel flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <button 
                onClick={() => setIsPlaying(!isPlaying)}
                className="px-3.5 py-1.5 rounded-btn bg-apex-surface hover:bg-apex-hover border border-apex-accent text-apex-accent font-bold flex items-center space-x-1.5 transition-apex"
              >
                {isPlaying ? <Pause className="w-4 h-4 fill-apex-accent" /> : <Play className="w-4 h-4 fill-apex-accent" />}
                <span>{isPlaying ? 'PAUSE' : 'PLAY'}</span>
              </button>

              <button 
                onClick={() => { setIsPlaying(false); setCurrentStepIndex(0); }}
                className="p-1.5 rounded-btn bg-apex-surface hover:bg-apex-hover border border-apex-border text-apex-muted hover:text-apex-text transition-apex"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            </div>

            {/* Timeframe Selector */}
            <div className="flex items-center space-x-1.5">
              <span className="text-[11px] text-apex-muted font-bold">TIMEFRAME:</span>
              {(['M1', 'M5', 'M15', 'H1'] as const).map((tf) => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`px-2 py-0.5 rounded text-[10px] font-bold transition-apex ${
                    timeframe === tf ? 'bg-apex-hover text-apex-accent border border-apex-border' : 'text-apex-muted hover:text-apex-text'
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>

            {/* Speed Selection (1x, 2x, 5x, 10x) */}
            <div className="flex items-center space-x-1.5">
              <span className="text-[11px] text-apex-muted font-bold">SPEED:</span>
              {[1, 2, 5, 10].map((s) => (
                <button
                  key={s}
                  onClick={() => setSpeed(s)}
                  className={`px-2 py-0.5 rounded text-[11px] font-bold transition-apex ${
                    speed === s ? 'bg-apex-hover text-apex-accent border border-apex-border' : 'text-apex-muted hover:text-apex-text'
                  }`}
                >
                  {s}X
                </button>
              ))}
            </div>
          </div>

          {/* Real TradingView Candlestick Replay Chart */}
          <div className="h-80 workstation-panel overflow-hidden relative">
            <ReactECharts option={getReplayChartOption()} style={{ height: '100%', width: '100%' }} />
          </div>

          {/* Current Step Event Inspector */}
          <div className="workstation-panel p-3.5 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-apex-muted font-bold">REPLAY EVENT STEP {currentStepIndex + 1} OF {activePosition.timeline.length}</span>
              <span className="text-apex-accent font-bold">[{currentTimelineStep.timestamp}]</span>
            </div>

            <div className="font-bold text-sm text-apex-text">{currentTimelineStep.title}</div>
            <div className="text-apex-textSecondary text-xs leading-relaxed font-sans">{currentTimelineStep.reason}</div>

            <div className="pt-2 border-t border-apex-border grid grid-cols-3 gap-2 text-[11px]">
              <div><span className="text-apex-muted">TRIGGERED BY:</span> <strong className="text-apex-text">{currentTimelineStep.triggeredBy}</strong></div>
              <div><span className="text-apex-muted">RISK IMPACT:</span> <strong className="text-apex-accent">{currentTimelineStep.riskImpact}</strong></div>
              <div><span className="text-apex-muted">PROP CHALLENGE IMPACT:</span> <strong className="text-apex-success">{currentTimelineStep.challengeImpact}</strong></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
