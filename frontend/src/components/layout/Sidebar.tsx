import React from "react";
import {
  Layers,
  GitBranch,
  Cpu,
  CheckCircle2,
  Send,
  Sliders,
  FileCode,
} from "@/components/ui/Icons";

export const Sidebar: React.FC = () => {
  const chapters = [
    {
      num: 1,
      title: "Foundation & Setup",
      active: true,
      desc: "Architecture, Backend, Frontend, DB & LLM Base",
      icon: Layers,
    },
    {
      num: 2,
      title: "Repo Intelligence",
      active: false,
      desc: "GitHub, Codebase Analysis, Architect Agent",
      icon: GitBranch,
    },
    {
      num: 3,
      title: "Autonomous Engine",
      active: false,
      desc: "Developer Agent, Isolated Sandbox, Git",
      icon: Cpu,
    },
    {
      num: 4,
      title: "QA & Code Review",
      active: false,
      desc: "QA Engineer, Tests, Reviewer Agent",
      icon: CheckCircle2,
    },
    {
      num: 5,
      title: "GitHub Delivery",
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
              return (
                <div
                  key={ch.num}
                  className={`p-2.5 rounded-lg border text-left transition-all ${
                    ch.active
                      ? "bg-blue-950/40 border-blue-800/60 text-white shadow-sm"
                      : "border-transparent text-gray-500 opacity-60 hover:opacity-80"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon
                      className={`w-4 h-4 ${
                        ch.active ? "text-blue-400" : "text-gray-500"
                      }`}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium truncate">
                          Ch. {ch.num}: {ch.title}
                        </span>
                        {ch.active && (
                          <span className="text-[10px] bg-blue-500/20 text-blue-300 px-1.5 py-0.2 rounded font-mono">
                            ACTIVE
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-gray-400 truncate mt-0.5">
                        {ch.desc}
                      </p>
                    </div>
                  </div>
                </div>
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
            <div className="flex items-center gap-2 px-2.5 py-2 rounded-md text-gray-500 cursor-not-allowed">
              <Sliders className="w-4 h-4 text-gray-500" />
              <span>Agent Settings (Ch. 2)</span>
            </div>
          </div>
        </div>
      </div>

      <div className="p-4 border-t border-gray-800 text-[11px] text-gray-500 space-y-1">
        <p>DevPilot Architecture v0.1.0</p>
        <p className="text-[10px] text-gray-600">Chapter 1 Foundation Active</p>
      </div>
    </aside>
  );
};
