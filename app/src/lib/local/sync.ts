// Keeps the on-device store in step with the server.
//
// One sync = POST /api/sync with this device's unsent entries and the cursor
// from last time; the server answers with every entry after that cursor in the
// user's projects (including ours, now numbered). Applying those to the store
// is safe in any order because of last-write-wins (see store.ts). Repeat while
// `more` is true.
//
// The server may also answer:
// - `dropped`: some of our edits weren't allowed (e.g. we were removed from the
//   project while offline). They're discarded here.
// - `reset`: the user's projects changed (joined or left one). We forget what
//   we downloaded, keep our unsent edits, and take everything the server sends.

import type { Member, Role, User } from '../types'
import type { LocalStore, LogEntry } from './store'

export interface SyncRequest {
  device_id: string
  since: number
  epoch: number
  changes: Omit<LogEntry, 'seq' | 'device_id' | 'user_id'>[]
}

export interface Membership {
  project_id: string
  user_id: string
  role: Role
}

export interface People {
  me: User | null
  users: User[] // everyone sharing a project with me
  members: Membership[]
}

export interface SyncResponse extends People {
  changes: (LogEntry & { seq: number; user_id: string })[]
  cursor: number
  more: boolean
  dropped: { entity: string; entity_id: string; field: string; ts: number; reason: string }[]
  reset: boolean
  epoch: number
}

/** Sends one sync request. Throws SyncRejected (HTTP 400) or SignedOut (HTTP 401). */
export type Transport = (serverUrl: string, token: string, body: SyncRequest) => Promise<SyncResponse>

export class SyncRejected extends Error {}
export class SignedOut extends Error {}

export interface SyncSettings {
  deviceId: string
  serverUrl: string // '' = same site the page came from (desktop browser testing)
  token: string
  cursor: number
  epoch: number // -1 = never synced
}

/** Member rows with names, for the UI. */
export function membersWithNames(people: People, projectId: string): Member[] {
  return people.members
    .filter((m) => m.project_id === projectId)
    .map((m) => {
      const u = people.users.find((x) => x.id === m.user_id)
      return { ...m, username: u?.username ?? '?', display_name: u?.display_name ?? 'Someone' }
    })
}

export interface SyncStatus {
  syncing: boolean
  lastSync: number | null // ms since epoch of the last successful sync
  error: string
  rejected: boolean // the server refused our changes; they must be discarded to continue
  pending: number
}

export function initialStatus(): SyncStatus {
  return { syncing: false, lastSync: null, error: '', rejected: false, pending: 0 }
}

export class SyncEngine {
  private running: Promise<boolean> | null = null

  constructor(
    private store: LocalStore,
    readonly settings: SyncSettings,
    private transport: Transport,
    private onChange: (dataChanged: boolean) => void, // save to disk, refresh the UI
    readonly status: SyncStatus = initialStatus(), // the UI passes a reactive object to watch
    private onPeople: (people: People) => void = () => {},
    private onSignedOut: () => void = () => {},
  ) {
    this.status.pending = store.pending(settings.deviceId).length
  }

  /** Run a sync unless one is already running (then wait for that one). Returns whether data changed. */
  sync(): Promise<boolean> {
    this.running ??= this.run().finally(() => (this.running = null))
    return this.running
  }

  private async run(): Promise<boolean> {
    if (this.status.rejected) return false
    this.update({ syncing: true })
    let dataChanged = false
    try {
      let outgoing = this.store.pending(this.settings.deviceId)
      for (;;) {
        const res = await this.transport(this.settings.serverUrl, this.settings.token, {
          device_id: this.settings.deviceId,
          since: this.settings.cursor,
          epoch: this.settings.epoch,
          changes: outgoing.map(({ entity, entity_id, field, value, ts }) => ({ entity, entity_id, field, value, ts })),
        })
        if (res.reset) {
          this.store.keepOnlyPending(this.settings.deviceId)
          dataChanged = true
        }
        for (const change of res.changes) {
          if (this.store.apply(change)) dataChanged = true
        }
        if (res.dropped.length) {
          this.store.removePending(this.settings.deviceId, res.dropped)
          dataChanged = true
        }
        this.settings.cursor = res.cursor
        this.settings.epoch = res.epoch
        this.onPeople({ me: res.me, users: res.users, members: res.members })
        if (!res.more) break
        // Later pages only download; our changes were accepted with the first request.
        outgoing = []
      }
      this.update({ lastSync: Date.now(), error: '' })
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e)
      this.update({ error: message, rejected: e instanceof SyncRejected })
      if (e instanceof SignedOut) this.onSignedOut()
    } finally {
      this.update({ syncing: false, pending: this.store.pending(this.settings.deviceId).length })
      this.onChange(dataChanged)
    }
    return dataChanged
  }

  /** Call after a local edit. */
  noteLocalChange() {
    this.update({ pending: this.store.pending(this.settings.deviceId).length })
  }

  /** Throw away this device's unsent edits (after the server rejected them). */
  discardPending() {
    this.store.discardPending(this.settings.deviceId)
    this.update({ rejected: false, error: '', pending: 0 })
    this.onChange(true)
  }

  private update(patch: Partial<SyncStatus>) {
    Object.assign(this.status, patch)
  }
}

/** Transport over fetch. On Android, CapacitorHttp routes fetch through native HTTP. */
export const fetchTransport: Transport = async (serverUrl, token, body) => {
  let res: Response
  try {
    res = await fetch(`${serverUrl.replace(/\/$/, '')}/api/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    })
  } catch (e) {
    const reason = e instanceof Error ? e.message : String(e)
    // An https:// address for a server that only speaks plain HTTP fails with a TLS error.
    const hint = serverUrl.startsWith('https://') && /TLS|SSL/i.test(reason) ? ' (try http:// instead of https://)' : ''
    throw new Error(`Can't reach the server${serverUrl ? ` at ${serverUrl}` : ''}: ${reason}${hint}`)
  }
  if (res.status === 401) throw new SignedOut('Signed out: sign in again')
  if (res.status === 400 || res.status === 422) {
    const detail = await res.json().then((j) => JSON.stringify(j.detail), () => res.statusText)
    throw new SyncRejected(`Server rejected changes: ${detail}`)
  }
  if (!res.ok) throw new Error(`Server error ${res.status}`)
  return res.json()
}
