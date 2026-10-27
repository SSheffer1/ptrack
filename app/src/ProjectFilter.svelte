<script lang="ts">
  import { filters, projects } from './lib/state.svelte'
  import { keepOnScreen } from './lib/popover'

  // A checklist of projects, like the Status dropdown. Nothing ticked shows every project.
  let panel = $state<HTMLDetailsElement>()
  let list = $state<HTMLDivElement>()

  // Only keys of projects that still exist count (one may have been deleted since it was ticked).
  const chosen = $derived(projects.list.filter((p) => filters.projects.includes(p.key)))
  const label = $derived.by(() => {
    const n = chosen.length
    const which = n === 0 || n === projects.list.length ? 'All' : n === 1 ? chosen[0].key : `${n} of ${projects.list.length}`
    return `Projects: ${which}`
  })

  function toggle(key: string) {
    filters.projects = filters.projects.includes(key)
      ? filters.projects.filter((k) => k !== key)
      : projects.list.map((p) => p.key).filter((k) => k === key || filters.projects.includes(k)) // keep the list order
  }

  function closeIfOutside(e: Event) {
    if (panel?.open && !panel.contains(e.target as Node)) panel.open = false
  }
</script>

<svelte:window onclick={closeIfOutside} onkeydown={(e) => e.key === 'Escape' && panel && (panel.open = false)} />

<details class="pick-filter" bind:this={panel} ontoggle={() => panel?.open && keepOnScreen(list)}>
  <summary><span class="pick-label">{label}</span> <span aria-hidden="true">▾</span></summary>
  <div class="pick-panel" bind:this={list} role="group" aria-label="Show projects">
    {#each projects.list as p (p.id)}
      <label class="pick-option">
        <input type="checkbox" checked={filters.projects.includes(p.key)} onchange={() => toggle(p.key)} />
        {p.key} · {p.name}
      </label>
    {/each}
    {#if filters.projects.length}
      <hr />
      <button type="button" class="link" onclick={() => (filters.projects = [])}>Show all</button>
    {/if}
  </div>
</details>
