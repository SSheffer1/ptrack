// Reminder offsets (see server/src/ptrack/reminders.py): "0", "-30m", "-8h", "-2d",
// counted from the due moment = due date at its due time, or 9:00 without one.
// `reminders: null` means the default; [] means none.

import { formatDueWithTime } from './format'
import { type Item, notifiedUser } from './types'

export const UNTIMED_HOUR = 9
const OFFSET_RE = /^(0|-\d{1,4}[mhd])$/
const UNIT_MINUTES = { m: 1, h: 60, d: 1440 } as const

export function defaultReminders(timed: boolean): string[] {
  return timed ? ['-8h'] : ['0']
}

/** The reminders that actually apply to an item (its own, or the default). */
export function effectiveReminders(item: Pick<Item, 'reminders' | 'due_time'>): string[] {
  return item.reminders ?? defaultReminders(!!item.due_time)
}

export function isValidOffset(offset: string): boolean {
  return OFFSET_RE.test(offset)
}

export function offsetMinutes(offset: string): number {
  if (offset === '0') return 0
  return Number(offset.slice(0, -1)) * UNIT_MINUTES[offset.at(-1) as keyof typeof UNIT_MINUTES]
}

/** Cleaned up and sorted earliest first, like the server stores them. */
export function normalizeReminders(list: string[] | null | undefined): string[] | null {
  if (list == null) return null
  return [...new Set(list.map((r) => r.trim().toLowerCase()))].sort((a, b) => offsetMinutes(a) - offsetMinutes(b))
}

export function dueMoment(item: Pick<Item, 'due' | 'due_time'>): Date | null {
  if (!item.due) return null
  const [y, m, d] = item.due.split('-').map(Number)
  const [hh, mm] = (item.due_time ?? `${UNTIMED_HOUR}:00`).split(':').map(Number)
  return new Date(y, m - 1, d, hh, mm)
}

/** "8 hours before", "1 day before", "At due time" (or "9 AM on the day" for untimed tickets). */
export function describeOffset(offset: string, timed: boolean): string {
  const minutes = -offsetMinutes(offset)
  if (minutes === 0) return timed ? 'At due time' : `${UNTIMED_HOUR} AM on the day`
  if (!timed && minutes % 1440 === 0) {
    const days = minutes / 1440
    return days === 1 ? `${UNTIMED_HOUR} AM the day before` : `${UNTIMED_HOUR} AM, ${days} days before`
  }
  const [n, unit] = minutes % 1440 === 0 ? [minutes / 1440, 'day'] : minutes % 60 === 0 ? [minutes / 60, 'hour'] : [minutes, 'minute']
  return `${n} ${unit}${n === 1 ? '' : 's'} before`
}

/** Offsets offered as one-tap choices. */
export function reminderChoices(timed: boolean): string[] {
  return timed ? ['0', '-1h', '-8h', '-1d', '-2d', '-7d'] : ['0', '-1d', '-2d', '-7d']
}

export interface ScheduledReminder {
  id: number // Android notification ids are 32-bit integers
  at: Date
  itemId: string
  title: string
  body: string
}

/** Every reminder still to come for my open tickets, soonest first. Mine = assigned to me,
 * or unassigned and created by me (see notifiedUser). */
export function upcomingReminders(items: Item[], now: Date, me: string, limit = 50): ScheduledReminder[] {
  const result: ScheduledReminder[] = []
  for (const item of items) {
    const due = dueMoment(item)
    if (!due || item.status === 'done' || notifiedUser(item, me) !== me) continue
    for (const offset of effectiveReminders(item)) {
      const at = new Date(due.getTime() + offsetMinutes(offset) * 60_000)
      if (at <= now) continue
      result.push({
        id: hash(`${item.id} ${offset}`),
        at,
        itemId: item.id,
        title: item.title,
        body: `Due ${formatDueWithTime(item.due!, item.due_time)}${item.key ? ` · ${item.key}` : ''}`,
      })
    }
  }
  return result.sort((a, b) => a.at.getTime() - b.at.getTime()).slice(0, limit)
}

// Stable positive 31-bit id from a string (FNV-1a).
function hash(s: string): number {
  let h = 0x811c9dc5
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 0x01000193)
  return (h >>> 1) || 1
}
