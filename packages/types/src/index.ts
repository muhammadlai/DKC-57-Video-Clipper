/**
 * @aitzaz/types — API contract types shared between the FastAPI backend and
 * the Next.js frontend. Keep these in sync with apps/api/aitzaz_api/schemas.
 */

export type UUID = string;
export type ISODate = string;

// --- Auth ---------------------------------------------------------------

export interface User {
  id: UUID;
  email: string;
  name: string;
  role: "admin" | "user" | string;
  is_active: boolean;
  created_at: ISODate;
  last_login_at: ISODate | null;
}

export interface AuthResponse {
  user: User;
  access_token: string;
  token_type: string;
  expires_at: ISODate;
}

// --- Chat -----------------------------------------------------------------

export interface ToolCallInfo {
  slug: string;
  arguments?: Record<string, unknown>;
  ok: boolean;
  result?: unknown;
  error?: string | null;
  duration_ms: number;
}

export interface ChatMessage {
  id: UUID;
  role: "user" | "assistant" | "system";
  content: string;
  meta?: {
    provider?: string;
    model?: string;
    demo_mode?: boolean;
    rounds?: number;
    tool_calls?: ToolCallInfo[];
    provider_warning?: string | null;
  } | null;
  created_at: ISODate;
}

export interface Conversation {
  id: UUID;
  title: string;
  agent_id: UUID | null;
  created_at: ISODate;
  last_message_at: ISODate | null;
  message_count: number;
}

export interface ChatResponse {
  conversation_id: UUID;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
  tool_calls: ToolCallInfo[];
  provider: string;
  model: string;
  demo_mode: boolean;
}

// --- Tasks ------------------------------------------------------------------

export type TaskStatus =
  | "pending"
  | "running"
  | "waiting_approval"
  | "completed"
  | "failed"
  | "cancelled";

export type TaskPriority = "low" | "medium" | "high" | "urgent";

export interface Task {
  id: UUID;
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  due_at: ISODate | null;
  created_at: ISODate;
  updated_at: ISODate;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

// --- Approvals --------------------------------------------------------------

export type ApprovalStatus = "pending" | "approved" | "rejected" | "expired";

export interface Approval {
  id: UUID;
  task_id: UUID | null;
  action_type: string;
  description: string;
  payload: Record<string, unknown>;
  status: ApprovalStatus;
  requested_at: ISODate;
  decided_at: ISODate | null;
  expires_at: ISODate | null;
  decision_note: string | null;
  created_at: ISODate;
  updated_at: ISODate;
}

// --- Memory -------------------------------------------------------------------

export type MemoryCategory = "preference" | "fact" | "conversation" | "task" | "system";

export interface Memory {
  id: UUID;
  category: MemoryCategory;
  content: string;
  importance: number;
  metadata?: Record<string, unknown> | null;
  created_at: ISODate;
  updated_at: ISODate;
}

// --- Activity -------------------------------------------------------------------

export interface ActivityEntry {
  id: UUID;
  activity_type: string;
  message: string;
  meta?: Record<string, unknown> | null;
  ip?: string | null;
  created_at: ISODate;
}

// --- Tools ------------------------------------------------------------------------

export interface ToolInfo {
  id: UUID;
  slug: string;
  name: string;
  description: string;
  category: string;
  input_schema: JsonSchema;
  output_schema: JsonSchema;
  required_permission: string | null;
  execution: string;
  enabled: boolean;
  is_builtin: boolean;
  created_at: ISODate;
  updated_at: ISODate;
}

export interface JsonSchema {
  type?: string;
  properties?: Record<string, JsonSchemaProperty>;
  required?: string[];
}

export interface JsonSchemaProperty {
  type?: string;
  description?: string;
  enum?: string[];
  default?: unknown;
  minimum?: number;
  maximum?: number;
  minLength?: number;
  maxLength?: number;
}

export interface ToolRunResult {
  tool: string;
  ok: boolean;
  result?: unknown;
  error?: string | null;
  error_code?: string | null;
  duration_ms: number;
}

// --- Agents -------------------------------------------------------------------------

export interface Agent {
  id: UUID;
  slug: string;
  name: string;
  description: string;
  system_instructions: string;
  capabilities: string[];
  tools: string[];
  default_config: Record<string, unknown>;
  status: "active" | "paused" | "disabled" | string;
  is_builtin: boolean;
  created_at: ISODate;
  updated_at: ISODate;
}

export interface FutureAgent {
  slug: string;
  name: string;
  phase: string;
  description: string;
}

// --- Dashboard ------------------------------------------------------------------------

export interface TaskStats {
  total: number;
  pending: number;
  running: number;
  waiting_approval: number;
  completed: number;
  failed: number;
  cancelled: number;
}

export interface DashboardStats {
  tasks: TaskStats;
  pending_approvals: number;
  memories_count: number;
  tools_connected: number;
  conversations_count: number;
  agent_status: string;
  demo_mode: boolean;
  recent_activity: ActivityEntry[];
}

// --- Settings --------------------------------------------------------------------------

export interface AppSettings {
  data: {
    general?: Record<string, unknown>;
    ai_provider?: Record<string, unknown>;
    appearance?: Record<string, unknown>;
    security?: Record<string, unknown>;
    notifications?: Record<string, unknown>;
    memory?: Record<string, unknown>;
    tools?: Record<string, unknown>;
    permissions?: Record<string, unknown>;
  };
}

// --- Errors ------------------------------------------------------------------------------

export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}
