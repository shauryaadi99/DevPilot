"use client";

import { useEffect, useState, useMemo } from "react";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { PatModal } from "@/components/auth/PatModal";
import { ChapterProgressBar, ChapterStatusInfo } from "@/components/ui/ChapterProgressBar";
import {
  fetchHealth,
  testGroqConnection,
  listUserRepositories,
  selectRepository,
  createTask,
  runTaskPipeline,
  submitPlanApproval,
  executeTask,
  resumeExecution,
  getExecutionStatus,
  cancelExecution,
  closeTask,
  reopenTask,
  runQa,
  getSessionState,
  submitPat,
  getPatStatus,
  devLogin,
  logout,
  getSavedRepositories,
  getGithubLoginUrl,
  submitFinalApproval,
  deliverTask,
  getDeliveryStatus,
  getTaskDiff,
  getTaskTimeline,
  startNewProject,
  startNewTask,
  switchRepository,
  switchTask,
  listTasks,
  getTask,
  type TaskSummary,
  type HealthResponse,
  type GroqTestResult,
  type GitHubUser,
  type GitHubRepo,
  type TaskDetail,
  type ExecutionStatus,
  type QAReportData,
  type CodeReviewReportData,
  type UserProfile,
  type PatStatus,
  type DeliveryApprovalData,
  type PullRequestData,
  type DiffResponse,
  type TimelineEvent,
} from "@/lib/api";
import {
  Database,
  Cpu,
  RefreshCw,
  CheckCircle,
  CheckCircle2,
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
  Sliders,
  Send,
  GitPullRequest,
  ExternalLink,
} from "@/components/ui/Icons";

export default function WorkspacePage() {
  const [activeTab, setActiveTab] = useState<"planning" | "diagnostics" | "execution" | "qa" | "delivery" | "all">("planning");

  // Chapter 1 Diagnostics State
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loadingHealth, setLoadingHealth] = useState<boolean>(true);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [testingGroq, setTestingGroq] = useState<boolean>(false);
  const [groqTestResult, setGroqTestResult] = useState<GroqTestResult | null>(null);

  // User & Authentication State
  const [user, setUser] = useState<UserProfile | null>(null);
  const [patStatus, setPatStatus] = useState<PatStatus | null>(null);
  const [isPatModalOpen, setIsPatModalOpen] = useState<boolean>(false);
  const [canResume, setCanResume] = useState<boolean>(false);

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
  const [runningQa, setRunningQa] = useState<boolean>(false);
  const [executionError, setExecutionError] = useState<string | null>(null);
  const [pollingExecution, setPollingExecution] = useState<boolean>(false);

  // Chapter 5: Delivery & Pull Request State
  const [deliveringTask, setDeliveringTask] = useState<boolean>(false);
  const [deliveryError, setDeliveryError] = useState<string | null>(null);
  const [submittingFinalApproval, setSubmittingFinalApproval] = useState<boolean>(false);
  const [finalApprovalFeedback, setFinalApprovalFeedback] = useState<string>("");
  const [taskDiff, setTaskDiff] = useState<DiffResponse | null>(null);
  const [loadingDiff, setLoadingDiff] = useState<boolean>(false);
  const [taskTimeline, setTaskTimeline] = useState<TimelineEvent[]>([]);
  const [loadingTimeline, setLoadingTimeline] = useState<boolean>(false);
  const [showRawDiff, setShowRawDiff] = useState<boolean>(false);

  // Multi-Project & Multi-Task Navigation State
  const [availableTasks, setAvailableTasks] = useState<TaskSummary[]>([]);
  const [isProjectDropdownOpen, setIsProjectDropdownOpen] = useState<boolean>(false);
  const [isTaskDropdownOpen, setIsTaskDropdownOpen] = useState<boolean>(false);

  const refreshTasksForRepo = async (repoId?: string) => {
    if (!repoId) return;
    try {
      const tasks = await listTasks(repoId);
      setAvailableTasks(tasks);
    } catch (err) {
      console.warn("Failed to fetch tasks for repo:", err);
    }
  };

  const handleStartNewProject = async () => {
    try {
      await startNewProject();
      setSelectedRepo(null);
      setCurrentTask(null);
      setExecutionStatus(null);
      setTaskDiff(null);
      setTaskTimeline([]);
      setAvailableTasks([]);
      setTaskTitle("");
      setTaskRequirement("");
      setActiveTab("planning");
    } catch (err: any) {
      console.error("Failed to start new project:", err);
    }
  };

  const handleStartNewTask = async () => {
    try {
      await startNewTask();
      setCurrentTask(null);
      setExecutionStatus(null);
      setTaskDiff(null);
      setTaskTimeline([]);
      setTaskTitle("");
      setTaskRequirement("");
      setActiveTab("planning");
      if (selectedRepo?.id) {
        await refreshTasksForRepo(String(selectedRepo.id));
      }
    } catch (err: any) {
      console.error("Failed to start new task:", err);
    }
  };

  const handleSwitchProject = async (repo: GitHubRepo) => {
    try {
      setSelectedRepo(repo);
      await selectRepository(repo);
      setCurrentTask(null);
      setExecutionStatus(null);
      setTaskDiff(null);
      setTaskTimeline([]);
      setTaskTitle("");
      setTaskRequirement("");
      setActiveTab("planning");
      await initSession();
    } catch (err: any) {
      console.error("Failed to switch project:", err);
    }
  };

  const handleSwitchTask = async (taskId: string) => {
    try {
      await switchTask(taskId);
      const detail = await getTask(taskId);
      setCurrentTask(detail);
      if (detail.title) setTaskTitle(detail.title);
      if (detail.requirement) setTaskRequirement(detail.requirement);

      try {
        const execStatus = await getExecutionStatus(taskId);
        setExecutionStatus(execStatus);
      } catch {
        setExecutionStatus(null);
      }

      const status = detail.status || "";
      if (detail.is_delivered || detail.pull_request || status === "COMPLETED") {
        setActiveTab("delivery");
        loadDiffAndTimeline(detail.id);
      } else if (["AWAITING_QA", "AWAITING_REVIEW", "AWAITING_DELIVERY"].includes(status)) {
        setActiveTab("qa");
      } else if (["EXECUTING", "COMMITTING", "CLONING", "FAILED", "CLOSED"].includes(status)) {
        setActiveTab("execution");
      } else {
        setActiveTab("planning");
      }
    } catch (err: any) {
      console.error("Failed to switch task:", err);
    }
  };

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

  const initSession = async () => {
    try {
      const state = await getSessionState();
      if (state.authenticated && state.user) {
        setUser(state.user);
        setGithubUser({
          login: state.user.username,
          name: state.user.name,
          avatar_url: state.user.avatar_url,
          html_url: `https://github.com/${state.user.username}`,
          public_repos: 0,
        });
      }
      if (state.pat_status) {
        setPatStatus(state.pat_status);
        if (state.pat_status.has_pat && state.pat_status.is_valid) {
          loadRepositories();
        } else {
          loadSavedRepos();
        }
      } else {
        loadSavedRepos();
      }
      if (state.selected_repository) {
        setSelectedRepo(state.selected_repository);
      } else {
        setSelectedRepo(null);
      }
      if (state.available_tasks) {
        setAvailableTasks(state.available_tasks);
      } else if (state.selected_repository?.id) {
        refreshTasksForRepo(String(state.selected_repository.id));
      }
      if (state.current_task) {
        setCurrentTask(state.current_task);
        if (state.current_task.title) setTaskTitle(state.current_task.title);
        if (state.current_task.requirement) setTaskRequirement(state.current_task.requirement);

        // Smart chapter navigation based on current pipeline status
        const currentExecStatus = state.execution?.status || "";
        const currentTaskStatus = state.current_task.status || "";
        if (
          state.current_task.is_delivered ||
          state.current_task.pull_request ||
          currentTaskStatus === "COMPLETED" ||
          (currentTaskStatus === "AWAITING_DELIVERY" &&
            state.current_task.delivery_approvals?.some((a: any) => a?.decision === "APPROVED"))
        ) {
          setActiveTab("delivery");
        } else if (
          ["AWAITING_QA", "AWAITING_REVIEW", "AWAITING_DELIVERY"].includes(currentTaskStatus) ||
          ["AWAITING_QA", "AWAITING_REVIEW", "AWAITING_DELIVERY"].includes(currentExecStatus)
        ) {
          setActiveTab("qa");
        } else if (
          ["EXECUTING", "COMMITTING", "CLONING", "FAILED", "CLOSED"].includes(currentTaskStatus) ||
          ["EXECUTING", "COMMITTING", "CLONING", "FAILED", "CLOSED"].includes(currentExecStatus)
        ) {
          // If execution failed and has QA reports, direct user to QA to review failures
          if (state.execution?.qa_reports && state.execution.qa_reports.length > 0) {
            setActiveTab("qa");
          } else {
            setActiveTab("execution");
          }
        } else if (
          ["APPROVED", "AWAITING_APPROVAL", "PLANNING", "INSPECTING", "ANALYZING"].includes(currentTaskStatus)
        ) {
          setActiveTab("planning");
        }
      } else {
        setCurrentTask(null);
        setExecutionStatus(null);
        setTaskDiff(null);
        setTaskTimeline([]);
      }
      if (state.execution) {
        setExecutionStatus(state.execution);
        if (["CLONING", "EXECUTING", "COMMITTING", "QA_TESTING", "REVIEWING"].includes(state.execution.status)) {
          setPollingExecution(true);
          pollExecutionStatus(state.execution.task_id);
        }
      }
      setCanResume(state.can_resume || false);
    } catch (err: any) {
      console.warn("Session rehydration:", err?.message || err);
      loadSavedRepos();
    }
  };

  const loadSavedRepos = async () => {
    try {
      const saved = await getSavedRepositories();
      if (saved && saved.length > 0) {
        setRepositories(saved);
      }
    } catch {
      // Ignore
    }
  };

  const loadRepositories = async () => {
    try {
      setLoadingRepos(true);
      const repos = await listUserRepositories();
      if (repos && repos.length > 0) {
        setRepositories(repos);
      } else {
        loadSavedRepos();
      }
    } catch (err: any) {
      console.warn("Direct repo listing failed, fetching saved repos:", err?.message);
      loadSavedRepos();
    } finally {
      setLoadingRepos(false);
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

  const handleLogin = async () => {
    try {
      const data = await getGithubLoginUrl();
      if (data.oauth_url) {
        window.location.href = data.oauth_url;
        return;
      }
    } catch {
      // GitHub OAuth credentials not configured; prompt with PAT modal for GitHub auth
    }
    setIsPatModalOpen(true);
  };

  const handleDevLogin = async () => {
    try {
      const res = await devLogin("developer");
      setUser(res.user);
      setGithubUser({
        login: res.user.username,
        name: res.user.name,
        avatar_url: res.user.avatar_url,
        html_url: `https://github.com/${res.user.username}`,
        public_repos: 0,
      });
      await initSession();
    } catch (err: any) {
      setGithubError(err?.message || "Dev login failed.");
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
      setUser(null);
      setGithubUser(null);
      setPatStatus(null);
      setRepositories([]);
      setSelectedRepo(null);
      setCurrentTask(null);
      setExecutionStatus(null);
      setCanResume(false);
    } catch (err: any) {
      console.error("Logout failed:", err);
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
      await submitPat(githubToken.trim());
      setGithubToken("");
      await initSession();
      await loadRepositories();
    } catch (err: any) {
      setGithubError(err?.message || "GitHub authentication failed.");
    } finally {
      setConnectingGithub(false);
    }
  };

  const handleSelectRepository = async (repo: GitHubRepo) => {
    try {
      setSelectedRepo(repo);
      const res = await selectRepository(repo);
      const backendRepoId = res?.repository?.id || repo.id;
      const currentRepoId = currentTask?.repository_id || currentTask?.repository?.id;
      if (currentTask && currentRepoId && currentRepoId !== backendRepoId) {
        setCurrentTask(null);
        setExecutionStatus(null);
        setTaskDiff(null);
        setTaskTimeline([]);
        setTaskTitle("");
        setTaskRequirement("");
      }
      if (backendRepoId) {
        await refreshTasksForRepo(String(backendRepoId));
      }
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
      const backendRepoId = String(repoRes.repository.id || "");

      // 2. Create task
      const newTask = await createTask(backendRepoId, taskTitle, taskRequirement);
      await refreshTasksForRepo(backendRepoId);

      // 3. Run full intelligence pipeline
      const taskDetail = await runTaskPipeline(newTask.id);
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
            ...(currentTask.approvals || []),
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
        setActiveTab("execution");
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
      setActiveTab("execution");
      setExecutingPlan(true);
      setExecutionError(null);
      await executeTask(currentTask.id);
      // Start polling
      setPollingExecution(true);
      pollExecutionStatus(currentTask.id);
    } catch (err: any) {
      setExecutionError(err?.message || "Failed to start execution.");
      setExecutingPlan(false);
      getExecutionStatus(currentTask.id).then(setExecutionStatus).catch(() => {});
    }
  };

  const handleResumePlan = async () => {
    if (!currentTask) return;
    try {
      setActiveTab("execution");
      setExecutingPlan(true);
      setExecutionError(null);
      await resumeExecution(currentTask.id);
      setPollingExecution(true);
      pollExecutionStatus(currentTask.id);
    } catch (err: any) {
      setExecutionError(err?.message || "Failed to resume execution.");
      setExecutingPlan(false);
      getExecutionStatus(currentTask.id).then(setExecutionStatus).catch(() => {});
    }
  };

  const handleStartQa = async () => {
    if (!currentTask) return;
    try {
      setActiveTab("qa");
      setRunningQa(true);
      setExecutionError(null);
      await runQa(currentTask.id);
      setPollingExecution(true);
      pollExecutionStatus(currentTask.id);
    } catch (err: any) {
      setExecutionError(err?.message || "Failed to start QA & Code Review.");
      setRunningQa(false);
      getExecutionStatus(currentTask.id).then(setExecutionStatus).catch(() => {});
    }
  };

  const pollExecutionStatus = async (taskId: string) => {
    const TERMINAL = ["AWAITING_DELIVERY", "COMPLETED", "FAILED", "CANCELLED", "CLOSED"];
    let attempts = 0;
    const MAX_ATTEMPTS = 120; // 10 min at 4s intervals
    const poll = async () => {
      try {
        const status = await getExecutionStatus(taskId);
        setExecutionStatus(status);
        if (status.status === "AWAITING_QA") {
          // Developer Agent implementation has finished and committed, awaiting QA
          setExecutingPlan(false);
          setRunningQa(false);
          setPollingExecution(false);
          getTask(taskId).then(setCurrentTask).catch(() => {});
          return;
        } else if (["QA_TESTING", "REVIEWING"].includes(status.status)) {
          setExecutingPlan(false);
          setRunningQa(true);
        } else if (["EXECUTING", "COMMITTING", "CLONING"].includes(status.status)) {
          setExecutingPlan(true);
          setRunningQa(false);
        }
        if (TERMINAL.includes(status.status) || attempts >= MAX_ATTEMPTS) {
          setPollingExecution(false);
          setExecutingPlan(false);
          setRunningQa(false);
          getTask(taskId).then(setCurrentTask).catch(() => {});
        } else {
          attempts++;
          setTimeout(poll, 4000);
        }
      } catch {
        setPollingExecution(false);
        setExecutingPlan(false);
        setRunningQa(false);
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

  const loadDiffAndTimeline = async (taskId?: string) => {
    const id = taskId || currentTask?.id;
    if (!id) return;
    try {
      setLoadingDiff(true);
      const diffData = await getTaskDiff(id);
      setTaskDiff(diffData);
    } catch (err: any) {
      console.warn("Failed to load diff:", err?.message);
    } finally {
      setLoadingDiff(false);
    }

    try {
      setLoadingTimeline(true);
      const timelineData = await getTaskTimeline(id);
      setTaskTimeline(timelineData.timeline || []);
    } catch (err: any) {
      console.warn("Failed to load timeline:", err?.message);
    } finally {
      setLoadingTimeline(false);
    }
  };

  const handleFinalApproval = async (decision: "APPROVED" | "REJECTED") => {
    if (!currentTask) return;
    try {
      setSubmittingFinalApproval(true);
      setDeliveryError(null);
      const res = await submitFinalApproval(currentTask.id, {
        decision,
        feedback: finalApprovalFeedback.trim() || undefined,
      });

      const approvalItem: DeliveryApprovalData = res.approval || {
        id: res.id,
        task_id: res.task_id || currentTask.id,
        decision: res.decision,
        feedback: res.feedback,
        decided_at: res.decided_at,
      };

      setCurrentTask((prev) =>
        prev
          ? {
              ...prev,
              status: res.task_status || prev.status,
              delivery_approvals: [
                approvalItem,
                ...(prev.delivery_approvals?.filter((a) => a && a.id !== approvalItem.id) || []),
              ].filter(Boolean),
            }
          : null
      );
      setFinalApprovalFeedback("");
      loadDiffAndTimeline(currentTask.id);
    } catch (err: any) {
      setDeliveryError(err?.message || "Failed to submit final approval decision.");
    } finally {
      setSubmittingFinalApproval(false);
    }
  };

  const handleDeliver = async () => {
    if (!currentTask) return;
    try {
      setDeliveringTask(true);
      setDeliveryError(null);
      const res = await deliverTask(currentTask.id);
      if (res.pull_request) {
        setCurrentTask((prev) =>
          prev
            ? {
                ...prev,
                status: "COMPLETED",
                is_delivered: true,
                pull_request: res.pull_request,
              }
            : null
        );
      }
      loadDiffAndTimeline(currentTask.id);
    } catch (err: any) {
      setDeliveryError(err?.message || "GitHub Delivery failed.");
    } finally {
      setDeliveringTask(false);
    }
  };

  useEffect(() => {
    if (currentTask?.id && (activeTab === "delivery" || activeTab === "all")) {
      loadDiffAndTimeline(currentTask.id);
    }
  }, [activeTab, currentTask?.id, currentTask?.status]);

  useEffect(() => {
    if (currentTask?.id && !executionStatus && !executingPlan) {
      getExecutionStatus(currentTask.id)
        .then(setExecutionStatus)
        .catch(() => {});
    }
  }, [currentTask?.id, executionStatus, executingPlan]);

  useEffect(() => {
    loadHealthData();
    initSession();
  }, []);

  const backendOnline = !healthError && health !== null;

  const chapterProgress = useMemo<ChapterStatusInfo[]>(() => {
    // Chapter 1: Foundation & Setup
    const ch1Complete = Boolean((user || patStatus?.has_pat) && health?.status !== undefined);
    const ch1Percent = ch1Complete ? 100 : health?.status === "healthy" ? 75 : 50;
    const ch1Status = ch1Complete ? "COMPLETED" : "IN_PROGRESS";
    const ch1Detail = ch1Complete ? "FastAPI, PostgreSQL & GitHub Connected" : "Connecting services...";

    // Chapter 2: Repo Intelligence & Architecture
    let ch2Percent = 0;
    let ch2Status: "COMPLETED" | "IN_PROGRESS" | "PENDING" | "FAILED" = "PENDING";
    let ch2Detail = "Select repository & formulate requirement";

    if (selectedRepo) {
      ch2Percent = 25;
      ch2Status = "IN_PROGRESS";
      ch2Detail = `Selected ${selectedRepo.name}`;
    }

    if (currentTask) {
      if (["INSPECTING", "ANALYZING", "PLANNING"].includes(currentTask.status)) {
        ch2Percent = 50;
        ch2Status = "IN_PROGRESS";
        ch2Detail = `Architect Agent ${currentTask.status.toLowerCase()}...`;
      } else if (currentTask.status === "AWAITING_APPROVAL") {
        ch2Percent = 75;
        ch2Status = "IN_PROGRESS";
        ch2Detail = "Implementation plan ready • Awaiting review";
      } else if (currentTask.status === "REJECTED") {
        ch2Percent = 60;
        ch2Status = "FAILED";
        ch2Detail = "Plan rejected by user";
      } else if (
        ["APPROVED", "EXECUTING", "AWAITING_QA", "AWAITING_REVIEW", "AWAITING_DELIVERY", "CLOSED"].includes(
          currentTask.status
        )
      ) {
        ch2Percent = 100;
        ch2Status = "COMPLETED";
        ch2Detail = "Plan Approved by Human Reviewer";
      }
    }

    // Chapter 3: Autonomous Development Engine
    let ch3Percent = 0;
    let ch3Status: "COMPLETED" | "IN_PROGRESS" | "PENDING" | "FAILED" = "PENDING";
    let ch3Detail = "Awaiting developer execution";

    const isExecutingOrPastCh3 =
      executionStatus &&
      ["CLONING", "EXECUTING", "COMMITTING", "QA_TESTING", "REVIEWING", "AWAITING_QA", "AWAITING_REVIEW", "AWAITING_DELIVERY", "CLOSED"].includes(
        executionStatus.status
      );

    if (currentTask?.status === "APPROVED" && !isExecutingOrPastCh3) {
      ch3Percent = 0;
      ch3Status = "PENDING";
      ch3Detail = "Approved • Ready to execute";
    } else if (executionStatus?.status === "CLONING") {
      ch3Percent = 20;
      ch3Status = "IN_PROGRESS";
      ch3Detail = "Cloning & isolating workspace...";
    } else if (executionStatus?.status === "EXECUTING") {
      const total = Math.max(executionStatus.total_steps || 1, 1);
      const curr = executionStatus.current_step || 0;
      ch3Percent = Math.min(85, Math.round(20 + (curr / total) * 65));
      ch3Status = "IN_PROGRESS";
      ch3Detail = `Developer Step ${curr} of ${total}`;
    } else if (executionStatus?.status === "COMMITTING") {
      ch3Percent = 90;
      ch3Status = "IN_PROGRESS";
      ch3Detail = "Staging & committing to task branch...";
    } else if (
      ["AWAITING_QA", "AWAITING_REVIEW", "AWAITING_DELIVERY", "CLOSED"].includes(executionStatus?.status || "") ||
      ["AWAITING_QA", "AWAITING_REVIEW", "AWAITING_DELIVERY", "CLOSED"].includes(currentTask?.status || "")
    ) {
      ch3Percent = 100;
      ch3Status = "COMPLETED";
      ch3Detail = "Changes committed to task branch";
    } else if (executionStatus?.status === "FAILED" || currentTask?.status === "FAILED") {
      ch3Percent = 50;
      ch3Status = "FAILED";
      ch3Detail = executionStatus?.error_message?.slice(0, 45) || "Execution encountered an error";
    }

    // Chapter 4: QA & Code Review
    let ch4Percent = 0;
    let ch4Status: "COMPLETED" | "IN_PROGRESS" | "PENDING" | "FAILED" = "PENDING";
    let ch4Detail = "Awaiting QA & review";

    const hasQa = Boolean(executionStatus?.qa_reports && executionStatus.qa_reports.length > 0);
    const hasReview = Boolean(executionStatus?.review_reports && executionStatus.review_reports.length > 0);
    const reviewApproved = Boolean(executionStatus?.review_reports?.some((r) => r.outcome === "APPROVED"));
    const isAwaitingDelivery = currentTask?.status === "AWAITING_DELIVERY" || executionStatus?.status === "AWAITING_DELIVERY";

    if (isAwaitingDelivery || reviewApproved) {
      ch4Percent = 100;
      ch4Status = "COMPLETED";
      ch4Detail = "Tests Passed & Code Review APPROVED";
    } else if (executionStatus?.status === "AWAITING_REVIEW" || (hasQa && !hasReview)) {
      ch4Percent = 60;
      ch4Status = "IN_PROGRESS";
      ch4Detail = `QA Cycle #${executionStatus?.qa_reports?.length || 1} • Reviewing diff...`;
    } else if (executionStatus?.status === "AWAITING_QA") {
      ch4Percent = 25;
      ch4Status = "IN_PROGRESS";
      ch4Detail = "Running repository-aware test suite...";
    } else if (
      (executionStatus?.status === "FAILED" || currentTask?.status === "FAILED") &&
      hasQa
    ) {
      ch4Percent = 50;
      ch4Status = "FAILED";
      ch4Detail = `QA Tests Failed (${executionStatus?.qa_reports?.length || 0} cycles)`;
    }

    // Chapter 5: GitHub Delivery
    let ch5Percent = 0;
    let ch5Status: "COMPLETED" | "IN_PROGRESS" | "PENDING" | "FAILED" = "PENDING";
    let ch5Detail = isAwaitingDelivery ? "Ready for GitHub PR Delivery" : "Awaiting Chapter 4 completion";

    const hasDeliveredPr = Boolean(currentTask?.pull_request || currentTask?.is_delivered);
    const hasFinalApproval = Boolean(currentTask?.delivery_approvals?.some((a) => a?.decision === "APPROVED"));
    const hasFinalRejection = Boolean(currentTask?.delivery_approvals?.some((a) => a?.decision === "REJECTED"));

    if (currentTask?.status === "COMPLETED" || hasDeliveredPr) {
      ch5Percent = 100;
      ch5Status = "COMPLETED";
      ch5Detail = currentTask?.pull_request?.pr_number
        ? `Pull Request #${currentTask.pull_request.pr_number} Delivered`
        : "Delivery completed";
    } else if (isAwaitingDelivery) {
      if (hasFinalApproval) {
        ch5Percent = 75;
        ch5Status = "IN_PROGRESS";
        ch5Detail = "Approval 2 granted • Ready to deliver PR";
      } else if (hasFinalRejection) {
        ch5Percent = 40;
        ch5Status = "FAILED";
        ch5Detail = "Delivery rejected by reviewer";
      } else {
        ch5Percent = 50;
        ch5Status = "IN_PROGRESS";
        ch5Detail = "Awaiting final Human Approval 2";
      }
    } else if (currentTask?.status === "CLOSED") {
      ch5Percent = 100;
      ch5Status = "COMPLETED";
      ch5Detail = "Delivery completed";
    }

    return [
      {
        num: 1,
        title: "Foundation & Setup",
        shortTitle: "Ch. 1 Foundation",
        desc: "FastAPI, PostgreSQL & LLM Base",
        status: ch1Status,
        percent: ch1Percent,
        detail: ch1Detail,
        tab: "diagnostics",
      },
      {
        num: 2,
        title: "Repo Intelligence",
        shortTitle: "Ch. 2 Intelligence",
        desc: "Codebase Analysis & Architect Plan",
        status: ch2Status,
        percent: ch2Percent,
        detail: ch2Detail,
        tab: "planning",
      },
      {
        num: 3,
        title: "Autonomous Engine",
        shortTitle: "Ch. 3 Autonomous Dev",
        desc: "Developer Agent & Git Commit",
        status: ch3Status,
        percent: ch3Percent,
        detail: ch3Detail,
        tab: "execution",
      },
      {
        num: 4,
        title: "QA & Code Review",
        shortTitle: "Ch. 4 QA & Review",
        desc: "Test Discovery, Feedback & Reviewer",
        status: ch4Status,
        percent: ch4Percent,
        detail: ch4Detail,
        tab: "qa",
      },
      {
        num: 5,
        title: "GitHub Delivery",
        shortTitle: "Ch. 5 Delivery",
        desc: "PR Creation & Final Audit",
        status: ch5Status,
        percent: ch5Percent,
        detail: ch5Detail,
        tab: "delivery",
      },
    ];
  }, [health, user, patStatus, selectedRepo, currentTask, executionStatus]);

  const filteredRepos = repositories.filter(
    (r) =>
      r.name.toLowerCase().includes(repoSearch.toLowerCase()) ||
      r.full_name.toLowerCase().includes(repoSearch.toLowerCase())
  );

  return (
    <div className="min-h-screen flex flex-col bg-[#090d16] text-gray-100">
      <Header
        backendOnline={backendOnline}
        user={user}
        patStatus={patStatus}
        onOpenPatModal={() => setIsPatModalOpen(true)}
        onLogin={handleLogin}
        onLogout={handleLogout}
      />
      <PatModal
        isOpen={isPatModalOpen}
        patStatus={patStatus}
        onClose={() => setIsPatModalOpen(false)}
        onSaved={async (newStatus) => {
          setPatStatus(newStatus);
          await initSession();
          await loadRepositories();
        }}
      />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          activeTab={activeTab}
          onTabChange={setActiveTab}
          chapters={chapterProgress}
          selectedRepo={selectedRepo}
          currentTask={currentTask}
          onStartNewProject={handleStartNewProject}
          onStartNewTask={handleStartNewTask}
        />

        <main className="flex-1 overflow-y-auto p-6 md:p-8 space-y-6">
          {/* Global Project & Task Context Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-xl bg-gradient-to-r from-gray-950 via-[#0d1424] to-gray-950 border border-gray-800 shadow-lg">
            {/* Left: Active Project & Task with Switchers */}
            <div className="flex flex-wrap items-center gap-2.5">
              {/* Project / Repo Selector Dropdown */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => {
                    setIsProjectDropdownOpen(!isProjectDropdownOpen);
                    setIsTaskDropdownOpen(false);
                  }}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-900/90 border border-gray-700 hover:border-gray-500 text-xs text-white transition-all shadow-sm"
                  title="Switch repository or start new project"
                >
                  <FolderGit2 className="w-4 h-4 text-blue-400 shrink-0" />
                  <span className="font-semibold text-gray-200 truncate max-w-[200px]">
                    {selectedRepo ? selectedRepo.full_name : "No Project Selected"}
                  </span>
                  <span className="text-[9px] text-gray-400 font-mono">▼</span>
                </button>

                {isProjectDropdownOpen && (
                  <div className="absolute left-0 mt-2 w-72 rounded-xl bg-gray-950 border border-gray-800 shadow-2xl z-50 p-2 space-y-1">
                    <div className="px-2 py-1 text-[10px] font-bold text-gray-400 uppercase tracking-wider flex items-center justify-between">
                      <span>Projects / Repositories</span>
                      <span className="text-gray-500 font-mono">{repositories.length}</span>
                    </div>
                    <div className="max-h-56 overflow-y-auto space-y-1 pr-1">
                      {repositories.length > 0 ? (
                        repositories.map((r) => (
                          <button
                            key={r.full_name}
                            type="button"
                            onClick={() => {
                              handleSwitchProject(r);
                              setIsProjectDropdownOpen(false);
                            }}
                            className={`w-full text-left p-2 rounded-lg text-xs flex items-center justify-between transition-colors ${
                              selectedRepo?.full_name === r.full_name
                                ? "bg-blue-950/60 border border-blue-800/80 text-white font-medium"
                                : "text-gray-300 hover:bg-gray-900"
                            }`}
                          >
                            <div className="truncate min-w-0 pr-2">
                              <div className="font-semibold truncate">{r.name}</div>
                              <div className="text-[10px] text-gray-500 truncate">{r.full_name}</div>
                            </div>
                            {selectedRepo?.full_name === r.full_name && (
                              <Check className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                            )}
                          </button>
                        ))
                      ) : (
                        <div className="p-3 text-center text-xs text-gray-500">
                          No repositories loaded yet.
                        </div>
                      )}
                    </div>
                    <div className="pt-2 border-t border-gray-800">
                      <button
                        type="button"
                        onClick={() => {
                          handleStartNewProject();
                          setIsProjectDropdownOpen(false);
                        }}
                        className="w-full p-2 rounded-lg text-xs font-semibold text-purple-400 hover:bg-purple-950/40 hover:text-purple-300 flex items-center gap-1.5 transition-colors"
                      >
                        <FolderGit2 className="w-3.5 h-3.5" /> + Connect / Switch to New Project
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Task Selector Dropdown (if project selected) */}
              {selectedRepo && (
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => {
                      setIsTaskDropdownOpen(!isTaskDropdownOpen);
                      setIsProjectDropdownOpen(false);
                    }}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-900/90 border border-gray-700 hover:border-gray-500 text-xs text-white transition-all shadow-sm"
                    title="Switch task or start new task in this repository"
                  >
                    <Terminal className="w-3.5 h-3.5 text-purple-400 shrink-0" />
                    <span className="font-medium text-gray-300 max-w-[200px] truncate">
                      {currentTask ? currentTask.title : "New Task Formulation"}
                    </span>
                    {currentTask && (
                      <span className={`text-[9px] px-1.5 py-0.2 rounded font-mono font-semibold shrink-0 ${
                        currentTask.is_delivered || currentTask.status === "COMPLETED"
                          ? "bg-emerald-950 text-emerald-300 border border-emerald-800/60"
                          : currentTask.status === "APPROVED"
                          ? "bg-purple-950 text-purple-300 border border-purple-800/60"
                          : "bg-blue-950 text-blue-300 border border-blue-800/60"
                      }`}>
                        {currentTask.is_delivered ? "DELIVERED" : currentTask.status}
                      </span>
                    )}
                    <span className="text-[9px] text-gray-400 font-mono">▼</span>
                  </button>

                  {isTaskDropdownOpen && (
                    <div className="absolute left-0 mt-2 w-80 rounded-xl bg-gray-950 border border-gray-800 shadow-2xl z-50 p-2 space-y-1">
                      <div className="px-2 py-1 text-[10px] font-bold text-gray-400 uppercase tracking-wider flex items-center justify-between">
                        <span>Tasks in {selectedRepo.name}</span>
                        <span className="text-gray-500 font-mono">{availableTasks.length}</span>
                      </div>
                      <div className="max-h-56 overflow-y-auto space-y-1 pr-1">
                        {availableTasks.length > 0 ? (
                          availableTasks.map((t) => (
                            <button
                              key={t.id}
                              type="button"
                              onClick={() => {
                                handleSwitchTask(t.id);
                                setIsTaskDropdownOpen(false);
                              }}
                              className={`w-full text-left p-2 rounded-lg text-xs flex items-center justify-between gap-2 transition-colors ${
                                currentTask?.id === t.id
                                  ? "bg-purple-950/60 border border-purple-800/80 text-white font-medium"
                                  : "text-gray-300 hover:bg-gray-900"
                              }`}
                            >
                              <div className="truncate min-w-0 flex-1">
                                <div className="font-semibold truncate">{t.title}</div>
                                <div className="text-[10px] text-gray-500 truncate">
                                  {t.created_at ? new Date(t.created_at).toLocaleDateString() : ""}
                                  {t.pr_number ? ` • PR #${t.pr_number}` : ""}
                                </div>
                              </div>
                              <span className={`text-[9px] px-1.5 py-0.5 rounded font-mono font-semibold shrink-0 ${
                                t.is_delivered || t.status === "COMPLETED"
                                  ? "bg-emerald-950 text-emerald-300 border border-emerald-800/60"
                                  : "bg-gray-800 text-gray-400"
                              }`}>
                                {t.is_delivered ? "DELIVERED" : t.status}
                              </span>
                            </button>
                          ))
                        ) : (
                          <div className="p-3 text-center text-xs text-gray-500">
                            No tasks for this project yet.
                          </div>
                        )}
                      </div>
                      <div className="pt-2 border-t border-gray-800">
                        <button
                          type="button"
                          onClick={() => {
                            handleStartNewTask();
                            setIsTaskDropdownOpen(false);
                          }}
                          className="w-full p-2 rounded-lg text-xs font-semibold text-blue-400 hover:bg-blue-950/40 hover:text-blue-300 flex items-center gap-1.5 transition-colors"
                        >
                          <FilePlus className="w-3.5 h-3.5" /> + Formulate New Task
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Right: Quick Action Buttons */}
            <div className="flex items-center gap-2 self-start sm:self-auto">
              {selectedRepo && (
                <button
                  type="button"
                  onClick={handleStartNewTask}
                  className="px-3 py-1.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/40 text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm"
                  title="Start a new task in this repository"
                >
                  <FilePlus className="w-3.5 h-3.5" />
                  + New Task
                </button>
              )}
              <button
                type="button"
                onClick={handleStartNewProject}
                className="px-3 py-1.5 rounded-lg bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/40 text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm"
                title="Switch to another repository or start a new project"
              >
                <FolderGit2 className="w-3.5 h-3.5" />
                + New Project
              </button>
            </div>
          </div>
          {/* Chapter Progress & Status Bars across all 5 chapters */}
          <ChapterProgressBar
            chapters={chapterProgress}
            activeTab={activeTab}
            onTabChange={setActiveTab}
          />

          {/* Chapter View Switcher Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-gray-950/80 border border-gray-800 shadow-md">
            <div className="flex items-center gap-1.5 overflow-x-auto">
              <span className="text-[10px] uppercase font-bold tracking-wider text-gray-500 px-2 shrink-0">
                Phase View:
              </span>
              <button
                type="button"
                onClick={() => setActiveTab("planning")}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 shrink-0 ${
                  activeTab === "planning"
                    ? "bg-purple-600 text-white shadow-lg shadow-purple-950/50"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-900/60"
                }`}
              >
                <GitBranch className="w-3.5 h-3.5" />
                Ch. 2: Intelligence &amp; Plan
                {currentTask && (
                  <span className={`w-2 h-2 rounded-full ${
                    currentTask.status === "APPROVED" ? "bg-emerald-400" : "bg-purple-400"
                  }`} />
                )}
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("execution")}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 shrink-0 ${
                  activeTab === "execution"
                    ? "bg-purple-600 text-white shadow-lg shadow-purple-950/50"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-900/60"
                }`}
              >
                <Cpu className="w-3.5 h-3.5" />
                Ch. 3: Autonomous Dev
                {executionStatus && (
                  <span className={`w-2 h-2 rounded-full ${
                    ["AWAITING_QA", "AWAITING_REVIEW", "AWAITING_DELIVERY", "COMPLETED"].includes(executionStatus.status)
                      ? "bg-emerald-400"
                      : ["CLONING", "EXECUTING", "COMMITTING"].includes(executionStatus.status)
                      ? "bg-blue-400 animate-pulse"
                      : executionStatus.status === "FAILED"
                      ? "bg-rose-400"
                      : "bg-gray-500"
                  }`} />
                )}
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("qa")}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 shrink-0 ${
                  activeTab === "qa"
                    ? "bg-purple-600 text-white shadow-lg shadow-purple-950/50"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-900/60"
                }`}
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                Ch. 4: QA &amp; Review
                {executionStatus && (
                  <span className={`w-2 h-2 rounded-full ${
                    executionStatus.status === "AWAITING_DELIVERY"
                      ? "bg-emerald-400"
                      : executionStatus.qa_reports && executionStatus.qa_reports.length > 0
                      ? (executionStatus.qa_reports[executionStatus.qa_reports.length - 1].overall_passed ? "bg-emerald-400" : "bg-rose-400")
                      : executionStatus.status === "AWAITING_QA"
                      ? "bg-amber-400"
                      : "bg-gray-500"
                  }`} />
                )}
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("delivery")}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 shrink-0 ${
                  activeTab === "delivery"
                    ? "bg-purple-600 text-white shadow-lg shadow-purple-950/50"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-900/60"
                }`}
              >
                <Send className="w-3.5 h-3.5" />
                Ch. 5: Delivery &amp; PR
                {currentTask && (
                  <span
                    className={`w-2 h-2 rounded-full ${
                      currentTask.pull_request || currentTask.is_delivered || currentTask.status === "COMPLETED"
                        ? "bg-emerald-400"
                        : currentTask.status === "AWAITING_DELIVERY"
                        ? "bg-blue-400 animate-pulse"
                        : "bg-gray-500"
                    }`}
                  />
                )}
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("diagnostics")}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 shrink-0 ${
                  activeTab === "diagnostics"
                    ? "bg-purple-600 text-white shadow-lg shadow-purple-950/50"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-900/60"
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                Ch. 1: Diagnostics
              </button>
            </div>

            <button
              type="button"
              onClick={() => setActiveTab(activeTab === "all" ? "planning" : "all")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 shrink-0 border ${
                activeTab === "all"
                  ? "bg-indigo-950/80 border-indigo-700/80 text-indigo-300 ring-1 ring-indigo-500/40"
                  : "border-gray-800 text-gray-400 hover:text-white hover:bg-gray-900/60"
              }`}
            >
              <Sliders className="w-3.5 h-3.5 text-indigo-400" />
              {activeTab === "all" ? "Focused Chapter Mode" : "Full Pipeline (All Chapters)"}
            </button>
          </div>

          {/* Chapter 1 — Engineering Foundation */}
          {(activeTab === "diagnostics" || activeTab === "all") && (
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

          {/* Chapter 2: Repo Intelligence, Formulation & Architecture Plan */}
          {(activeTab === "planning" || activeTab === "all") && (
            <div className="space-y-6">
              {/* Header Title */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-gray-800">
                <div>
                  <div className="flex items-center gap-2">
                    <h1 className="text-2xl font-bold tracking-tight text-white">
                      Chapter 2 — Repository Intelligence &amp; Formulated Requirements
                    </h1>
                    <StatusBadge
                      status={
                        currentTask?.status === "APPROVED"
                          ? "COMPLETED"
                          : ["INSPECTING", "ANALYZING", "PLANNING"].includes(currentTask?.status || "")
                          ? "IN_PROGRESS"
                          : currentTask?.status === "AWAITING_APPROVAL"
                          ? "AWAITING_APPROVAL"
                          : selectedRepo
                          ? "ACTIVE"
                          : "PENDING"
                      }
                      label={
                        currentTask?.status === "APPROVED"
                          ? "PLAN APPROVED"
                          : currentTask?.status === "AWAITING_APPROVAL"
                          ? "AWAITING HUMAN APPROVAL"
                          : undefined
                      }
                    />
                  </div>
                  <p className="text-sm text-gray-400 mt-1">
                    Connect repository, analyze existing codebase architecture, formulate requirements via Product Analyst, and review the Architect plan.
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
                      <h3 className="text-sm font-semibold text-white">GitHub Authorization &amp; Repository Access</h3>
                      <p className="text-xs text-gray-400">
                        {user ? (
                          patStatus?.has_pat && patStatus?.is_valid ? (
                            <span className="text-emerald-400 flex items-center gap-1.5 mt-0.5">
                              <CheckCircle className="w-3.5 h-3.5" /> Authenticated as{" "}
                              <span className="font-semibold text-white">{user.username}</span> • PAT:{" "}
                              <span className="font-mono text-emerald-300">{patStatus.pat_masked || "Active"}</span> (Encrypted)
                            </span>
                          ) : (
                            <span className="text-amber-400 flex items-center gap-1.5 mt-0.5">
                              <AlertTriangle className="w-3.5 h-3.5" /> Signed in as{" "}
                              <span className="font-semibold text-white">{user.username}</span>. Personal Access Token required to clone and modify code.
                            </span>
                          )
                        ) : (
                          "Sign in with GitHub or enter a Personal Access Token (PAT) with repo scope."
                        )}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {user ? (
                      <button
                        type="button"
                        onClick={() => setIsPatModalOpen(true)}
                        className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-medium text-white transition-colors"
                      >
                        {patStatus?.has_pat ? "Manage PAT" : "Configure PAT"}
                      </button>
                    ) : (
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={handleLogin}
                          className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white transition-colors flex items-center gap-1.5 shadow-sm"
                        >
                          <Github className="w-3.5 h-3.5" />
                          Sign in
                        </button>
                        <button
                          type="button"
                          onClick={handleDevLogin}
                          className="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs font-medium text-gray-300 border border-gray-700 transition-colors"
                          title="Local Dev Login"
                        >
                          Dev Login
                        </button>
                        <input
                          type="password"
                          placeholder="ghp_xxxxxxxxxxxx"
                          value={githubToken}
                          onChange={(e) => setGithubToken(e.target.value)}
                          className="px-3 py-1.5 rounded-lg bg-gray-950 border border-gray-700 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 w-48 font-mono"
                        />
                        <button
                          onClick={handleConnectGitHub}
                          disabled={connectingGithub}
                          className="px-3.5 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs font-medium text-white border border-gray-700 transition-colors disabled:opacity-50"
                        >
                          {connectingGithub ? "Saving..." : "Save PAT"}
                        </button>
                      </div>
                    )}
                  </div>
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
                    <button
                      onClick={() => loadRepositories()}
                      disabled={loadingRepos}
                      className="text-gray-400 hover:text-white"
                      title="Refresh repositories"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${loadingRepos ? "animate-spin" : ""}`} />
                    </button>
                  </div>

                  {(user || githubUser || repositories.length > 0) ? (
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
                    <div className="flex items-center gap-2">
                      {currentTask && (
                        <button
                          type="button"
                          onClick={handleStartNewTask}
                          className="px-2.5 py-1 rounded bg-blue-600/30 hover:bg-blue-600/40 text-blue-300 border border-blue-500/50 text-[11px] font-semibold flex items-center gap-1 transition-colors"
                          title="Start formulating a new task in this repository"
                        >
                          <FilePlus className="w-3 h-3" /> + New Task Form
                        </button>
                      )}
                      {selectedRepo && (
                        <span className="text-xs text-emerald-400 font-mono flex items-center gap-1.5">
                          <FolderGit2 className="w-3.5 h-3.5" /> {selectedRepo.full_name} ({selectedRepo.default_branch})
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Previous Project Tasks Switcher */}
                  {selectedRepo && availableTasks.length > 0 && (
                    <div className="p-3 rounded-lg bg-gray-950/70 border border-gray-800 space-y-2">
                      <div className="flex items-center justify-between text-[11px] text-gray-400">
                        <span className="font-semibold text-gray-300 uppercase tracking-wider text-[10px]">
                          Tasks in this Project ({availableTasks.length})
                        </span>
                        <span className="text-gray-500 text-[10px]">Click any task to view or switch</span>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {availableTasks.map((t) => (
                          <button
                            key={t.id}
                            type="button"
                            onClick={() => handleSwitchTask(t.id)}
                            className={`px-2.5 py-1.5 rounded-lg border text-xs flex items-center gap-1.5 transition-all text-left ${
                              currentTask?.id === t.id
                                ? "bg-purple-950/60 border-purple-600 text-white font-medium shadow-sm"
                                : "bg-gray-900 border-gray-800 text-gray-300 hover:bg-gray-800/80 hover:text-white"
                            }`}
                          >
                            <Terminal className="w-3 h-3 text-purple-400 shrink-0" />
                            <span className="truncate max-w-[160px] font-medium">{t.title}</span>
                            <span
                              className={`text-[9px] px-1 py-0.2 rounded font-mono ${
                                t.is_delivered
                                  ? "bg-emerald-950 text-emerald-300 border border-emerald-800/60"
                                  : "bg-gray-800 text-gray-400"
                              }`}
                            >
                              {t.is_delivered ? "PR" : t.status}
                            </span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

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
                      <span className={(currentTask.is_plan_approved || currentTask.plan_approval_status === "APPROVED" || currentTask.status === "APPROVED") ? "text-green-400 font-semibold" : "text-blue-400 font-semibold"}>4. Human Review</span>
                      {(currentTask.is_plan_approved || currentTask.plan_approval_status === "APPROVED" || currentTask.status === "APPROVED") && (
                        <>
                          <ChevronRight className="w-3.5 h-3.5" />
                          <span className={
                            executionStatus?.status === "FAILED" || currentTask.status === "FAILED"
                              ? "text-rose-400 font-semibold"
                              : ["EXECUTING","COMMITTING","AWAITING_QA","AWAITING_REVIEW","AWAITING_DELIVERY","CLOSED"].includes(executionStatus?.status || "")
                              ? "text-purple-400 font-semibold"
                              : "text-gray-500"
                          }>
                            {executionStatus?.status === "FAILED" || currentTask.status === "FAILED" ? "5. Dev Agent (Failed)" : "5. Dev Agent"}
                          </span>
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
                        <StatusBadge status={currentTask.plan_approval_status || (currentTask.is_plan_approved ? "APPROVED" : "FORMULATED")} />
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
                              disabled={submittingApproval || Boolean(currentTask.is_plan_approved || currentTask.plan_approval_status === "APPROVED" || currentTask.status === "APPROVED")}
                              className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white transition-colors disabled:opacity-50 flex items-center gap-1.5 shadow-md shadow-emerald-900/20"
                            >
                              <Check className="w-3.5 h-3.5" />
                              {submittingApproval && approvalAction === "APPROVED"
                                ? "Approving..."
                                : (currentTask.is_plan_approved || currentTask.plan_approval_status === "APPROVED" || currentTask.status === "APPROVED")
                                ? "Plan Approved"
                                : "Approve Plan"}
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
                        {currentTask.approvals && currentTask.approvals.length > 0 && (
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

                  {/* If plan is approved, show prominent transition card to Chapter 3 */}
                  {(currentTask.is_plan_approved || currentTask.plan_approval_status === "APPROVED" || currentTask.status === "APPROVED" || ["CLONING", "EXECUTING", "COMMITTING", "AWAITING_QA", "AWAITING_REVIEW", "AWAITING_DELIVERY", "COMPLETED"].includes(currentTask.status)) && (
                    <div className="p-4 rounded-xl bg-gradient-to-r from-emerald-950/60 via-purple-950/40 to-blue-950/60 border border-emerald-800/70 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-lg">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-lg bg-emerald-900/60 border border-emerald-700/60 flex items-center justify-center text-emerald-400 shrink-0">
                          <CheckCircle2 className="w-5 h-5" />
                        </div>
                        <div>
                          <div className="font-semibold text-white text-xs sm:text-sm">Plan Approved by Human Reviewer</div>
                          <p className="text-[11px] text-gray-300 mt-0.5">
                            Target repository architecture formulated. Launch the Developer Agent to autonomously execute plan steps in Chapter 3.
                          </p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => setActiveTab("execution")}
                        className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-xs font-semibold text-white flex items-center gap-1.5 shrink-0 transition-colors shadow-md shadow-purple-950/50"
                      >
                        <Cpu className="w-3.5 h-3.5" />
                        Go to Chapter 3: Autonomous Dev
                        <ArrowRight className="w-3.5 h-3.5 ml-0.5" />
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Chapter 3 — Autonomous Development Engine */}
          {(activeTab === "execution" || activeTab === "all") && (
            <div className="space-y-6">
              {/* Header Title */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-gray-800">
                <div>
                  <div className="flex items-center gap-2">
                    <h1 className="text-2xl font-bold tracking-tight text-white">
                      Chapter 3 — Autonomous Development Engine
                    </h1>
                    <StatusBadge
                      status={
                        ["AWAITING_QA", "AWAITING_REVIEW", "AWAITING_DELIVERY", "COMPLETED"].includes(executionStatus?.status || "")
                          ? "COMPLETED"
                          : ["CLONING", "EXECUTING", "COMMITTING"].includes(executionStatus?.status || "")
                          ? "IN_PROGRESS"
                          : executionStatus?.status === "FAILED"
                          ? "FAILED"
                          : executionStatus?.status === "CANCELLED"
                          ? "CANCELLED"
                          : (currentTask?.is_plan_approved || currentTask?.plan_approval_status === "APPROVED" || currentTask?.status === "APPROVED")
                          ? "READY"
                          : "PENDING"
                      }
                      label={
                        ["AWAITING_QA", "AWAITING_REVIEW", "AWAITING_DELIVERY", "COMPLETED"].includes(executionStatus?.status || "")
                          ? "CODE COMMITTED"
                          : ["CLONING", "EXECUTING", "COMMITTING"].includes(executionStatus?.status || "")
                          ? "DEVELOPER RUNNING"
                          : (currentTask?.is_plan_approved || currentTask?.plan_approval_status === "APPROVED" || currentTask?.status === "APPROVED")
                          ? "READY FOR EXECUTION"
                          : "AWAITING PLAN"
                      }
                    />
                  </div>
                  <p className="text-sm text-gray-400 mt-1">
                    Developer Agent executes approved plan steps in an isolated Git workspace, generating code and creating atomic commits on a task branch.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400 font-mono">Model:</span>
                  <span className="text-xs px-2.5 py-1 rounded-md bg-blue-950/60 border border-blue-800/60 text-blue-300 font-mono">
                    {health?.components.llm.model || "openai/gpt-oss-120b"}
                  </span>
                </div>
              </div>

              {!currentTask ? (
                <div className="p-8 rounded-xl bg-gray-900/40 border border-gray-800 text-center space-y-3">
                  <div className="w-12 h-12 rounded-xl bg-gray-800/80 border border-gray-700/60 flex items-center justify-center mx-auto text-gray-400">
                    <Cpu className="w-6 h-6" />
                  </div>
                  <h3 className="text-sm font-semibold text-white">No Active Task Selected</h3>
                  <p className="text-xs text-gray-400 max-w-md mx-auto">
                    Select a repository and generate an implementation plan in Chapter 2 before launching the autonomous development engine.
                  </p>
                  <div>
                    <button
                      type="button"
                      onClick={() => setActiveTab("planning")}
                      className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white transition-colors"
                    >
                      Go to Chapter 2: Repo Intelligence
                    </button>
                  </div>
                </div>
              ) : !(currentTask.is_plan_approved || currentTask.plan_approval_status === "APPROVED" || currentTask.status === "APPROVED" || executionStatus !== null) ? (
                <div className="p-8 rounded-xl bg-gray-900/40 border border-gray-800 text-center space-y-3">
                  <div className="w-12 h-12 rounded-xl bg-amber-950/40 border border-amber-800/60 flex items-center justify-center mx-auto text-amber-400">
                    <AlertTriangle className="w-6 h-6" />
                  </div>
                  <h3 className="text-sm font-semibold text-white">Awaiting Plan Approval</h3>
                  <p className="text-xs text-gray-400 max-w-md mx-auto">
                    Task <code className="text-purple-300 font-mono">{currentTask.title}</code> requires human review and approval in Chapter 2 before developer execution can begin.
                  </p>
                  <div>
                    <button
                      type="button"
                      onClick={() => setActiveTab("planning")}
                      className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-xs font-semibold text-white transition-colors"
                    >
                      Review &amp; Approve Plan in Chapter 2
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-5">
                  {/* Task & Branch Summary Card */}
                  <div className="p-5 rounded-xl bg-gray-900/60 border border-purple-900/40 space-y-4 shadow-xl shadow-purple-950/10">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-gray-800 gap-3">
                      <div className="flex items-center gap-2.5">
                        <div className="p-2 rounded-lg bg-purple-950/60 border border-purple-800/60 text-purple-400">
                          <Terminal className="w-5 h-5" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="text-sm font-semibold text-white">{currentTask.title}</h4>
                            <StatusBadge
                              status={executionStatus?.status || (currentTask.status === "APPROVED" ? "READY" : currentTask.status)}
                            />
                          </div>
                          <p className="text-xs text-gray-400 mt-0.5">
                            Target Repo: <span className="text-gray-300 font-mono">{currentTask.repository?.full_name}</span>
                          </p>
                        </div>
                      </div>

                      {/* Git Branch Badge */}
                      <div className="flex items-center gap-2">
                        <span className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-gray-950 border border-gray-800 text-[11px] font-mono text-purple-300">
                          <GitBranch className="w-3.5 h-3.5 text-purple-400" />
                          {executionStatus?.branch_name || `devpilot/task-${currentTask.id.slice(0, 8)}`}
                        </span>
                      </div>
                    </div>

                    {/* Security & Sandbox Info */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      <div className="p-3 rounded-lg bg-gray-950/60 border border-gray-800/80 flex items-center gap-2.5">
                        <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                        <div>
                          <div className="font-semibold text-emerald-300 text-[11px]">Branch Isolation Active</div>
                          <div className="text-[10px] text-gray-400">Default branch ({currentTask.repository?.default_branch || "master"}) strictly protected. Changes confined to task branch.</div>
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
                        ) : runningQa || ["QA_TESTING", "REVIEWING"].includes(executionStatus?.status || "") ? (
                          <div className="flex items-center gap-2 text-teal-300">
                            <RefreshCw className="w-4 h-4 animate-spin text-teal-400" />
                            <span className="font-semibold">QA &amp; Code Review Pipeline Active:</span>
                            <span className="text-gray-400">
                              {executionStatus?.status === "QA_TESTING"
                                ? `Running QA test cycle #${(executionStatus?.qa_reports?.length || 0) + 1}...`
                                : "Code Auditor verifying modifications against base branch..."}
                            </span>
                            <button
                              type="button"
                              onClick={() => setActiveTab("qa")}
                              className="ml-2 text-xs text-teal-400 underline hover:text-teal-300 font-semibold"
                            >
                              View in Ch. 4 &rarr;
                            </button>
                          </div>
                        ) : ["AWAITING_QA", "AWAITING_REVIEW", "AWAITING_DELIVERY", "COMPLETED"].includes(executionStatus?.status || "") ? (
                          <div className="flex items-center gap-2 text-emerald-400 font-semibold">
                            <CheckCircle className="w-4 h-4" />
                            Implementation Complete — Code Committed to Task Branch
                            {executionStatus?.commit_sha && (
                              <span className="ml-2 px-2 py-0.5 rounded bg-emerald-950/80 border border-emerald-800/60 text-emerald-200 font-mono text-[10px]">
                                {executionStatus.commit_sha.slice(0, 7)}
                              </span>
                            )}
                          </div>
                        ) : executionStatus?.status === "FAILED" || currentTask.status === "FAILED" ? (
                          <div className="flex items-center gap-2 text-rose-400 font-semibold">
                            <AlertTriangle className="w-4 h-4 shrink-0" />
                            <span>Execution Encountered an Error: {executionStatus?.error_message || "QA retry limit exhausted or execution halted."}</span>
                          </div>
                        ) : executionStatus?.status === "CLOSED" || currentTask.status === "CLOSED" ? (
                          <div className="flex items-center gap-2 text-gray-400 font-semibold">
                            <CheckCircle className="w-4 h-4 text-gray-500" />
                            Task is Closed. Workspace has been released.
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
                          <>
                            {canResume && (
                              <button
                                onClick={handleResumePlan}
                                disabled={executingPlan || runningQa}
                                className="px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white transition-all shadow-lg shadow-emerald-950/40 flex items-center gap-2 disabled:opacity-40"
                              >
                                <RefreshCw className="w-3.5 h-3.5" />
                                Resume Interrupted Plan
                              </button>
                            )}
                            <button
                              onClick={async () => {
                                if (currentTask?.id && (currentTask.status === "AWAITING_DELIVERY" || executionStatus?.status === "AWAITING_DELIVERY")) {
                                  try { await reopenTask(currentTask.id); } catch {}
                                }
                                handleExecutePlan();
                              }}
                              disabled={executingPlan || runningQa}
                              className="px-5 py-2.5 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-xs font-semibold text-white transition-all shadow-lg shadow-purple-950/40 flex items-center gap-2 disabled:opacity-40"
                            >
                              <Sparkles className="w-4 h-4" />
                              {executionStatus?.status === "FAILED" || executionStatus?.status === "CANCELLED" || executionStatus?.status === "CLOSED" || executionStatus?.status === "AWAITING_DELIVERY" || currentTask.status === "FAILED" || currentTask.status === "CLOSED" || currentTask.status === "AWAITING_DELIVERY"
                                ? "Retry Execution"
                                : "Execute Approved Plan"}
                            </button>
                            {(currentTask.status === "CLOSED" || executionStatus?.status === "CLOSED") ? (
                              <button
                                onClick={async () => {
                                  try {
                                    await reopenTask(currentTask.id);
                                    await initSession();
                                  } catch (e: any) {
                                    alert(e.message);
                                  }
                                }}
                                className="px-4 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-xs font-semibold text-white transition-colors flex items-center gap-1.5"
                              >
                                Reopen Task
                              </button>
                            ) : ["AWAITING_QA", "AWAITING_REVIEW", "AWAITING_DELIVERY", "FAILED", "CANCELLED"].includes(executionStatus?.status || currentTask.status) && (
                              <button
                                onClick={async () => {
                                  try {
                                    await closeTask(currentTask.id);
                                    await initSession();
                                  } catch (e: any) {
                                    alert(e.message);
                                  }
                                }}
                                className="px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-xs font-semibold text-gray-200 transition-colors flex items-center gap-1.5"
                              >
                                Close Task
                              </button>
                            )}
                          </>
                        )}
                      </div>
                    </div>

                    {/* Execution Error Banner */}
                    {(executionError || (executionStatus?.status === "FAILED" && executionStatus?.error_message)) && (
                      <div className="flex items-start gap-2.5 p-3.5 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-200 text-xs">
                        <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                        <div>
                          <div className="font-semibold text-rose-300">Execution Error</div>
                          <p className="text-[11px] text-rose-200/80 mt-0.5">{executionError || executionStatus?.error_message}</p>
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

                    {/* Developer Agent Execution Logs Terminal (FILTERED to Developer Agent & ExecutionService) */}
                    {executionStatus?.logs && executionStatus.logs.length > 0 && (() => {
                      const devLogs = executionStatus.logs.filter(
                        (l) => l.agent === "DeveloperAgent" || l.agent === "ExecutionService" || !["QAEngineerAgent", "CodeReviewerAgent"].includes(l.agent)
                      );
                      if (devLogs.length === 0) return null;
                      return (
                        <div className="p-4 rounded-xl bg-gray-950 border border-gray-800 space-y-2">
                          <div className="flex items-center justify-between pb-2 border-b border-gray-800/80">
                            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
                              <Terminal className="w-3.5 h-3.5 text-purple-400" />
                              Developer Agent Audit Trail &amp; Logs
                            </span>
                            <span className="text-[10px] font-mono text-gray-500">
                              {devLogs.length} entries
                            </span>
                          </div>

                          <div className="max-h-48 overflow-y-auto space-y-1 font-mono text-[11px] text-gray-300 pt-1">
                            {devLogs.map((log, idx) => (
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
                      );
                    })()}

                    {/* Transition Banner to Chapter 4 when code is committed */}
                    {["AWAITING_QA", "AWAITING_REVIEW", "AWAITING_DELIVERY", "COMPLETED"].includes(executionStatus?.status || "") && (
                      <div className="p-4 rounded-xl bg-gradient-to-r from-emerald-950/60 to-teal-950/60 border border-emerald-800/70 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-lg">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-lg bg-emerald-900/60 border border-emerald-700/60 flex items-center justify-center text-emerald-400 shrink-0">
                            <CheckCircle className="w-5 h-5" />
                          </div>
                          <div>
                            <div className="font-semibold text-white text-xs sm:text-sm">Changes Committed to Task Branch</div>
                            <p className="text-[11px] text-emerald-200/80 mt-0.5">
                              Implementation is verified and committed. Proceed to Chapter 4 to run automated test suites and independent code review.
                            </p>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => {
                            setActiveTab("qa");
                            if (!(executionStatus?.qa_reports && executionStatus.qa_reports.length > 0)) {
                              handleStartQa();
                            }
                          }}
                          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white flex items-center gap-1.5 shrink-0 transition-colors shadow-md shadow-emerald-950/50"
                        >
                          <ShieldCheck className="w-3.5 h-3.5" />
                          Proceed to Chapter 4: QA &amp; Review
                          <ArrowRight className="w-3.5 h-3.5 ml-0.5" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Chapter 4 — Quality Assurance & Code Review */}
          {(activeTab === "qa" || activeTab === "all") && (
            <div className="space-y-6">
              {/* Header Title */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-gray-800">
                <div>
                  <div className="flex items-center gap-2">
                    <h1 className="text-2xl font-bold tracking-tight text-white">
                      Chapter 4 — Quality Assurance &amp; Code Review
                    </h1>
                    <StatusBadge
                      status={
                        executionStatus?.status === "AWAITING_DELIVERY" || currentTask?.status === "AWAITING_DELIVERY"
                          ? "AWAITING_DELIVERY"
                          : executionStatus?.status === "FAILED"
                          ? "FAILED"
                          : runningQa
                          ? "IN_PROGRESS"
                          : (executionStatus?.qa_reports && executionStatus.qa_reports.length > 0)
                          ? "ACTIVE"
                          : "AWAITING_QA"
                      }
                      label={
                        executionStatus?.status === "AWAITING_DELIVERY" || currentTask?.status === "AWAITING_DELIVERY"
                          ? "REVIEW APPROVED"
                          : runningQa
                          ? "QA RUNNING"
                          : (executionStatus?.qa_reports && executionStatus.qa_reports.length > 0)
                          ? "CYCLE COMPLETED"
                          : "READY FOR QA"
                      }
                    />
                  </div>
                  <p className="text-sm text-gray-400 mt-1">
                    Automated test execution, bounded developer recovery loops, deterministic stall detection, and independent code review.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs px-2.5 py-1 rounded-md bg-gray-800 border border-gray-700 text-gray-300 font-mono">
                    QA Cycles: {executionStatus?.qa_reports?.length || 0}/3
                  </span>
                  <span className="text-xs px-2.5 py-1 rounded-md bg-gray-800 border border-gray-700 text-gray-300 font-mono">
                    Review Cycles: {executionStatus?.review_reports?.length || 0}/2
                  </span>
                </div>
              </div>

              {!currentTask ? (
                <div className="p-8 rounded-xl bg-gray-900/40 border border-gray-800 text-center space-y-3">
                  <div className="w-12 h-12 rounded-xl bg-gray-800/80 border border-gray-700/60 flex items-center justify-center mx-auto text-gray-400">
                    <ShieldCheck className="w-6 h-6" />
                  </div>
                  <h3 className="text-sm font-semibold text-white">No Active Task Selected</h3>
                  <p className="text-xs text-gray-400 max-w-md mx-auto">
                    Select a repository and complete development in Chapters 2 and 3 before running QA and Code Review.
                  </p>
                  <div>
                    <button
                      type="button"
                      onClick={() => setActiveTab("planning")}
                      className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white transition-colors"
                    >
                      Go to Chapter 2: Repo Intelligence
                    </button>
                  </div>
                </div>
              ) : !(
                [
                  "AWAITING_QA",
                  "AWAITING_REVIEW",
                  "AWAITING_DELIVERY",
                  "COMPLETED",
                  "FAILED",
                  "QA_TESTING",
                  "REVIEWING",
                  "CLOSED",
                ].includes(executionStatus?.status || "") ||
                [
                  "AWAITING_QA",
                  "AWAITING_REVIEW",
                  "AWAITING_DELIVERY",
                  "COMPLETED",
                  "FAILED",
                  "QA_TESTING",
                  "REVIEWING",
                  "CLOSED",
                ].includes(currentTask?.status || "") ||
                Boolean(executionStatus?.qa_reports && executionStatus.qa_reports.length > 0)
              ) ? (
                <div className="p-8 rounded-xl bg-gray-900/40 border border-gray-800 text-center space-y-3">
                  <div className="w-12 h-12 rounded-xl bg-amber-950/40 border border-amber-800/60 flex items-center justify-center mx-auto text-amber-400">
                    <AlertTriangle className="w-6 h-6" />
                  </div>
                  <h3 className="text-sm font-semibold text-white">Awaiting Developer Execution</h3>
                  <p className="text-xs text-gray-400 max-w-md mx-auto">
                    Task <code className="text-purple-300 font-mono">{currentTask.title}</code> changes must be implemented and committed in Chapter 3 before QA testing can proceed.
                  </p>
                  <div>
                    <button
                      type="button"
                      onClick={() => setActiveTab("execution")}
                      className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-xs font-semibold text-white transition-colors"
                    >
                      Go to Chapter 3: Autonomous Dev
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-5">
                  {/* QA Controls & Launch Card */}
                  <div className="p-5 rounded-xl bg-gray-900/60 border border-emerald-900/40 space-y-4 shadow-xl shadow-emerald-950/10">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-gray-800 gap-3">
                      <div className="flex items-center gap-2.5">
                        <div className="p-2 rounded-lg bg-emerald-950/60 border border-emerald-800/60 text-emerald-400">
                          <ShieldCheck className="w-5 h-5" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="text-sm font-semibold text-white">Automated QA &amp; Code Review Suite</h4>
                            <StatusBadge
                              status={
                                executionStatus?.status === "AWAITING_DELIVERY"
                                  ? "APPROVED"
                                  : runningQa
                                  ? "RUNNING"
                                  : executionStatus?.status === "FAILED"
                                  ? "FAILED"
                                  : "READY"
                              }
                            />
                          </div>
                          <p className="text-xs text-gray-400 mt-0.5">
                            Target Branch: <span className="text-purple-300 font-mono">{executionStatus?.branch_name || `devpilot/task-${currentTask.id.slice(0, 8)}`}</span>
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={handleStartQa}
                          disabled={runningQa || executingPlan}
                          className="px-5 py-2.5 rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-xs font-semibold text-white transition-all shadow-lg shadow-emerald-950/40 flex items-center gap-2 disabled:opacity-50"
                        >
                          {runningQa ? (
                            <>
                              <RefreshCw className="w-4 h-4 animate-spin" />
                              Running QA &amp; Review...
                            </>
                          ) : (
                            <>
                              <ShieldCheck className="w-4 h-4" />
                              {executionStatus?.qa_reports && executionStatus.qa_reports.length > 0 ? "Rerun QA & Code Review" : "Start QA & Code Review"}
                            </>
                          )}
                        </button>
                      </div>
                    </div>

                    {/* Status Feedback banner during QA */}
                    {runningQa && (
                      <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-800/60 flex items-center gap-3 text-xs text-emerald-200">
                        <RefreshCw className="w-4 h-4 animate-spin text-emerald-400 shrink-0" />
                        <div>
                          <span className="font-semibold text-emerald-300">QA Engineer &amp; Code Reviewer Active:</span>
                          <p className="text-[11px] text-emerald-200/80 mt-0.5">
                            Executing test commands in isolated sandbox, evaluating acceptance criteria, and performing adversarial static code review...
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Failure Diagnostic Banner when QA fails / exhausts */}
                    {executionStatus?.status === "FAILED" && (
                      <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/70 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-rose-200 shadow-lg">
                        <div className="flex items-start gap-3">
                          <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                          <div>
                            <span className="font-semibold text-rose-300 text-sm">QA Pipeline Halted — Tests Failed</span>
                            <p className="text-[11px] text-rose-200/90 mt-1">
                              {executionStatus.error_message || "QA retry limit reached without passing all tests. Review the failure signature, diagnostic feedback, and raw terminal logs below."}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <button
                            type="button"
                            onClick={() => setActiveTab("planning")}
                            className="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-semibold border border-gray-700 transition-colors"
                          >
                            Revise Plan in Ch. 2
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setActiveTab("execution");
                              handleExecutePlan();
                            }}
                            className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold transition-colors shadow-md shadow-rose-950/50"
                          >
                            Retry Execution
                          </button>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* QA Test Reports List */}
                  {executionStatus?.qa_reports && executionStatus.qa_reports.length > 0 && (
                    <div className="space-y-4">
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-300 flex items-center gap-2">
                        <ShieldCheck className="w-4 h-4 text-emerald-400" />
                        QA Test Execution Reports ({executionStatus.qa_reports.length})
                      </h4>
                      {executionStatus.qa_reports.map((qa, qIdx) => (
                        <div key={qIdx} className="p-4 rounded-xl bg-gray-950/80 border border-gray-800 space-y-3">
                          <div className="flex items-center justify-between border-b border-gray-800/80 pb-2">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-semibold text-gray-200">
                                QA Cycle #{qa.cycle_number}
                              </span>
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                  qa.overall_passed
                                    ? "bg-emerald-950 text-emerald-400 border border-emerald-800/60"
                                    : "bg-rose-950 text-rose-400 border border-rose-800/60"
                                }`}
                              >
                                {qa.overall_passed ? "PASSED" : "FAILURES DETECTED"}
                              </span>
                            </div>
                            {qa.failure_signature && (
                              <span className="text-[10px] font-mono text-gray-500">
                                Sig: {qa.failure_signature}
                              </span>
                            )}
                          </div>

                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                            <div className="p-2.5 rounded-lg bg-gray-900 border border-gray-800 flex items-center justify-between">
                              <span className="text-gray-400">Passed:</span>
                              <span className="text-emerald-400 font-bold">{qa.tests_passed}</span>
                            </div>
                            <div className="p-2.5 rounded-lg bg-gray-900 border border-gray-800 flex items-center justify-between">
                              <span className="text-gray-400">Failed:</span>
                              <span className={qa.tests_failed > 0 ? "text-rose-400 font-bold" : "text-gray-500"}>
                                {qa.tests_failed}
                              </span>
                            </div>
                            <div className="p-2.5 rounded-lg bg-gray-900 border border-gray-800 flex items-center justify-between">
                              <span className="text-gray-400">Skipped:</span>
                              <span className="text-gray-400">{qa.tests_skipped}</span>
                            </div>
                            <div className="p-2.5 rounded-lg bg-gray-900 border border-gray-800 flex items-center justify-between">
                              <span className="text-gray-400">Commands:</span>
                              <span className="text-blue-400 truncate max-w-[120px]" title={qa.commands_executed?.join(", ")}>
                                {qa.commands_executed?.join(", ") || "none"}
                              </span>
                            </div>
                          </div>

                          {qa.acceptance_criteria_results && qa.acceptance_criteria_results.length > 0 && (
                            <div className="space-y-1.5 pt-1">
                              <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
                                Acceptance Criteria Validation
                              </span>
                              <div className="space-y-1">
                                {qa.acceptance_criteria_results.map((cr: any, cIdx: number) => (
                                  <div key={cIdx} className="flex items-start gap-2 text-xs p-2 rounded bg-gray-900/60 border border-gray-800/60">
                                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${cr.status === "SATISFIED" ? "bg-emerald-950 text-emerald-400" : "bg-rose-950 text-rose-400"}`}>
                                      {cr.status}
                                    </span>
                                    <span className="text-gray-300">{cr.criterion}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {qa.failure_summary && (
                            <div className="p-3 rounded bg-rose-950/30 border border-rose-800/40 text-xs text-rose-200">
                              <span className="font-semibold text-rose-300">Failure Summary:</span>
                              <p className="mt-0.5 text-[11px] text-rose-200/90">{qa.failure_summary}</p>
                            </div>
                          )}

                          {qa.actionable_feedback && (
                            <div className="p-3 rounded bg-amber-950/30 border border-amber-800/40 text-xs text-amber-200">
                              <span className="font-semibold text-amber-300">Developer Diagnostic Feedback:</span>
                              <p className="mt-0.5 text-[11px] text-amber-200/90">{qa.actionable_feedback}</p>
                            </div>
                          )}

                          {qa.logs && (
                            <details className="group rounded-lg bg-gray-900 border border-gray-800 text-xs overflow-hidden">
                              <summary className="px-3 py-2 cursor-pointer font-semibold text-gray-300 hover:text-white flex items-center justify-between bg-gray-900/90 select-none">
                                <span className="flex items-center gap-1.5 font-mono text-[11px]">
                                  <Terminal className="w-3.5 h-3.5 text-gray-400" />
                                  Raw Test Execution Logs (stdout / stderr)
                                </span>
                                <span className="text-[10px] text-gray-500 group-open:rotate-180 transition-transform">&darr;</span>
                              </summary>
                              <pre className="p-3 text-[11px] font-mono text-gray-300 bg-black/60 overflow-x-auto max-h-60 whitespace-pre-wrap">
                                {qa.logs}
                              </pre>
                            </details>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Code Reviewer Reports */}
                  {executionStatus?.review_reports && executionStatus.review_reports.length > 0 && (
                    <div className="space-y-4 pt-3 border-t border-gray-800">
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-300 flex items-center gap-2">
                        <ShieldCheck className="w-4 h-4 text-purple-400" />
                        Independent Code Review Reports ({executionStatus.review_reports.length})
                      </h4>
                      {executionStatus.review_reports.map((rev, rIdx) => (
                        <div key={rIdx} className="p-4 rounded-xl bg-gray-950/80 border border-gray-800 space-y-3">
                          <div className="flex items-center justify-between border-b border-gray-800/80 pb-2">
                            <div className="flex items-center gap-2.5">
                              <span className="text-xs font-semibold text-gray-200">Review Cycle #{rev.cycle_number}</span>
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                  rev.outcome === "APPROVED"
                                    ? "bg-emerald-950 text-emerald-400 border border-emerald-800/60"
                                    : rev.outcome === "CHANGES_REQUESTED"
                                    ? "bg-amber-950 text-amber-400 border border-amber-800/60"
                                    : "bg-rose-950 text-rose-400 border border-rose-800/60"
                                }`}
                              >
                                {rev.outcome}
                              </span>
                            </div>
                            <div className="flex items-center gap-1.5 text-xs">
                              <span className="text-gray-400">Quality Score:</span>
                              <span className="font-bold text-emerald-400 font-mono">{rev.quality_score}/10</span>
                            </div>
                          </div>

                          <p className="text-xs text-gray-300">{rev.summary}</p>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                            <div className="p-2.5 rounded bg-gray-900 border border-gray-800">
                              <span className="font-semibold text-blue-400">Correctness: </span>
                              <span className="text-gray-300">{rev.correctness_assessment}</span>
                            </div>
                            <div className="p-2.5 rounded bg-gray-900 border border-gray-800">
                              <span className="font-semibold text-emerald-400">Security: </span>
                              <span className="text-gray-300">{rev.security_assessment}</span>
                            </div>
                          </div>

                          {rev.issues && rev.issues.length > 0 && (
                            <div className="space-y-1.5 pt-1">
                              <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
                                Identified Issues ({rev.issues.length})
                              </span>
                              <div className="space-y-1">
                                {rev.issues.map((iss, iIdx) => (
                                  <div key={iIdx} className="p-2 rounded bg-gray-900/60 border border-gray-800 text-xs space-y-1">
                                    <div className="flex items-center justify-between">
                                      <div className="flex items-center gap-2">
                                        <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${iss.severity === "CRITICAL" ? "bg-rose-950 text-rose-400" : iss.severity === "HIGH" ? "bg-amber-950 text-amber-400" : "bg-blue-950 text-blue-400"}`}>
                                          {iss.severity}
                                        </span>
                                        <span className="font-mono text-gray-200">{iss.file_path}{iss.line_number ? `:${iss.line_number}` : ""}</span>
                                      </div>
                                    </div>
                                    <p className="text-gray-300 text-[11px]">{iss.description}</p>
                                    {iss.suggested_fix && (
                                      <p className="text-emerald-400/90 text-[11px]">Fix: {iss.suggested_fix}</p>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Ready for Chapter 5 Delivery Banner */}
                  {(executionStatus?.review_reports?.some((r) => r.outcome === "APPROVED") || currentTask?.status === "AWAITING_DELIVERY") && (
                    <div className="p-4 rounded-xl bg-gradient-to-r from-emerald-950/60 to-blue-950/60 border border-emerald-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-lg">
                      <div className="flex items-center gap-3">
                        <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0" />
                        <div>
                          <div className="font-semibold text-white text-sm">Chapter 4 QA &amp; Code Review Verified</div>
                          <p className="text-xs text-emerald-200/80">
                            All automated tests pass and Code Reviewer has APPROVED the implementation. Task branch is ready for Chapter 5 GitHub Pull Request Delivery.
                          </p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          setActiveTab("delivery");
                          if (currentTask) loadDiffAndTimeline(currentTask.id);
                        }}
                        className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white shadow-lg shadow-emerald-950/50 flex items-center gap-1.5 shrink-0 self-start sm:self-auto transition-all cursor-pointer"
                      >
                        <Send className="w-3.5 h-3.5" /> Proceed to Chapter 5: Delivery &amp; PR <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Chapter 5 — GitHub Delivery & Production Readiness */}
          {(activeTab === "delivery" || activeTab === "all") && (
            <div className="space-y-6">
              {/* Header */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-gray-800">
                <div>
                  <div className="flex items-center gap-2">
                    <h1 className="text-2xl font-bold tracking-tight text-white">
                      Chapter 5 — GitHub Delivery &amp; Production Readiness
                    </h1>
                    <StatusBadge
                      status={
                        currentTask?.pull_request || currentTask?.is_delivered
                          ? "COMPLETED"
                          : currentTask?.status === "AWAITING_DELIVERY"
                          ? "IN_PROGRESS"
                          : "PENDING"
                      }
                      label={
                        currentTask?.pull_request || currentTask?.is_delivered
                          ? "DELIVERY COMPLETE"
                          : currentTask?.status === "AWAITING_DELIVERY"
                          ? "APPROVAL & PR READY"
                          : "AWAITING CHAPTER 4"
                      }
                    />
                  </div>
                  <p className="text-sm text-gray-400 mt-1">
                    Pre-delivery unified diff inspection, mandatory Human Approval 2, automated isolated branch push, and GitHub Pull Request creation.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {currentTask && (
                    <button
                      type="button"
                      onClick={() => loadDiffAndTimeline(currentTask.id)}
                      disabled={loadingDiff || loadingTimeline}
                      className="px-3 py-1.5 rounded-lg border border-gray-800 text-xs font-medium text-gray-300 hover:bg-gray-900 transition-colors flex items-center gap-1.5"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${loadingDiff || loadingTimeline ? "animate-spin" : ""}`} />
                      Refresh Diff &amp; Timeline
                    </button>
                  )}
                </div>
              </div>

              {/* Delivery Error Banner */}
              {deliveryError && (
                <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/80 text-rose-200 text-sm flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <div className="font-semibold text-rose-300">Delivery Alert</div>
                    <div className="text-xs text-rose-200/90 mt-0.5">{deliveryError}</div>
                    {deliveryError.includes("No commits between base branch") && (
                      <div className="mt-3 flex items-center gap-2">
                        <button
                          type="button"
                          onClick={async () => {
                            if (currentTask?.id) {
                              try { await reopenTask(currentTask.id); } catch {}
                            }
                            setActiveTab("execution");
                            handleExecutePlan();
                          }}
                          className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold transition-colors"
                        >
                          Execute Plan in Chapter 3
                        </button>
                      </div>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => setDeliveryError(null)}
                    className="text-xs text-rose-400 hover:text-white"
                  >
                    Dismiss
                  </button>
                </div>
              )}

              {/* Delivered PR Banner (if PR already exists) */}
              {(currentTask?.pull_request || currentTask?.is_delivered) && (
                <div className="p-5 rounded-2xl bg-gradient-to-r from-emerald-950/80 via-gray-950 to-blue-950/80 border border-emerald-700/80 shadow-2xl space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-800/80 pb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center">
                        <GitPullRequest className="w-6 h-6 text-emerald-400" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                            Pull Request Delivered
                          </span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800/60">
                            {currentTask.pull_request?.status || "OPEN"}
                          </span>
                        </div>
                        <h3 className="text-base font-bold text-white mt-0.5">
                          #{currentTask.pull_request?.pr_number}: {currentTask.pull_request?.title || currentTask.title}
                        </h3>
                      </div>
                    </div>
                    {currentTask.pull_request?.html_url && (
                      <a
                        href={currentTask.pull_request.html_url}
                        target="_blank"
                        rel="noreferrer"
                        className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs shadow-lg shadow-emerald-950/50 flex items-center gap-2 transition-all self-start sm:self-auto cursor-pointer"
                      >
                        <ExternalLink className="w-4 h-4" />
                        View Pull Request on GitHub
                      </a>
                    )}
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                    <div className="p-2.5 rounded-lg bg-gray-900/80 border border-gray-800">
                      <div className="text-gray-400 text-[10px] uppercase font-sans">Head Branch</div>
                      <div className="text-purple-300 font-semibold truncate mt-0.5">
                        {currentTask.pull_request?.head_branch || `devpilot/task-${currentTask.id.slice(0, 8)}`}
                      </div>
                    </div>
                    <div className="p-2.5 rounded-lg bg-gray-900/80 border border-gray-800">
                      <div className="text-gray-400 text-[10px] uppercase font-sans">Base Branch</div>
                      <div className="text-blue-300 font-semibold truncate mt-0.5">
                        {currentTask.pull_request?.base_branch || "main"}
                      </div>
                    </div>
                    <div className="p-2.5 rounded-lg bg-gray-900/80 border border-gray-800">
                      <div className="text-gray-400 text-[10px] uppercase font-sans">PR Number</div>
                      <div className="text-emerald-400 font-bold mt-0.5">
                        #{currentTask.pull_request?.pr_number}
                      </div>
                    </div>
                    <div className="p-2.5 rounded-lg bg-gray-900/80 border border-gray-800">
                      <div className="text-gray-400 text-[10px] uppercase font-sans">Pipeline Lifecycle</div>
                      <div className="text-emerald-300 font-semibold mt-0.5">
                        ALL 5 PHASES COMPLETE
                      </div>
                    </div>
                  </div>

                  {/* Next Milestone / Next Project Separation */}
                  <div className="pt-3 border-t border-gray-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="text-xs text-gray-300">
                      <span className="text-emerald-400 font-bold">🚀 Engineering Milestone Complete!</span> What would you like to build next?
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        type="button"
                        onClick={handleStartNewTask}
                        className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs flex items-center gap-1.5 transition-all shadow-md shadow-blue-950/40 cursor-pointer"
                      >
                        <FilePlus className="w-3.5 h-3.5" />
                        + Start New Task in This Repo
                      </button>
                      <button
                        type="button"
                        onClick={handleStartNewProject}
                        className="px-3.5 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs flex items-center gap-1.5 transition-all shadow-md shadow-purple-950/40 cursor-pointer"
                      >
                        <FolderGit2 className="w-3.5 h-3.5" />
                        🚀 Switch / Start New Project
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Pre-requisite Verification Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                <div className={`p-4 rounded-xl border ${
                  ["APPROVED", "EXECUTING", "AWAITING_QA", "AWAITING_REVIEW", "AWAITING_DELIVERY", "COMPLETED", "CLOSED"].includes(currentTask?.status || "")
                    ? "bg-emerald-950/20 border-emerald-800/60 text-emerald-300"
                    : "bg-gray-900/40 border-gray-800 text-gray-400"
                }`}>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] uppercase font-bold tracking-wider">Chapter 2</span>
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="text-xs font-semibold text-white mt-1">Plan Approved</div>
                  <div className="text-[11px] text-gray-400 mt-0.5">Architect &amp; Human Approval 1</div>
                </div>

                <div className={`p-4 rounded-xl border ${
                  ["AWAITING_QA", "AWAITING_REVIEW", "AWAITING_DELIVERY", "COMPLETED", "CLOSED"].includes(executionStatus?.status || "") ||
                  ["AWAITING_QA", "AWAITING_REVIEW", "AWAITING_DELIVERY", "COMPLETED", "CLOSED"].includes(currentTask?.status || "")
                    ? "bg-emerald-950/20 border-emerald-800/60 text-emerald-300"
                    : "bg-gray-900/40 border-gray-800 text-gray-400"
                }`}>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] uppercase font-bold tracking-wider">Chapter 3</span>
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="text-xs font-semibold text-white mt-1">Code Committed</div>
                  <div className="text-[11px] text-gray-400 mt-0.5">Developer Agent isolated branch</div>
                </div>

                <div className={`p-4 rounded-xl border ${
                  executionStatus?.qa_reports?.some((q) => q.overall_passed) || currentTask?.status === "AWAITING_DELIVERY" || currentTask?.status === "COMPLETED"
                    ? "bg-emerald-950/20 border-emerald-800/60 text-emerald-300"
                    : "bg-gray-900/40 border-gray-800 text-gray-400"
                }`}>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] uppercase font-bold tracking-wider">Chapter 4</span>
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="text-xs font-semibold text-white mt-1">QA Tests Passed</div>
                  <div className="text-[11px] text-gray-400 mt-0.5">Automated test suite verified</div>
                </div>

                <div className={`p-4 rounded-xl border ${
                  executionStatus?.review_reports?.some((r) => r.outcome === "APPROVED") || currentTask?.status === "AWAITING_DELIVERY" || currentTask?.status === "COMPLETED"
                    ? "bg-emerald-950/20 border-emerald-800/60 text-emerald-300"
                    : "bg-gray-900/40 border-gray-800 text-gray-400"
                }`}>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] uppercase font-bold tracking-wider">Chapter 4</span>
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="text-xs font-semibold text-white mt-1">Review Approved</div>
                  <div className="text-[11px] text-gray-400 mt-0.5">Independent code auditor verified</div>
                </div>
              </div>

              {/* Pre-Delivery Code Diff Viewer */}
              <div className="p-5 rounded-2xl bg-gray-950/80 border border-gray-800 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-800/80 pb-3">
                  <div className="flex items-center gap-2">
                    <FileCode className="w-4 h-4 text-purple-400" />
                    <h3 className="text-sm font-semibold text-white">
                      Pre-Delivery Unified Code Diff
                    </h3>
                    {taskDiff && (
                      <span className="text-xs text-gray-400 font-mono">
                        ({taskDiff.file_changes?.length || 0} files •{" "}
                        <span className="text-emerald-400 font-bold">+{taskDiff.total_added}</span>{" "}
                        <span className="text-rose-400 font-bold">-{taskDiff.total_removed}</span>)
                      </span>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowRawDiff(!showRawDiff)}
                    className="px-3 py-1 rounded-lg bg-gray-900 border border-gray-800 hover:bg-gray-800 text-xs font-medium text-gray-300 transition-colors"
                  >
                    {showRawDiff ? "Collapse Unified Diff" : "Expand Unified Diff View"}
                  </button>
                </div>

                {/* File Changes List */}
                {taskDiff?.file_changes && taskDiff.file_changes.length > 0 ? (
                  <div className="space-y-2">
                    {taskDiff.file_changes.map((f, fIdx) => (
                      <div
                        key={fIdx}
                        className="p-3 rounded-xl bg-gray-900/70 border border-gray-800 flex items-center justify-between text-xs"
                      >
                        <div className="flex items-center gap-2.5 truncate font-mono">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                              f.change_type === "CREATED" || f.change_type === "CREATE"
                                ? "bg-emerald-950 text-emerald-400"
                                : f.change_type === "DELETED" || f.change_type === "DELETE"
                                ? "bg-rose-950 text-rose-400"
                                : "bg-blue-950 text-blue-400"
                            }`}
                          >
                            {f.change_type}
                          </span>
                          <span className="text-gray-200 truncate">{f.file_path}</span>
                        </div>
                        <div className="flex items-center gap-2 font-mono shrink-0">
                          {f.lines_added !== undefined && (
                            <span className="text-emerald-400 font-semibold">+{f.lines_added}</span>
                          )}
                          {f.lines_removed !== undefined && (
                            <span className="text-rose-400 font-semibold">-{f.lines_removed}</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : executionStatus?.file_changes && executionStatus.file_changes.length > 0 ? (
                  <div className="space-y-2">
                    {executionStatus.file_changes.map((fc, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-xl bg-gray-900/70 border border-gray-800 flex items-center justify-between text-xs font-mono"
                      >
                        <div className="flex items-center gap-2 truncate">
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-purple-950 text-purple-300">
                            {fc.change_type}
                          </span>
                          <span className="text-gray-200 truncate">{fc.file_path}</span>
                        </div>
                        <span className="text-gray-400 text-[11px] font-sans">Committed</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-xs text-gray-500 py-3 text-center">
                    No diff records loaded yet. Task changes will appear here upon execution.
                  </div>
                )}

                {/* Raw Unified Diff Box */}
                {showRawDiff && taskDiff?.raw_diff && (
                  <div className="p-3 rounded-xl bg-gray-950 border border-gray-800 font-mono text-[11px] overflow-x-auto max-h-96 leading-relaxed">
                    <pre className="text-gray-300">
                      {taskDiff.raw_diff.split("\n").map((line, lIdx) => {
                        let colorClass = "text-gray-400";
                        if (line.startsWith("+") && !line.startsWith("+++")) colorClass = "text-emerald-400 bg-emerald-950/30";
                        else if (line.startsWith("-") && !line.startsWith("---")) colorClass = "text-rose-400 bg-rose-950/30";
                        else if (line.startsWith("@@")) colorClass = "text-cyan-400 font-bold";
                        else if (line.startsWith("diff") || line.startsWith("index")) colorClass = "text-purple-400 font-bold";
                        return (
                          <div key={lIdx} className={`${colorClass} px-1.5 py-0.5 rounded`}>
                            {line || " "}
                          </div>
                        );
                      })}
                    </pre>
                  </div>
                )}
              </div>

              {/* Human Approval 2 & Delivery Card */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Approval 2 (Pre-Delivery Gate) */}
                <div className="p-5 rounded-2xl bg-gray-950/80 border border-gray-800 space-y-4 flex flex-col justify-between">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between border-b border-gray-800/80 pb-3">
                      <div className="flex items-center gap-2">
                        <ShieldCheck className="w-4 h-4 text-emerald-400" />
                        <h3 className="text-sm font-semibold text-white">
                          Human Approval 2 (Pre-Delivery Gate)
                        </h3>
                      </div>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800/60">
                        MANDATORY GATE
                      </span>
                    </div>

                    <p className="text-xs text-gray-300">
                      In accordance with DevPilot safety policies, code changes cannot be pushed to remote or opened as a Pull Request without explicit human sign-off.
                    </p>

                    {/* Recorded Approvals History */}
                    {currentTask?.delivery_approvals && currentTask.delivery_approvals.length > 0 && (
                      <div className="space-y-2">
                        <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
                          Approval History
                        </span>
                        {currentTask.delivery_approvals.filter(Boolean).map((app, aIdx) => (
                          <div
                            key={app.id || aIdx}
                            className={`p-3 rounded-xl border text-xs space-y-1 ${
                              app.decision === "APPROVED"
                                ? "bg-emerald-950/30 border-emerald-800/60 text-emerald-300"
                                : "bg-rose-950/30 border-rose-800/60 text-rose-300"
                            }`}
                          >
                            <div className="flex items-center justify-between font-semibold">
                              <span className="flex items-center gap-1.5">
                                {app.decision === "APPROVED" ? (
                                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                                ) : (
                                  <X className="w-3.5 h-3.5 text-rose-400" />
                                )}
                                Decision: {app.decision}
                              </span>
                              <span className="text-[10px] font-mono text-gray-400">
                                {app.decided_at ? new Date(app.decided_at).toLocaleTimeString() : "--:--"}
                              </span>
                            </div>
                            {app.feedback && (
                              <p className="text-[11px] text-gray-300 mt-1 italic">
                                &quot;{app.feedback}&quot;
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Feedback Form (if not delivered) */}
                    {!currentTask?.pull_request && !currentTask?.is_delivered && (
                      <div className="space-y-2 pt-2">
                        <label className="text-xs font-medium text-gray-300 flex items-center gap-1.5">
                          <MessageSquare className="w-3.5 h-3.5 text-purple-400" />
                          Delivery Reviewer Feedback (Optional):
                        </label>
                        <textarea
                          rows={3}
                          value={finalApprovalFeedback}
                          onChange={(e) => setFinalApprovalFeedback(e.target.value)}
                          placeholder="Provide sign-off comments, notes on verification, or reason for rejection..."
                          className="w-full text-xs p-3 rounded-xl bg-gray-900 border border-gray-800 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 resize-none"
                        />
                      </div>
                    )}
                  </div>

                  {/* Approval Action Buttons */}
                  {!currentTask?.pull_request && !currentTask?.is_delivered && (
                    <div className="flex items-center gap-3 pt-3 border-t border-gray-800/80">
                      <button
                        type="button"
                        onClick={() => handleFinalApproval("APPROVED")}
                        disabled={submittingFinalApproval}
                        className="flex-1 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs shadow-lg shadow-emerald-950/50 flex items-center justify-center gap-2 transition-all cursor-pointer disabled:opacity-50"
                      >
                        <Check className="w-4 h-4" />
                        {submittingFinalApproval ? "Recording..." : "Approve Final Delivery"}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleFinalApproval("REJECTED")}
                        disabled={submittingFinalApproval}
                        className="px-4 py-2.5 rounded-xl bg-rose-950/60 hover:bg-rose-900/80 border border-rose-800/80 text-rose-300 font-semibold text-xs flex items-center justify-center gap-2 transition-all cursor-pointer disabled:opacity-50"
                      >
                        <X className="w-4 h-4" />
                        Reject
                      </button>
                    </div>
                  )}
                </div>

                {/* GitHub Pull Request Trigger Card */}
                <div className="p-5 rounded-2xl bg-gray-950/80 border border-gray-800 space-y-4 flex flex-col justify-between">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between border-b border-gray-800/80 pb-3">
                      <div className="flex items-center gap-2">
                        <Github className="w-4 h-4 text-purple-400" />
                        <h3 className="text-sm font-semibold text-white">
                          GitHub Pull Request Delivery
                        </h3>
                      </div>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-gray-900 text-gray-400 border border-gray-800">
                        AUTOMATED DELIVERY
                      </span>
                    </div>

                    <div className="space-y-2 text-xs">
                      <div className="p-2.5 rounded-lg bg-gray-900/60 border border-gray-800 flex items-center justify-between">
                        <span className="text-gray-400">Target Repository:</span>
                        <span className="text-gray-200 font-semibold font-mono">
                          {selectedRepo?.full_name || "Repository"}
                        </span>
                      </div>
                      <div className="p-2.5 rounded-lg bg-gray-900/60 border border-gray-800 flex items-center justify-between">
                        <span className="text-gray-400">Push Branch:</span>
                        <span className="text-purple-300 font-semibold font-mono">
                          devpilot/task-{currentTask?.id?.slice(0, 8) || "id"}
                        </span>
                      </div>
                      <div className="p-2.5 rounded-lg bg-gray-900/60 border border-gray-800 flex items-center justify-between">
                        <span className="text-gray-400">Base Branch:</span>
                        <span className="text-blue-300 font-semibold font-mono">
                          {selectedRepo?.default_branch || "main"}
                        </span>
                      </div>
                    </div>

                    <div className="p-3 rounded-xl bg-gray-900/80 border border-gray-800 space-y-1.5">
                      <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
                        PR Description Content Summary
                      </span>
                      <ul className="text-[11px] text-gray-300 space-y-1 list-disc list-inside">
                        <li>Original User Requirement &amp; Acceptance Criteria</li>
                        <li>Architecture Plan &amp; File Change Summary</li>
                        <li>Automated QA Test Execution Report (Cycle #{executionStatus?.qa_reports?.length || 1})</li>
                        <li>Code Reviewer Score &amp; Quality Assessment</li>
                        <li>Complete Multi-Agent Engineering Audit Trail</li>
                      </ul>
                    </div>
                  </div>

                  {/* Trigger Delivery Action */}
                  <div className="pt-3 border-t border-gray-800/80">
                    {currentTask?.pull_request || currentTask?.is_delivered ? (
                      <div className="p-3 rounded-xl bg-emerald-950/40 border border-emerald-800/80 text-emerald-300 text-xs flex items-center justify-between">
                        <span className="flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                          Pull Request successfully delivered to GitHub
                        </span>
                        {currentTask.pull_request?.html_url && (
                          <a
                            href={currentTask.pull_request.html_url}
                            target="_blank"
                            rel="noreferrer"
                            className="font-semibold underline hover:text-emerald-200"
                          >
                            PR #{currentTask.pull_request.pr_number} ↗
                          </a>
                        )}
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={handleDeliver}
                        disabled={
                          deliveringTask ||
                          !currentTask?.delivery_approvals?.some((a) => a?.decision === "APPROVED")
                        }
                        className={`w-full px-4 py-3 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition-all shadow-lg ${
                          currentTask?.delivery_approvals?.some((a) => a?.decision === "APPROVED")
                            ? "bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-purple-950/50 cursor-pointer"
                            : "bg-gray-800 text-gray-500 cursor-not-allowed border border-gray-700"
                        }`}
                      >
                        <Send className={`w-4 h-4 ${deliveringTask ? "animate-spin" : ""}`} />
                        {deliveringTask
                          ? "Pushing Branch & Creating Pull Request..."
                          : currentTask?.delivery_approvals?.some((a) => a?.decision === "APPROVED")
                          ? "Deliver & Create Pull Request on GitHub"
                          : "Approval 2 Required to Deliver PR"}
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* End-to-End Activity Timeline */}
              <div className="p-5 rounded-2xl bg-gray-950/80 border border-gray-800 space-y-4">
                <div className="flex items-center justify-between border-b border-gray-800/80 pb-3">
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-purple-400" />
                    <h3 className="text-sm font-semibold text-white">
                      End-to-End Autonomous Engineering Timeline
                    </h3>
                  </div>
                  <span className="text-xs text-gray-400 font-mono">
                    Chapters 1 – 5 Audit Log
                  </span>
                </div>

                {taskTimeline && taskTimeline.length > 0 ? (
                  <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-gray-800">
                    {taskTimeline.map((item, tIdx) => (
                      <div key={tIdx} className="relative group">
                        <div
                          className={`absolute -left-6 top-1 w-2.5 h-2.5 rounded-full border-2 border-gray-950 ${
                            item.status === "COMPLETED" || item.type.includes("APPROVED") || item.type.includes("DELIVERED")
                              ? "bg-emerald-400 ring-2 ring-emerald-950"
                              : item.status === "IN_PROGRESS"
                              ? "bg-blue-400 ring-2 ring-blue-950 animate-pulse"
                              : "bg-purple-400 ring-2 ring-purple-950"
                          }`}
                        />
                        <div className="p-3 rounded-xl bg-gray-900/60 border border-gray-800/80 text-xs space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-gray-200">
                              {item.title}
                            </span>
                            <span className="text-[10px] font-mono text-gray-500">
                              {item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : "--:--"}
                            </span>
                          </div>
                          <p className="text-gray-400 text-[11px]">{item.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-xs text-gray-500 py-4 text-center">
                    Timeline events will be recorded and displayed as each chapter completes.
                  </div>
                )}
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
