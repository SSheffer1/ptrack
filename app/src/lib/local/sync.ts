// Keeps the on-device store in step with the server.
//
// One sync = POST /api/sync with this device's unsent entries and the cursor
// from last time; the server answers with every entry after that cursor
// (including ours, now numbered). Applying those to the store is safe in any
// order because of last-write-wins (see store.ts). Repeat while `more` is true.

import type { LocalStore, LogEntry } from './store'

export interface SyncRequest {
  device_id: string
  since: number
  changes: Omit<LogEntry, 'seq' | 'device_id'>[]
}

export interface SyncResponse {
  changes: (LogEntry & { seq: number })[]
  cursor: number
  more: boolean
}

/** Sends one sync request. Throws SyncRejected if the server refused the changes (HTTP 400). */
export type Transport = (serverUrl: string, body: SyncRequest) => Promise<SyncResponse>

export class SyncRejected extends Error {}

export interface SyncSettings {
  deviceId: string
  serverUrl: string // '' = same site the page came from (desktop browser testing)
  cursor: number
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
        const res = await this.transport(this.settings.serverUrl, {
          device_id: this.settings.deviceId,
          since: this.settings.cursor,
          changes: outgoing.map(({ entity, entity_id, field, value, ts }) => ({ entity, entity_id, field, value, ts })),
        })
        for (const change of res.changes) {
          if (this.store.apply(change)) dataChanged = true
        }
        this.settings.cursor = res.cursor
        if (!res.more) break
        // Later pages only download; our changes were accepted with the first request.
        outgoing = []
      }
      this.update({ lastSync: Date.now(), error: '' })
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e)
      this.update({ error: message, rejected: e instanceof SyncRejected })
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
export const fetchTransport: Transport = async (serverUrl, body) => {
  let res: Response
  try {
    res = await fetch(`${serverUrl.replace(/\/$/, '')}/api/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  } catch (e) {
    const reason = e instanceof Error ? e.message : String(e)
    // An https:// address for a server that only speaks plain HTTP fails with a TLS error.
    const hint = serverUrl.startsWith('https://') && /TLS|SSL/i.test(reason) ? ' (try http:// instead of https://)' : ''
    throw new Error(`Can't reach the server${serverUrl ? ` at ${serverUrl}` : ''}: ${reason}${hint}`)
  }
  if (res.status === 400 || res.status === 422) {
    const detail = await res.json().then((j) => JSON.stringify(j.detail), () => res.statusText)
    throw new SyncRejected(`Server rejected changes: ${detail}`)
  }
  if (!res.ok) throw new Error(`Server error ${res.status}`)
  return res.json()
}
