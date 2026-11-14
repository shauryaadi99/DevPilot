import React from "react";
import {
  Layers,
  GitBranch,
  Cpu,
  CheckCircle2,
  Send,
  Sliders,
  FileCode,
  Check,
} from "@/components/ui/Icons";

interface SidebarProps {
  activeTab?: "diagnostics" | "planning" | "execution";
  onTabChange?: (tab: "diagnostics" | "planning" | "execution") => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab = "planning",
  onTabChange,
}) => {
  const chapters = [
    {
      num: 1,
      title: "Foundation & Setup",
      completed: true,
      active: activeTab === "diagnostics",
      desc: "Architecture, Backend, Frontend, DB & LLM Base",
      icon: Layers,
      tab: "diagnostics" as const,
    },
    {
      num: 2,
      title: "Repo Intelligence",
      completed: true,
      active: false,
      desc: "GitHub, Codebase Analysis, Architect Agent",
      icon: GitBranch,
      tab: "planning" as const,
    },
    {
      num: 3,
      title: "Autonomous Engine",
      completed: false,
      active: activeTab === "planning" || activeTab === "execution",
      desc: "Developer Agent, Isolated Sandbox, Git",
      icon: Cpu,
      tab: "execution" as const,
    },
    {
      num: 4,
      title: "QA & Code Review",
      completed: false,
      active: false,
      desc: "QA Engineer, Tests, Reviewer Agent",
      icon: CheckCircle2,
    },
    {
      num: 5,
      title: "GitHub Delivery",
      completed: false,
      active: false,
      desc: "Dashboard, PR Creation, End-to-End",
      icon: Send,
    },
  ];

  return (
    <aside className="w-64 border-r border-gray-800 bg-[#090d16] flex flex-col justify-between shrink-0 h-[calc(100vh-4rem)]">
      <div className="p-4 space-y-6 overflow-y-auto">
        <div>
          <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider px-2">
            Engineering Phases
          </span>
          <div className="mt-2 space-y-1">
            {chapters.map((ch) => {
              const Icon = ch.icon;
              const isClickable = ch.tab !== undefined;

              return (
                <button
                  key={ch.num}
                  type="button"
                  disabled={!isClickable}
                  onClick={() => ch.tab && onTabChange && onTabChange(ch.tab)}
                  className={`w-full p-2.5 rounded-lg border text-left transition-all ${
                    ch.active
                      ? "bg-blue-950/40 border-blue-800/60 text-white shadow-sm ring-1 ring-blue-500/30"
                      : ch.completed
                      ? "bg-emerald-950/10 border-gray-800/60 text-gray-300 hover:bg-gray-900/60"
                      : isClickable
                      ? "border-transparent text-gray-300 hover:bg-gray-900/60"
                      : "border-transparent text-gray-600 opacity-60 cursor-not-allowed"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon
                      className={`w-4 h-4 shrink-0 ${
                        ch.active
                          ? "text-blue-400"
                          : ch.completed
                          ? "text-emerald-400"
                          : "text-gray-500"
                      }`}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium truncate">
                          Ch. {ch.num}: {ch.title}
                        </span>
                        {ch.active ? (
                          <span className="text-[10px] bg-blue-500/20 text-blue-300 px-1.5 py-0.2 rounded font-mono">
                            ACTIVE
                          </span>
                        ) : ch.completed ? (
                          <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-1.5 py-0.2 rounded font-mono flex items-center gap-1">
                            <Check className="w-2.5 h-2.5" /> DONE
                          </span>
                        ) : null}
                      </div>
                      <p className="text-[11px] text-gray-400 truncate mt-0.5">
                        {ch.desc}
                      </p>
                    </div>
                  </div>
                </button>
              );
            })}
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
        <p className="text-[10px] text-purple-400/90 font-medium">Chapter 3 Active</p>
      </div>
    </aside>
  );
};
