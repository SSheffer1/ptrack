<script lang="ts">
  import type { Snippet } from 'svelte'
  import ProjectFilter from './ProjectFilter.svelte'
  import StatusFilter from './StatusFilter.svelte'
  import { filters } from './lib/state.svelte'

  // Three rows: search (if shown), then the project and status dropdowns side by
  // side at fixed widths (so a changing label can't reflow anything), then the
  // view's own controls (`actions`), if any. Rows 2 and 3 share a 4-column grid
  // so their edges line up.
  // `search = false` hides the search box (the calendar and agenda have no use for it).
  let { actions, search = true }: { actions?: Snippet; search?: boolean } = $props()
</script>

<section class="filters">
  {#if search}
    <div class="filters-row">
      <input type="search" bind:value={filters.q} placeholder="Search…" aria-label="Search" />
    </div>
  {/if}
  <div class="filters-row grid4 pickers">
    <ProjectFilter />
    <StatusFilter />
  </div>
  {#if actions}
    <div class="filters-row grid4">
      {@render actions()}
    </div>
  {/if}
</section>
