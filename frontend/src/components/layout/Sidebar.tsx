import React from "react";
import {
  Layers,
  GitBranch,
  Cpu,
  ShieldCheck,
  Send,
  Sliders,
  FileCode,
  Check,
  FolderGit2,
  Terminal,
  FilePlus,
} from "@/components/ui/Icons";
import { ChapterStatusInfo } from "@/components/ui/ChapterProgressBar";
import { type GitHubRepo, type TaskDetail } from "@/lib/api";

interface SidebarProps {
  activeTab?: "diagnostics" | "planning" | "execution" | "qa" | "delivery" | "all";
  onTabChange?: (tab: "diagnostics" | "planning" | "execution" | "qa" | "delivery" | "all") => void;
  chapters?: ChapterStatusInfo[];
  selectedRepo?: GitHubRepo | null;
  currentTask?: TaskDetail | null;
  onStartNewProject?: () => void;
  onStartNewTask?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab = "planning",
  onTabChange,
  chapters: dynamicChapters,
  selectedRepo,
  currentTask,
  onStartNewProject,
  onStartNewTask,
}) => {
  const chapterIcons = [Layers, GitBranch, Cpu, ShieldCheck, Send];

  const defaultChapters: ChapterStatusInfo[] = [
    {
      num: 1,
      title: "Foundation & Setup",
      shortTitle: "Ch. 1 Foundation",
      desc: "FastAPI, PostgreSQL & LLM Base",
      status: "COMPLETED",
      percent: 100,
      detail: "Core API, DB & GitHub Connected",
      tab: "diagnostics",
    },
    {
      num: 2,
      title: "Repo Intelligence",
      shortTitle: "Ch. 2 Intelligence",
      desc: "Codebase Analysis & Architect Plan",
      status: "COMPLETED",
      percent: 100,
      detail: "Plan Approved by Human Reviewer",
      tab: "planning",
    },
    {
      num: 3,
      title: "Autonomous Engine",
      shortTitle: "Ch. 3 Autonomous Dev",
      desc: "Developer Agent & Git Commit",
      status: "IN_PROGRESS",
      percent: 60,
      detail: "Developer execution active",
      tab: "execution",
    },
    {
      num: 4,
      title: "QA & Code Review",
      shortTitle: "Ch. 4 QA & Review",
      desc: "Test Discovery, Feedback & Reviewer",
      status: "PENDING",
      percent: 0,
      detail: "Awaiting QA & review",
      tab: "qa",
    },
    {
      num: 5,
      title: "GitHub Delivery",
      shortTitle: "Ch. 5 Delivery",
      desc: "PR Creation & Final Audit",
      status: "PENDING",
      percent: 0,
      detail: "Awaiting delivery",
      tab: "delivery",
    },
  ];

  const chapters = dynamicChapters || defaultChapters;

  const overallPercent = Math.round(
    chapters.reduce((sum, ch) => sum + ch.percent, 0) / chapters.length
  );

  return (
    <aside className="w-64 border-r border-gray-800 bg-[#090d16] flex flex-col justify-between shrink-0 h-[calc(100vh-4rem)]">
      <div className="p-4 space-y-5 overflow-y-auto">
        {/* Active Project & Task Context Card */}
        <div className="p-3 rounded-xl bg-gray-950/80 border border-gray-800 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
              Project Context
            </span>
            {selectedRepo && onStartNewProject && (
              <button
                type="button"
                onClick={onStartNewProject}
                className="text-[10px] text-purple-400 hover:text-purple-300 font-medium transition-colors"
                title="Switch repository or start new project"
              >
                + Switch
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-blue-950/70 border border-blue-800/60 flex items-center justify-center text-blue-400 shrink-0">
              <FolderGit2 className="w-3.5 h-3.5" />
            </div>
            <div className="min-w-0 flex-1">
              <div
                className="text-xs font-semibold text-white truncate"
                title={selectedRepo?.full_name || "No Project Selected"}
              >
                {selectedRepo?.name || "No Project Selected"}
              </div>
              <div className="text-[10px] text-gray-500 font-mono truncate">
                {selectedRepo ? selectedRepo.default_branch : "Select in Ch. 2"}
              </div>
            </div>
          </div>

          {currentTask ? (
            <div className="pt-2 border-t border-gray-800/80">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                  Active Task
                </span>
                {onStartNewTask && (
                  <button
                    type="button"
                    onClick={onStartNewTask}
                    className="text-[10px] text-blue-400 hover:text-blue-300 font-medium transition-colors"
                    title="Start a new task in this repository"
                  >
                    + New Task
                  </button>
                )}
              </div>
              <div
                className="text-xs text-gray-200 font-medium truncate mt-1"
                title={currentTask.title}
              >
                {currentTask.title}
              </div>
              <div className="flex items-center gap-1.5 mt-1">
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    currentTask.is_delivered || currentTask.status === "COMPLETED"
                      ? "bg-emerald-400"
                      : currentTask.status === "APPROVED"
                      ? "bg-purple-400"
                      : "bg-blue-400"
                  }`}
                />
                <span className="text-[10px] font-mono text-gray-400">
                  {currentTask.is_delivered ? "PR Delivered" : currentTask.status}
                </span>
              </div>
            </div>
          ) : selectedRepo ? (
            <div className="pt-2 border-t border-gray-800/80">
              <div className="text-[10px] text-gray-500 italic">No task currently active</div>
              {onStartNewTask && (
                <button
                  type="button"
                  onClick={onStartNewTask}
                  className="mt-1 text-[11px] text-blue-400 hover:text-blue-300 font-semibold flex items-center gap-1 transition-colors"
                >
                  <FilePlus className="w-3 h-3" /> Start New Task
                </button>
              )}
            </div>
          ) : null}
        </div>

        <div>
          <div className="flex items-center justify-between px-2 mb-2">
            <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
              Engineering Phases
            </span>
            <span className="text-[10px] font-mono font-bold text-purple-400">
              {overallPercent}%
            </span>
          </div>

          <div className="space-y-1.5">
            {chapters.map((ch, idx) => {
              const Icon = chapterIcons[idx] || Layers;
              const isClickable = ch.tab !== undefined;
              const isActive = ch.tab === activeTab;

              // Color styles
              const barColor =
                ch.status === "COMPLETED"
                  ? "bg-emerald-500"
                  : ch.status === "FAILED"
                  ? "bg-rose-500"
                  : ch.status === "IN_PROGRESS"
                  ? "bg-gradient-to-r from-blue-500 to-purple-500"
                  : "bg-gray-700";

              return (
                <button
                  key={ch.num}
                  type="button"
                  disabled={!isClickable}
                  onClick={() => ch.tab && onTabChange && onTabChange(ch.tab)}
                  className={`w-full p-2.5 rounded-lg border text-left transition-all relative ${
                    isActive
                      ? "bg-blue-950/40 border-blue-800/60 text-white shadow-sm ring-1 ring-blue-500/30"
                      : ch.status === "COMPLETED"
                      ? "bg-emerald-950/10 border-gray-800/60 text-gray-300 hover:bg-gray-900/60"
                      : isClickable
                      ? "border-transparent text-gray-300 hover:bg-gray-900/60"
                      : "border-transparent text-gray-600 opacity-60 cursor-not-allowed"
                  }`}
                >
                  <div className="flex items-start gap-2.5">
                    <Icon
                      className={`w-4 h-4 shrink-0 mt-0.5 ${
                        isActive
                          ? "text-blue-400"
                          : ch.status === "COMPLETED"
                          ? "text-emerald-400"
                          : ch.status === "FAILED"
                          ? "text-rose-400"
                          : ch.status === "IN_PROGRESS"
                          ? "text-purple-400 animate-pulse"
                          : "text-gray-500"
                      }`}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium truncate">
                          Ch. {ch.num}: {ch.title}
                        </span>
                        <span
                          className={`text-[9px] font-mono px-1 py-0.2 rounded font-semibold ${
                            ch.status === "COMPLETED"
                              ? "bg-emerald-500/20 text-emerald-400"
                              : ch.status === "FAILED"
                              ? "bg-rose-500/20 text-rose-400"
                              : ch.status === "IN_PROGRESS"
                              ? "bg-blue-500/20 text-blue-300"
                              : "text-gray-500"
                          }`}
                        >
                          {ch.status === "COMPLETED" ? (
                            <span className="flex items-center gap-0.5">
                              <Check className="w-2.5 h-2.5" /> 100%
                            </span>
                          ) : (
                            `${ch.percent}%`
                          )}
                        </span>
                      </div>

                      <p className="text-[10px] text-gray-400 truncate mt-0.5">
                        {ch.detail || ch.desc}
                      </p>

                      {/* Mini Status Bar */}
                      <div className="w-full bg-gray-950 h-1 rounded-full overflow-hidden mt-1.5 border border-gray-800/80">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
                          style={{ width: `${Math.max(ch.percent, 2)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </button>
              );
            })}

            {/* View Full Pipeline Button */}
            <button
              type="button"
              onClick={() => onTabChange && onTabChange("all")}
              className={`w-full mt-2 p-2 rounded-lg border text-left transition-all text-xs font-semibold flex items-center justify-between ${
                activeTab === "all"
                  ? "bg-purple-950/40 border-purple-800/80 text-purple-200 ring-1 ring-purple-500/30"
                  : "border-gray-800/80 text-gray-400 hover:text-gray-200 hover:bg-gray-900/60"
              }`}
            >
              <span className="flex items-center gap-2">
                <Sliders className="w-3.5 h-3.5 text-purple-400" />
                Full Pipeline (All Chapters)
              </span>
              <span className="text-[10px] font-mono text-gray-500">All</span>
            </button>
          </div>
        </div>

        <div>
          <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider px-2">
            Workspace Resources
          </span>
          <div className="mt-2 space-y-1 text-xs">
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 px-2.5 py-2 rounded-md text-gray-400 hover:text-gray-200 hover:bg-gray-900/60"
            >
              <FileCode className="w-4 h-4 text-gray-400" />
              <span>Swagger API Docs</span>
            </a>
            <button
              onClick={() => onTabChange && onTabChange("execution")}
              className="w-full flex items-center gap-2 px-2.5 py-2 rounded-md text-gray-400 hover:text-gray-200 hover:bg-gray-900/60 text-left transition-colors"
            >
              <Sliders className="w-4 h-4 text-purple-400" />
              <span>Execution Sandbox (Ch. 3)</span>
            </button>
          </div>
        </div>
      </div>

      <div className="p-4 border-t border-gray-800 text-[11px] text-gray-500 space-y-1">
        <p>DevPilot Multi-Agent System</p>
        <p className="text-[10px] text-purple-400/90 font-medium font-mono">
          Pipeline {overallPercent}% Complete
        </p>
      </div>
    </aside>
  );
};
