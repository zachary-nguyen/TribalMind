/**
 * Thin wrapper around fetch for calling the Backboard proxy endpoints.
 */

const BASE = "/api/backboard"

async function request<T = unknown>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status}: ${detail}`)
  }
  if (res.status === 204) return {} as T
  return res.json() as Promise<T>
}

// ── Assistants ──────────────────────────────────────────────────────────────

export interface Assistant {
  assistant_id: string
  name: string
  system_prompt?: string
  embedding_provider?: string
  embedding_model?: string
  created_at?: string
  updated_at?: string
  [key: string]: unknown
}

export function listAssistants(): Promise<Assistant[]> {
  return request<Assistant[]>("GET", "/assistants")
}

export function getAssistant(id: string): Promise<Assistant> {
  return request<Assistant>("GET", `/assistants/${id}`)
}

export function deleteAssistant(id: string): Promise<unknown> {
  return request("DELETE", `/assistants/${id}`)
}

// ── Memories ────────────────────────────────────────────────────────────────

export interface Memory {
  memory_id?: string
  id?: string
  content: string
  created_at?: string
  updated_at?: string
  score?: number
  [key: string]: unknown
}

export function listMemories(assistantId: string): Promise<Memory[]> {
  return request<Memory[]>("GET", `/assistants/${assistantId}/memories`)
}

export function addMemory(assistantId: string, content: string): Promise<Memory> {
  return request<Memory>("POST", `/assistants/${assistantId}/memories`, { content })
}

export function searchMemories(assistantId: string, query: string, limit = 10): Promise<Memory[]> {
  return request<Memory[]>("POST", `/assistants/${assistantId}/memories/search`, { query, limit })
}

export function deleteMemory(assistantId: string, memoryId: string): Promise<unknown> {
  return request("DELETE", `/assistants/${assistantId}/memories/${memoryId}`)
}

export function clearMemories(assistantId: string): Promise<{ deleted: number }> {
  return request<{ deleted: number }>("DELETE", `/assistants/${assistantId}/memories`)
}

// ── Activity ──────────────────────────────────────────────────────────────

export interface ActivityEvent {
  timestamp: string
  action: string
  summary: string
  query?: string
  memory_id?: string
  count?: number
  source?: string
  assistant_id?: string
  [key: string]: unknown
}

async function activityRequest<T = unknown>(
  method: string,
  path: string,
): Promise<T> {
  const res = await fetch(`/api${path}`, { method })
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status}: ${detail}`)
  }
  if (res.status === 204) return {} as T
  return res.json() as Promise<T>
}

export function getActivity(
  limit = 100,
  offset = 0,
  action = "",
  assistantId = "",
): Promise<ActivityEvent[]> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  if (action) params.set("action", action)
  if (assistantId) params.set("assistant_id", assistantId)
  return activityRequest<ActivityEvent[]>("GET", `/activity?${params}`)
}

export function clearActivity(): Promise<{ deleted: number }> {
  return activityRequest<{ deleted: number }>("DELETE", "/activity")
}

