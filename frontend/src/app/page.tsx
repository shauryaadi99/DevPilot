"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  fetchHealth,
  testGroqConnection,
  type HealthResponse,
  type GroqTestResult,
} from "@/lib/api";
import {
  Database,
  Cpu,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  Server,
  Zap,
  Clock,
  ShieldAlert,
} from "@/components/ui/Icons";

export default function WorkspacePage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [testingGroq, setTestingGroq] = useState<boolean>(false);
  const [groqTestResult, setGroqTestResult] = useState<GroqTestResult | null>(null);

  const loadHealthData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchHealth();
      setHealth(data);
    } catch (err: any) {
      console.error("Health check error:", err);
      setError(err?.message || "Failed to contact backend API server.");
    } finally {
      setLoading(false);
    }
  };

  const handleTestGroq = async () => {
    try {
      setTestingGroq(true);
      setGroqTestResult(null);
      const result = await testGroqConnection();
      setGroqTestResult(result);
    } catch (err: any) {
      setGroqTestResult({
        configured: false,
        status: "error",
        provider: "groq",
        model: "unknown",
        message: err?.message || "Groq connection test failed.",
      });
    } finally {
      setTestingGroq(false);
    }
  };

  useEffect(() => {
    loadHealthData();
  }, []);

  const backendOnline = !error && health !== null;

  return (
    <div className="min-h-screen flex flex-col bg-[#090d16] text-gray-100">
      <Header backendOnline={backendOnline} />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar />

        <main className="flex-1 overflow-y-auto p-6 md:p-8 space-y-6">
          {/* Top banner / Status intro */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-gray-800">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold tracking-tight text-white">
                  Chapter 1 — Engineering Foundation
                </h1>
                <StatusBadge status="ACTIVE" label="PHASE 1 ACTIVE" />
              </div>
              <p className="text-sm text-gray-400 mt-1">
                Baseline architecture, modular backend API, database connectivity, and isolated Groq LLM integration.
              </p>
            </div>

            <button
              onClick={loadHealthData}
              disabled={loading}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-sm font-medium text-gray-200 transition-colors border border-gray-700 disabled:opacity-50 w-fit"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
              Refresh Diagnostics
            </button>
          </div>

          {/* Error Banner if Backend is down */}
          {error && (
            <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 flex items-start gap-3">
              <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-rose-300">Backend Communication Failure</h3>
                <p className="text-xs text-rose-300/80 mt-1">{error}</p>
                <p className="text-xs text-gray-400 mt-2 font-mono">
                  Make sure FastAPI is running:{" "}
                  <code className="text-gray-200 bg-gray-900 px-1.5 py-0.5 rounded">
                    uvicorn app.main:app --reload --port 8000
                  </code>
                </p>
              </div>
            </div>
          )}

          {/* 3 Core Status Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* 1. Backend Service */}
            <div className="p-5 rounded-xl bg-gray-900/60 border border-gray-800 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-gray-400">
                  <Server className="w-4 h-4 text-blue-400" />
                  <span className="text-xs font-semibold uppercase tracking-wider">FastAPI Backend</span>
                </div>
                <StatusBadge
                  status={backendOnline ? health?.status || "healthy" : "disconnected"}
                />
              </div>

              <div>
                <div className="text-lg font-semibold text-white">
                  {backendOnline ? `FastAPI v${health?.version}` : "Unavailable"}
                </div>
                <p className="text-xs text-gray-400 mt-0.5">
                  Environment: <span className="font-mono text-gray-300">{health?.environment || "development"}</span>
                </p>
              </div>

              <div className="pt-2 border-t border-gray-800/80 flex items-center justify-between text-xs text-gray-400">
                <span className="flex items-center gap-1 font-mono">
                  <Clock className="w-3.5 h-3.5 text-gray-500" />
                  {health ? new Date(health.timestamp).toLocaleTimeString() : "--:--:--"}
                </span>
                <span className="text-emerald-400">CORS Allowed</span>
              </div>
            </div>

            {/* 2. Database Engine */}
            <div className="p-5 rounded-xl bg-gray-900/60 border border-gray-800 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-gray-400">
                  <Database className="w-4 h-4 text-emerald-400" />
                  <span className="text-xs font-semibold uppercase tracking-wider">Database Layer</span>
                </div>
                <StatusBadge
                  status={health?.components.database.status || (backendOnline ? "connected" : "disconnected")}
                />
              </div>

              <div>
                <div className="text-lg font-semibold text-white capitalize">
                  {health?.components.database.engine || "SQLite"}
                </div>
                <p className="text-xs text-gray-400 mt-0.5">
                  ORM: <span className="text-gray-300">SQLAlchemy 2.0 (Alembic)</span>
                </p>
              </div>

              <div className="pt-2 border-t border-gray-800/80 text-xs text-gray-400 flex items-center justify-between">
                <span>Migration State: Active</span>
                <span className="text-emerald-400">Local Free-First</span>
              </div>
            </div>

            {/* 3. Groq LLM Integration */}
            <div className="p-5 rounded-xl bg-gray-900/60 border border-gray-800 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-gray-400">
                  <Cpu className="w-4 h-4 text-amber-400" />
                  <span className="text-xs font-semibold uppercase tracking-wider">Groq LLM Base</span>
                </div>
                <StatusBadge
                  status={
                    health?.components.llm.configured
                      ? "connected"
                      : "not_configured"
                  }
                  label={
                    health?.components.llm.configured
                      ? "CONFIGURED"
                      : "API KEY MISSING"
                  }
                />
              </div>

              <div>
                <div className="text-lg font-semibold text-white truncate">
                  {health?.components.llm.model || "llama-3.3-70b-versatile"}
                </div>
                <p className="text-xs text-gray-400 mt-0.5">
                  Provider: <span className="text-gray-300 font-mono">Groq Cloud (Free Tier)</span>
                </p>
              </div>

              <div className="pt-2 border-t border-gray-800/80 flex items-center justify-between text-xs">
                <span className="text-gray-400">Credentials: Isolated</span>
                <button
                  onClick={handleTestGroq}
                  disabled={testingGroq || !backendOnline}
                  className="text-blue-400 hover:text-blue-300 font-medium inline-flex items-center gap-1 disabled:opacity-50"
                >
                  <Zap className={`w-3.5 h-3.5 ${testingGroq ? "animate-pulse" : ""}`} />
                  {testingGroq ? "Testing..." : "Test Connection"}
                </button>
              </div>
            </div>
          </div>

          {/* Groq Live Test Feedback */}
          {groqTestResult && (
            <div
              className={`p-4 rounded-xl border text-sm flex items-start gap-3 ${
                groqTestResult.status === "connected"
                  ? "bg-emerald-950/40 border-emerald-800/60 text-emerald-200"
                  : groqTestResult.status === "not_configured"
                  ? "bg-amber-950/40 border-amber-800/60 text-amber-200"
                  : "bg-rose-950/40 border-rose-800/60 text-rose-200"
              }`}
            >
              {groqTestResult.status === "connected" ? (
                <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              )}
              <div className="flex-1">
                <div className="font-semibold capitalize flex items-center gap-2">
                  <span>Groq Status: {groqTestResult.status}</span>
                  <span className="text-xs font-mono opacity-75">({groqTestResult.model})</span>
                </div>
                <p className="text-xs opacity-90 mt-1">{groqTestResult.message}</p>
              </div>
            </div>
          )}

          {/* Chapter 1 Acceptance Criteria Checklist */}
          <div className="p-6 rounded-xl bg-gray-900/40 border border-gray-800 space-y-4">
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-blue-400" />
              Chapter 1 Deliverables & Acceptance Checklist
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-gray-900/80 border border-gray-800">
                <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                <span className="text-gray-300">Clean modular directory structure & Git repo initialized</span>
              </div>
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-gray-900/80 border border-gray-800">
                <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                <span className="text-gray-300">FastAPI backend running with CORS & structured logging</span>
              </div>
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-gray-900/80 border border-gray-800">
                <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                <span className="text-gray-300">Next.js App Router workspace shell communicating with backend</span>
              </div>
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-gray-900/80 border border-gray-800">
                <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                <span className="text-gray-300">SQLAlchemy 2.0 ORM + Alembic migrations verified</span>
              </div>
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-gray-900/80 border border-gray-800">
                <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                <span className="text-gray-300">Isolated Groq LLM module with secret sanitization</span>
              </div>
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-gray-900/80 border border-gray-800">
                <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                <span className="text-gray-300">Full backend unit test suite passing (pytest)</span>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
