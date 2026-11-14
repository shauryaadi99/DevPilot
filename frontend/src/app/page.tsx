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
  executeTask,
  getExecutionStatus,
  cancelExecution,
  type HealthResponse,
  type GroqTestResult,
  type GitHubUser,
  type GitHubRepo,
  type TaskDetail,
  type ExecutionStatus,
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
  Terminal,
  GitBranch,
  ShieldCheck,
  Layers,
  FileCode,
} from "@/components/ui/Icons";

export default function WorkspacePage() {
  const [activeTab, setActiveTab] = useState<"planning" | "diagnostics" | "execution">("planning");

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
  const [approvalAction, setApprovalAction] = useState<string | null>(null);
  const [planRevisionMessage, setPlanRevisionMessage] = useState<string | null>(null);

  // Chapter 3: Execution State
  const [executionStatus, setExecutionStatus] = useState<ExecutionStatus | null>(null);
  const [executingPlan, setExecutingPlan] = useState<boolean>(false);
  const [executionError, setExecutionError] = useState<string | null>(null);
  const [pollingExecution, setPollingExecution] = useState<boolean>(false);

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

    if (decision === "CHANGES_REQUESTED" && !approvalFeedback.trim()) {
      setPipelineError("Please enter your review feedback or requested changes below before clicking 'Request Changes'.");
      return;
    }

    try {
      setSubmittingApproval(true);
      setApprovalAction(decision);
      setPipelineError(null);
      setPlanRevisionMessage(null);

      const result = await submitPlanApproval(currentTask.id, decision, approvalFeedback.trim() || undefined);

      if (result.task) {
        setCurrentTask(result.task);
      } else {
        // Fallback: update local task status and append approval
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
      }

      if (decision === "CHANGES_REQUESTED") {
        setPlanRevisionMessage(
          result.message || "Plan revised by Product Analyst & Architect Agents based on your feedback! Ready for re-review."
        );
      } else if (decision === "APPROVED") {
        setPlanRevisionMessage(
          result.message || "Plan approved! Ready for autonomous execution in Chapter 3."
        );
      }

      setApprovalFeedback("");
    } catch (err: any) {
      setPipelineError(err?.message || "Failed to submit approval.");
    } finally {
      setSubmittingApproval(false);
      setApprovalAction(null);
    }
  };

  // ── Chapter 3: Execute plan handler ──────────────────────────────────────
  const handleExecutePlan = async () => {
    if (!currentTask) return;
    try {
      setExecutingPlan(true);
      setExecutionError(null);
      setExecutionStatus(null);
      await executeTask(currentTask.id, githubToken || undefined);
      // Start polling
      setPollingExecution(true);
      pollExecutionStatus(currentTask.id);
    } catch (err: any) {
      setExecutionError(err?.message || "Failed to start execution.");
      setExecutingPlan(false);
    }
  };

  const pollExecutionStatus = async (taskId: string) => {
    const TERMINAL = ["COMPLETED", "FAILED", "CANCELLED"];
    let attempts = 0;
    const MAX_ATTEMPTS = 120; // 10 min at 5s intervals
    const poll = async () => {
      try {
        const status = await getExecutionStatus(taskId);
        setExecutionStatus(status);
        if (TERMINAL.includes(status.status) || attempts >= MAX_ATTEMPTS) {
          setPollingExecution(false);
          setExecutingPlan(false);
        } else {
          attempts++;
          setTimeout(poll, 5000);
        }
      } catch {
        setPollingExecution(false);
        setExecutingPlan(false);
      }
    };
    poll();
  };

  const handleCancelExecution = async () => {
    if (!currentTask) return;
    try {
      await cancelExecution(currentTask.id);
      const status = await getExecutionStatus(currentTask.id);
      setExecutionStatus(status);
      setPollingExecution(false);
      setExecutingPlan(false);
    } catch (err: any) {
      setExecutionError(err?.message || "Cancel failed.");
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
          {(activeTab === "planning" || activeTab === "execution") && (
            <div className="space-y-6">
              {/* Header Title */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-gray-800">
                <div>
                  <div className="flex items-center gap-2">
                    <h1 className="text-2xl font-bold tracking-tight text-white">
                      Chapter 3 — Autonomous Development Engine
                    </h1>
                    <StatusBadge status="ACTIVE" label="CHAPTER 3 ACTIVE" />
                  </div>
                  <p className="text-sm text-gray-400 mt-1">
                    Connect repository, analyze requirements, formulate architecture-aware plans, and autonomously implement approved changes via Developer Agent in an isolated sandbox.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400 font-mono">Model:</span>
                  <span className="text-xs px-2.5 py-1 rounded-md bg-blue-950/60 border border-blue-800/60 text-blue-300 font-mono">
                    {health?.components.llm.model || "openai/gpt-oss-120b"}
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
                            setTaskTitle("Add Password Reset Functionality");
                            setTaskRequirement(
                              "Implement a secure password reset feature in the existing TaskFlow application.\n\n" +
                              "Requirements:\n" +
                              "1. Add a Forgot Password option to the login page.\n" +
                              "2. Allow users to request a password reset using their registered email address.\n" +
                              "3. Generate a secure, unique, time-limited reset token.\n" +
                              "4. Allow users to reset their password using the token.\n" +
                              "5. Hash the new password before storing it in MongoDB.\n" +
                              "6. Ensure reset tokens expire and cannot be reused.\n" +
                              "7. Add appropriate backend API endpoints and frontend UI.\n" +
                              "8. Include validation, error handling and security checks."
                            );
                          }}
                          className="text-[10px] px-2 py-1 rounded bg-blue-900/40 hover:bg-blue-800/60 text-blue-300 border border-blue-700/50"
                        >
                          Password Reset (MERN)
                        </button>
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
                      <span className={currentTask.status === "APPROVED" ? "text-green-400 font-semibold" : "text-blue-400 font-semibold"}>4. Human Review</span>
                      {currentTask.status === "APPROVED" && (
                        <>
                          <ChevronRight className="w-3.5 h-3.5" />
                          <span className={["EXECUTING","COMPLETED","COMMITTING"].includes(executionStatus?.status || "") ? "text-purple-400 font-semibold" : "text-gray-500"}>5. Dev Agent</span>
                        </>
                      )}
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
                              <Check className="w-3.5 h-3.5" />
                              {submittingApproval && approvalAction === "APPROVED" ? "Approving..." : "Approve Plan"}
                            </button>

                            <button
                              onClick={() => handleApprovalDecision("CHANGES_REQUESTED")}
                              disabled={submittingApproval}
                              className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-xs font-semibold text-white transition-colors disabled:opacity-50 flex items-center gap-1.5"
                            >
                              <MessageSquare className="w-3.5 h-3.5" />
                              {submittingApproval && approvalAction === "CHANGES_REQUESTED" ? "Revising Plan..." : "Request Changes"}
                            </button>

                            <button
                              onClick={() => handleApprovalDecision("REJECTED")}
                              disabled={submittingApproval}
                              className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-xs font-semibold text-white transition-colors disabled:opacity-50 flex items-center gap-1.5"
                            >
                              <X className="w-3.5 h-3.5" />
                              {submittingApproval && approvalAction === "REJECTED" ? "Rejecting..." : "Reject Plan"}
                            </button>
                          </div>
                        </div>

                        {/* Re-planning in-progress indicator */}
                        {submittingApproval && approvalAction === "CHANGES_REQUESTED" && (
                          <div className="flex items-center gap-2.5 p-3.5 rounded-lg bg-amber-950/40 border border-amber-800/60 text-amber-200 text-xs animate-pulse">
                            <RefreshCw className="w-4 h-4 animate-spin text-amber-400 shrink-0" />
                            <div>
                              <div className="font-semibold text-amber-300">Revising Implementation Plan</div>
                              <p className="text-[11px] text-amber-200/80 mt-0.5">
                                Re-running Product Analyst and Architect agents to incorporate your review feedback into the files, steps, and test strategy...
                              </p>
                            </div>
                          </div>
                        )}

                        {/* Plan revision success message */}
                        {planRevisionMessage && !submittingApproval && (
                          <div className="flex items-start gap-2.5 p-3.5 rounded-lg bg-emerald-950/40 border border-emerald-800/60 text-emerald-200 text-xs">
                            <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                            <div>
                              <div className="font-semibold text-emerald-300">Review Update</div>
                              <p className="text-[11px] text-emerald-200/80 mt-0.5">{planRevisionMessage}</p>
                            </div>
                          </div>
                        )}

                        {/* Optional Feedback Input */}
                        <div className="pt-2">
                          <input
                            type="text"
                            placeholder="Enter review feedback or requested changes (e.g. 'Use Redis for token storage and hash with bcrypt')..."
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

                  {/* Chapter 3 — Autonomous Development Engine Card */}
                  {(currentTask.status === "APPROVED" ||
                    ["CLONING", "EXECUTING", "COMMITTING", "COMPLETED", "FAILED", "CANCELLED"].includes(currentTask.status) ||
                    executionStatus !== null) && (
                    <div className="p-5 rounded-xl bg-gray-900/60 border border-purple-900/40 space-y-4 shadow-xl shadow-purple-950/10">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-gray-800 gap-3">
                        <div className="flex items-center gap-2.5">
                          <div className="p-2 rounded-lg bg-purple-950/60 border border-purple-800/60 text-purple-400">
                            <Terminal className="w-5 h-5" />
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <h4 className="text-sm font-semibold text-white">Chapter 3 — Autonomous Development Engine</h4>
                              <StatusBadge
                                status={executionStatus?.status || (currentTask.status === "APPROVED" ? "READY" : currentTask.status)}
                              />
                            </div>
                            <p className="text-xs text-gray-400 mt-0.5">
                              Developer Agent executes approved plan steps in an isolated Git workspace.
                            </p>
                          </div>
                        </div>

                        {/* Git Branch Badge */}
                        <div className="flex items-center gap-2">
                          <span className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-gray-950 border border-gray-800 text-[11px] font-mono text-purple-300">
                            <GitBranch className="w-3.5 h-3.5 text-purple-400" />
                            devpilot/task-{currentTask.id.slice(0, 8)}
                          </span>
                        </div>
                      </div>

                      {/* Security & Sandbox Info */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                        <div className="p-3 rounded-lg bg-gray-950/60 border border-gray-800/80 flex items-center gap-2.5">
                          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                          <div>
                            <div className="font-semibold text-emerald-300 text-[11px]">Branch Isolation Active</div>
                            <div className="text-[10px] text-gray-400">Default branch ({currentTask.repository.default_branch}) strictly protected. Changes confined to task branch.</div>
                          </div>
                        </div>

                        <div className="p-3 rounded-lg bg-gray-950/60 border border-gray-800/80 flex items-center gap-2.5">
                          <Layers className="w-4 h-4 text-blue-400 shrink-0" />
                          <div>
                            <div className="font-semibold text-blue-300 text-[11px]">Restricted Execution Sandbox</div>
                            <div className="text-[10px] text-gray-400">Path traversal blocked • 512MB RAM cap • 60s timeout • Stripped secrets.</div>
                          </div>
                        </div>
                      </div>

                      {/* Action & Trigger Controls */}
                      <div className="p-4 rounded-xl bg-gray-950/80 border border-gray-800 flex flex-col sm:flex-row items-center justify-between gap-3">
                        <div className="text-xs">
                          {executingPlan || ["CLONING", "EXECUTING", "COMMITTING"].includes(executionStatus?.status || "") ? (
                            <div className="flex items-center gap-2 text-purple-300">
                              <RefreshCw className="w-4 h-4 animate-spin text-purple-400" />
                              <span className="font-semibold">Developer Agent Running:</span>
                              <span className="text-gray-400">
                                Step {executionStatus?.current_step || 0} of {executionStatus?.total_steps || currentTask.implementation_plan?.implementation_steps.length || 0}
                              </span>
                            </div>
                          ) : executionStatus?.status === "COMPLETED" ? (
                            <div className="flex items-center gap-2 text-emerald-400 font-semibold">
                              <CheckCircle className="w-4 h-4" />
                              Plan Implemented & Committed Successfully!
                              {executionStatus.commit_sha && (
                                <span className="ml-2 px-2 py-0.5 rounded bg-emerald-950/80 border border-emerald-800/60 text-emerald-200 font-mono text-[10px]">
                                  {executionStatus.commit_sha.slice(0, 7)}
                                </span>
                              )}
                            </div>
                          ) : executionStatus?.status === "FAILED" ? (
                            <div className="flex items-center gap-2 text-rose-400 font-semibold">
                              <AlertTriangle className="w-4 h-4" />
                              Execution Encountered an Error: {executionStatus.error_message}
                            </div>
                          ) : executionStatus?.status === "CANCELLED" ? (
                            <div className="flex items-center gap-2 text-amber-400 font-semibold">
                              <AlertTriangle className="w-4 h-4" />
                              Execution was cancelled. Workspace cleaned up.
                            </div>
                          ) : (
                            <div>
                              <div className="font-semibold text-white">Ready for Autonomous Execution</div>
                              <p className="text-gray-400 text-[11px] mt-0.5">
                                Plan approved. Click to launch the Developer Agent inside the sandboxed workspace.
                              </p>
                            </div>
                          )}
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          {executingPlan || ["CLONING", "EXECUTING", "COMMITTING"].includes(executionStatus?.status || "") ? (
                            <button
                              onClick={handleCancelExecution}
                              className="px-4 py-2 rounded-lg bg-rose-700 hover:bg-rose-600 text-xs font-semibold text-white transition-colors flex items-center gap-1.5"
                            >
                              <X className="w-3.5 h-3.5" />
                              Cancel Execution
                            </button>
                          ) : (
                            <button
                              onClick={handleExecutePlan}
                              disabled={executingPlan}
                              className="px-5 py-2.5 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-xs font-semibold text-white transition-all shadow-lg shadow-purple-950/40 flex items-center gap-2 disabled:opacity-50"
                            >
                              <Sparkles className="w-4 h-4" />
                              {executionStatus?.status === "FAILED" || executionStatus?.status === "CANCELLED"
                                ? "Retry Execution"
                                : "Execute Approved Plan"}
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Execution Error Banner */}
                      {executionError && (
                        <div className="flex items-start gap-2.5 p-3.5 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-200 text-xs">
                          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                          <div>
                            <div className="font-semibold text-rose-300">Execution Error</div>
                            <p className="text-[11px] text-rose-200/80 mt-0.5">{executionError}</p>
                          </div>
                        </div>
                      )}

                      {/* Tracked File Changes */}
                      {executionStatus?.file_changes && executionStatus.file_changes.length > 0 && (
                        <div className="p-4 rounded-xl bg-gray-950/60 border border-gray-800 space-y-3">
                          <div className="flex items-center justify-between border-b border-gray-800 pb-2">
                            <span className="text-xs font-semibold text-gray-300 uppercase tracking-wider flex items-center gap-1.5">
                              <FileCode className="w-3.5 h-3.5 text-purple-400" />
                              Tracked Codebase Modifications ({executionStatus.file_changes.length})
                            </span>
                          </div>

                          <div className="space-y-2">
                            {executionStatus.file_changes.map((fc, idx) => (
                              <div
                                key={idx}
                                className="flex items-center justify-between p-2.5 rounded-lg bg-gray-900/60 border border-gray-800/80 text-xs font-mono"
                              >
                                <div className="flex items-center gap-2.5">
                                  <span
                                    className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                                      fc.change_type === "CREATE"
                                        ? "bg-emerald-950 text-emerald-400 border border-emerald-800/60"
                                        : fc.change_type === "MODIFY"
                                        ? "bg-blue-950 text-blue-400 border border-blue-800/60"
                                        : "bg-rose-950 text-rose-400 border border-rose-800/60"
                                    }`}
                                  >
                                    {fc.change_type}
                                  </span>
                                  <span className="text-gray-200">{fc.file_path}</span>
                                </div>

                                <div className="flex items-center gap-3 text-[11px]">
                                  {fc.lines_added > 0 && (
                                    <span className="text-emerald-400">+{fc.lines_added}</span>
                                  )}
                                  {fc.lines_removed > 0 && (
                                    <span className="text-rose-400">-{fc.lines_removed}</span>
                                  )}
                                  {fc.diff_summary && (
                                    <span className="text-gray-500">{fc.diff_summary}</span>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Developer Agent Execution Logs Terminal */}
                      {executionStatus?.logs && executionStatus.logs.length > 0 && (
                        <div className="p-4 rounded-xl bg-gray-950 border border-gray-800 space-y-2">
                          <div className="flex items-center justify-between pb-2 border-b border-gray-800/80">
                            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
                              <Terminal className="w-3.5 h-3.5 text-gray-400" />
                              Execution Audit Trail & Logs
                            </span>
                            <span className="text-[10px] font-mono text-gray-500">
                              {executionStatus.logs.length} entries
                            </span>
                          </div>

                          <div className="max-h-48 overflow-y-auto space-y-1 font-mono text-[11px] text-gray-300 pt-1">
                            {executionStatus.logs.map((log, idx) => (
                              <div key={idx} className="flex items-start gap-2 py-0.5">
                                <span className="text-gray-600 shrink-0">
                                  {new Date(log.timestamp).toLocaleTimeString()}
                                </span>
                                <span
                                  className={`shrink-0 font-semibold ${
                                    log.level === "ERROR"
                                      ? "text-rose-400"
                                      : log.level === "WARNING"
                                      ? "text-amber-400"
                                      : "text-purple-400"
                                  }`}
                                >
                                  [{log.agent}]
                                </span>
                                <span className="text-gray-300 break-all">{log.message}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
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
                      {health?.components.llm.model || "openai/gpt-oss-120b"}
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
