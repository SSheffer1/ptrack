import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import { applyPrefs } from './prefs.svelte'
import { describeOffset, dueMoment, normalizeReminders, upcomingReminders } from './reminders'
import type { Item } from './types'

function item(extra: Partial<Item>): Item {
  return {
    id: 'i1', key: 'SCHOOL-1', project_id: 'p', type: 'ticket', number: 1, title: 'Circuits exam', body: '',
    status: 'todo', priority: 'none', labels: [], due: null, due_time: null, repeat: null, next_id: null,
    assigned_on: null, assigned: '2026-10-20', completed_on: null, reminders: null, created_at: 0, updated_at: 0,
    created_by: 'me', assignee_id: null,
    ...extra,
  }
}

const NOW = new Date(2026, 9, 24, 12, 0) // Sat Oct 24 2026, noon
const remind = (items: Item[], now: Date) => upcomingReminders(items, now, 'me')

// Dates near today print as "Today"/"Tomorrow", so the clock is frozen at NOW;
// otherwise these tests fail on the days they mention.
beforeAll(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(NOW)
})
afterAll(() => vi.useRealTimers())

describe('reminders', () => {
  it('untimed tickets are due at 9:00', () => {
    expect(dueMoment(item({ due: '2026-10-28' }))).toEqual(new Date(2026, 9, 28, 9, 0))
    expect(dueMoment(item({ due: '2026-10-28', due_time: '14:30:00' }))).toEqual(new Date(2026, 9, 28, 14, 30))
  })

  it('default: at the due time (9 AM on the day without a time)', () => {
    const [timed] = remind([item({ due: '2026-10-28', due_time: '10:00:00' })], NOW)
    expect(timed.at).toEqual(new Date(2026, 9, 28, 10, 0))
    const [untimed] = remind([item({ due: '2026-10-28' })], NOW)
    expect(untimed.at).toEqual(new Date(2026, 9, 28, 9, 0))
    expect(untimed.body).toBe('Due Wed, Oct 28 · SCHOOL-1')
  })

  it('uses the ticket’s own reminders, or none', () => {
    const at = remind([item({ due: '2026-10-28', reminders: ['-2d', '-1d'] })], NOW).map((r) => r.at)
    expect(at).toEqual([new Date(2026, 9, 26, 9, 0), new Date(2026, 9, 27, 9, 0)])
    expect(remind([item({ due: '2026-10-28', reminders: [] })], NOW)).toEqual([])
  })

  it('skips done tickets, undated tickets and reminders in the past', () => {
    expect(remind([item({ due: '2026-10-28', status: 'done' })], NOW)).toEqual([])
    expect(remind([item({})], NOW)).toEqual([])
    expect(remind([item({ due: '2026-10-25', reminders: ['-2d', '0'] })], NOW).map((r) => r.at)).toEqual([
      new Date(2026, 9, 25, 9, 0),
    ])
  })

  it('gives each reminder a stable id', () => {
    const a = remind([item({ due: '2026-10-28', reminders: ['-1d', '0'] })], NOW)
    const b = remind([item({ due: '2026-10-28', reminders: ['-1d', '0'] })], NOW)
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

  it("only reminds me about tickets that are mine", () => {
    const due = { due: '2026-10-28' }
    expect(remind([item({ ...due, assignee_id: 'bob' })], NOW)).toEqual([])
    expect(remind([item({ ...due, created_by: 'bob', assignee_id: 'me' })], NOW)).toHaveLength(1)
    expect(remind([item({ ...due, created_by: 'bob' })], NOW)).toEqual([]) // bob's, unassigned
  })

  describe('with your preferences', () => {
    afterEach(() => applyPrefs({}))

    it('uses your untimed hour and default reminders', () => {
      applyPrefs({ untimed_hour: 7, reminders: ['-1d', '-1h'] }) // the same default for both kinds
      expect(remind([item({ due: '2026-10-28' })], NOW).map((r) => r.at)).toEqual([
        new Date(2026, 9, 27, 7, 0),
        new Date(2026, 9, 28, 6, 0),
      ])
      expect(remind([item({ due: '2026-10-28', due_time: '10:00:00' })], NOW).map((r) => r.at)).toEqual([
        new Date(2026, 9, 27, 10, 0),
        new Date(2026, 9, 28, 9, 0),
      ])
      expect(describeOffset('0', false)).toBe('7 AM on the day')
    })

    it("a ticket's own reminders still win", () => {
      applyPrefs({ reminders: [] })
      expect(remind([item({ due: '2026-10-28' })], NOW)).toEqual([])
      expect(remind([item({ due: '2026-10-28', reminders: ['0'] })], NOW)).toHaveLength(1)
    })
  })
})

describe('specific-time reminders', () => {
  it('fire at their time, with or without a due date', () => {
    const undated = remind([item({ reminders: ['@2026-10-27T19:30'] })], NOW)
    expect(undated.map((r) => [r.at, r.body])).toEqual([[new Date(2026, 9, 27, 19, 30), 'Reminder · SCHOOL-1']])
    const dated = remind([item({ due: '2026-10-28', reminders: ['-1d', '@2026-10-25T08:15'] })], NOW)
    expect(dated.map((r) => r.at)).toEqual([new Date(2026, 9, 25, 8, 15), new Date(2026, 9, 27, 9, 0)])
  })

  it('skips past times and offsets on undated tickets', () => {
    expect(remind([item({ reminders: ['@2026-10-01T10:00', '-1d'] })], NOW)).toEqual([])
  })

  it('normalize like the server and describe as a date', () => {
    expect(normalizeReminders(['@2026-10-27t19:30', '-8H', '@2026-10-26T09:00'])).toEqual(['-8h', '@2026-10-26T09:00', '@2026-10-27T19:30'])
    expect(describeOffset('@2026-10-27T19:30', true)).toMatch(/^Tue, Oct 27 · 7:30\s?PM$/)
  })
})
