<script lang="ts">
  import Filters from './Filters.svelte'
  import NewProject from './NewProject.svelte'
  import NewTicket from './NewTicket.svelte'
  import TicketRow from './TicketRow.svelte'
  import { api, errorText, SORT_LABELS, type Item, type ItemFilters, type SortOrder } from './lib/api'
  import { addProject, commonFilters, filters, projects } from './lib/state.svelte'
  import { runtime } from './lib/runtime.svelte'

  let items = $state<Item[]>([])
  let error = $state('')
  let adding = $state<'ticket' | 'project' | null>(null)

  // Re-fetch whenever a filter changes. Responses can arrive out of order when
  // typing fast, so only the newest request is allowed to update the list.
  let latestRequest = 0
  async function loadItems(f: ItemFilters) {
    const request = ++latestRequest
    try {
      const result = await api.listItems(f)
      if (request === latestRequest) {
        items = result
        error = ''
      }
    } catch (e) {
      error = errorText(e)
    }
  }

  const reload = () =>
    loadItems({ ...commonFilters(), status: [...filters.statuses], sort: filters.sort })
  $effect(() => {
    void runtime.dataVersion // also refresh after a sync
    reload()
  })
</script>

<Filters>
  {#snippet actions()}
    <select bind:value={filters.sort} aria-label="Sort">
      {#each Object.entries(SORT_LABELS) as [value, label] (value)}
        <option value={value as SortOrder}>{label}</option>
      {/each}
    </select>
    <button onclick={() => (adding = 'project')}>+ Project</button>
    <button class="primary" onclick={() => (adding = 'ticket')} disabled={projects.list.length === 0}>+ Ticket</button>
  {/snippet}
</Filters>

{#if adding === 'project'}
  <NewProject
    oncancel={() => (adding = null)}
    oncreated={(p) => {
      addProject(p)
      adding = null
    }}
  />
{:else if adding === 'ticket'}
  <NewTicket
    oncancel={() => (adding = null)}
    oncreated={() => {
      adding = null
      reload()
    }}
  />
{/if}

{#if error || projects.error}<p class="error">{error || projects.error}</p>{/if}

{#if projects.loaded && projects.list.length === 0}
  <p class="empty">No projects yet. Create one (e.g. SCHOOL) to start adding tickets.</p>
{:else if items.length === 0}
  <p class="empty">No tickets match these filters.</p>
{:else}
  <ul class="tickets">
    {#each items as item (item.id)}
      <li><TicketRow {item} /></li>
    {/each}
  </ul>
{/if}
