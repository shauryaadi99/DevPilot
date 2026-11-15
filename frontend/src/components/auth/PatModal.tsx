"use client";

import React, { useState } from "react";
import { Lock, Unlock, CheckCircle, AlertTriangle, X, RefreshCw, Github } from "@/components/ui/Icons";
import { submitPat, type PatStatus } from "@/lib/api";

interface PatModalProps {
  isOpen: boolean;
  patStatus: PatStatus | null;
  onClose: () => void;
  onSaved: (newStatus: PatStatus) => void;
}

export const PatModal: React.FC<PatModalProps> = ({
  isOpen,
  patStatus,
  onClose,
  onSaved,
}) => {
  const [patInput, setPatInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showUpdateForm, setShowUpdateForm] = useState(false);

  if (!isOpen) return null;

  const hasExistingPat = Boolean(patStatus?.has_pat);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = patInput.trim();
    if (!token) {
      setError("Please enter a valid GitHub Personal Access Token (starts with ghp_ or github_pat_).");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const res = await submitPat(token);
      setPatInput("");
      setShowUpdateForm(false);
      onSaved({
        has_pat: true,
        is_valid: true,
        pat_masked: res.pat_masked,
        scopes: res.scopes || [],
        last_validated_at: new Date().toISOString(),
      });
      onClose();
    } catch (err: any) {
      setError(err?.message || "Failed to validate GitHub token. Check scope and permissions.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
      <div className="bg-[#0f172a] border border-gray-800 rounded-2xl max-w-lg w-full shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between bg-gray-900/50">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-blue-600/20 border border-blue-500/40 text-blue-400">
              <Lock className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">GitHub Access Token (PAT)</h3>
              <p className="text-xs text-gray-400">AES-256 Encrypted backend persistence</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800/60 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          {/* Existing PAT Status Card */}
          {hasExistingPat && !showUpdateForm ? (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-gray-950/80 border border-gray-800 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                    <span className="text-xs font-semibold text-white">Configured Personal Access Token</span>
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-950/80 border border-emerald-800/80 text-emerald-300 font-mono">
                    {patStatus?.is_valid ? "VALIDATED" : "CHECK REQUIRED"}
                  </span>
                </div>

                <div className="flex items-center justify-between bg-gray-900/60 p-2.5 rounded-lg border border-gray-800/80 text-xs font-mono">
                  <span className="text-gray-300">{patStatus?.pat_masked || "ghp_••••••••"}</span>
                  <span className="text-gray-500 text-[10px]">AES-256 Fernet</span>
                </div>

                {patStatus?.scopes && patStatus.scopes.length > 0 && (
                  <div>
                    <span className="text-[11px] text-gray-400 block mb-1 font-sans">Detected Scopes:</span>
                    <div className="flex flex-wrap gap-1">
                      {patStatus.scopes.map((s) => (
                        <span key={s} className="px-2 py-0.5 rounded bg-gray-800 text-gray-300 font-mono text-[10px]">
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  onClick={() => setShowUpdateForm(true)}
                  className="px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs font-medium text-gray-200 border border-gray-700 transition-colors"
                >
                  Replace / Update PAT
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white transition-colors"
                >
                  Use Existing PAT
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <p className="text-xs text-gray-300 leading-relaxed">
                  DevPilot requires a GitHub Personal Access Token with <code className="text-blue-400 font-mono bg-blue-950/40 px-1 py-0.5 rounded">repo</code> scope
                  to inspect repositories, clone code, and commit verified plan implementations.
                </p>
                <div className="p-3 rounded-lg bg-blue-950/20 border border-blue-800/40 text-[11px] text-blue-300 space-y-1">
                  <div className="font-semibold flex items-center gap-1.5">
                    <Github className="w-3.5 h-3.5" />
                    How to generate:
                  </div>
                  <ol className="list-decimal list-inside space-y-0.5 text-gray-300">
                    <li>Open GitHub Settings &gt; Developer Settings &gt; Personal Access Tokens (Classic)</li>
                    <li>Generate new token with <strong className="text-white">repo</strong> scope</li>
                    <li>Paste the token below. It will be encrypted in PostgreSQL and never exposed to browser storage.</li>
                  </ol>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-gray-300 block">Personal Access Token</label>
                <input
                  type="password"
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                  value={patInput}
                  onChange={(e) => setPatInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-gray-950 border border-gray-700 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 font-mono"
                  autoFocus
                />
              </div>

              {error && (
                <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/60 text-xs text-rose-300 flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

              <div className="flex items-center justify-between pt-2">
                {hasExistingPat && (
                  <button
                    type="button"
                    onClick={() => {
                      setShowUpdateForm(false);
                      setError(null);
                    }}
                    className="px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs font-medium text-gray-300 border border-gray-700 transition-colors"
                  >
                    Cancel
                  </button>
                )}
                <div className="flex items-center gap-2 ml-auto">
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-4 py-2 rounded-lg bg-transparent hover:bg-gray-800 text-xs font-medium text-gray-400 hover:text-white transition-colors"
                  >
                    Skip for Now
                  </button>
                  <button
                    type="submit"
                    disabled={loading || !patInput.trim()}
                    className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white transition-colors disabled:opacity-50 flex items-center gap-2 shadow-lg shadow-blue-900/30"
                  >
                    {loading ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        Validating with GitHub...
                      </>
                    ) : (
                      "Save & Encrypt PAT"
                    )}
                  </button>
                </div>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
