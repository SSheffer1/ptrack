// End-to-end: the phone's data layer against a real ptrack server.
// Skipped unless PTRACK_E2E_URL points at a server with an EMPTY database, e.g.
//   (cd server && PTRACK_DB=sqlite:////tmp/e2e.db uv run uvicorn ptrack.main:app --port 8765)
//   PTRACK_E2E_URL=http://localhost:8765 npx vitest run sync.e2e

import { describe, expect, it } from 'vitest'
import { LocalBackend } from './backend'
import { LocalStore } from './store'
import { fetchTransport, SyncEngine } from './sync'

// (Read via globalThis: the app's TypeScript setup doesn't include Node's types.)
const url = (globalThis as { process?: { env: Record<string, string | undefined> } }).process?.env.PTRACK_E2E_URL

function device(id: string) {
  const store = new LocalStore()
  const api = new LocalBackend(store, () => id, () => {})
  const engine = new SyncEngine(store, { deviceId: id, serverUrl: url!, cursor: 0 }, fetchTransport, () => {})
  return { api, engine }
}

const rest = (path: string, init?: RequestInit) =>
  fetch(`${url}/api${path}`, { headers: { 'Content-Type': 'application/json' }, ...init }).then((r) => r.json())

describe.skipIf(!url)('phone ↔ real server', () => {
  it('offline-created ticket syncs, gets a number, and web edits flow back', async () => {
    const phone = device(`android-e2e-${Date.now()}`)
    await phone.api.createProject('E2E', 'End to end')
    const { id } = await phone.api.createItem({
      project: 'E2E',
      title: 'Lab report',
      due: '2026-11-06',
      due_time: '23:59',
      repeat: 'FREQ=WEEKLY',
      labels: ['lab'],
    })
    await phone.engine.sync()
    expect(phone.engine.status.error).toBe('')
    expect((await phone.api.getItem(id)).key).toBe('E2E-1')

    // The web sees it, and marks it done; the server creates next week's copy.
    expect((await rest('/items/E2E-1')).title).toBe('Lab report')
    const done = await rest('/items/E2E-1', { method: 'PATCH', body: JSON.stringify({ status: 'done' }) })
    expect(done.next_id).toBeTruthy()

    await phone.engine.sync()
    const mine = await phone.api.getItem(id)
    expect([mine.status, mine.completed_on, mine.next_id]).toEqual(['done', done.completed_on, done.next_id])
    const next = await phone.api.getItem(done.next_id)
    expect([next.key, next.due, next.due_time, next.status]).toEqual(['E2E-2', '2026-11-13', '23:59:00', 'todo'])

    // A second phone starting from nothing gets the same picture.
    const other = device(`android-e2e-2-${Date.now()}`)
    await other.engine.sync()
    expect((await other.api.listItems({ project: 'E2E' })).map((i) => [i.key, i.status])).toEqual([
      ['E2E-1', 'done'],
      ['E2E-2', 'todo'],
    ])
  })
})
