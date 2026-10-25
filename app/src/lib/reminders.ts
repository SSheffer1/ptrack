// Reminders (see server/src/ptrack/reminders.py) are of two kinds:
// - offsets "0", "-30m", "-8h", "-2d", counted from the due moment = due date at
//   its due time, or at your "untimed hour" (9:00 unless changed) without one;
// - specific times "@2026-10-27T19:30" (local time), which need no due date.
// `reminders: null` means your default reminders; [] means none.

import { formatDueWithTime, formatTime } from './format'
import { prefs } from './prefs.svelte'
import { type Item, notifiedUser } from './types'
const OFFSET_RE = /^(0|-\d{1,4}[mhd])$/
const AT_RE = /^@(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/
const UNIT_MINUTES = { m: 1, h: 60, d: 1440 } as const

export function defaultReminders(timed: boolean): string[] {
  return timed ? prefs.reminders_timed : prefs.reminders_untimed
}

const untimedTime = () => `${String(prefs.untimed_hour).padStart(2, '0')}:00`

/** The reminders that actually apply to an item (its own, or the default). */
export function effectiveReminders(item: Pick<Item, 'reminders' | 'due_time'>): string[] {
  return item.reminders ?? defaultReminders(!!item.due_time)
}

export function isValidOffset(offset: string): boolean {
  return OFFSET_RE.test(offset)
}

export const isSpecificTime = (r: string) => r.startsWith('@')

/** The moment of a specific-time reminder, or null if it isn't a real date and time. */
export function specificMoment(r: string): Date | null {
  const m = AT_RE.exec(r)
  if (!m) return null
  const [y, mo, d, hh, mm] = m.slice(1).map(Number)
  const at = new Date(y, mo - 1, d, hh, mm)
  return at.getMonth() === mo - 1 && at.getDate() === d && hh < 24 && mm < 60 ? at : null
}

/** "2026-10-27T19:30" (what a datetime-local input gives) → "@2026-10-27T19:30". */
export function specificTime(local: string): string {
  return `@${local.slice(0, 16)}`
}

export function isValidReminder(r: string): boolean {
  return isSpecificTime(r) ? specificMoment(r) !== null : isValidOffset(r)
}

export function offsetMinutes(offset: string): number {
  if (offset === '0') return 0
  return Number(offset.slice(0, -1)) * UNIT_MINUTES[offset.at(-1) as keyof typeof UNIT_MINUTES]
}

/** Cleaned up and sorted like the server stores them: offsets earliest first, then specific times. */
export function normalizeReminders(list: string[] | null | undefined): string[] | null {
  if (list == null) return null
  const cleaned = [...new Set(list.map((r) => (r.trim().startsWith('@') ? r.trim().toUpperCase() : r.trim().toLowerCase())))]
  const offsets = cleaned.filter((r) => !isSpecificTime(r)).sort((a, b) => offsetMinutes(a) - offsetMinutes(b))
  return [...offsets, ...cleaned.filter(isSpecificTime).sort()]
}

export function dueMoment(item: Pick<Item, 'due' | 'due_time'>): Date | null {
  if (!item.due) return null
  const [y, m, d] = item.due.split('-').map(Number)
  const [hh, mm] = (item.due_time ?? untimedTime()).split(':').map(Number)
  return new Date(y, m - 1, d, hh, mm)
}

/** "8 hours before", "1 day before", "At due time" (or "9 AM on the day" for untimed tickets). */
export function describeOffset(offset: string, timed: boolean): string {
  if (isSpecificTime(offset)) return describeSpecific(offset)
  const minutes = -offsetMinutes(offset)
  const at = formatTime(untimedTime()).replace(':00', '')
  if (minutes === 0) return timed ? 'At due time' : `${at} on the day`
  if (!timed && minutes % 1440 === 0) {
    const days = minutes / 1440
    return days === 1 ? `${at} the day before` : `${at}, ${days} days before`
  }
  const [n, unit] = minutes % 1440 === 0 ? [minutes / 1440, 'day'] : minutes % 60 === 0 ? [minutes / 60, 'hour'] : [minutes, 'minute']
  return `${n} ${unit}${n === 1 ? '' : 's'} before`
}

/** "Tue, Oct 27 · 7:30 PM" */
export function describeSpecific(r: string): string {
  return formatDueWithTime(r.slice(1, 11), r.slice(12))
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
    if (item.status === 'done' || notifiedUser(item, me) !== me) continue
    const due = dueMoment(item)
    const body = (due ? `Due ${formatDueWithTime(item.due!, item.due_time)}` : 'Reminder') + (item.key ? ` · ${item.key}` : '')
    for (const r of effectiveReminders(item)) {
      // Offsets need a due date; specific times don't.
      const at = isSpecificTime(r) ? specificMoment(r) : due && new Date(due.getTime() + offsetMinutes(r) * 60_000)
      if (!at || at <= now) continue
      result.push({ id: hash(`${item.id} ${r}`), at, itemId: item.id, title: item.title, body })
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
