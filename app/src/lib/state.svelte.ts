// State shared by every view, so filters stay put when switching between
// List, Calendar and Agenda. (`.svelte.ts` lets a plain module use $state.)

import { account } from './account'
import { applyPrefs, type Prefs, prefs } from './prefs.svelte'
import { api, errorText, type ItemFilters, type Project, type SortOrder, type Status, type User } from './api'
import { runtime } from './runtime.svelte'

export const filters = $state({
  projects: [] as string[], // project keys; none ticked = all
  statuses: ['backlog', 'todo', 'in_progress', 'blocked'] as Status[], // done hidden by default
  q: '',
  mine: false, // only tickets assigned to me (or unassigned ones I created)
  sort: 'created' as SortOrder, // List view only; the calendar and agenda are always by date
})

/** The filters every view applies (each view adds its own dates, statuses or sort). */
export function commonFilters(): ItemFilters {
  // Skip ticked projects that have since been deleted (asking for one is an error).
  const project = filters.projects.filter((key) => projects.list.some((p) => p.key === key))
  return { project, q: filters.q, assignee: filters.mine ? 'me' : undefined }
}

export const projects = $state({
  list: [] as Project[],
  loaded: false,
  error: '',
})

export async function loadProjects() {
  try {
    projects.list = await api.listProjects()
    projects.loaded = true
  } catch (e) {
    projects.error = errorText(e)
  }
}

// People who share a project with me. Offline-first mode gets them from the
// last sync; online mode asks the server.
const onlineUsers = $state({ list: [] as User[] })

export async function loadUsers() {
  if (runtime.local) return
  try {
    onlineUsers.list = await account.visibleUsers()
  } catch {
    // names fall back to "Someone"
  }
}

export function users(): User[] {
  return runtime.local ? runtime.people.users : onlineUsers.list
}

export function userName(id: string | null | undefined): string {
  if (!id) return ''
  if (id === runtime.me?.id) return 'you'
  return users().find((u) => u.id === id)?.display_name ?? 'Someone'
}

// Your preferences, and the starting filters they imply (applied once per sign-in,
// so changing filters by hand isn't undone by the next sync).
let filtersFromPrefs = false

export async function loadPrefs() {
  try {
    applyPrefs((await api.getPrefs()) as Partial<Prefs>)
  } catch {
    return // offline in online mode; keep what we have
  }
  if (!filtersFromPrefs) {
    filtersFromPrefs = true
    filters.statuses = [...prefs.default_statuses]
    filters.sort = prefs.default_sort
  }
}

export async function savePrefs(values: Partial<Record<keyof Prefs, unknown>>) {
  applyPrefs((await api.updatePrefs(values)) as Partial<Prefs>)
}

export function addProject(p: Project) {
  projects.list = [...projects.list, p].sort((a, b) => a.key.localeCompare(b.key))
}
