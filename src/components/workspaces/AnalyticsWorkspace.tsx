import React from 'react';
import { useTerminal } from '../../context/TerminalContext';
import ReactECharts from 'echarts-for-react';
import { BarChart3, Clock, Calendar, Award } from 'lucide-react';

export const AnalyticsWorkspace: React.FC = () => {
  const { backtest } = useTerminal();

  const getHeatmapOption = () => {
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
    const hours = ['08:00', '10:00', '12:00', '14:00', '16:00', '18:00'];
    
    const data = [
      [0, 0, 12], [0, 1, 18], [0, 2, 25], [0, 3, 42], [0, 4, 15], [0, 5, 8],
      [1, 0, 15], [1, 1, 24], [1, 2, 45], [1, 3, 78], [1, 4, 32], [1, 5, 12],
      [2, 0, 22], [2, 1, 35], [2, 2, 58], [2, 3, 92], [2, 4, 40], [2, 5, 18],
      [3, 0, 10], [3, 1, 20], [3, 2, 32], [3, 3, 64], [3, 4, 28], [3, 5, 10],
      [4, 0, 8],  [4, 1, 14], [4, 2, 22], [4, 3, 38], [4, 4, 18], [4, 5, 5]
    ];

    return {
      backgroundColor: '#151A21',
      tooltip: { position: 'top' },
      grid: { height: '65%', top: '10%' },
      xAxis: { type: 'category', data: hours, axisLine: { lineStyle: { color: '#2C3643' } } },
      yAxis: { type: 'category', data: days, axisLine: { lineStyle: { color: '#2C3643' } } },
      visualMap: {
        min: 0,
        max: 100,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: '0%',
        inRange: { color: ['#1B222C', '#242D39', '#5EA8FF', '#22C55E'] },
        textStyle: { color: '#F5F7FA', fontFamily: 'JetBrains Mono', fontSize: 10 }
      },
      series: [
        {
          name: 'Win Rate %',
          type: 'heatmap',
          data: data,
          label: { show: true, color: '#F5F7FA', fontSize: 10 }
        }
      ]
    };
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-sans text-xs p-4 space-y-4">
      <div className="flex items-center justify-between border-b border-apex-border pb-3 font-mono">
        <div className="flex items-center space-x-2 font-bold text-sm text-apex-text">
          <BarChart3 className="w-5 h-5 text-apex-accent" />
          <span>ADVANCED PERFORMANCE ANALYTICS & WIN RATE HEATMAP</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 font-mono">
        <div className="workstation-panel p-4 space-y-1">
          <div className="text-apex-muted text-[10px]">BEST SESSION</div>
          <div className="text-xl font-bold text-apex-success">13:00 - 15:00 UTC</div>
          <div className="text-[10px] text-apex-muted">NY Open (+92% WR)</div>
        </div>
        <div className="workstation-panel p-4 space-y-1">
          <div className="text-apex-muted text-[10px]">BEST DAY</div>
          <div className="text-xl font-bold text-apex-accent">WEDNESDAY</div>
          <div className="text-[10px] text-apex-muted">Highest Volume Expansions</div>
        </div>
        <div className="workstation-panel p-4 space-y-1">
          <div className="text-apex-muted text-[10px]">PROFIT FACTOR</div>
          <div className="text-xl font-bold text-apex-text">{backtest.profitFactor}</div>
          <div className="text-[10px] text-apex-muted">Average R:R = 2.85</div>
        </div>
        <div className="workstation-panel p-4 space-y-1">
          <div className="text-apex-muted text-[10px]">EXPECTANCY</div>
          <div className="text-xl font-bold text-apex-success">+$420 / Trade</div>
          <div className="text-[10px] text-apex-muted">Based on 428 Trades</div>
        </div>
      </div>

      <div className="workstation-panel p-4 flex flex-col font-mono">
        <div className="font-bold text-xs text-apex-text mb-2">WIN RATE HEATMAP BY DAY & SESSION HOUR</div>
        <div className="h-64 w-full">
          <ReactECharts option={getHeatmapOption()} style={{ height: '100%', width: '100%' }} />
        </div>
      </div>
    </div>
  );
};
