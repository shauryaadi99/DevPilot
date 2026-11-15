"use client";

import React from "react";
import { Terminal, ShieldCheck, Github, Lock, CheckCircle, AlertTriangle } from "@/components/ui/Icons";
import { type UserProfile, type PatStatus } from "@/lib/api";

interface HeaderProps {
  backendOnline: boolean;
  user?: UserProfile | null;
  patStatus?: PatStatus | null;
  onOpenPatModal?: () => void;
  onLogin?: () => void;
  onLogout?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  backendOnline,
  user,
  patStatus,
  onOpenPatModal,
  onLogin,
  onLogout,
}) => {
  return (
    <header className="h-16 border-b border-gray-800 bg-[#0c121e]/80 backdrop-blur sticky top-0 z-40 px-6 flex items-center justify-between">
      {/* Brand */}
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

      {/* Center / Right status elements */}
      <div className="flex items-center gap-3 text-xs font-mono">
        {/* Free-First Stack indicator */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-md bg-gray-900/80 border border-gray-800">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span className="text-gray-300">Free-First Stack</span>
        </div>

        {/* Backend Online status */}
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

        {/* PAT Status Badge (clickable to open modal) */}
        {user && onOpenPatModal && (
          <button
            type="button"
            onClick={onOpenPatModal}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md border text-xs transition-colors ${
              patStatus?.has_pat && patStatus?.is_valid
                ? "bg-emerald-950/40 border-emerald-800/60 text-emerald-300 hover:bg-emerald-950/70"
                : patStatus?.has_pat && !patStatus?.is_valid
                ? "bg-amber-950/40 border-amber-800/60 text-amber-300 hover:bg-amber-950/70"
                : "bg-gray-900/80 border-gray-700 text-gray-400 hover:text-white hover:border-gray-600"
            }`}
            title="Manage Encrypted GitHub Personal Access Token"
          >
            <Lock className="w-3.5 h-3.5" />
            <span>
              {patStatus?.has_pat && patStatus?.is_valid
                ? patStatus.pat_masked || "PAT: Active"
                : patStatus?.has_pat && !patStatus?.is_valid
                ? "PAT: Invalid"
                : "Configure PAT"}
            </span>
          </button>
        )}

        {/* User Account / Auth */}
        {user ? (
          <div className="flex items-center gap-2.5 pl-2 border-l border-gray-800">
            {user.avatar_url ? (
              <img
                src={user.avatar_url}
                alt={user.username}
                className="w-7 h-7 rounded-full border border-gray-700 object-cover"
              />
            ) : (
              <div className="w-7 h-7 rounded-full bg-blue-600/30 border border-blue-500/50 flex items-center justify-center text-blue-300 text-xs font-semibold">
                {user.username.slice(0, 2).toUpperCase()}
              </div>
            )}
            <span className="text-gray-200 font-medium hidden md:inline">{user.username}</span>
            {onLogout && (
              <button
                type="button"
                onClick={onLogout}
                className="px-2.5 py-1 rounded bg-gray-800 hover:bg-gray-700 text-[11px] text-gray-300 transition-colors"
                title="Sign out"
              >
                Logout
              </button>
            )}
          </div>
        ) : (
          onLogin && (
            <button
              type="button"
              onClick={onLogin}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-blue-600 hover:bg-blue-500 text-white font-sans text-xs font-semibold transition-colors shadow-sm"
            >
              <Github className="w-3.5 h-3.5" />
              Sign in with GitHub
            </button>
          )
        )}
      </div>
    </header>
  );
};
