"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  fetchHealth,
  testGroqConnection,
  connectGitHub,
  listUserRepositories,
  selectRepository,
  createTask,
  runTaskPipeline,
  submitPlanApproval,
  type HealthResponse,
  type GroqTestResult,
  type GitHubUser,
  type GitHubRepo,
  type TaskDetail,
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
  Github,
  FolderGit2,
  Check,
  X,
  MessageSquare,
  ArrowRight,
  Search,
  Lock,
  Unlock,
  ListChecks,
  FilePlus,
  FileEdit,
  Sparkles,
  ChevronRight,
} from "@/components/ui/Icons";

export default function WorkspacePage() {
  const [activeTab, setActiveTab] = useState<"planning" | "diagnostics">("planning");

  // Chapter 1 Diagnostics State
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loadingHealth, setLoadingHealth] = useState<boolean>(true);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [testingGroq, setTestingGroq] = useState<boolean>(false);
  const [groqTestResult, setGroqTestResult] = useState<GroqTestResult | null>(null);

  // Chapter 2 GitHub & Task State
  const [githubToken, setGithubToken] = useState<string>("");
  const [githubUser, setGithubUser] = useState<GitHubUser | null>(null);
  const [connectingGithub, setConnectingGithub] = useState<boolean>(false);
  const [githubError, setGithubError] = useState<string | null>(null);

  const [repositories, setRepositories] = useState<GitHubRepo[]>([]);
  const [loadingRepos, setLoadingRepos] = useState<boolean>(false);
  const [repoSearch, setRepoSearch] = useState<string>("");
  const [selectedRepo, setSelectedRepo] = useState<GitHubRepo | null>(null);

  // Task & Planning
  const [taskTitle, setTaskTitle] = useState<string>("Add Rate Limiting Middleware");
  const [taskRequirement, setTaskRequirement] = useState<string>(
    "Implement an in-memory rate limiting middleware for all public API endpoints to prevent request flooding, allowing 60 requests per minute per IP address."
  );
  const [currentTask, setCurrentTask] = useState<TaskDetail | null>(null);
  const [runningPipeline, setRunningPipeline] = useState<boolean>(false);
  const [pipelineError, setPipelineError] = useState<string | null>(null);

  // Approval Modal/State
  const [approvalFeedback, setApprovalFeedback] = useState<string>("");
  const [submittingApproval, setSubmittingApproval] = useState<boolean>(false);

  const loadHealthData = async () => {
    try {
      setLoadingHealth(true);
      setHealthError(null);
      const data = await fetchHealth();
      setHealth(data);
    } catch (err: any) {
      setHealthError(err?.message || "Failed to contact backend API server.");
    } finally {
      setLoadingHealth(false);
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

  const handleConnectGitHub = async () => {
    if (!githubToken.trim()) {
      setGithubError("Please enter a valid GitHub token.");
      return;
    }
    try {
      setConnectingGithub(true);
      setGithubError(null);
      const res = await connectGitHub(githubToken);
      setGithubUser(res.user);
      loadRepositories(githubToken);
    } catch (err: any) {
      setGithubError(err?.message || "GitHub authentication failed.");
    } finally {
      setConnectingGithub(false);
    }
  };

  const loadRepositories = async (token: string) => {
    try {
      setLoadingRepos(true);
      const repos = await listUserRepositories(token);
      setRepositories(repos);
    } catch (err: any) {
      setGithubError(err?.message || "Failed to list repositories.");
    } finally {
      setLoadingRepos(false);
    }
  };

  const handleSelectRepository = async (repo: GitHubRepo) => {
    try {
      setSelectedRepo(repo);
      await selectRepository(repo);
    } catch (err: any) {
      setGithubError(err?.message || "Failed to select repository.");
    }
  };

  const handleRunPipeline = async () => {
    if (!selectedRepo) {
      setPipelineError("Please connect and select a repository first.");
      return;
    }
    if (!taskRequirement.trim()) {
      setPipelineError("Please enter a software requirement.");
      return;
    }

    try {
      setRunningPipeline(true);
      setPipelineError(null);

      // 1. Create or persist repository in backend
      const repoRes = await selectRepository(selectedRepo);
      const backendRepoId = repoRes.repository.id;

      // 2. Create task
      const newTask = await createTask(backendRepoId, taskTitle, taskRequirement);

      // 3. Run full intelligence pipeline
      const taskDetail = await runTaskPipeline(newTask.id, githubToken || undefined);
      setCurrentTask(taskDetail);
    } catch (err: any) {
      console.error("Pipeline failure:", err);
      setPipelineError(err?.message || "Failed to execute planning pipeline.");
    } finally {
      setRunningPipeline(false);
    }
  };

  const handleApprovalDecision = async (decision: "APPROVED" | "REJECTED" | "CHANGES_REQUESTED") => {
    if (!currentTask) return;
    try {
      setSubmittingApproval(true);
      const result = await submitPlanApproval(currentTask.id, decision, approvalFeedback);
      // Update local task status and append approval
      setCurrentTask({
        ...currentTask,
        status: decision,
        approvals: [
          ...currentTask.approvals,
          {
            id: result.approval.id,
            decision: result.approval.decision,
            feedback: result.approval.feedback,
            decided_at: result.approval.decided_at,
          },
        ],
      });
      setApprovalFeedback("");
    } catch (err: any) {
      setPipelineError(err?.message || "Failed to submit approval.");
    } finally {
      setSubmittingApproval(false);
    }
  };

  useEffect(() => {
    loadHealthData();
  }, []);

  const backendOnline = !healthError && health !== null;

  const filteredRepos = repositories.filter(
    (r) =>
      r.name.toLowerCase().includes(repoSearch.toLowerCase()) ||
      r.full_name.toLowerCase().includes(repoSearch.toLowerCase())
  );

  return (
    <div className="min-h-screen flex flex-col bg-[#090d16] text-gray-100">
      <Header backendOnline={backendOnline} />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

        <main className="flex-1 overflow-y-auto p-6 md:p-8 space-y-6">
          {/* Chapter 2: Repo Intelligence & Planning View */}
          {activeTab === "planning" && (
            <div className="space-y-6">
              {/* Header Title */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-gray-800">
                <div>
                  <div className="flex items-center gap-2">
                    <h1 className="text-2xl font-bold tracking-tight text-white">
                      Chapter 2 — Repository Intelligence & Planning
                    </h1>
                    <StatusBadge status="ACTIVE" label="CHAPTER 2 ACTIVE" />
                  </div>
                  <p className="text-sm text-gray-400 mt-1">
                    Connect a GitHub repository, inspect codebases, and generate repository-aware implementation plans with Product Analyst & Architect Agents.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400 font-mono">Model:</span>
                  <span className="text-xs px-2.5 py-1 rounded-md bg-blue-950/60 border border-blue-800/60 text-blue-300 font-mono">
                    qwen/qwen3.8-27b
                  </span>
                </div>
              </div>

              {/* GitHub Connection Banner */}
              <div className="p-5 rounded-xl bg-gray-900/60 border border-gray-800 space-y-4">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-gray-800 border border-gray-700 flex items-center justify-center text-white">
                      <Github className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-white">GitHub Authorization</h3>
                      <p className="text-xs text-gray-400">
                        {githubUser ? (
                          <span className="text-emerald-400 flex items-center gap-1.5 mt-0.5">
                            <CheckCircle className="w-3.5 h-3.5" /> Connected as{" "}
                            <span className="font-semibold text-white">{githubUser.login}</span> ({githubUser.public_repos} repos)
                          </span>
                        ) : (
                          "Enter a Personal Access Token (PAT) with repo scope for zero-friction access."
                        )}
                      </p>
                    </div>
                  </div>

                  {!githubUser && (
                    <div className="flex items-center gap-2">
                      <input
                        type="password"
                        placeholder="ghp_xxxxxxxxxxxx"
                        value={githubToken}
                        onChange={(e) => setGithubToken(e.target.value)}
                        className="px-3 py-1.5 rounded-lg bg-gray-950 border border-gray-700 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 w-64 font-mono"
                      />
                      <button
                        onClick={handleConnectGitHub}
                        disabled={connectingGithub}
                        className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-medium text-white transition-colors disabled:opacity-50"
                      >
                        {connectingGithub ? "Connecting..." : "Connect"}
                      </button>
                    </div>
                  )}
                </div>

                {githubError && (
                  <div className="text-xs text-rose-400 bg-rose-950/40 p-2.5 rounded-lg border border-rose-800/60">
                    {githubError}
                  </div>
                )}
              </div>

              {/* Repository Selector & Task Creator Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Repositories List */}
                <div className="p-5 rounded-xl bg-gray-900/60 border border-gray-800 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <FolderGit2 className="w-4 h-4 text-blue-400" />
                      <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-300">
                        Repositories ({repositories.length})
                      </h3>
                    </div>
                    {githubToken && (
                      <button
                        onClick={() => loadRepositories(githubToken)}
                        disabled={loadingRepos}
                        className="text-gray-400 hover:text-white"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${loadingRepos ? "animate-spin" : ""}`} />
                      </button>
                    )}
                  </div>

                  {githubUser ? (
                    <div className="space-y-3">
                      <div className="relative">
                        <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-gray-500" />
                        <input
                          type="text"
                          placeholder="Search repositories..."
                          value={repoSearch}
                          onChange={(e) => setRepoSearch(e.target.value)}
                          className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-gray-950 border border-gray-800 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                        />
                      </div>

                      <div className="max-h-60 overflow-y-auto space-y-1.5 pr-1">
                        {filteredRepos.length > 0 ? (
                          filteredRepos.map((repo) => (
                            <button
                              key={repo.id || repo.full_name}
                              type="button"
                              onClick={() => handleSelectRepository(repo)}
                              className={`w-full p-2.5 rounded-lg border text-left transition-colors flex items-center justify-between text-xs ${
                                selectedRepo?.full_name === repo.full_name
                                  ? "bg-blue-950/40 border-blue-600 text-white"
                                  : "bg-gray-950/60 border-gray-800 text-gray-300 hover:bg-gray-800/40"
                              }`}
                            >
                              <div className="truncate pr-2">
                                <div className="font-medium truncate">{repo.name}</div>
                                <div className="text-[10px] text-gray-500 truncate">{repo.full_name}</div>
                              </div>
                              <span className="text-[10px] text-gray-400 shrink-0 font-mono">
                                {repo.language || "code"}
                              </span>
                            </button>
                          ))
                        ) : (
                          <div className="text-xs text-gray-500 text-center py-4">No matching repositories.</div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-6 space-y-2">
                      <p className="text-xs text-gray-400">Connect GitHub or choose sample repository:</p>
                      <button
                        onClick={() =>
                          handleSelectRepository({
                            name: "DevPilot",
                            full_name: "bit/DevPilot",
                            owner: "bit",
                            default_branch: "master",
                            is_private: false,
                            html_url: "https://github.com/bit/DevPilot",
                            description: "Autonomous software engineering platform",
                            language: "Python / TypeScript",
                          })
                        }
                        className="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs text-blue-300 font-mono border border-gray-700"
                      >
                        Select Current Repo (DevPilot)
                      </button>
                    </div>
                  )}
                </div>

                {/* Task Requirement Submission */}
                <div className="lg:col-span-2 p-5 rounded-xl bg-gray-900/60 border border-gray-800 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-amber-400" />
                      <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-300">
                        Engineering Task & Requirement
                      </h3>
                    </div>
                    {selectedRepo && (
                      <span className="text-xs text-emerald-400 font-mono flex items-center gap-1.5">
                        <FolderGit2 className="w-3.5 h-3.5" /> {selectedRepo.full_name} ({selectedRepo.default_branch})
                      </span>
                    )}
                  </div>

                  <div className="space-y-3">
                    <div>
                      <label className="text-xs text-gray-400 block mb-1">Task Title</label>
                      <input
                        type="text"
                        value={taskTitle}
                        onChange={(e) => setTaskTitle(e.target.value)}
                        placeholder="e.g., Add Health Endpoint"
                        className="w-full px-3 py-2 rounded-lg bg-gray-950 border border-gray-800 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                      />
                    </div>

                    <div>
                      <label className="text-xs text-gray-400 block mb-1">Software Requirement</label>
                      <textarea
                        rows={3}
                        value={taskRequirement}
                        onChange={(e) => setTaskRequirement(e.target.value)}
                        placeholder="Describe the software requirement in natural language..."
                        className="w-full px-3 py-2 rounded-lg bg-gray-950 border border-gray-800 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 resize-none font-mono"
                      />
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] text-gray-500">Quick Prompts:</span>
                        <button
                          type="button"
                          onClick={() => {
                            setTaskTitle("Add In-Memory Rate Limiting");
                            setTaskRequirement("Implement a rate limiting middleware for API routes to restrict clients to 60 requests/minute.");
                          }}
                          className="text-[10px] px-2 py-1 rounded bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700"
                        >
                          Rate Limiting
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setTaskTitle("Add Health Diagnostics Probe");
                            setTaskRequirement("Add a comprehensive /health endpoint that reports database connectivity and memory usage.");
                          }}
                          className="text-[10px] px-2 py-1 rounded bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700"
                        >
                          Health Probe
                        </button>
                      </div>

                      <button
                        onClick={handleRunPipeline}
                        disabled={runningPipeline || !selectedRepo}
                        className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white transition-colors disabled:opacity-50 flex items-center gap-2 shadow-lg shadow-blue-900/20"
                      >
                        {runningPipeline ? (
                          <>
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                            Running Agent Pipeline...
                          </>
                        ) : (
                          <>
                            <ArrowRight className="w-3.5 h-3.5" />
                            Generate Implementation Plan
                          </>
                        )}
                      </button>
                    </div>

                    {pipelineError && (
                      <div className="text-xs text-rose-400 bg-rose-950/40 p-2.5 rounded-lg border border-rose-800/60 mt-2">
                        {pipelineError}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Execution Pipeline & Implementation Plan Display */}
              {currentTask && (
                <div className="space-y-6 pt-2">
                  {/* Pipeline Stage Breadcrumbs */}
                  <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-3">
                      <span className="font-semibold text-white">Pipeline Execution Status:</span>
                      <StatusBadge status={currentTask.status} />
                    </div>
                    <div className="flex items-center gap-2 text-gray-400 font-mono text-[11px]">
                      <span>1. Inspection</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                      <span>2. Product Analyst</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                      <span>3. Architect Plan</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                      <span className="text-blue-400 font-semibold">4. Human Review</span>
                    </div>
                  </div>

                  {/* 1. Repository Inspection Card */}
                  {currentTask.inspection && (
                    <div className="p-5 rounded-xl bg-gray-900/40 border border-gray-800 space-y-3">
                      <div className="flex items-center justify-between border-b border-gray-800/80 pb-2">
                        <div className="flex items-center gap-2 text-blue-400 text-xs font-semibold uppercase">
                          <FolderGit2 className="w-4 h-4" />
                          Codebase Inspection Findings
                        </div>
                        <span className="text-xs text-gray-400 font-mono">
                          {currentTask.inspection.tree_summary.total_files} Tracked Files
                        </span>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                        <div>
                          <span className="text-gray-500 block mb-1">Detected Languages</span>
                          <div className="flex flex-wrap gap-1">
                            {currentTask.inspection.detected_languages.map((l) => (
                              <span key={l} className="px-2 py-0.5 rounded bg-gray-800 text-gray-200">
                                {l}
                              </span>
                            ))}
                          </div>
                        </div>

                        <div>
                          <span className="text-gray-500 block mb-1">Detected Frameworks</span>
                          <div className="flex flex-wrap gap-1">
                            {currentTask.inspection.detected_frameworks.length > 0 ? (
                              currentTask.inspection.detected_frameworks.map((f) => (
                                <span key={f} className="px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800/40">
                                  {f}
                                </span>
                              ))
                            ) : (
                              <span className="text-gray-500">None detected</span>
                            )}
                          </div>
                        </div>

                        <div>
                          <span className="text-gray-500 block mb-1">Identified Entrypoints</span>
                          <div className="flex flex-wrap gap-1 font-mono text-[11px]">
                            {currentTask.inspection.detected_entrypoints.map((ep) => (
                              <span key={ep} className="px-2 py-0.5 rounded bg-gray-800 text-emerald-400">
                                {ep}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>

                      <div className="pt-2">
                        <span className="text-[11px] text-gray-500 block mb-1 font-semibold uppercase">Confirmed Codebase Observations:</span>
                        <ul className="list-disc list-inside space-y-0.5 text-xs text-gray-300">
                          {currentTask.inspection.confirmed_facts.map((cf, idx) => (
                            <li key={idx}>{cf}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}

                  {/* 2. Product Analyst Requirements Card */}
                  {currentTask.requirement_analysis && (
                    <div className="p-5 rounded-xl bg-gray-900/40 border border-gray-800 space-y-4">
                      <div className="flex items-center gap-2 text-amber-400 text-xs font-semibold uppercase border-b border-gray-800/80 pb-2">
                        <Sparkles className="w-4 h-4" />
                        Product Analyst Specification
                      </div>

                      <div>
                        <h4 className="text-xs font-semibold text-white">Requirement Summary</h4>
                        <p className="text-xs text-gray-300 mt-1">{currentTask.requirement_analysis.requirement_summary}</p>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                        <div className="space-y-1.5">
                          <span className="font-semibold text-gray-300">Functional Deliverables</span>
                          <ul className="space-y-1 text-gray-300">
                            {currentTask.requirement_analysis.functional_requirements.map((fr, idx) => (
                              <li key={idx} className="flex items-start gap-1.5">
                                <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                                <span>{fr}</span>
                              </li>
                            ))}
                          </ul>
                        </div>

                        <div className="space-y-1.5">
                          <span className="font-semibold text-gray-300">Acceptance Criteria</span>
                          <ul className="space-y-1 text-gray-300">
                            {currentTask.requirement_analysis.acceptance_criteria.map((ac, idx) => (
                              <li key={idx} className="flex items-start gap-1.5">
                                <ListChecks className="w-3.5 h-3.5 text-blue-400 shrink-0 mt-0.5" />
                                <span>{ac}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 3. Architect Implementation Plan & Review Card */}
                  {currentTask.implementation_plan && (
                    <div className="p-6 rounded-xl bg-gray-900/60 border border-blue-900/40 space-y-5 ring-1 ring-blue-500/20">
                      <div className="flex items-center justify-between border-b border-gray-800 pb-3">
                        <div className="flex items-center gap-2 text-white font-semibold text-sm">
                          <Cpu className="w-5 h-5 text-blue-400" />
                          Architect Agent: Implementation Plan
                        </div>
                        <StatusBadge status={currentTask.status} />
                      </div>

                      <div className="space-y-2">
                        <h4 className="text-xs font-semibold text-gray-400 uppercase">Architecture Strategy</h4>
                        <p className="text-xs text-gray-200 leading-relaxed">{currentTask.implementation_plan.summary}</p>
                      </div>

                      {/* Files to Create and Modify */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Files to Create */}
                        <div className="p-3.5 rounded-lg bg-gray-950 border border-gray-800 space-y-2">
                          <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
                            <FilePlus className="w-4 h-4" /> Files to Create ({currentTask.implementation_plan.files_to_create.length})
                          </span>
                          <div className="space-y-1.5 text-xs">
                            {currentTask.implementation_plan.files_to_create.length > 0 ? (
                              currentTask.implementation_plan.files_to_create.map((fc, idx) => (
                                <div key={idx} className="p-2 rounded bg-gray-900/60 border border-gray-800">
                                  <div className="font-mono text-emerald-300 text-[11px] font-semibold">{fc.path}</div>
                                  <div className="text-[11px] text-gray-400 mt-0.5">{fc.purpose}</div>
                                </div>
                              ))
                            ) : (
                              <p className="text-gray-500 text-[11px]">No new files to create.</p>
                            )}
                          </div>
                        </div>

                        {/* Files to Modify */}
                        <div className="p-3.5 rounded-lg bg-gray-950 border border-gray-800 space-y-2">
                          <span className="text-xs font-semibold text-amber-400 flex items-center gap-1.5">
                            <FileEdit className="w-4 h-4" /> Files to Modify ({currentTask.implementation_plan.files_to_modify.length})
                          </span>
                          <div className="space-y-1.5 text-xs">
                            {currentTask.implementation_plan.files_to_modify.length > 0 ? (
                              currentTask.implementation_plan.files_to_modify.map((fm, idx) => (
                                <div key={idx} className="p-2 rounded bg-gray-900/60 border border-gray-800">
                                  <div className="font-mono text-amber-300 text-[11px] font-semibold">{fm.path}</div>
                                  <div className="text-[11px] text-gray-400 mt-0.5">{fm.reason}</div>
                                </div>
                              ))
                            ) : (
                              <p className="text-gray-500 text-[11px]">No existing files modified.</p>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Implementation Steps */}
                      <div className="space-y-2">
                        <span className="text-xs font-semibold text-gray-400 uppercase">Ordered Execution Sequence</span>
                        <div className="space-y-2">
                          {currentTask.implementation_plan.implementation_steps.map((step) => (
                            <div key={step.step_number} className="p-3 rounded-lg bg-gray-950 border border-gray-800 flex items-start gap-3 text-xs">
                              <span className="w-5 h-5 rounded-full bg-blue-900/60 text-blue-300 font-mono text-[10px] flex items-center justify-center shrink-0 mt-0.5 border border-blue-700/40">
                                {step.step_number}
                              </span>
                              <div className="flex-1">
                                <div className="font-semibold text-white">{step.title}</div>
                                <div className="text-gray-400 text-[11px] mt-0.5">{step.description}</div>
                                {step.affected_files.length > 0 && (
                                  <div className="mt-1 flex gap-1 font-mono text-[10px] text-gray-500">
                                    <span>Files:</span> {step.affected_files.join(", ")}
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Human Approval Section */}
                      <div className="pt-4 border-t border-gray-800 space-y-4">
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                          <div>
                            <h4 className="text-sm font-semibold text-white">Human Plan Review & Approval</h4>
                            <p className="text-xs text-gray-400 mt-0.5">
                              Chapter 2 requires explicit human approval before any subsequent code generation engine can be authorized.
                            </p>
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleApprovalDecision("APPROVED")}
                              disabled={submittingApproval || currentTask.status === "APPROVED"}
                              className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white transition-colors disabled:opacity-50 flex items-center gap-1.5 shadow-md shadow-emerald-900/20"
                            >
                              <Check className="w-3.5 h-3.5" /> Approve Plan
                            </button>

                            <button
                              onClick={() => handleApprovalDecision("CHANGES_REQUESTED")}
                              disabled={submittingApproval}
                              className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-xs font-semibold text-white transition-colors disabled:opacity-50 flex items-center gap-1.5"
                            >
                              <MessageSquare className="w-3.5 h-3.5" /> Request Changes
                            </button>

                            <button
                              onClick={() => handleApprovalDecision("REJECTED")}
                              disabled={submittingApproval}
                              className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-xs font-semibold text-white transition-colors disabled:opacity-50 flex items-center gap-1.5"
                            >
                              <X className="w-3.5 h-3.5" /> Reject Plan
                            </button>
                          </div>
                        </div>

                        {/* Optional Feedback Input */}
                        <div className="pt-2">
                          <input
                            type="text"
                            placeholder="Optional review feedback or requested changes..."
                            value={approvalFeedback}
                            onChange={(e) => setApprovalFeedback(e.target.value)}
                            className="w-full px-3 py-2 rounded-lg bg-gray-950 border border-gray-800 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                          />
                        </div>

                        {/* Persistent Approvals List */}
                        {currentTask.approvals.length > 0 && (
                          <div className="p-3 rounded-lg bg-gray-950/80 border border-gray-800 space-y-1.5 text-xs">
                            <span className="font-semibold text-gray-400 text-[11px] uppercase">Recorded Review Decisions:</span>
                            {currentTask.approvals.map((appr) => (
                              <div key={appr.id} className="flex items-center justify-between py-1 border-b border-gray-900 last:border-0">
                                <div className="flex items-center gap-2">
                                  <StatusBadge status={appr.decision} />
                                  <span className="text-gray-300">{appr.feedback || "No feedback specified"}</span>
                                </div>
                                <span className="text-gray-500 text-[10px] font-mono">
                                  {new Date(appr.decided_at).toLocaleString()}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Chapter 1: Diagnostics Tab */}
          {activeTab === "diagnostics" && (
            <div className="space-y-6">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-gray-800">
                <div>
                  <div className="flex items-center gap-2">
                    <h1 className="text-2xl font-bold tracking-tight text-white">
                      Chapter 1 — Engineering Foundation
                    </h1>
                    <StatusBadge status="COMPLETED" label="PHASE 1 COMPLETE" />
                  </div>
                  <p className="text-sm text-gray-400 mt-1">
                    System health diagnostics, database connectivity, and Groq LLM integration verification.
                  </p>
                </div>

                <button
                  onClick={loadHealthData}
                  disabled={loadingHealth}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-sm font-medium text-gray-200 transition-colors border border-gray-700 disabled:opacity-50 w-fit"
                >
                  <RefreshCw className={`w-4 h-4 ${loadingHealth ? "animate-spin" : ""}`} />
                  Refresh Diagnostics
                </button>
              </div>

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
                      {health?.components.llm.model || "qwen/qwen3.8-27b"}
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5">
                      Provider: <span className="text-gray-300 font-mono">Groq Cloud</span>
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
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
