// Data types shared by the whole app. They mirror the Pydantic models in
// server/src/ptrack/api.py; if one changes, change both.

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
  type: 'ticket'
  number: number | null
  title: string
  body: string
  status: Status
  priority: Priority
  labels: string[]
  due: string | null // "YYYY-MM-DD"
  due_time: string | null // "HH:MM:SS"
  repeat: string | null // RRULE, see lib/recurrence.ts
  next_id: string | null // next copy of a recurring ticket, once this one is done
  assigned_on: string | null // only if set by hand
  assigned: string // assigned_on, or else the day it was created
  completed_on: string | null // set when marked done; can be changed
  reminders: string[] | null // offsets like "-8h"; null = default, [] = none (see reminders.ts)
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
  due_time?: string | null
  repeat?: string | null
  assigned_on?: string | null
  reminders?: string[] | null
}

export type ItemUpdate = Partial<
  Pick<
    Item,
    | 'title'
    | 'body'
    | 'status'
    | 'priority'
    | 'labels'
    | 'due'
    | 'due_time'
    | 'repeat'
    | 'assigned_on'
    | 'completed_on'
    | 'reminders'
  >
>

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
  due_from?: string
  due_to?: string
  completed_from?: string
  completed_to?: string
  sort?: SortOrder
}

export type SortOrder = 'created' | 'due' | 'completed'
export const SORT_LABELS: Record<SortOrder, string> = {
  created: 'Newest last',
  due: 'Due date',
  completed: 'Recently completed',
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

export function errorText(e: unknown): string {
  return e instanceof Error ? e.message : String(e)
}

/** Everything the UI can ask for. Implemented by the server API (http.ts) and the on-device store (local/). */
export interface Backend {
  listProjects(): Promise<Project[]>
  createProject(key: string, name: string): Promise<Project>
  listItems(filters?: ItemFilters): Promise<Item[]>
  getItem(ref: string): Promise<Item>
  createItem(item: ItemCreate): Promise<Item>
  updateItem(ref: string, fields: ItemUpdate): Promise<Item>
  deleteItem(ref: string): Promise<void>
  getHistory(ref: string): Promise<Change[]>
  listComments(ref: string): Promise<Comment[]>
  addComment(ref: string, body: string): Promise<Comment>
}
