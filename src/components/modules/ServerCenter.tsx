import React from 'react';
import { useTerminal } from '../../context/TerminalContext';
import { Server, Cpu, Database, HardDrive, ShieldCheck, Activity } from 'lucide-react';

export const ServerCenter: React.FC = () => {
  const { metrics } = useTerminal();

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-mono text-xs p-4 space-y-4">
      <div className="flex items-center justify-between border-b border-apex-border pb-3">
        <div className="flex items-center space-x-2 font-bold text-sm text-apex-text">
          <Server className="w-5 h-5 text-apex-cyan" />
          <span>INFRASTRUCTURE MONITORING & DOCKER CLUSTER</span>
        </div>
        <div className="text-[11px] text-apex-green font-bold flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-apex-green animate-ping" /> ALL 5 DOCKER CONTAINERS HEALTHY
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-1">
          <div className="text-apex-muted text-[10px]">CPU UTILIZATION</div>
          <div className="text-2xl font-bold text-apex-cyan">{metrics.cpuUsagePct}%</div>
          <div className="text-apex-muted text-[10px]">8 Cores @ 4.2 GHz</div>
        </div>

        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-1">
          <div className="text-apex-muted text-[10px]">GPU UTILIZATION</div>
          <div className="text-2xl font-bold text-emerald-400">{metrics.gpuUsagePct}%</div>
          <div className="text-apex-muted text-[10px]">Nvidia RTX 4090 ONNX Inference</div>
        </div>

        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-1">
          <div className="text-apex-muted text-[10px]">RAM USAGE</div>
          <div className="text-2xl font-bold text-apex-text">{metrics.ramUsedGb} GB / {metrics.ramTotalGb} GB</div>
          <div className="text-apex-muted text-[10px]">DDR5 ECC Memory</div>
        </div>

        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-1">
          <div className="text-apex-muted text-[10px]">DISK STORAGE</div>
          <div className="text-2xl font-bold text-amber-400">{metrics.diskUsedGb} GB / {metrics.diskTotalGb} GB</div>
          <div className="text-apex-muted text-[10px]">NVMe PCIe 4.0 SSD</div>
        </div>
      </div>

      <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-3">
        <div className="font-bold text-apex-text text-xs">DOCKER CONTAINER ORCHESTRATION</div>
        <div className="space-y-2">
          {metrics.dockerContainers.map((c) => (
            <div key={c.name} className="flex justify-between items-center bg-apex-panel p-2.5 rounded border border-apex-border text-[11px]">
              <div className="flex items-center space-x-2">
                <span className="w-2 h-2 rounded-full bg-apex-green" />
                <span className="font-bold text-apex-text">{c.name}</span>
              </div>
              <div className="flex space-x-4 text-apex-muted">
                <span>CPU: {c.cpu}</span>
                <span>MEM: {c.mem}</span>
                <span className="text-apex-green font-bold uppercase">{c.status}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
