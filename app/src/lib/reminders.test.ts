import { describe, expect, it } from 'vitest'
import { describeOffset, dueMoment, normalizeReminders, upcomingReminders } from './reminders'
import type { Item } from './types'

function item(extra: Partial<Item>): Item {
  return {
    id: 'i1', key: 'SCHOOL-1', project_id: 'p', type: 'ticket', number: 1, title: 'Circuits exam', body: '',
    status: 'todo', priority: 'none', labels: [], due: null, due_time: null, repeat: null, next_id: null,
    assigned_on: null, assigned: '2026-10-20', completed_on: null, reminders: null, created_at: 0, updated_at: 0,
    ...extra,
  }
}

const NOW = new Date(2026, 9, 24, 12, 0) // Sat Oct 24 2026, noon

describe('reminders', () => {
  it('untimed tickets are due at 9:00', () => {
    expect(dueMoment(item({ due: '2026-10-28' }))).toEqual(new Date(2026, 9, 28, 9, 0))
    expect(dueMoment(item({ due: '2026-10-28', due_time: '14:30:00' }))).toEqual(new Date(2026, 9, 28, 14, 30))
  })

  it('defaults: 8 hours before a timed ticket, 9 AM on the day otherwise', () => {
    const [timed] = upcomingReminders([item({ due: '2026-10-28', due_time: '10:00:00' })], NOW)
    expect(timed.at).toEqual(new Date(2026, 9, 28, 2, 0))
    const [untimed] = upcomingReminders([item({ due: '2026-10-28' })], NOW)
    expect(untimed.at).toEqual(new Date(2026, 9, 28, 9, 0))
    expect(untimed.body).toBe('Due Wed, Oct 28 · SCHOOL-1')
  })

  it('uses the ticket’s own reminders, or none', () => {
    const at = upcomingReminders([item({ due: '2026-10-28', reminders: ['-2d', '-1d'] })], NOW).map((r) => r.at)
    expect(at).toEqual([new Date(2026, 9, 26, 9, 0), new Date(2026, 9, 27, 9, 0)])
    expect(upcomingReminders([item({ due: '2026-10-28', reminders: [] })], NOW)).toEqual([])
  })

  it('skips done tickets, undated tickets and reminders in the past', () => {
    expect(upcomingReminders([item({ due: '2026-10-28', status: 'done' })], NOW)).toEqual([])
    expect(upcomingReminders([item({})], NOW)).toEqual([])
    expect(upcomingReminders([item({ due: '2026-10-25', reminders: ['-2d', '0'] })], NOW).map((r) => r.at)).toEqual([
      new Date(2026, 9, 25, 9, 0),
    ])
  })

  it('gives each reminder a stable id', () => {
    const a = upcomingReminders([item({ due: '2026-10-28', reminders: ['-1d', '0'] })], NOW)
    const b = upcomingReminders([item({ due: '2026-10-28', reminders: ['-1d', '0'] })], NOW)
    expect(a.map((r) => r.id)).toEqual(b.map((r) => r.id))
    expect(new Set(a.map((r) => r.id)).size).toBe(2)
    expect(a.every((r) => Number.isInteger(r.id) && r.id > 0 && r.id < 2 ** 31)).toBe(true)
  })

  it('describes offsets in words', () => {
    expect(describeOffset('-8h', true)).toBe('8 hours before')
    expect(describeOffset('-1d', true)).toBe('1 day before')
    expect(describeOffset('0', true)).toBe('At due time')
    expect(describeOffset('0', false)).toBe('9 AM on the day')
    expect(describeOffset('-1d', false)).toBe('9 AM the day before')
    expect(describeOffset('-30m', true)).toBe('30 minutes before')
  })

  it('normalizes like the server', () => {
    expect(normalizeReminders([' -8H', '0', '-1d', '-8h'])).toEqual(['-1d', '-8h', '0'])
    expect(normalizeReminders(null)).toBeNull()
  })
})
