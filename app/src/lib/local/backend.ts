// Backend that reads and writes the on-device store, so the app works offline.
// It mirrors the server's REST endpoints (server/src/ptrack/api.py): same
// filters, same validation, same results. Writes become log entries that the
// sync engine sends to the server later.
//
// Two things only the server does, so they appear after the next sync:
// ticket numbers (the 12 in HOME-12) and the next copy of a recurring ticket.
//
// Sharing: the same permission rules as server/src/ptrack/sync.py are checked
// here too, so a disallowed edit is refused right away instead of being dropped
// by the server later. Membership itself comes from the server (`people`), and
// adding/removing members goes straight to the server (`online`).

import {
  ApiError,
  type Backend,
  type Change,
  type Comment,
  type Item,
  type ItemCreate,
  type ItemFilters,
  type ItemUpdate,
  type Member,
  type Project,
  type Role,
  notifiedUser,
} from '../types'
import { toISODate } from '../format'
import { PREF_DEFAULTS } from '../prefs.svelte'
import { isValidOffset, normalizeReminders } from '../reminders'
import type { Entity, LocalStore, Row } from './store'
import { membersWithNames, type People } from './sync'

const KEY_RE = /^([A-Z][A-Z0-9]{0,9})-(\d+)$/
const PROJECT_KEY_RE = /^[A-Z][A-Z0-9]{0,9}$/

export class LocalBackend implements Backend {
  constructor(
    private store: LocalStore,
    private deviceId: () => string,
    private onWrite: () => void, // tells the sync engine there's something to send
    private people: () => People = () => ({ me: null, users: [], members: [] }),
    private online?: Pick<Backend, 'addMember' | 'removeMember'>,
  ) {}

  private me(): string {
    return this.people().me?.id ?? ''
  }

  /** My role in a project. A project made on this device that hasn't synced yet is mine. */
  private role(projectId: string): Role | null {
    const m = this.people().members.find((x) => x.project_id === projectId && x.user_id === this.me())
    if (m) return m.role
    const project = this.store.rows.project.get(projectId)
    return project && !project.created_by ? 'owner' : null
  }

  private requireOwner(projectId: string, what: string) {
    if (this.role(projectId) !== 'owner') throw new ApiError(403, `only the project's owner can ${what}`)
  }

  // --- Writing -----------------------------------------------------------------

  private write(entity: Entity, id: string, fields: Record<string, unknown>) {
    const ts = this.store.nextTs()
    for (const [field, value] of Object.entries(fields)) {
      this.store.apply({ entity, entity_id: id, field, value, ts, device_id: this.deviceId() })
    }
    this.onWrite()
  }

  // --- Projects -------------------------------------------------------------------

  private projects(): Row[] {
    return [...this.store.rows.project.values()].filter((p) => !p.deleted && this.role(p.id))
  }

  private projectByKey(key: string): Row | undefined {
    return this.projects().find((p) => p.key === key)
  }

  async listProjects(): Promise<Project[]> {
    return this.projects()
      .sort((a, b) => String(a.key).localeCompare(String(b.key)))
      .map((p) => this.toProject(p))
  }

  async createProject(key: string, name: string): Promise<Project> {
    if (!PROJECT_KEY_RE.test(key)) throw new ApiError(422, 'key: must be A-Z/0-9, starting with a letter, max 10')
    if (!name.trim()) throw new ApiError(422, 'name: must not be empty')
    if (this.projectByKey(key)) throw new ApiError(409, `project ${key} already exists`)
    const id = newId()
    this.write('project', id, { key, name })
    return this.toProject(this.store.rows.project.get(id)!)
  }

  private toProject(row: Row): Project {
    return { id: row.id, key: row.key as string, name: row.name as string, role: this.role(row.id) ?? 'editor' }
  }

  private getProject(key: string): Row {
    const p = this.projectByKey(key)
    if (!p) throw new ApiError(404, `project ${key} not found`)
    return p
  }

  async updateProject(key: string, fields: { name?: string }): Promise<Project> {
    const p = this.getProject(key)
    this.requireOwner(p.id, 'rename it')
    if (fields.name !== undefined && !fields.name.trim()) throw new ApiError(422, 'name: must not be empty')
    if (fields.name !== undefined) this.write('project', p.id, { name: fields.name })
    return this.toProject(p)
  }

  async deleteProject(key: string): Promise<void> {
    const p = this.getProject(key)
    this.requireOwner(p.id, 'delete it')
    this.write('project', p.id, { deleted: true })
  }

  async listMembers(key: string): Promise<Member[]> {
    const p = this.getProject(key)
    const members = membersWithNames(this.people(), p.id)
    if (members.length || p.created_by) return members
    const me = this.people().me // a project made here, before its first sync
    return me ? [{ project_id: p.id, user_id: me.id, username: me.username, display_name: me.display_name, role: 'owner' }] : []
  }

  async addMember(key: string, username: string): Promise<Member[]> {
    if (!this.online) throw new ApiError(0, 'adding members needs a connection to the server')
    return this.online.addMember(key, username)
  }

  async removeMember(key: string, userId: string): Promise<void> {
    if (!this.online) throw new ApiError(0, 'removing members needs a connection to the server')
    return this.online.removeMember(key, userId)
  }

  // --- Items ------------------------------------------------------------------------

  private toItem(row: Row): Item {
    const project = row.project_id ? this.store.rows.project.get(row.project_id as string) : undefined
    const key = project && row.number ? `${project.key}-${row.number}` : null
    const assigned = (row.assigned_on as string | null) ?? toISODate(new Date(row.created_at))
    // A ticket made here that hasn't synced yet was made by me.
    const created_by = (row.created_by as string | null) ?? (this.me() || null)
    return { ...(row as unknown as Item), key, assigned, created_by }
  }

  private findItem(ref: string): Row {
    let row: Row | undefined
    const m = KEY_RE.exec(ref)
    if (m) {
      const project = this.projectByKey(m[1])
      row = project && [...this.store.rows.item.values()].find((i) => i.project_id === project.id && i.number === Number(m[2]))
    } else {
      row = this.store.rows.item.get(ref)
    }
    if (!row || row.deleted || !this.role(row.project_id as string)) throw new ApiError(404, `item ${ref} not found`)
    const project = this.store.rows.project.get(row.project_id as string)
    if (!project || project.deleted) throw new ApiError(404, `item ${ref} not found`)
    return row
  }

  async listItems(f: ItemFilters = {}): Promise<Item[]> {
    const visible = new Set(this.projects().map((p) => p.id))
    let rows = [...this.store.rows.item.values()].filter((i) => !i.deleted && visible.has(i.project_id as string))
    if (f.project) {
      const p = this.projectByKey(f.project)
      if (!p) throw new ApiError(404, `project ${f.project} not found`)
      rows = rows.filter((i) => i.project_id === p.id)
    }
    if (f.status?.length) rows = rows.filter((i) => f.status!.includes(i.status as Item['status']))
    if (f.q) {
      const q = f.q.toLowerCase()
      rows = rows.filter((i) => `${i.title}\n${i.body}`.toLowerCase().includes(q))
    }
    if (f.label) rows = rows.filter((i) => (i.labels as string[]).includes(f.label!))
    const inRange = (v: unknown, from?: string, to?: string) =>
      (!from || (v !== null && (v as string) >= from)) && (!to || (v !== null && (v as string) <= to))
    rows = rows.filter((i) => inRange(i.due, f.due_from, f.due_to))
    rows = rows.filter((i) => inRange(i.completed_on, f.completed_from, f.completed_to))
    if (f.assignee === 'me') rows = rows.filter((i) => notifiedUser(this.toItem(i), this.me()) === this.me())

    // Same orders as the server: undated / unfinished last.
    const by = (get: (r: Row) => string | number | null, desc = false) => (a: Row, b: Row) => {
      const x = get(a) ?? null
      const y = get(b) ?? null
      if (x === y) return 0
      if (x === null) return 1
      if (y === null) return -1
      return (x < y ? -1 : 1) * (desc ? -1 : 1)
    }
    const chain =
      (...cmps: ((a: Row, b: Row) => number)[]) =>
      (a: Row, b: Row) => {
        for (const cmp of cmps) {
          const r = cmp(a, b)
          if (r) return r
        }
        return 0
      }
    const sorts = {
      created: by((r) => r.created_at),
      due: chain(
        by((r) => r.due as string | null),
        by((r) => r.due_time as string | null),
      ),
      completed: chain(
        by((r) => r.completed_on as string | null, true),
        by((r) => r.updated_at, true),
      ),
    }
    return rows.sort(sorts[f.sort ?? 'created']).map((r) => this.toItem(r))
  }

  async getItem(ref: string): Promise<Item> {
    return this.toItem(this.findItem(ref))
  }

  async createItem(body: ItemCreate): Promise<Item> {
    const project = this.projectByKey(body.project)
    if (!project) throw new ApiError(404, `project ${body.project} not found`)
    if (!body.title?.trim()) throw new ApiError(422, 'title: must not be empty')
    checkRepeat(body.repeat)
    checkReminders(body.reminders)
    this.checkAssignee(project.id, body.assignee_id)
    const id = newId()
    const status = body.status ?? 'todo'
    this.write('item', id, {
      type: 'ticket',
      project_id: project.id,
      title: body.title,
      body: body.body ?? '',
      status,
      priority: body.priority ?? 'none',
      labels: body.labels ?? [],
      due: body.due ?? null,
      due_time: normalizeTime(body.due_time ?? null),
      repeat: normalizeRepeat(body.repeat ?? null),
      assigned_on: body.assigned_on ?? null,
      reminders: normalizeReminders(body.reminders),
      assignee_id: body.assignee_id ?? null,
      ...(status === 'done' ? { completed_on: toISODate(new Date()) } : {}),
    })
    return this.getItem(id)
  }

  async updateItem(ref: string, fields: ItemUpdate): Promise<Item> {
    const row = this.findItem(ref)
    if ('title' in fields && !fields.title?.trim()) throw new ApiError(422, 'title: must not be empty')
    if ('repeat' in fields) checkRepeat(fields.repeat)
    if ('reminders' in fields) {
      checkReminders(fields.reminders)
      if (notifiedUser(this.toItem(row), this.me()) !== this.me()) {
        throw new ApiError(403, 'only the person the ticket is assigned to can change its reminders')
      }
    }
    if ('assignee_id' in fields) this.checkAssignee(row.project_id as string, fields.assignee_id)
    const changes: Record<string, unknown> = { ...fields }
    if ('due_time' in fields) changes.due_time = normalizeTime(fields.due_time ?? null)
    if ('repeat' in fields) changes.repeat = normalizeRepeat(fields.repeat ?? null)
    if ('reminders' in fields) changes.reminders = normalizeReminders(fields.reminders)

    // Completion date follows the status (the server keeps a date sent explicitly).
    if ('status' in fields && !('completed_on' in fields)) {
      if (fields.status === 'done' && !row.completed_on) changes.completed_on = toISODate(new Date())
      if (fields.status !== 'done' && row.completed_on) changes.completed_on = null
    }
    if (Object.keys(changes).length) this.write('item', row.id, changes)
    return this.getItem(row.id)
  }

  async deleteItem(ref: string): Promise<void> {
    const row = this.findItem(ref)
    this.requireOwner(row.project_id as string, 'delete tickets')
    this.write('item', row.id, { deleted: true })
  }

  private checkAssignee(projectId: string, userId: string | null | undefined) {
    if (!userId || userId === this.me()) return
    if (!this.people().members.some((m) => m.project_id === projectId && m.user_id === userId)) {
      throw new ApiError(403, 'the assignee must be a member of the project')
    }
  }

  async getHistory(ref: string): Promise<Change[]> {
    return this.store.historyOf(this.findItem(ref).id).map((e) => ({
      seq: e.seq ?? 0,
      field: e.field,
      value: e.value,
      ts: e.ts,
      device_id: e.device_id,
      user_id: e.user_id ?? this.me(),
    }))
  }

  // --- Comments --------------------------------------------------------------------

  async listComments(ref: string): Promise<Comment[]> {
    const item = this.findItem(ref)
    return [...this.store.rows.comment.values()]
      .filter((c) => c.item_id === item.id && !c.deleted)
      .sort((a, b) => a.created_at - b.created_at)
      .map((c) => ({
        id: c.id,
        item_id: c.item_id as string,
        body: c.body as string,
        created_by: (c.created_by as string | null) ?? (this.me() || null),
        created_at: c.created_at,
      }))
  }

  // --- Preferences ---------------------------------------------------------------

  async getPrefs(): Promise<Record<string, unknown>> {
    const row = this.store.rows.prefs.get(this.me())
    if (!row) return {}
    const { id: _id, created_at: _c, updated_at: _u, ...values } = row
    return Object.fromEntries(Object.entries(values).filter(([, v]) => v !== null && v !== undefined))
  }

  async updatePrefs(values: Record<string, unknown>): Promise<Record<string, unknown>> {
    for (const name of Object.keys(values)) {
      if (!(name in PREF_DEFAULTS)) throw new ApiError(400, `unknown preference ${name}`)
    }
    const cleaned = { ...values }
    for (const name of ['reminders_timed', 'reminders_untimed']) {
      if (Array.isArray(cleaned[name])) {
        checkReminders(cleaned[name] as string[])
        cleaned[name] = normalizeReminders(cleaned[name] as string[])
      }
    }
    if (this.me() && Object.keys(cleaned).length) this.write('prefs', this.me(), cleaned)
    return this.getPrefs()
  }

  async addComment(ref: string, body: string): Promise<Comment> {
    const item = this.findItem(ref)
    if (!body.trim()) throw new ApiError(422, 'body: must not be empty')
    const id = newId()
    this.write('comment', id, { item_id: item.id, body })
    const c = this.store.rows.comment.get(id)!
    return { id, item_id: item.id, body, created_by: this.me() || null, created_at: c.created_at }
  }
}

function newId(): string {
  return crypto.randomUUID()
}

// "10:00" (from <input type="time">) → "10:00:00", the form the server stores.
function normalizeTime(t: string | null): string | null {
  return t && /^\d{2}:\d{2}$/.test(t) ? `${t}:00` : t
}

function normalizeRepeat(rule: string | null): string | null {
  return rule?.trim() ? rule.trim().toUpperCase().replace(/^RRULE:/, '') : null
}

// The server rejects a whole sync batch if one change is invalid, and a rejected
// batch would block syncing until discarded. So check repeat rules here with the
// same limits as server/src/ptrack/recurrence.py (the server does the full check).
function checkRepeat(rule: string | null | undefined) {
  const r = normalizeRepeat(rule ?? null)
  if (r === null) return
  if (!/^FREQ=(DAILY|WEEKLY|MONTHLY|YEARLY)(;[A-Z]+=[A-Z0-9,+-]+)*$/.test(r)) {
    throw new ApiError(400, `invalid repeat rule ${r}`)
  }
  if (r.includes('COUNT=')) throw new ApiError(400, "COUNT isn't supported; use UNTIL=YYYYMMDD to end a repeat")
}

function checkReminders(list: string[] | null | undefined) {
  for (const r of normalizeReminders(list) ?? []) {
    if (!isValidOffset(r)) throw new ApiError(400, `invalid reminder ${r}; use e.g. 0, -30m, -8h, -1d`)
  }
}
