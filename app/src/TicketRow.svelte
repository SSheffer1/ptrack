<script lang="ts">
  import StatusIcon from './StatusIcon.svelte'
  import { PRIORITY_LABELS, type Item } from './lib/api'
  import { dueTone, formatDue, formatDueWithTime, formatTime } from './lib/format'
  import { describeRule } from './lib/recurrence'
  import { runtime } from './lib/runtime.svelte'
  import { userName } from './lib/state.svelte'

  // Every piece has a fixed place, whatever else the ticket has:
  //   [status]  Title ................... due date
  //             KEY · → who · labels ..... ↻ priority
  // In the agenda the day is already the heading, so only the time is shown.
  let { item, showDate = true }: { item: Item; showDate?: boolean } = $props()

  const when = $derived(
    item.status === 'done' && item.completed_on
      ? `✓ ${formatDue(item.completed_on)}`
      : item.due && showDate
        ? formatDueWithTime(item.due, item.due_time)
        : item.due_time
          ? formatTime(item.due_time)
          : '',
  )
  const tone = $derived(item.due && item.status !== 'done' ? dueTone(item.due, item.status) : '')
  const others = $derived(item.assignee_id && item.assignee_id !== runtime.me?.id ? [`→ ${userName(item.assignee_id)}`] : [])
  const sub = $derived([item.key ?? '…', ...others, ...item.labels].join(' · '))
</script>

<a href="#/items/{item.key ?? item.id}" class="ticket">
  <StatusIcon status={item.status} />
  <span class="title">{item.title}</span>
  <span class="when {tone}">{when}</span>
  <span class="sub">{sub}</span>
  <span class="side">
    {#if item.repeat}<span title={describeRule(item.repeat)}>↻</span>{/if}
    {#if item.priority !== 'none'}
      <span class="priority-{item.priority}">{PRIORITY_LABELS[item.priority]}</span>
    {/if}
  </span>
</a>
