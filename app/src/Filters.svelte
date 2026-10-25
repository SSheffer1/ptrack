<script lang="ts">
  import type { Snippet } from 'svelte'
  import { STATUS_LABELS, STATUSES, type Status } from './lib/api'
  import { filters, projects } from './lib/state.svelte'

  // `actions` = the view's own controls, shown as a second row (beside the first on wide screens).
  let { actions }: { actions?: Snippet } = $props()

  function toggleStatus(s: Status) {
    filters.statuses = filters.statuses.includes(s)
      ? filters.statuses.filter((x) => x !== s)
      : [...filters.statuses, s]
  }
</script>

<section class="filters">
  <div class="filters-row">
    <input type="search" bind:value={filters.q} placeholder="Search…" aria-label="Search" />
    <select bind:value={filters.project} aria-label="Project">
      <option value="">All projects</option>
      {#each projects.list as p (p.id)}
        <option value={p.key}>{p.key} · {p.name}</option>
      {/each}
    </select>
  </div>
  {#if actions}
    <div class="filters-row">{@render actions()}</div>
  {/if}
</section>

<section class="chips" aria-label="Status filter">
  {#each STATUSES as s (s)}
    <button class="chip status-{s}" class:on={filters.statuses.includes(s)} onclick={() => toggleStatus(s)}>
      {STATUS_LABELS[s]}
    </button>
  {/each}
  <span class="chip-gap"></span>
  <button class="chip mine" class:on={filters.mine} onclick={() => (filters.mine = !filters.mine)}>
    Assigned to me
  </button>
</section>
