import { describe, expect, it } from 'vitest'
import { LocalStore, type LogEntry } from './store'

const e = (field: string, value: unknown, ts: number, device = 'a', extra: Partial<LogEntry> = {}): LogEntry => ({
  entity: 'item',
  entity_id: 'i1',
  field,
  value,
  ts,
  device_id: device,
  ...extra,
})

describe('LocalStore', () => {
  it('latest edit wins regardless of arrival order', () => {
    const entries = [e('title', 'first', 1), e('title', 'third', 3), e('title', 'second', 2)]
    for (const order of [entries, [...entries].reverse()]) {
      const store = new LocalStore(order)
      expect(store.rows.item.get('i1')!.title).toBe('third')
    }
  })

  it('breaks exact timestamp ties by device id, like the server', () => {
    const store = new LocalStore([e('title', 'from b', 5, 'b'), e('title', 'from a', 5, 'a')])
    expect(store.rows.item.get('i1')!.title).toBe('from b')
  })

  it('edits to different fields both apply', () => {
    const store = new LocalStore([e('title', 'x', 1), e('status', 'done', 2, 'b'), e('priority', 'high', 3)])
    const row = store.rows.item.get('i1')!
    expect([row.title, row.status, row.priority]).toEqual(['x', 'done', 'high'])
  })

  it('new rows get the server defaults', () => {
    const row = new LocalStore([e('title', 'x', 1)]).rows.item.get('i1')!
    expect(row).toMatchObject({ status: 'todo', priority: 'none', labels: [], number: null, deleted: false })
  })

  it('ignores duplicates but records the server confirming our entry', () => {
    const store = new LocalStore([e('title', 'x', 1, 'phone')])
    expect(store.pending('phone')).toHaveLength(1)
    expect(store.apply(e('title', 'x', 1, 'phone', { seq: 7 }))).toBe(false)
    expect(store.pending('phone')).toHaveLength(0)
    expect(store.historyOf('i1')).toHaveLength(1)
  })

  it('new timestamps always move forward, even past a fast clock elsewhere', () => {
    const future = Date.now() + 60_000
    const store = new LocalStore([e('title', 'from a fast phone', future, 'b')])
    expect(store.nextTs()).toBeGreaterThan(future)
    expect(store.nextTs()).toBeGreaterThan(future + 1)
  })

  it('discarding pending edits rolls back to what the server has', () => {
    const store = new LocalStore([e('title', 'server', 1, 'web', { seq: 1 }), e('title', 'mine', 2, 'phone')])
    expect(store.rows.item.get('i1')!.title).toBe('mine')
    store.discardPending('phone')
    expect(store.rows.item.get('i1')!.title).toBe('server')
    expect(store.pending('phone')).toEqual([])
  })
})
