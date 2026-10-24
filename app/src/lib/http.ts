// Backend that talks to the server's /api endpoints directly. Used by the
// desktop browser, where the page is served by (or proxied to) the server.

import {
  ApiError,
  type Backend,
  type Change,
  type Comment,
  type Item,
  type ItemCreate,
  type ItemFilters,
  type ItemUpdate,
  type Project,
} from './types'

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

export const httpBackend: Backend = {
  listProjects: () => request<Project[]>('GET', '/projects'),
  createProject: (key: string, name: string) => request<Project>('POST', '/projects', { key, name }),

  listItems(filters: ItemFilters = {}) {
    const params = new URLSearchParams()
    if (filters.project) params.set('project', filters.project)
    for (const s of filters.status ?? []) params.append('status', s)
    if (filters.label) params.set('label', filters.label)
    if (filters.q) params.set('q', filters.q)
    if (filters.due_from) params.set('due_from', filters.due_from)
    if (filters.due_to) params.set('due_to', filters.due_to)
    if (filters.completed_from) params.set('completed_from', filters.completed_from)
    if (filters.completed_to) params.set('completed_to', filters.completed_to)
    if (filters.sort) params.set('sort', filters.sort)
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

