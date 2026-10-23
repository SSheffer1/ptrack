// Repeat rules use the iCalendar RRULE format (see server/src/ptrack/recurrence.py).
// The presets don't name a weekday or day of month: the ticket's due date
// supplies those, so "Every week" means "every week on the day it's due".

export const REPEAT_PRESETS: { label: string; rule: string }[] = [
  { label: 'Every day', rule: 'FREQ=DAILY' },
  { label: 'Every weekday (Mon–Fri)', rule: 'FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR' },
  { label: 'Every week', rule: 'FREQ=WEEKLY' },
  { label: 'Every 2 weeks', rule: 'FREQ=WEEKLY;INTERVAL=2' },
  { label: 'Every month', rule: 'FREQ=MONTHLY' },
  { label: 'Every year', rule: 'FREQ=YEARLY' },
]

const UNITS: Record<string, string> = { DAILY: 'day', WEEKLY: 'week', MONTHLY: 'month', YEARLY: 'year' }
const DAYS: Record<string, string> = { MO: 'Mon', TU: 'Tue', WE: 'Wed', TH: 'Thu', FR: 'Fri', SA: 'Sat', SU: 'Sun' }
const KNOWN_PARTS = new Set(['FREQ', 'INTERVAL', 'BYDAY', 'BYMONTHDAY', 'UNTIL'])

function ordinal(n: number): string {
  const suffix = n % 100 >= 11 && n % 100 <= 13 ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' } as Record<number, string>)[n % 10] ?? 'th'
  return `${n}${suffix}`
}

/** "FREQ=WEEKLY;INTERVAL=2;BYDAY=TU,TH" → "Every 2 weeks on Tue, Thu". Unusual rules are shown as-is. */
export function describeRule(rule: string): string {
  const preset = REPEAT_PRESETS.find((p) => p.rule === rule)
  if (preset) return preset.label

  const parts = Object.fromEntries(rule.split(';').map((p) => p.split('=') as [string, string]))
  const unit = UNITS[parts.FREQ]
  if (!unit || Object.keys(parts).some((k) => !KNOWN_PARTS.has(k))) return rule

  const interval = Number(parts.INTERVAL ?? 1)
  let text = interval > 1 ? `Every ${interval} ${unit}s` : `Every ${unit}`
  if (parts.BYDAY) text += ` on ${parts.BYDAY.split(',').map((d) => DAYS[d] ?? d).join(', ')}`
  if (parts.BYMONTHDAY) text += ` on the ${parts.BYMONTHDAY.split(',').map((d) => ordinal(Number(d))).join(', ')}`
  if (parts.UNTIL) {
    const u = parts.UNTIL
    const until = new Date(Number(u.slice(0, 4)), Number(u.slice(4, 6)) - 1, Number(u.slice(6, 8)))
    text += ` until ${until.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}`
  }
  return text
}
