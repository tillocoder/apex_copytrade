import React, { useEffect, useState } from 'react';
import { BarChart3, Clock, Calendar, Award, TrendingUp, Sparkles } from 'lucide-react';
import ReactECharts from 'echarts-for-react';
import { AnalyticsService, type PerformanceAnalyticsData } from '../../services/analyticsService';

export const AnalyticsModule: React.FC = () => {
  const [analytics, setAnalytics] = useState<PerformanceAnalyticsData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    AnalyticsService.fetchAnalyticsPerformance().then(data => {
      if (data) setAnalytics(data);
      setLoading(false);
    });
  }, []);

  const heatmapMatrix = analytics?.heatmapData || [
    [12, 25, 38, 20, 10],
    [18, 34, 45, 28, 14],
    [25, 45, 58, 32, 22],
    [42, 78, 92, 64, 38],
    [15, 32, 40, 28, 18]
  ];

  const getHeatmapChartOption = () => {
    const hours = ['08:00', '10:00', '12:00', '14:00', '16:00'];
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
    const data: [number, number, number][] = [];

    days.forEach((day, dIdx) => {
      hours.forEach((hr, hIdx) => {
        data.push([hIdx, dIdx, heatmapMatrix[dIdx][hIdx]]);
      });
    });

    return {
      backgroundColor: '#151A21',
      tooltip: { position: 'top' },
      grid: { height: '65%', top: '10%' },
      xAxis: { type: 'category', data: hours, splitArea: { show: true } },
      yAxis: { type: 'category', data: days, splitArea: { show: true } },
      visualMap: {
        min: 0,
        max: 100,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: '0%',
        inRange: { color: ['#1B222C', '#1E3A8A', '#0284C7', '#10B981'] }
      },
      series: [
        {
          name: 'Win Rate %',
          type: 'heatmap',
          data: data,
          label: { show: true, color: '#F5F7FA' },
          emphasis: {
            itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' }
          }
        }
      ]
    };
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-mono text-xs p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-apex-border pb-3">
        <div className="flex items-center space-x-2 font-bold text-sm text-apex-text">
          <BarChart3 className="w-5 h-5 text-apex-cyan" />
          <span>ADVANCED PERFORMANCE ANALYTICS & WIN RATE HEATMAP</span>
        </div>
      </div>

      {/* Dynamic Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-1 shadow-xl">
          <div className="text-apex-muted text-[10px]">BEST SESSION</div>
          <div className="text-lg font-bold text-apex-green">{analytics?.bestSession || '14:00 - 16:00 UTC'}</div>
          <div className="text-apex-muted text-[10px]">NY Open (+92% WR)</div>
        </div>

        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-1 shadow-xl">
          <div className="text-apex-muted text-[10px]">BEST DAY</div>
          <div className="text-lg font-bold text-apex-cyan">{analytics?.bestDay || 'THURSDAY & WEDNESDAY'}</div>
          <div className="text-apex-muted text-[10px]">Highest Volume Expansions</div>
        </div>

        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-1 shadow-xl">
          <div className="text-apex-muted text-[10px]">PROFIT FACTOR</div>
          <div className="text-lg font-bold text-apex-text">{analytics?.profitFactor || 1.81}</div>
          <div className="text-apex-muted text-[10px]">Average R:R = 2.85</div>
        </div>

        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-1 shadow-xl">
          <div className="text-apex-muted text-[10px]">EXPECTANCY</div>
          <div className="text-lg font-bold text-emerald-400">{analytics?.expectancy || '+$15.03 / Trade'}</div>
          <div className="text-apex-muted text-[10px]">Based on {analytics?.totalTrades || 368} Trades</div>
        </div>
      </div>

      {/* Heatmap Section */}
      <div className="flex-1 bg-apex-surface border border-apex-border rounded-lg p-4 flex flex-col shadow-xl overflow-hidden">
        <div className="font-bold text-apex-text mb-2">WIN RATE HEATMAP BY DAY & SESSION HOUR</div>
        <div className="flex-1 w-full min-h-[260px]">
          <ReactECharts option={getHeatmapChartOption()} style={{ height: '100%', width: '100%' }} />
        </div>
      </div>
    </div>
  );
};
