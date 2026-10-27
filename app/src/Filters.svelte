<script lang="ts">
  import type { Snippet } from 'svelte'
  import ProjectFilter from './ProjectFilter.svelte'
  import StatusFilter from './StatusFilter.svelte'
  import { filters } from './lib/state.svelte'

  // Row 1: search (if shown) and project. The status dropdown goes on row 2 with the
  // view's own controls (`actions`); without a search box it fits on row 1 instead.
  // `search = false` hides the search box (the calendar and agenda have no use for it).
  let { actions, search = true }: { actions?: Snippet; search?: boolean } = $props()
</script>

<section class="filters">
  <div class="filters-row">
    {#if search}
      <input type="search" bind:value={filters.q} placeholder="Search…" aria-label="Search" />
    {/if}
    <ProjectFilter />
    {#if !search}<StatusFilter />{/if}
  </div>
  {#if search || actions}
    <div class="filters-row wrap">
      {#if search}<StatusFilter />{/if}
      {@render actions?.()}
    </div>
  {/if}
</section>
