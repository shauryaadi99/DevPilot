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

export interface GitHubUser {
  login: string;
  name?: string;
  avatar_url?: string;
  html_url: string;
  public_repos: number;
}

export interface GitHubRepo {
  id?: number;
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

export interface InspectionData {
  tree_summary: {
    total_files: number;
    manifest_count: number;
    key_paths: string[];
  };
  detected_languages: string[];
  detected_frameworks: string[];
  detected_entrypoints: string[];
  manifests_summary: Record<string, string>;
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

export interface ImplementationPlanData {
  id: string;
  summary: string;
  repository_understanding: string;
  confirmed_observations: string[];
  files_to_create: FileToCreate[];
  files_to_modify: FileToModify[];
  api_contract_changes: ApiContractChange[];
  implementation_steps: ImplementationStep[];
  dependencies: string[];
  testing_strategy: {
    unit_tests?: string[];
    integration_tests?: string[];
    manual_checks?: string[];
    [key: string]: any;
  };
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
  title: string;
  requirement: string;
  status: string;
  created_at: string;
  updated_at: string;
  repository: {
    id: string;
    name: string;
    full_name: string;
    owner: string;
    default_branch: string;
    html_url: string;
  };
  inspection?: InspectionData | null;
  requirement_analysis?: RequirementAnalysisData | null;
  implementation_plan?: ImplementationPlanData | null;
  approvals: PlanApprovalData[];
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchHealth(): Promise<HealthResponse> {
  const url = `${API_BASE_URL}/api/v1/health`;
  const response = await fetch(url, {
    cache: "no-store",
    headers: { "Accept": "application/json" },
  });

  if (!response.ok) {
    throw new Error(`Backend returned HTTP status ${response.status}: ${response.statusText}`);
  }

  return response.json();
}

export async function testGroqConnection(): Promise<GroqTestResult> {
  const url = `${API_BASE_URL}/api/v1/llm/test`;
  const response = await fetch(url, {
    method: "POST",
    headers: { "Accept": "application/json" },
  });

  if (!response.ok) {
    throw new Error(`LLM test returned HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
}

export async function connectGitHub(token: string): Promise<{ status: string; user: GitHubUser }> {
  const url = `${API_BASE_URL}/api/v1/github/connect`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Accept": "application/json" },
    body: JSON.stringify({ token }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `GitHub connection failed with status ${res.status}`);
  }
  return res.json();
}

export async function listUserRepositories(token: string): Promise<GitHubRepo[]> {
  const url = `${API_BASE_URL}/api/v1/github/repos`;
  const res = await fetch(url, {
    headers: {
      "Accept": "application/json",
      "X-GitHub-Token": token,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to list repositories: ${res.status}`);
  }
  const data = await res.json();
  return data.repositories;
}

export async function selectRepository(repo: GitHubRepo): Promise<{ status: string; repository: any }> {
  const url = `${API_BASE_URL}/api/v1/github/select`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Accept": "application/json" },
    body: JSON.stringify({
      github_id: repo.id,
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
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to select repository: ${res.status}`);
  }
  return res.json();
}

export async function createTask(repoId: string, title: string, requirement: string): Promise<any> {
  const url = `${API_BASE_URL}/api/v1/tasks`;
  const res = await fetch(url, {
    method: "POST",
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
    cache: "no-store",
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
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Pipeline execution failed: ${res.status}`);
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
    headers: { "Content-Type": "application/json", "Accept": "application/json" },
    body: JSON.stringify({ decision, feedback }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Approval submission failed: ${res.status}`);
  }
  return res.json();
}


// ── Chapter 3: Execution API ───────────────────────────────────────────────

export interface FileChangeData {
  file_path: string;
  change_type: "CREATE" | "MODIFY" | "DELETE";
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

export interface ExecutionStatus {
  execution_id: string;
  task_id: string;
  status: "PENDING" | "CLONING" | "EXECUTING" | "COMMITTING" | "AWAITING_QA" | "AWAITING_REVIEW" | "AWAITING_DELIVERY" | "COMPLETED" | "FAILED" | "CANCELLED" | "CLOSED";
  branch_name: string | null;
  current_step: number;
  total_steps: number;
  commit_sha: string | null;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
  file_changes: FileChangeData[];
  logs: ExecutionLogEntry[];
}

export async function executeTask(
  taskId: string,
  githubToken?: string,
): Promise<{ status: string; execution_id: string; task_id: string; message: string }> {
  const url = `${API_BASE_URL}/api/v1/tasks/${taskId}/execute`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Accept": "application/json" },
    body: JSON.stringify({ github_token: githubToken || null }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Execution start failed: ${res.status}`);
  }
  return res.json();
}

export async function getExecutionStatus(taskId: string): Promise<ExecutionStatus> {
  const url = `${API_BASE_URL}/api/v1/tasks/${taskId}/execution`;
  const res = await fetch(url, {
    cache: "no-store",
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
    headers: { "Accept": "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Close task failed: ${res.status}`);
  }
  return res.json();
}
