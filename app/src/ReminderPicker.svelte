<script lang="ts">
  import {
    defaultReminders,
    describeOffset,
    describeSpecific,
    isSpecificTime,
    normalizeReminders,
    reminderChoices,
    specificMoment,
    specificTime,
  } from './lib/reminders'

  // value: null = the default, [] = none, else the chosen reminders.
  interface Props {
    value: string[] | null
    hasDue: boolean // the before-due choices only make sense with a due date
    timed: boolean // whether the ticket has a due time (changes the choices)
    onchange: (value: string[] | null) => void
  }
  let { value, hasDue, timed, onchange }: Props = $props()

  // Without a due date the defaults don't apply, so nothing is on until a time is added.
  const active = $derived(value ?? (hasDue ? defaultReminders() : []))
  // Show the standard choices, plus any custom offset already on the ticket.
  const choices = $derived(normalizeReminders([...reminderChoices(timed), ...active.filter((r) => !isSpecificTime(r))])!)
  const times = $derived(active.filter(isSpecificTime))

  let picked = $state('') // "YYYY-MM-DDTHH:MM" from the datetime-local input
  const pickedOk = $derived(!!picked && (specificMoment(specificTime(picked))?.getTime() ?? 0) > Date.now())

  function toggle(r: string) {
    const next = active.includes(r) ? active.filter((o) => o !== r) : [...active, r]
    onchange(normalizeReminders(next))
  }

  function addTime() {
    if (!pickedOk) return
    const r = specificTime(picked)
    if (!active.includes(r)) toggle(r)
    picked = ''
  }
</script>

<div class="reminders">
  {#if hasDue}
    <div class="chips">
      {#each choices as offset (offset)}
        <button type="button" class="chip" class:on={active.includes(offset)} onclick={() => toggle(offset)}>
          {describeOffset(offset, timed)}
        </button>
      {/each}
    </div>
  {/if}
  {#if times.length}
    <div class="chips">
      {#each times as r (r)}
        <span class="chip on removable">
          {describeSpecific(r)}
          <button type="button" class="chip-x" aria-label="Remove reminder at {describeSpecific(r)}" onclick={() => toggle(r)}>×</button>
        </span>
      {/each}
    </div>
  {/if}
  <div class="add-time">
    <span class="hint">At a specific time</span>
    <input type="datetime-local" bind:value={picked} onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), addTime())} />
    <button type="button" onclick={addTime} disabled={!pickedOk}>Add</button>
  </div>
  {#if hasDue}
    <span class="hint">
      {#if value === null}
        Default
      {:else if value.length === 0}
        No reminders ·
        <button type="button" class="link" onclick={() => onchange(null)}>use default</button>
      {:else}
        <button type="button" class="link" onclick={() => onchange(null)}>Reset to default</button>
      {/if}
    </span>
  {/if}
</div>
