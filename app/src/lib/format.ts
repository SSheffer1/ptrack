import type { Status } from './api'

const DAY_MS = 24 * 60 * 60 * 1000

// "YYYY-MM-DD" → local midnight. (new Date("2026-10-28") would be UTC midnight,
// which is the previous evening in US time zones.)
export function parseDate(d: string): Date {
  const [y, m, day] = d.split('-').map(Number)
  return new Date(y, m - 1, day)
}

function daysFromToday(d: string): number {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return Math.round((parseDate(d).getTime() - today.getTime()) / DAY_MS)
}

export function formatDue(d: string): string {
  const days = daysFromToday(d)
  if (days === 0) return 'Today'
  if (days === 1) return 'Tomorrow'
  if (days === -1) return 'Yesterday'
  const date = parseDate(d)
  const sameYear = date.getFullYear() === new Date().getFullYear()
  return date.toLocaleDateString(undefined, {
    weekday: days > 0 && days < 7 ? 'short' : undefined,
    month: 'short',
    day: 'numeric',
    year: sameYear ? undefined : 'numeric',
  })
}

export function dueTone(d: string, status: Status): 'overdue' | 'soon' | '' {
  if (status === 'done') return ''
  const days = daysFromToday(d)
  if (days < 0) return 'overdue'
  if (days <= 2) return 'soon'
  return ''
}

export function ago(ms: number): string {
  const s = Math.round((Date.now() - ms) / 1000)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  if (s < 7 * 86400) return `${Math.floor(s / 86400)} d ago`
  return new Date(ms).toLocaleDateString()
}

export function exactTime(ms: number): string {
  return new Date(ms).toLocaleString()
}

export function parseLabels(text: string): string[] {
  return [...new Set(text.split(',').map((l) => l.trim()).filter(Boolean))]
}

// Date → "YYYY-MM-DD" in local time (toISOString would convert to UTC first).
export function toISODate(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export function addDays(d: Date, days: number): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate() + days)
}

// "14:30:00" → "2:30 PM" (or "14:30", depending on the browser's locale).
export function formatTime(t: string): string {
  const [h, m] = t.split(':').map(Number)
  return new Date(2000, 0, 1, h, m).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

export function formatDueWithTime(due: string, time: string | null): string {
  return time ? `${formatDue(due)} · ${formatTime(time)}` : formatDue(due)
}

// Whole days from a to b ("YYYY-MM-DD" strings).
export function daysBetween(a: string, b: string): number {
  return Math.round((parseDate(b).getTime() - parseDate(a).getTime()) / DAY_MS)
}

// "2 days early" / "on the due date" / "1 day late".
export function timing(due: string, completed: string): string {
  const n = daysBetween(completed, due)
  if (n === 0) return 'on the due date'
  const days = Math.abs(n) === 1 ? '1 day' : `${Math.abs(n)} days`
  return n > 0 ? `${days} early` : `${days} late`
}
