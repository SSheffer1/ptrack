// Your preferences: set in Settings, synced to all your devices (see
// server/src/ptrack/prefs.py, which checks and stores them). Anything you
// haven't set uses the default below. Code that depends on a preference reads
// it from `prefs`, so changing one takes effect everywhere at once.

import type { SortOrder, Status } from './types'

export interface Prefs {
  reminders_timed: string[] // default reminders for tickets with a due time
  reminders_untimed: string[] // …and without one
  untimed_hour: number // 0–23: when an untimed ticket counts as due (reminders count from it)
  week_start: 'sunday' | 'monday'
  soon_days: number // due dates turn orange this many days ahead
  default_statuses: Status[] // shown when the app opens
  default_sort: SortOrder
}

export const PREF_DEFAULTS: Prefs = {
  reminders_timed: ['-8h'],
  reminders_untimed: ['0'],
  untimed_hour: 9,
  week_start: 'sunday',
  soon_days: 2,
  default_statuses: ['backlog', 'todo', 'in_progress', 'blocked'],
  default_sort: 'created',
}

/** What's in effect: your settings over the defaults. */
export const prefs = $state<Prefs>({ ...PREF_DEFAULTS })

/** Which ones you've set yourself (the rest are defaults). */
export const ownPrefs = $state<{ values: Partial<Prefs> }>({ values: {} })

export function applyPrefs(values: Partial<Prefs>) {
  ownPrefs.values = values
  Object.assign(prefs, PREF_DEFAULTS, values)
}
