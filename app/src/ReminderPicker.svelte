<script lang="ts">
  import { defaultReminders, describeOffset, normalizeReminders, reminderChoices } from './lib/reminders'

  // value: null = the default, [] = none, else the chosen offsets.
  interface Props {
    value: string[] | null
    timed: boolean // whether the ticket has a due time (changes the choices)
    onchange: (value: string[] | null) => void
  }
  let { value, timed, onchange }: Props = $props()

  const active = $derived(value ?? defaultReminders(timed))
  // Show the standard choices, plus any custom offset already on the ticket.
  const choices = $derived(normalizeReminders([...reminderChoices(timed), ...active])!)

  function toggle(offset: string) {
    const next = active.includes(offset) ? active.filter((o) => o !== offset) : [...active, offset]
    onchange(normalizeReminders(next))
  }
</script>

<div class="reminders">
  <div class="chips">
    {#each choices as offset (offset)}
      <button type="button" class="chip" class:on={active.includes(offset)} onclick={() => toggle(offset)}>
        {describeOffset(offset, timed)}
      </button>
    {/each}
  </div>
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
</div>
