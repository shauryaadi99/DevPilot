/**
 * Backend API communication client.
 */

export interface ComponentStatus {
  status: string;
  engine?: string;
  error?: string | null;
  provider?: string;
  configured?: boolean;
  model?: string;
}

export interface HealthResponse {
  status: "healthy" | "degraded" | "error";
  version: string;
  environment: string;
  timestamp: string;
  components: {
    database: {
      status: string;
      engine: string;
      error: string | null;
    };
    llm: {
      provider: string;
      configured: boolean;
      model: string;
    };
  };
}

export interface GroqTestResult {
  configured: boolean;
  status: string;
  provider: string;
  model: string;
  message: string;
}

export interface UserProfile {
  id: string;
  username: string;
  name?: string;
  email?: string;
  avatar_url?: string;
}

export interface PatStatus {
  has_pat: boolean;
  is_valid: boolean;
  pat_masked: string | null;
  scopes: string[];
  last_validated_at?: string;
  message?: string;
}

export interface TaskSummary {
  id: string;
  repository_id: string;
  repository_name?: string | null;
  user_id?: string | null;
  title: string;
  requirement: string;
  status: string;
  is_delivered: boolean;
  pr_number?: number | null;
  pr_url?: string | null;
  pr_status?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export interface SessionState {
  authenticated: boolean;
  user: UserProfile | null;
  pat_status: PatStatus;
  active_chapter: string;
  selected_repository: GitHubRepo | null;
  current_task: TaskDetail | null;
  execution: ExecutionStatus | null;
  available_repositories?: GitHubRepo[];
  available_tasks?: TaskSummary[];
  can_resume: boolean;
}

export interface GitHubUser {
  login: string;
  name?: string;
  avatar_url?: string;
  html_url: string;
  public_repos: number;
}

export interface GitHubRepo {
  id?: number | string;
  name: string;
  full_name: string;
  owner: string;
  default_branch: string;
  is_private: boolean;
  html_url: string;
  description?: string | null;
  language?: string | null;
  stargazers_count?: number;
  updated_at?: string;
}

export interface TreeSummary {
  total_files: number;
  key_paths: string[];
}

export interface InspectionData {
  tree_summary: TreeSummary;
  detected_languages: string[];
  detected_frameworks: string[];
  detected_entrypoints: string[];
  manifests_summary: Record<string, any>;
  confirmed_facts: string[];
  unknowns: string[];
}

export interface RequirementAnalysisData {
  requirement_summary: string;
  functional_requirements: string[];
  nonfunctional_requirements: string[];
  acceptance_criteria: string[];
  ambiguities: string[];
  clarification_questions: string[];
}

export interface FileToCreate {
  path: string;
  purpose: string;
}

export interface FileToModify {
  path: string;
  reason: string;
  changes_summary: string;
}

export interface ApiContractChange {
  endpoint: string;
  method: string;
  description: string;
}

export interface ImplementationStep {
  step_number: number;
  title: string;
  description: string;
  affected_files: string[];
}

export interface ImplementationPlanData {
  id: string;
  version: number;
  summary: string;
  repository_understanding: string;
  confirmed_observations: string[];
  files_to_create: FileToCreate[];
  files_to_modify: FileToModify[];
  api_contract_changes: ApiContractChange[];
  implementation_steps: ImplementationStep[];
  dependencies: string[];
  testing_strategy: Record<string, any>;
  risks_and_assumptions: string[];
}

export interface PlanApprovalData {
  id: string;
  decision: "APPROVED" | "REJECTED" | "CHANGES_REQUESTED" | string;
  feedback?: string | null;
  decided_at: string;
}

export interface TaskDetail {
  id: string;
  repository_id?: string;
  title: string;
  requirement: string;
  status: string;
  plan_approval_status?: string | null;
  is_plan_approved?: boolean;
  execution_status?: string | null;
  created_at: string;
  updated_at: string;
  repository: GitHubRepo;
  inspection?: InspectionData | null;
  requirement_analysis?: RequirementAnalysisData | null;
  implementation_plan?: ImplementationPlanData | null;
  latest_approval?: PlanApprovalData | null;
  approvals?: PlanApprovalData[];
  delivery_approvals?: DeliveryApprovalData[];
  pull_request?: PullRequestData | null;
  is_delivered?: boolean;
  executions?: any[];
}

export interface DeliveryApprovalData {
  id: string;
  task_id: string;
  decision: "APPROVED" | "REJECTED";
  feedback?: string | null;
  decided_at?: string;
}

export interface PullRequestData {
  id: string;
  task_id: string;
  repository_id: string;
  pr_number: number;
  html_url: string;
  title: string;
  head_branch: string;
  base_branch: string;
  status: string;
  body?: string | null;
  created_at?: string | null;
}

export interface DeliveryStatusResponse {
  task_id: string;
  task_status: string;
  is_delivered: boolean;
  can_deliver: boolean;
  pull_request?: PullRequestData | null;
  approvals: DeliveryApprovalData[];
}

export interface DiffResponse {
  task_id: string;
  branch_name: string;
  base_branch: string;
  raw_diff: string;
  file_changes: Array<{
    change_type: string;
    file_path: string;
    lines_added: number;
    lines_removed: number;
    diff_summary?: string;
  }>;
  total_added: number;
  total_removed: number;
}

export interface TimelineEvent {
  chapter: number;
  type: string;
  title: string;
  description: string;
  timestamp?: string | null;
  status: "COMPLETED" | "FAILED" | "IN_PROGRESS" | "PENDING";
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Health & Diagnostics ───────────────────────────────────────────────────

export async function fetchHealth(): Promise<HealthResponse> {
  const url = `${API_BASE_URL}/health`;
  const res = await fetch(url, {
    cache: "no-store",
    credentials: "include",
    headers: { "Accept": "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Health check request failed with HTTP ${res.status}`);
  }
  return res.json();
}

export async function testGroqConnection(): Promise<GroqTestResult> {
  const url = `${API_BASE_URL}/api/v1/llm/groq/test`;
  const res = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: { "Accept": "application/json" },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Groq test failed with status ${res.status}`);
  }
  return res.json();
}

// ── Authentication & PAT ───────────────────────────────────────────────────

export async function getGithubLoginUrl(): Promise<{ oauth_url: string }> {
  const res = await fetch(`${API_BASE_URL}/api/v1/auth/github/login`, {
    credentials: "include",
    headers: { "Accept": "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to initiate GitHub OAuth login.");
  }
  return res.json();
}

export async function devLogin(username: string): Promise<{ status: string; session_id: string; user: UserProfile }> {
  const res = await fetch(`${API_BASE_URL}/api/v1/auth/dev-login`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", "Accept": "application/json" },
    body: JSON.stringify({ username }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Dev login failed.");
  }
  return res.json();
}

export async function submitPat(token: string): Promise<{ status: string; pat_masked: string; scopes: string[]; user: any; message: string }> {
  const res = await fetch(`${API_BASE_URL}/api/v1/auth/pat`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", "Accept": "application/json" },
    body: JSON.stringify({ token }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `PAT submission failed: ${res.status}`);
  }
  return res.json();
}

export async function getPatStatus(): Promise<PatStatus> {
  const res = await fetch(`${API_BASE_URL}/api/v1/auth/pat/status`, {
    credentials: "include",
    headers: { "Accept": "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to check PAT status.");
  }
  return res.json();
}

export async function logout(): Promise<void> {
  await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
    method: "POST",
    credentials: "include",
  }).catch(() => {});
}

// ── Session & Rehydration ──────────────────────────────────────────────────

export async function getSessionState(): Promise<SessionState> {
  const res = await fetch(`${API_BASE_URL}/api/v1/session/state`, {
    cache: "no-store",
    credentials: "include",
    headers: { "Accept": "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Failed to retrieve session state: ${res.status}`);
  }
  return res.json();
}

// ── GitHub & Repositories ──────────────────────────────────────────────────

export async function connectGitHub(token: string): Promise<{ status: string; user: GitHubUser }> {
  // Legacy / Direct connect shim
  const url = `${API_BASE_URL}/api/v1/github/connect`;
  const res = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", "Accept": "application/json" },
    body: JSON.stringify({ token }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `GitHub authorization failed with status ${res.status}`);
  }
  return res.json();
}

export async function listRepositories(token?: string): Promise<GitHubRepo[]> {
  const url = `${API_BASE_URL}/api/v1/github/repos`;
  const headers: Record<string, string> = { "Accept": "application/json" };
  if (token) {
    headers["X-GitHub-Token"] = token;
  }
  const res = await fetch(url, {
    credentials: "include",
    headers,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch repositories: ${res.status}`);
  }
  const data = await res.json();
  return data.repositories || [];
}

export const listUserRepositories = listRepositories;

export async function getSavedRepositories(): Promise<GitHubRepo[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/github/saved-repos`, {
    credentials: "include",
    headers: { "Accept": "application/json" },
  });
  if (!res.ok) {
    return [];
  }
  const data = await res.json();
  return data.repositories || [];
}

export async function selectRepository(repo: GitHubRepo): Promise<{ status: string; repository: GitHubRepo }> {
  const url = `${API_BASE_URL}/api/v1/github/select`;
  const res = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", "Accept": "application/json" },
    body: JSON.stringify({
      github_id: repo.id ? (typeof repo.id === "string" ? parseInt(repo.id, 10) || null : repo.id) : null,
      name: repo.name,
      full_name: repo.full_name,
      owner: repo.owner,
      default_branch: repo.default_branch || "main",
      is_private: repo.is_private || false,
      html_url: repo.html_url,
      description: repo.description,
    }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to persist repository selection: ${res.status}`);
  }
  return res.json();
}

export async function switchRepository(repositoryId: string | null): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/v1/session/select-repo`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Accept": "application/json" },
    credentials: "include",
    body: JSON.stringify({ repository_id: repositoryId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to switch repository.");
  }
  return res.json();
}

export async function switchTask(taskId: string | null): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/v1/session/select-task`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Accept": "application/json" },
    credentials: "include",
    body: JSON.stringify({ task_id: taskId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to switch task.");
  }
  return res.json();
}

export async function startNewProject(): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/v1/session/new-project`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Accept": "application/json" },
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to start new project.");
  }
  return res.json();
}

export async function startNewTask(): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/v1/session/new-task`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Accept": "application/json" },
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to start new task.");
  }
  return res.json();
}

export async function listTasks(repositoryId?: string): Promise<TaskSummary[]> {
  const url = repositoryId
    ? `${API_BASE_URL}/api/v1/tasks?repository_id=${encodeURIComponent(repositoryId)}`
    : `${API_BASE_URL}/api/v1/tasks`;
  const res = await fetch(url, {
    credentials: "include",
    headers: { "Accept": "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch tasks.");
  }
  return res.json();
}

// ── Tasks & Planning ───────────────────────────────────────────────────────

export async function createTask(repoId: string, title: string, requirement: string): Promise<any> {
  const url = `${API_BASE_URL}/api/v1/tasks`;
  const res = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", "Accept": "application/json" },
    body: JSON.stringify({ repository_id: repoId, title, requirement }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to create task: ${res.status}`);
  }
  return res.json();
}

export async function getTask(taskId: string): Promise<TaskDetail> {
  const url = `${API_BASE_URL}/api/v1/tasks/${taskId}`;
  const res = await fetch(url, {
    credentials: "include",
    headers: { "Accept": "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch task: ${res.status}`);
  }
  return res.json();
}

export async function runTaskPipeline(taskId: string, token?: string): Promise<TaskDetail> {
  const url = `${API_BASE_URL}/api/v1/tasks/${taskId}/pipeline`;
  const headers: Record<string, string> = { "Accept": "application/json" };
  if (token) {
    headers["X-GitHub-Token"] = token;
  }
  const res = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Task pipeline failed: ${res.status}`);
  }
  return res.json();
}

export async function submitPlanApproval(
  taskId: string,
  decision: "APPROVED" | "REJECTED" | "CHANGES_REQUESTED",
  feedback?: string,
): Promise<{ status: string; task_id?: string; decision: string; message: string; approval: PlanApprovalData; task?: TaskDetail }> {
  const url = `${API_BASE_URL}/api/v1/tasks/${taskId}/approval`;
  const res = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", "Accept": "application/json" },
    body: JSON.stringify({ decision, feedback }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Approval submission failed: ${res.status}`);
  }
  return res.json();
}

// ── Chapter 3 Execution ────────────────────────────────────────────────────

export interface FileChangeData {
  file_path: string;
  change_type: "CREATE" | "MODIFY" | "DELETE" | string;
  diff_summary: string;
  lines_added: number;
  lines_removed: number;
}

export interface ExecutionLogEntry {
  step_number: number;
  level: "INFO" | "WARNING" | "ERROR";
  agent: string;
  message: string;
  timestamp: string;
}

export interface QAReportData {
  id: string;
  execution_id: string;
  cycle_number: number;
  overall_passed: boolean;
  commands_executed: string[];
  tests_passed: number;
  tests_failed: number;
  tests_skipped: number;
  exit_codes: number[];
  logs: string;
  failure_summary?: string | null;
  failure_signature?: string | null;
  test_details?: any[];
  acceptance_criteria_results?: any[];
  actionable_feedback?: string | null;
  created_at: string;
}

export interface ReviewIssueData {
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO' | string;
  file_path: string;
  line_number?: number | null;
  description: string;
  suggested_fix?: string | null;
}

export interface CodeReviewReportData {
  id: string;
  execution_id: string;
  cycle_number: number;
  outcome: 'APPROVED' | 'CHANGES_REQUESTED' | 'BLOCKED' | string;
  summary: string;
  correctness_assessment?: string;
  security_assessment?: string;
  quality_score: number;
  issues: ReviewIssueData[];
  approval_recommendation?: string;
  created_at: string;
}

export interface ExecutionStatus {
  execution_id: string;
  task_id: string;
  status: "PENDING" | "CLONING" | "EXECUTING" | "COMMITTING" | "QA_TESTING" | "REVIEWING" | "AWAITING_QA" | "AWAITING_REVIEW" | "AWAITING_DELIVERY" | "COMPLETED" | "FAILED" | "CANCELLED" | "CLOSED";
  branch_name: string | null;
  current_step: number;
  total_steps: number;
  commit_sha: string | null;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
  file_changes: FileChangeData[];
  logs: ExecutionLogEntry[];
  qa_reports?: QAReportData[];
  review_reports?: CodeReviewReportData[];
}

export async function executeTask(
  taskId: string,
  githubToken?: string,
): Promise<{ status: string; execution_id: string; task_id: string; message: string }> {
  const url = `${API_BASE_URL}/api/v1/tasks/${taskId}/execute`;
  const res = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", "Accept": "application/json" },
    body: JSON.stringify({ github_token: githubToken || null }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Execution start failed: ${res.status}`);
  }
  return res.json();
}

export async function resumeExecution(
  taskId: string,
): Promise<{ status: string; execution_id: string; task_id: string; message: string }> {
  const url = `${API_BASE_URL}/api/v1/tasks/${taskId}/resume`;
  const res = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: { "Accept": "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Resume failed: ${res.status}`);
  }
  return res.json();
}

export async function runQa(
  taskId: string,
): Promise<{ status: string; execution_id: string; task_id: string; message: string }> {
  const url = `${API_BASE_URL}/api/v1/tasks/${taskId}/run-qa`;
  const res = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: { "Accept": "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `QA start failed: ${res.status}`);
  }
  return res.json();
}

export async function getExecutionStatus(taskId: string): Promise<ExecutionStatus> {
  const url = `${API_BASE_URL}/api/v1/tasks/${taskId}/execution`;
  const res = await fetch(url, {
    cache: "no-store",
    credentials: "include",
    headers: { "Accept": "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to get execution status: ${res.status}`);
  }
  return res.json();
}

export async function cancelExecution(
  taskId: string,
): Promise<{ status: string; execution_id: string; task_id: string; message: string }> {
  const url = `${API_BASE_URL}/api/v1/tasks/${taskId}/cancel`;
  const res = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: { "Accept": "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Cancel failed: ${res.status}`);
  }
  return res.json();
}

export async function closeTask(
  taskId: string,
): Promise<{ status: string; task_id: string; workspace_removed: boolean; message: string }> {
  const url = `${API_BASE_URL}/api/v1/tasks/${taskId}/close`;
  const res = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: { "Accept": "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Close task failed: ${res.status}`);
  }
  return res.json();
}

export async function reopenTask(
  taskId: string,
): Promise<{ status: string; task_id: string; task_status: string; message: string }> {
  const url = `${API_BASE_URL}/api/v1/tasks/${taskId}/reopen`;
  const res = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: { "Accept": "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Reopen task failed: ${res.status}`);
  }
  return res.json();
}


export async function getQaReports(
  taskId: string
): Promise<{ task_id: string; total_cycles: number; reports: QAReportData[] }> {
  const url = `${API_BASE_URL}/api/v1/tasks/${taskId}/qa-reports`;
  const res = await fetch(url, {
    cache: "no-store",
    credentials: "include",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch QA reports: ${res.status}`);
  }
  return res.json();
}

export async function getReviewReports(
  taskId: string
): Promise<{ task_id: string; total_reviews: number; reports: CodeReviewReportData[] }> {
  const url = `${API_BASE_URL}/api/v1/tasks/${taskId}/review-reports`;
  const res = await fetch(url, {
    cache: "no-store",
    credentials: "include",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch Code Review reports: ${res.status}`);
  }
  return res.json();
}

// ── Chapter 5: Delivery & Pull Request ─────────────────────────────────────

export interface FinalApprovalResponseData {
  id: string;
  task_id: string;
  decision: "APPROVED" | "REJECTED";
  feedback?: string | null;
  decided_at: string;
  task_status: string;
  approval?: DeliveryApprovalData;
}

export async function submitFinalApproval(
  taskId: string,
  decisionOrPayload: "APPROVED" | "REJECTED" | { decision: "APPROVED" | "REJECTED"; feedback?: string },
  feedback?: string
): Promise<FinalApprovalResponseData> {
  const url = `${API_BASE_URL}/api/v1/tasks/${taskId}/final-approval`;
  const body =
    typeof decisionOrPayload === "object"
      ? decisionOrPayload
      : { decision: decisionOrPayload, feedback };
  const res = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Final approval failed: ${res.status}`);
  }
  return res.json();
}

export async function deliverTask(
  taskId: string
): Promise<{ status: string; message: string; pull_request: PullRequestData }> {
  const url = `${API_BASE_URL}/api/v1/tasks/${taskId}/deliver`;
  const res = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: { "Accept": "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Delivery failed: ${res.status}`);
  }
  return res.json();
}

export async function getDeliveryStatus(taskId: string): Promise<DeliveryStatusResponse> {
  const url = `${API_BASE_URL}/api/v1/tasks/${taskId}/delivery`;
  const res = await fetch(url, {
    cache: "no-store",
    credentials: "include",
    headers: { "Accept": "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch delivery status: ${res.status}`);
  }
  return res.json();
}

export async function getTaskDiff(taskId: string): Promise<DiffResponse> {
  const url = `${API_BASE_URL}/api/v1/tasks/${taskId}/diff`;
  const res = await fetch(url, {
    cache: "no-store",
    credentials: "include",
    headers: { "Accept": "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch task diff: ${res.status}`);
  }
  return res.json();
}

export async function getTaskTimeline(
  taskId: string
): Promise<{ task_id: string; timeline: TimelineEvent[] }> {
  const url = `${API_BASE_URL}/api/v1/tasks/${taskId}/timeline`;
  const res = await fetch(url, {
    cache: "no-store",
    credentials: "include",
    headers: { "Accept": "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch task timeline: ${res.status}`);
  }
  return res.json();
}
