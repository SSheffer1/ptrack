<script lang="ts">
  import { describeRule, REPEAT_PRESETS } from './lib/recurrence'

  let { value, onchange }: { value: string | null; onchange: (rule: string | null) => void } = $props()

  let custom = $state(false)
  const isPreset = $derived(REPEAT_PRESETS.some((p) => p.rule === value))

  function pick(e: Event & { currentTarget: HTMLSelectElement }) {
    const v = e.currentTarget.value
    custom = v === '__custom'
    if (!custom) onchange(v || null)
  }
</script>

<select value={custom ? '__custom' : (value ?? '')} onchange={pick}>
  <option value="">Doesn't repeat</option>
  {#each REPEAT_PRESETS as p (p.rule)}
    <option value={p.rule}>{p.label}</option>
  {/each}
  {#if value && !isPreset}
    <option value={value}>{describeRule(value)}</option>
  {/if}
  <option value="__custom">Custom rule…</option>
</select>
{#if custom}
  <input
    value={value ?? ''}
    placeholder="FREQ=WEEKLY;BYDAY=TU,TH"
    onchange={(e) => onchange(e.currentTarget.value.trim() || null)}
    aria-label="Custom repeat rule"
  />
  <span class="hint">iCalendar RRULE, e.g. FREQ=MONTHLY;BYMONTHDAY=1 or FREQ=WEEKLY;UNTIL=20261211</span>
{/if}
