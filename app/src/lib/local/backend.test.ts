import { beforeEach, describe, expect, it } from 'vitest'
import { toISODate } from '../format'
import { ApiError } from '../types'
import { LocalBackend } from './backend'
import { LocalStore } from './store'
import type { People } from './sync'

let store: LocalStore
let api: LocalBackend
let writes: number
let people: People

const ALICE = { id: 'alice', username: 'alice', display_name: 'Alice', is_admin: false }
const BOB = { id: 'bob', username: 'bob', display_name: 'Bob', is_admin: false }

beforeEach(async () => {
  store = new LocalStore()
  writes = 0
  people = { me: ALICE, users: [ALICE, BOB], members: [] }
  api = new LocalBackend(store, () => 'phone', () => writes++, () => people)
  await api.createProject('HOME', 'Home')
})

/** Pretend the server synced HOME, with these members. */
function syncedMembers(roles: Record<string, 'owner' | 'editor'>) {
  const home = [...store.rows.project.values()][0]
  store.apply({ entity: 'project', entity_id: home.id, field: 'created_by', value: 'alice', ts: Date.now() + 1, device_id: 'server', seq: 99 })
  people.members = Object.entries(roles).map(([user_id, role]) => ({ project_id: home.id, user_id, role }))
}

const today = toISODate(new Date())

describe('LocalBackend', () => {
  it('creates tickets offline; the key waits for the server number', async () => {
    const item = await api.createItem({ project: 'HOME', title: 'Fix bike' })
    expect(item).toMatchObject({ key: null, number: null, status: 'todo', assigned: today })
    expect(writes).toBe(2)
    expect(store.pending('phone').length).toBeGreaterThan(0)

    // The server's number arrives with the next sync.
    store.apply({ entity: 'item', entity_id: item.id, field: 'number', value: 1, ts: Date.now() + 5, device_id: 'server', seq: 1 })
    expect((await api.getItem('HOME-1')).id).toBe(item.id)
  })

  it('rejects what the server would reject', async () => {
    await expect(api.createProject('HOME', 'Again')).rejects.toMatchObject({ status: 409 })
    await expect(api.createProject('home', 'Lower')).rejects.toBeInstanceOf(ApiError)
    await expect(api.createItem({ project: 'NOPE', title: 'x' })).rejects.toMatchObject({ status: 404 })
    await expect(api.createItem({ project: 'HOME', title: '  ' })).rejects.toMatchObject({ status: 422 })
    await expect(api.createItem({ project: 'HOME', title: 'x', repeat: 'FREQ=WEEKLY;COUNT=3' })).rejects.toMatchObject({ status: 400 })
    await expect(api.createItem({ project: 'HOME', title: 'x', repeat: 'whenever' })).rejects.toMatchObject({ status: 400 })
  })

  it('fills in and clears the completion date with the status', async () => {
    const { id } = await api.createItem({ project: 'HOME', title: 'x' })
    expect((await api.updateItem(id, { status: 'done' })).completed_on).toBe(today)
    expect((await api.updateItem(id, { status: 'todo' })).completed_on).toBeNull()
    expect((await api.updateItem(id, { status: 'done', completed_on: '2026-10-01' })).completed_on).toBe('2026-10-01')
  })

  it('accepts specific-time reminders, real dates only', async () => {
    const item = await api.createItem({ project: 'HOME', title: 'x', reminders: ['@2026-10-27t19:30', '-1d'] })
    expect(item.reminders).toEqual(['-1d', '@2026-10-27T19:30'])
    await expect(api.createItem({ project: 'HOME', title: 'x', reminders: ['@2026-02-30T10:00'] })).rejects.toMatchObject({ status: 400 })
  })

  it('normalizes due time and repeat like the server', async () => {
    const item = await api.createItem({ project: 'HOME', title: 'x', due: '2026-11-06', due_time: '23:59', repeat: 'rrule:freq=weekly' })
    expect(item.due_time).toBe('23:59:00')
    expect(item.repeat).toBe('FREQ=WEEKLY')
  })

  it('filters and sorts like the server', async () => {
    await api.createItem({ project: 'HOME', title: 'No date' })
    await api.createItem({ project: 'HOME', title: 'Later', due: '2026-11-02', labels: ['x'] })
    await api.createItem({ project: 'HOME', title: 'Sooner', due: '2026-11-01' })
    const titles = async (f = {}) => (await api.listItems(f)).map((i) => i.title)

    expect(await titles({ sort: 'due' })).toEqual(['Sooner', 'Later', 'No date'])
    expect(await titles({ label: 'x' })).toEqual(['Later'])
    expect(await titles({ q: 'SOON' })).toEqual(['Sooner'])
    expect(await titles({ due_from: '2026-11-02' })).toEqual(['Later'])
    await expect(api.listItems({ project: 'NOPE' })).rejects.toMatchObject({ status: 404 })
  })

  it('soft-deletes and keeps history and comments', async () => {
    const { id } = await api.createItem({ project: 'HOME', title: 'x' })
    await api.updateItem(id, { status: 'in_progress' })
    await api.addComment(id, 'note')
    expect((await api.getHistory(id)).filter((c) => c.field === 'status').map((c) => c.value)).toEqual(['todo', 'in_progress'])
    expect((await api.listComments(id)).map((c) => c.body)).toEqual(['note'])
    await api.deleteItem(id)
    await expect(api.getItem(id)).rejects.toMatchObject({ status: 404 })
    expect(await api.listItems()).toEqual([])
  })

  it('a project made here is mine until the server says otherwise', async () => {
    expect((await api.listProjects()).map((p) => p.role)).toEqual(['owner'])
    expect((await api.listMembers('HOME')).map((m) => m.username)).toEqual(['alice'])
    syncedMembers({ alice: 'editor', bob: 'owner' })
    expect((await api.listProjects()).map((p) => p.role)).toEqual(['editor'])
    expect((await api.listMembers('HOME')).map((m) => [m.display_name, m.role])).toEqual([
      ['Alice', 'editor'],
      ['Bob', 'owner'],
    ])
  })

  it('editors can edit but not delete tickets or rename the project', async () => {
    const { id } = await api.createItem({ project: 'HOME', title: 'x' })
    syncedMembers({ alice: 'editor', bob: 'owner' })
    await expect(api.updateItem(id, { status: 'done' })).resolves.toMatchObject({ status: 'done' })
    await expect(api.deleteItem(id)).rejects.toMatchObject({ status: 403 })
    await expect(api.updateProject('HOME', { name: 'Mine now' })).rejects.toMatchObject({ status: 403 })
    await expect(api.deleteProject('HOME')).rejects.toMatchObject({ status: 403 })
  })

  it('assignees must be members, and only they set reminders', async () => {
    const { id } = await api.createItem({ project: 'HOME', title: 'Mow lawn', due: '2026-11-01' })
    await expect(api.updateItem(id, { assignee_id: 'bob' })).rejects.toMatchObject({ status: 403 })
    syncedMembers({ alice: 'owner', bob: 'editor' })
    await api.updateItem(id, { assignee_id: 'bob' })
    await expect(api.updateItem(id, { reminders: [] })).rejects.toMatchObject({ status: 403 })
    expect((await api.listItems({ assignee: 'me' })).length).toBe(0)
    await api.updateItem(id, { assignee_id: null })
    expect((await api.listItems({ assignee: 'me' })).map((i) => i.title)).toEqual(['Mow lawn'])
  })

  it('hides projects I\u2019m not a member of', async () => {
    syncedMembers({ bob: 'owner' })
    expect(await api.listProjects()).toEqual([])
    expect(await api.listItems()).toEqual([])
  })

  it('keeps my preferences as a synced record', async () => {
    expect(await api.getPrefs()).toEqual({})
    expect(await api.updatePrefs({ week_start: 'monday', reminders_timed: ['-8H', '-1d'] })).toEqual({
      week_start: 'monday',
      reminders_timed: ['-1d', '-8h'],
    })
    expect(store.pending('phone').filter((e) => e.entity === 'prefs').map((e) => e.entity_id)).toEqual(['alice', 'alice'])
    expect(await api.updatePrefs({ week_start: null })).toEqual({ reminders_timed: ['-1d', '-8h'] })
    await expect(api.updatePrefs({ colour: 'blue' })).rejects.toMatchObject({ status: 400 })
    await expect(api.updatePrefs({ reminders_timed: ['@2026-10-27T19:30'] })).rejects.toMatchObject({ status: 400 })
  })

  it('comments: the author edits and deletes; the owner deletes others\u2019', async () => {
    const { id } = await api.createItem({ project: 'HOME', title: 'Fix sink' })
    const mine = await api.addComment(id, 'on it')
    expect(mine.edited).toBe(false)
    const edited = await api.editComment(id, mine.id, 'on it, tomorrow')
    expect([edited.body, edited.edited]).toEqual(['on it, tomorrow', true])
    await expect(api.editComment(id, mine.id, '  ')).rejects.toMatchObject({ status: 422 })

    // Bob's comment arrives by sync; I'm an editor here, not the owner.
    syncedMembers({ alice: 'editor', bob: 'owner' })
    for (const [field, value] of [['item_id', id], ['body', 'from bob'], ['created_by', 'bob']] as const) {
      store.apply({ entity: 'comment', entity_id: 'c-bob', field, value, ts: Date.now() + 10, device_id: 'server', seq: 200 })
    }
    await expect(api.editComment(id, 'c-bob', 'mine now')).rejects.toMatchObject({ status: 403 })
    await expect(api.deleteComment(id, 'c-bob')).rejects.toMatchObject({ status: 403 })
    await api.deleteComment(id, mine.id)
    expect((await api.listComments(id)).map((c) => c.body)).toEqual(['from bob'])

    // As the owner I may delete Bob's comment (but still not edit it).
    syncedMembers({ alice: 'owner', bob: 'editor' })
    await expect(api.editComment(id, 'c-bob', 'mine now')).rejects.toMatchObject({ status: 403 })
    await api.deleteComment(id, 'c-bob')
    expect(await api.listComments(id)).toEqual([])
  })
})

