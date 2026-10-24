// The on-device copy of the data: the change log, and the rows rebuilt from it.
//
// This mirrors server/src/ptrack/sync.py. Every edit is an entry "set `field`
// of `entity_id` to `value` at `ts`, from `device_id`". For each field the entry
// with the highest (ts, device_id) wins, so the result doesn't depend on the
// order entries arrive in. That lets the phone apply its own edits right away
// and the server's later, and still end up exactly where the server is.

export type Entity = 'project' | 'item' | 'comment'

export interface LogEntry {
  entity: Entity
  entity_id: string
  field: string
  value: unknown
  ts: number // ms since epoch
  device_id: string
  user_id?: string // who made it (from the server; unset for this device's unsent edits)
  seq?: number // set once the server has the entry (its position in the server's log)
}

export type Row = Record<string, unknown> & { id: string; created_at: number; updated_at: number }

// Values a row has before any entry sets them; same as the server's model defaults.
const DEFAULTS: Record<Entity, Record<string, unknown>> = {
  project: { key: '', name: '', deleted: false },
  item: {
    type: 'ticket',
    project_id: null,
    number: null,
    title: '',
    body: '',
    status: 'todo',
    priority: 'none',
    labels: [],
    due: null,
    due_time: null,
    repeat: null,
    next_id: null,
    assigned_on: null,
    completed_on: null,
    reminders: null,
    deleted: false,
  },
  comment: { item_id: '', body: '', deleted: false },
}

const SEP = '\u0000'

export class LocalStore {
  readonly rows: Record<Entity, Map<string, Row>> = { project: new Map(), item: new Map(), comment: new Map() }
  private log: LogEntry[] = []
  private byEntity = new Map<string, LogEntry[]>() // entity_id → its entries, for history
  private seen = new Map<string, LogEntry>() // identity → entry, to skip duplicates
  private winners = new Map<string, LogEntry>() // entity/id/field → entry currently in effect
  private lastTs = 0

  constructor(entries: LogEntry[] = []) {
    this.load(entries)
  }

  /** Replace everything with the given entries (replayed from scratch). */
  load(entries: LogEntry[]) {
    for (const rows of Object.values(this.rows)) rows.clear()
    this.log = []
    this.byEntity.clear()
    this.seen.clear()
    this.winners.clear()
    for (const e of entries) this.apply(e)
  }

  discardPending(deviceId: string) {
    this.load(this.log.filter((e) => !isPending(e, deviceId)))
  }

  /** Forget everything downloaded, keeping this device's unsent edits (the server sends it all again). */
  keepOnlyPending(deviceId: string) {
    this.load(this.log.filter((e) => isPending(e, deviceId)))
  }

  /** Remove unsent edits the server refused. */
  removePending(deviceId: string, refused: { entity_id: string; field: string; ts: number }[]) {
    const key = (e: { entity_id: string; field: string; ts: number }) => [e.entity_id, e.field, e.ts].join(SEP)
    const gone = new Set(refused.map(key))
    this.load(this.log.filter((e) => !(isPending(e, deviceId) && gone.has(key(e)))))
  }

  /** Add an entry (from this device or the server). Returns false if it was already known. */
  apply(entry: LogEntry): boolean {
    const identity = [entry.entity_id, entry.field, entry.ts, entry.device_id].join(SEP)
    const known = this.seen.get(identity)
    if (known) {
      if (entry.seq !== undefined) known.seq = entry.seq // the server confirmed one of ours
      return false
    }
    this.seen.set(identity, entry)
    this.log.push(entry)
    this.byEntity.set(entry.entity_id, [...(this.byEntity.get(entry.entity_id) ?? []), entry])
    this.lastTs = Math.max(this.lastTs, entry.ts)

    const fieldKey = [entry.entity, entry.entity_id, entry.field].join(SEP)
    const current = this.winners.get(fieldKey)
    let row = this.rows[entry.entity].get(entry.entity_id)
    if (!row) {
      row = { ...structuredClone(DEFAULTS[entry.entity]), id: entry.entity_id, created_at: entry.ts, updated_at: 0 }
      this.rows[entry.entity].set(entry.entity_id, row)
    }
    row.created_at = Math.min(row.created_at, entry.ts)
    if (current && newer(current, entry)) return true // an edit with a later timestamp already won

    this.winners.set(fieldKey, entry)
    row[entry.field] = entry.value
    row.updated_at = Math.max(row.updated_at, entry.ts)
    return true
  }

  /**
   * Timestamp for a new edit on this device: the wall clock, but always later
   * than anything already in the log (same "simplified hybrid logical clock" as
   * the server), so a new edit beats whatever it was based on.
   */
  nextTs(): number {
    this.lastTs = Math.max(Date.now(), this.lastTs + 1)
    return this.lastTs
  }

  /** This device's entries the server doesn't have yet. */
  pending(deviceId: string): LogEntry[] {
    return this.log.filter((e) => e.device_id === deviceId && e.seq === undefined)
  }

  historyOf(entityId: string): LogEntry[] {
    return [...(this.byEntity.get(entityId) ?? [])].sort((a, b) => a.ts - b.ts)
  }

  entries(): LogEntry[] {
    return this.log
  }
}

function isPending(e: LogEntry, deviceId: string): boolean {
  return e.device_id === deviceId && e.seq === undefined
}

/** Does `a` beat `b`? Later timestamp wins; the device id breaks exact ties (as on the server). */
function newer(a: LogEntry, b: LogEntry): boolean {
  return a.ts !== b.ts ? a.ts > b.ts : a.device_id > b.device_id
}
