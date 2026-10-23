// State shared by every view, so filters stay put when switching between
// List, Calendar and Agenda. (`.svelte.ts` lets a plain module use $state.)

import { api, errorText, type Project, type SortOrder, type Status } from './api'

export const filters = $state({
  project: '', // project key; '' = all
  statuses: ['backlog', 'todo', 'in_progress', 'blocked'] as Status[], // done hidden by default
  q: '',
  sort: 'created' as SortOrder, // List view only; the calendar and agenda are always by date
})

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

export function addProject(p: Project) {
  projects.list = [...projects.list, p].sort((a, b) => a.key.localeCompare(b.key))
}
