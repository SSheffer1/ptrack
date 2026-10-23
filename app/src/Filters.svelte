<script lang="ts">
  import type { Snippet } from 'svelte'
  import { STATUS_LABELS, STATUSES, type Status } from './lib/api'
  import { filters, projects } from './lib/state.svelte'

  // `actions` = buttons shown at the right end of the toolbar.
  let { actions }: { actions?: Snippet } = $props()

  function toggleStatus(s: Status) {
    filters.statuses = filters.statuses.includes(s)
      ? filters.statuses.filter((x) => x !== s)
      : [...filters.statuses, s]
  }
</script>

<section class="toolbar">
  <select bind:value={filters.project} aria-label="Project">
    <option value="">All projects</option>
    {#each projects.list as p (p.id)}
      <option value={p.key}>{p.key} · {p.name}</option>
    {/each}
  </select>
  <input type="search" bind:value={filters.q} placeholder="Search…" aria-label="Search" />
  <div class="spacer"></div>
  {@render actions?.()}
</section>

<section class="chips" aria-label="Status filter">
  {#each STATUSES as s (s)}
    <button class="chip status-{s}" class:on={filters.statuses.includes(s)} onclick={() => toggleStatus(s)}>
      {STATUS_LABELS[s]}
    </button>
  {/each}
</section>
