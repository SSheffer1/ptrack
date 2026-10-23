<script lang="ts">
  import { PRIORITY_LABELS, STATUS_LABELS, type Item } from './lib/api'
  import { dueTone, formatDue, formatDueWithTime, formatTime } from './lib/format'
  import { describeRule } from './lib/recurrence'

  // In the agenda the day is already the heading, so only the time is shown.
  let { item, showDate = true }: { item: Item; showDate?: boolean } = $props()
</script>

<a href="#/items/{item.key ?? item.id}" class="ticket">
  <span class="key">{item.key ?? '…'}</span>
  <span class="title">{item.title}</span>
  <span class="meta">
    {#each item.labels as label (label)}<span class="label">{label}</span>{/each}
    {#if item.priority !== 'none'}
      <span class="priority priority-{item.priority}">{PRIORITY_LABELS[item.priority]}</span>
    {/if}
    {#if item.repeat}
      <span class="repeat" title={describeRule(item.repeat)}>↻</span>
    {/if}
    {#if item.status === 'done' && item.completed_on}
      <span class="due" title="Completed">✓ {formatDue(item.completed_on)}</span>
    {:else if item.due && showDate}
      <span class="due {dueTone(item.due, item.status)}">{formatDueWithTime(item.due, item.due_time)}</span>
    {:else if item.due_time}
      <span class="due">{formatTime(item.due_time)}</span>
    {/if}
    <span class="badge status-{item.status}">{STATUS_LABELS[item.status]}</span>
  </span>
</a>
