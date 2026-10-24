// End-to-end: two family members' phones against a real ptrack server.
// Skipped unless PTRACK_E2E_URL points at a server with an EMPTY database and an
// admin account given by PTRACK_E2E_ADMIN / PTRACK_E2E_PASSWORD. See server/README.md.

import { describe, expect, it } from 'vitest'
import { LocalBackend } from './backend'
import { LocalStore } from './store'
import { fetchTransport, type People, SyncEngine } from './sync'

// (Read via globalThis: the app's TypeScript setup doesn't include Node's types.)
const env = (globalThis as { process?: { env: Record<string, string | undefined> } }).process?.env ?? {}
const url = env.PTRACK_E2E_URL

async function rest<T>(path: string, token: string, method = 'GET', body?: unknown): Promise<T> {
  const res = await fetch(`${url}/api${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${method} ${path}: ${res.status} ${await res.text()}`)
  return (res.status === 204 ? undefined : res.json()) as T
}

async function login(username: string, password: string): Promise<string> {
  const res = await fetch(`${url}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password, device_name: 'e2e phone' }),
  })
  return (await res.json()).token
}

async function phone(username: string, password: string) {
  const token = await login(username, password)
  const store = new LocalStore()
  let people: People = { me: null, users: [], members: [] }
  const api = new LocalBackend(store, () => `android-e2e-${username}`, () => {}, () => people)
  const engine = new SyncEngine(
    store,
    { deviceId: `android-e2e-${username}`, serverUrl: url!, token, cursor: 0, epoch: -1 },
    fetchTransport,
    () => {},
    undefined,
    (p) => (people = p),
  )
  await engine.sync()
  return { api, engine, token, me: () => people.me! }
}

describe.skipIf(!url)('two phones ↔ real server', () => {
  it('share a project, assign, sync both ways, recurring copy, leaving', async () => {
    const admin = await login(env.PTRACK_E2E_ADMIN ?? 'admin', env.PTRACK_E2E_PASSWORD ?? '')
    const suffix = Date.now().toString(36)
    for (const name of ['alice', 'bob']) {
      await rest('/admin/users', admin, 'POST', { username: `${name}${suffix}`, display_name: name, password: 'e2e password' })
    }
    const alice = await phone(`alice${suffix}`, 'e2e password')
    const bob = await phone(`bob${suffix}`, 'e2e password')

    // Alice, offline-style: a project and a weekly ticket, then sync.
    const key = `E${suffix.slice(-5).toUpperCase().replace(/[^A-Z0-9]/g, 'X')}`
    await alice.api.createProject(key, 'Chores')
    const { id } = await alice.api.createItem({ project: key, title: 'Trash out', due: '2026-11-06', repeat: 'FREQ=WEEKLY' })
    await alice.engine.sync()
    expect((await alice.api.getItem(id)).key).toBe(`${key}-1`)

    // Bob sees nothing until it's shared; then his next sync resets and brings it all.
    expect(await bob.api.listProjects()).toEqual([])
    await rest(`/projects/${key}/members`, alice.token, 'POST', { username: `bob${suffix}` })
    await bob.engine.sync()
    expect((await bob.api.listProjects()).map((p) => [p.key, p.role])).toEqual([[key, 'editor']])
    expect((await bob.api.getItem(`${key}-1`)).title).toBe('Trash out')

    // Alice assigns it to Bob; Bob finishes it on his phone; the server makes next week's copy, still Bob's.
    await alice.engine.sync()
    await alice.api.updateItem(id, { assignee_id: bob.me().id })
    await alice.engine.sync()
    await bob.engine.sync()
    await bob.api.updateItem(id, { status: 'done' })
    await expect(bob.api.deleteItem(id)).rejects.toMatchObject({ status: 403 }) // editors can't delete
    await bob.engine.sync()
    await alice.engine.sync()
    const done = await alice.api.getItem(id)
    expect([done.status, done.assignee_id]).toEqual(['done', bob.me().id])
    const next = await alice.api.getItem(done.next_id!)
    expect([next.key, next.due, next.assignee_id, next.created_by]).toEqual([`${key}-2`, '2026-11-13', bob.me().id, alice.me().id])

    // Bob leaves: his phone forgets the project; the copy becomes unassigned.
    await rest(`/projects/${key}/members/${bob.me().id}`, bob.token, 'DELETE')
    await bob.engine.sync()
    expect(await bob.api.listProjects()).toEqual([])
    expect(await bob.api.listItems()).toEqual([])
    await alice.engine.sync()
    expect((await alice.api.getItem(done.next_id!)).assignee_id).toBeNull()
  })
})
