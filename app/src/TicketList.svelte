<script lang="ts">
  import NewProject from './NewProject.svelte'
  import NewTicket from './NewTicket.svelte'
  import {
    api,
    errorText,
    PRIORITY_LABELS,
    STATUS_LABELS,
    STATUSES,
    type Item,
    type ItemFilters,
    type Project,
    type Status,
  } from './lib/api'
  import { dueTone, formatDue } from './lib/format'

  let projects = $state<Project[]>([])
  let items = $state<Item[]>([])
  let error = $state('')
  let adding = $state<'ticket' | 'project' | null>(null)

  // Filters. Done tickets are hidden by default.
  let project = $state('')
  let statuses = $state<Status[]>(['backlog', 'todo', 'in_progress', 'blocked'])
  let q = $state('')

  api.listProjects().then(
    (p) => (projects = p),
    (e) => (error = errorText(e)),
  )

  // Re-fetch whenever a filter changes. Responses can arrive out of order when
  // typing fast, so only the newest request is allowed to update the list.
  let latestRequest = 0
  async function loadItems(filters: ItemFilters) {
    const request = ++latestRequest
    try {
      const result = await api.listItems(filters)
      if (request === latestRequest) {
        items = result
        error = ''
      }
    } catch (e) {
      error = errorText(e)
    }
  }

  $effect(() => {
    loadItems({ project, status: [...statuses], q })
  })

  function toggleStatus(s: Status) {
    statuses = statuses.includes(s) ? statuses.filter((x) => x !== s) : [...statuses, s]
  }

  function reload() {
    loadItems({ project, status: [...statuses], q })
  }
</script>

<section class="toolbar">
  <select bind:value={project} aria-label="Project">
    <option value="">All projects</option>
    {#each projects as p (p.id)}
      <option value={p.key}>{p.key} · {p.name}</option>
    {/each}
  </select>
  <input type="search" bind:value={q} placeholder="Search…" aria-label="Search" />
  <div class="spacer"></div>
  <button onclick={() => (adding = 'project')}>+ Project</button>
  <button class="primary" onclick={() => (adding = 'ticket')} disabled={projects.length === 0}>+ Ticket</button>
</section>

<section class="chips" aria-label="Status filter">
  {#each STATUSES as s (s)}
    <button class="chip status-{s}" class:on={statuses.includes(s)} onclick={() => toggleStatus(s)}>
      {STATUS_LABELS[s]}
    </button>
  {/each}
</section>

{#if adding === 'project'}
  <NewProject
    oncancel={() => (adding = null)}
    oncreated={(p) => {
      projects = [...projects, p].sort((a, b) => a.key.localeCompare(b.key))
      adding = null
    }}
  />
{:else if adding === 'ticket'}
  <NewTicket
    {projects}
    initialProject={project}
    oncancel={() => (adding = null)}
    oncreated={() => {
      adding = null
      reload()
    }}
  />
{/if}

{#if error}<p class="error">{error}</p>{/if}

{#if projects.length === 0 && !error}
  <p class="empty">No projects yet. Create one (e.g. SCHOOL) to start adding tickets.</p>
{:else if items.length === 0}
  <p class="empty">No tickets match these filters.</p>
{:else}
  <ul class="tickets">
    {#each items as item (item.id)}
      <li>
        <a href="#/items/{item.key ?? item.id}" class="ticket">
          <span class="key">{item.key ?? '…'}</span>
          <span class="title">{item.title}</span>
          <span class="meta">
            {#each item.labels as label (label)}<span class="label">{label}</span>{/each}
            {#if item.priority !== 'none'}
              <span class="priority priority-{item.priority}">{PRIORITY_LABELS[item.priority]}</span>
            {/if}
            {#if item.due}
              <span class="due {dueTone(item.due, item.status)}">{formatDue(item.due)}</span>
            {/if}
            <span class="badge status-{item.status}">{STATUS_LABELS[item.status]}</span>
          </span>
        </a>
      </li>
    {/each}
  </ul>
{/if}
