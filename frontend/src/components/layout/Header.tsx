import React from "react";
import { Terminal, ShieldCheck } from "@/components/ui/Icons";

interface HeaderProps {
  backendOnline: boolean;
}

export const Header: React.FC<HeaderProps> = ({ backendOnline }) => {
  return (
    <header className="h-16 border-b border-gray-800 bg-[#0c121e]/80 backdrop-blur sticky top-0 z-40 px-6 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400">
          <Terminal className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-white tracking-tight">DevPilot</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-900/60 text-blue-300 font-mono border border-blue-700/50">
              v0.1.0
            </span>
          </div>
          <p className="text-xs text-gray-400">Autonomous Software Engineering Platform</p>
        </div>
      </div>

      <div className="flex items-center gap-4 text-xs font-mono">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-gray-900/80 border border-gray-800">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span className="text-gray-300">Free-First Stack</span>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-gray-900/80 border border-gray-800">
          <span
            className={`w-2 h-2 rounded-full ${
              backendOnline ? "bg-emerald-400 animate-pulse" : "bg-rose-500"
            }`}
          />
          <span className="text-gray-300">
            Backend: {backendOnline ? "Online" : "Connecting..."}
          </span>
        </div>
      </div>
    </header>
  );
};
