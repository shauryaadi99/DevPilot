import React from "react";
import {
  Check,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Layers,
  GitBranch,
  Cpu,
  ShieldCheck,
  Send,
} from "@/components/ui/Icons";

export interface ChapterStatusInfo {
  num: number;
  title: string;
  shortTitle: string;
  desc: string;
  status: "COMPLETED" | "IN_PROGRESS" | "PENDING" | "FAILED";
  percent: number;
  detail: string;
  tab?: "diagnostics" | "planning" | "execution" | "qa";
}

interface ChapterProgressBarProps {
  chapters: ChapterStatusInfo[];
  activeTab?: string;
  onTabChange?: (tab: "diagnostics" | "planning" | "execution" | "qa") => void;
}

export const ChapterProgressBar: React.FC<ChapterProgressBarProps> = ({
  chapters,
  activeTab,
  onTabChange,
}) => {
  const chapterIcons = [Layers, GitBranch, Cpu, ShieldCheck, Send];

  // Overall pipeline progress
  const totalPercent = Math.round(
    chapters.reduce((sum, ch) => sum + ch.percent, 0) / chapters.length
  );

  return (
    <div className="p-4 rounded-xl bg-gray-900/70 border border-gray-800 shadow-lg space-y-4">
      {/* Header with overall percentage */}
      <div className="flex items-center justify-between pb-3 border-b border-gray-800/80">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-purple-950/60 border border-purple-800/60 flex items-center justify-center text-purple-400">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
              Autonomous Engineering Pipeline Progress
            </h3>
            <p className="text-[11px] text-gray-400">
              End-to-end task progression across all 5 engineering chapters
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 font-mono">
          <div className="text-right">
            <span className="text-[10px] text-gray-400 uppercase tracking-wider block">
              Overall Pipeline
            </span>
            <span className="text-sm font-bold text-white">
              {totalPercent}%
            </span>
          </div>
          <div className="w-16 bg-gray-800 h-2 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-emerald-400 transition-all duration-500"
              style={{ width: `${totalPercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* Chapters Grid / Segmented Status Bars */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {chapters.map((ch, idx) => {
          const Icon = chapterIcons[idx] || Layers;
          const isClickable = Boolean(ch.tab && onTabChange);
          const isActive = ch.tab && activeTab === ch.tab;

          // Status colors
          const statusColors = {
            COMPLETED: {
              border: "border-emerald-800/60",
              bg: "bg-emerald-950/20",
              bar: "bg-emerald-500",
              badge: "bg-emerald-950/80 text-emerald-400 border-emerald-800/60",
              icon: "text-emerald-400",
            },
            IN_PROGRESS: {
              border: "border-blue-700/60",
              bg: "bg-blue-950/30",
              bar: "bg-gradient-to-r from-blue-500 to-cyan-400",
              badge: "bg-blue-950/80 text-blue-300 border-blue-800/60",
              icon: "text-blue-400 animate-pulse",
            },
            FAILED: {
              border: "border-rose-800/60",
              bg: "bg-rose-950/20",
              bar: "bg-rose-500",
              badge: "bg-rose-950/80 text-rose-400 border-rose-800/60",
              icon: "text-rose-400",
            },
            PENDING: {
              border: "border-gray-800/80",
              bg: "bg-gray-950/40",
              bar: "bg-gray-700",
              badge: "bg-gray-800/60 text-gray-400 border-gray-700/50",
              icon: "text-gray-500",
            },
          }[ch.status];

          return (
            <button
              key={ch.num}
              type="button"
              disabled={!isClickable}
              onClick={() => ch.tab && onTabChange && onTabChange(ch.tab)}
              className={`p-3 rounded-lg border text-left transition-all relative overflow-hidden flex flex-col justify-between ${
                statusColors.border
              } ${statusColors.bg} ${
                isActive
                  ? "ring-2 ring-purple-500/50 shadow-md"
                  : isClickable
                  ? "hover:border-gray-700 hover:bg-gray-900/60 cursor-pointer"
                  : "cursor-default"
              }`}
            >
              <div>
                {/* Chapter header */}
                <div className="flex items-center justify-between gap-1.5 mb-2">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <Icon className={`w-3.5 h-3.5 shrink-0 ${statusColors.icon}`} />
                    <span className="text-xs font-semibold text-white truncate">
                      Ch. {ch.num}
                    </span>
                  </div>

                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded border font-semibold ${statusColors.badge}`}
                  >
                    {ch.status === "COMPLETED" ? (
                      <span className="flex items-center gap-1">
                        <Check className="w-2.5 h-2.5" /> 100%
                      </span>
                    ) : (
                      `${ch.percent}%`
                    )}
                  </span>
                </div>

                <div className="text-[11px] font-medium text-gray-200 truncate">
                  {ch.title}
                </div>

                <div className="text-[10px] text-gray-400 truncate mt-0.5" title={ch.detail}>
                  {ch.detail}
                </div>
              </div>

              {/* Individual Chapter Progress Bar */}
              <div className="mt-3 pt-2 border-t border-gray-800/60">
                <div className="w-full bg-gray-950/80 h-1.5 rounded-full overflow-hidden border border-gray-800/80">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${statusColors.bar}`}
                    style={{ width: `${Math.max(ch.percent, 3)}%` }}
                  />
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};

