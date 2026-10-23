// Typed wrappers around the server's /api endpoints. These types mirror the
// Pydantic models in server/src/ptrack/api.py; if one changes, change both.

export type Status = 'backlog' | 'todo' | 'in_progress' | 'blocked' | 'done'
export type Priority = 'none' | 'low' | 'medium' | 'high' | 'urgent'

export const STATUSES: Status[] = ['backlog', 'todo', 'in_progress', 'blocked', 'done']
export const STATUS_LABELS: Record<Status, string> = {
  backlog: 'Backlog',
  todo: 'To do',
  in_progress: 'In progress',
  blocked: 'Blocked',
  done: 'Done',
}

export const PRIORITIES: Priority[] = ['none', 'low', 'medium', 'high', 'urgent']
export const PRIORITY_LABELS: Record<Priority, string> = {
  none: 'No priority',
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  urgent: 'Urgent',
}

export interface Project {
  id: string
  key: string
  name: string
}

export interface Item {
  id: string
  key: string | null
  project_id: string | null
  type: 'ticket' | 'event'
  number: number | null
  title: string
  body: string
  status: Status
  priority: Priority
  labels: string[]
  due: string | null // "YYYY-MM-DD"
  created_at: number
  updated_at: number
}

export interface ItemCreate {
  project: string
  title: string
  body?: string
  status?: Status
  priority?: Priority
  labels?: string[]
  due?: string | null
}

export type ItemUpdate = Partial<Pick<Item, 'title' | 'body' | 'status' | 'priority' | 'labels' | 'due'>>

export interface Comment {
  id: string
  item_id: string
  body: string
  created_at: number
}

export interface Change {
  seq: number
  field: string
  value: unknown
  ts: number
  device_id: string
}

export interface ItemFilters {
  project?: string
  status?: Status[]
  label?: string
  q?: string
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

// FastAPI errors look like {"detail": "text"} or, for invalid input,
// {"detail": [{"loc": ["body", "title"], "msg": "..."}]}.
async function errorMessage(res: Response): Promise<string> {
  try {
    const { detail } = await res.json()
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map((d) => `${d.loc.at(-1)}: ${d.msg}`).join('; ')
  } catch {
    // not JSON; fall through
  }
  return `${res.status} ${res.statusText}`
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) throw new ApiError(res.status, await errorMessage(res))
  return res.status === 204 ? (undefined as T) : res.json()
}

const enc = encodeURIComponent

export const api = {
  listProjects: () => request<Project[]>('GET', '/projects'),
  createProject: (key: string, name: string) => request<Project>('POST', '/projects', { key, name }),

  listItems(filters: ItemFilters = {}) {
    const params = new URLSearchParams()
    if (filters.project) params.set('project', filters.project)
    for (const s of filters.status ?? []) params.append('status', s)
    if (filters.label) params.set('label', filters.label)
    if (filters.q) params.set('q', filters.q)
    return request<Item[]>('GET', `/items?${params}`)
  },
  getItem: (ref: string) => request<Item>('GET', `/items/${enc(ref)}`),
  createItem: (item: ItemCreate) => request<Item>('POST', '/items', item),
  updateItem: (ref: string, fields: ItemUpdate) => request<Item>('PATCH', `/items/${enc(ref)}`, fields),
  deleteItem: (ref: string) => request<void>('DELETE', `/items/${enc(ref)}`),
  getHistory: (ref: string) => request<Change[]>('GET', `/items/${enc(ref)}/history`),

  listComments: (ref: string) => request<Comment[]>('GET', `/items/${enc(ref)}/comments`),
  addComment: (ref: string, body: string) => request<Comment>('POST', `/items/${enc(ref)}/comments`, { body }),
}

export function errorText(e: unknown): string {
  return e instanceof Error ? e.message : String(e)
}
