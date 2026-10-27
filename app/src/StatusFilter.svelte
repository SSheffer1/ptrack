<script lang="ts">
  import { STATUS_LABELS, STATUSES, type Status } from './lib/api'
  import { filters } from './lib/state.svelte'

  // One button that opens a checklist of statuses (plus "Assigned to me").
  // <details> does the opening and closing; a tap outside or Escape closes it too.
  let panel = $state<HTMLDetailsElement>()

  // Nothing ticked shows everything, same as everything ticked.
  const label = $derived.by(() => {
    const n = filters.statuses.length
    const which = n === 0 || n === STATUSES.length ? 'All' : n === 1 ? STATUS_LABELS[filters.statuses[0]] : `${n} of ${STATUSES.length}`
    return `Status: ${which}${filters.mine ? ' · mine' : ''}`
  })

  function toggle(s: Status) {
    filters.statuses = filters.statuses.includes(s)
      ? filters.statuses.filter((x) => x !== s)
      : STATUSES.filter((x) => x === s || filters.statuses.includes(x)) // keep the usual order
  }

  function closeIfOutside(e: Event) {
    if (panel?.open && !panel.contains(e.target as Node)) panel.open = false
  }
</script>

<svelte:window onclick={closeIfOutside} onkeydown={(e) => e.key === 'Escape' && panel && (panel.open = false)} />

<details class="pick-filter" bind:this={panel}>
  <summary>{label} <span aria-hidden="true">▾</span></summary>
  <div class="pick-panel" role="group" aria-label="Show statuses">
    {#each STATUSES as s (s)}
      <label class="pick-option">
        <input type="checkbox" checked={filters.statuses.includes(s)} onchange={() => toggle(s)} />
        <span class="dot status-{s}"></span>
        {STATUS_LABELS[s]}
      </label>
    {/each}
    <hr />
    <label class="pick-option">
      <input type="checkbox" bind:checked={filters.mine} />
      Assigned to me
    </label>
  </div>
</details>
