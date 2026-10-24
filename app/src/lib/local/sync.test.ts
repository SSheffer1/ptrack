import { describe, expect, it } from 'vitest'
import { LocalBackend } from './backend'
import { LocalStore, type LogEntry } from './store'
import { SyncEngine, SyncRejected, type SyncRequest, type SyncResponse, type Transport } from './sync'

/** A tiny stand-in for the real server: keeps a numbered log and hands out ticket numbers. */
function fakeServer(pageSize = 1000) {
  const log: (LogEntry & { seq: number })[] = []
  let nextNumber = 1
  let online = true
  let reject = false
  const transport: Transport = async (_url, req: SyncRequest): Promise<SyncResponse> => {
    if (!online) throw new Error("Can't reach the server")
    if (reject) throw new SyncRejected('Server rejected changes')
    for (const c of req.changes) {
      const dup = log.some((l) => l.entity_id === c.entity_id && l.field === c.field && l.ts === c.ts && l.device_id === req.device_id)
      if (dup) continue
      log.push({ ...c, device_id: req.device_id, seq: log.length + 1 })
      if (c.entity === 'item' && c.field === 'type') {
        log.push({ entity: 'item', entity_id: c.entity_id, field: 'number', value: nextNumber++, ts: c.ts + 1, device_id: 'server', seq: log.length + 1 })
      }
    }
    const changes = log.filter((l) => l.seq > req.since).slice(0, pageSize)
    return { changes, cursor: changes.at(-1)?.seq ?? req.since, more: changes.length === pageSize }
  }
  return {
    transport,
    log,
    goOffline: () => (online = false),
    goOnline: () => (online = true),
    rejectEverything: () => (reject = true),
  }
}

function device(id: string, transport: Transport) {
  const store = new LocalStore()
  const api = new LocalBackend(store, () => id, () => {})
  const engine = new SyncEngine(store, { deviceId: id, serverUrl: '', cursor: 0 }, transport, () => {})
  return { store, api, engine }
}

describe('SyncEngine', () => {
  it('sends offline edits when the server comes back, and gets ticket numbers', async () => {
    const server = fakeServer()
    const phone = device('phone', server.transport)
    await phone.api.createProject('HOME', 'Home')

    server.goOffline()
    const { id } = await phone.api.createItem({ project: 'HOME', title: 'Written on the bus' })
    await phone.engine.sync()
    expect(phone.engine.status.error).toMatch(/reach/)
    expect(phone.engine.status.pending).toBeGreaterThan(0)

    server.goOnline()
    expect(await phone.engine.sync()).toBe(true)
    expect(phone.engine.status).toMatchObject({ error: '', pending: 0 })
    expect((await phone.api.getItem(id)).key).toBe('HOME-1')
  })

  it('two devices converge, including conflicting edits', async () => {
    const server = fakeServer()
    const a = device('phone-a', server.transport)
    const b = device('phone-b', server.transport)
    await a.api.createProject('HOME', 'Home')
    const { id } = await a.api.createItem({ project: 'HOME', title: 'Original' })
    await a.engine.sync()
    await b.engine.sync()

    await b.api.updateItem(id, { title: "B's edit" }) // earlier
    await new Promise((r) => setTimeout(r, 5))
    await a.api.updateItem(id, { title: "A's edit", status: 'done' }) // later
    await a.engine.sync()
    await b.engine.sync() // B uploads its older edit, then downloads A's
    await a.engine.sync()

    for (const d of [a, b]) {
      const item = await d.api.getItem(id)
      expect([item.title, item.status, item.key]).toEqual(["A's edit", 'done', 'HOME-1'])
    }
  })

  it('downloads in pages until done', async () => {
    const server = fakeServer(3)
    const a = device('phone-a', server.transport)
    await a.api.createProject('HOME', 'Home')
    for (const t of ['one', 'two', 'three']) await a.api.createItem({ project: 'HOME', title: t })
    await a.engine.sync()

    const b = device('phone-b', server.transport)
    await b.engine.sync()
    expect((await b.api.listItems()).map((i) => i.key)).toEqual(['HOME-1', 'HOME-2', 'HOME-3'])
  })

  it('stops when the server rejects changes, until they are discarded', async () => {
    const server = fakeServer()
    const phone = device('phone', server.transport)
    await phone.api.createProject('HOME', 'Home')
    server.rejectEverything()
    await phone.engine.sync()
    expect(phone.engine.status.rejected).toBe(true)
    expect(await phone.engine.sync()).toBe(false) // doesn't keep retrying

    phone.engine.discardPending()
    expect(phone.engine.status).toMatchObject({ rejected: false, pending: 0 })
    expect(await phone.api.listProjects()).toEqual([])
  })
})
