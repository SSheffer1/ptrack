import { describe, expect, it } from 'vitest'
import { LocalBackend } from './backend'
import { LocalStore, type LogEntry } from './store'
import {
  type People,
  SignedOut,
  SyncEngine,
  SyncRejected,
  type SyncRequest,
  type SyncResponse,
  type Transport,
} from './sync'

const ME = { id: 'u1', username: 'alice', display_name: 'Alice', is_admin: true }

/** A tiny stand-in for the real server: one user, a numbered log, ticket numbers, and switches for
 * the awkward cases (offline, rejecting, refusing particular edits, a membership change). */
function fakeServer(pageSize = 1000) {
  const log: (LogEntry & { seq: number; user_id: string })[] = []
  const projects = new Set<string>()
  let nextNumber = 1
  let online = true
  let reject = false
  let epoch = 0
  let refuse = (_c: SyncRequest['changes'][number]) => false
  const transport: Transport = async (_url, token, req: SyncRequest): Promise<SyncResponse> => {
    if (!online) throw new Error("Can't reach the server")
    if (token !== 'good-token') throw new SignedOut('Signed out')
    if (reject) throw new SyncRejected('Server rejected changes')
    const dropped: SyncResponse['dropped'] = []
    for (const c of req.changes) {
      if (refuse(c)) {
        dropped.push({ entity: c.entity, entity_id: c.entity_id, field: c.field, ts: c.ts, reason: 'not allowed' })
        continue
      }
      const dup = log.some((l) => l.entity_id === c.entity_id && l.field === c.field && l.ts === c.ts && l.device_id === req.device_id)
      if (dup) continue
      log.push({ ...c, device_id: req.device_id, user_id: ME.id, seq: log.length + 1 })
      if (c.entity === 'project') projects.add(c.entity_id)
      if (c.entity === 'item' && c.field === 'type') {
        log.push({ entity: 'item', entity_id: c.entity_id, field: 'number', value: nextNumber++, ts: c.ts + 1, device_id: 'server', user_id: ME.id, seq: log.length + 1 })
      }
    }
    const reset = req.epoch !== epoch
    const since = reset ? 0 : req.since
    const changes = log.filter((l) => l.seq > since).slice(0, pageSize)
    return {
      changes,
      cursor: changes.at(-1)?.seq ?? since,
      more: changes.length === pageSize,
      dropped,
      reset,
      epoch,
      me: ME,
      users: [ME],
      members: [...projects].map((project_id) => ({ project_id, user_id: ME.id, role: 'owner' as const })),
    }
  }
  return {
    transport,
    log,
    goOffline: () => (online = false),
    goOnline: () => (online = true),
    rejectEverything: () => (reject = true),
    refuseWhen: (fn: typeof refuse) => (refuse = fn),
    changeMemberships: () => epoch++,
  }
}

function device(id: string, transport: Transport, token = 'good-token') {
  const store = new LocalStore()
  let people: People = { me: ME, users: [ME], members: [] }
  let signedOut = false
  const api = new LocalBackend(store, () => id, () => {}, () => people)
  const engine = new SyncEngine(
    store,
    { deviceId: id, serverUrl: '', token, cursor: 0, epoch: 0 },
    transport,
    () => {},
    undefined,
    (p) => (people = p),
    () => (signedOut = true),
  )
  return { store, api, engine, signedOut: () => signedOut }
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

  it('a membership change resets the download but keeps unsent edits', async () => {
    const server = fakeServer()
    const phone = device('phone', server.transport)
    await phone.api.createProject('HOME', 'Home')
    await phone.engine.sync()
    server.goOffline()
    const { id } = await phone.api.createItem({ project: 'HOME', title: 'Unsent' })
    server.goOnline()
    server.changeMemberships()
    await phone.engine.sync()
    expect(phone.engine.settings.epoch).toBe(1)
    expect((await phone.api.getItem(id)).title).toBe('Unsent') // kept, and now sent
    expect(phone.engine.status.pending).toBe(0)
    expect((await phone.api.listProjects()).map((p) => p.key)).toEqual(['HOME'])
  })

  it('discards edits the server refused, without blocking the rest', async () => {
    const server = fakeServer()
    const phone = device('phone', server.transport)
    await phone.api.createProject('HOME', 'Home')
    const { id } = await phone.api.createItem({ project: 'HOME', title: 'Original' })
    await phone.engine.sync()
    server.refuseWhen((c) => c.field === 'title')
    await phone.api.updateItem(id, { title: 'Refused', priority: 'high' })
    await phone.engine.sync()
    const item = await phone.api.getItem(id)
    expect([item.title, item.priority]).toEqual(['Original', 'high'])
    expect(phone.engine.status).toMatchObject({ pending: 0, rejected: false, error: '' })
  })

  it('reports being signed out', async () => {
    const server = fakeServer()
    const phone = device('phone', server.transport, 'revoked-token')
    await phone.engine.sync()
    expect(phone.signedOut()).toBe(true)
  })
})
