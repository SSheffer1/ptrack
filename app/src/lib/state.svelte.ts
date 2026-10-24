// State shared by every view, so filters stay put when switching between
// List, Calendar and Agenda. (`.svelte.ts` lets a plain module use $state.)

import { account } from './account'
import { api, errorText, type ItemFilters, type Project, type SortOrder, type Status, type User } from './api'
import { runtime } from './runtime.svelte'

export const filters = $state({
  project: '', // project key; '' = all
  statuses: ['backlog', 'todo', 'in_progress', 'blocked'] as Status[], // done hidden by default
  q: '',
  mine: false, // only tickets assigned to me (or unassigned ones I created)
  sort: 'created' as SortOrder, // List view only; the calendar and agenda are always by date
})

/** The filters every view applies (each view adds its own dates, statuses or sort). */
export function commonFilters(): ItemFilters {
  return { project: filters.project, q: filters.q, assignee: filters.mine ? 'me' : undefined }
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

export function addProject(p: Project) {
  projects.list = [...projects.list, p].sort((a, b) => a.key.localeCompare(b.key))
}
