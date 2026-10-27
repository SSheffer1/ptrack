<script lang="ts">
  import { STATUS_LABELS, type Status } from './lib/api'

  // A ticket's status as a small circle whose shape differs too, not only its
  // color: dashed = backlog, empty = to do, half full = in progress,
  // bar = blocked, check = done.
  let { status }: { status: Status } = $props()
</script>

<svg class="status-icon status-{status}" width="16" height="16" viewBox="0 0 16 16" role="img" aria-label={STATUS_LABELS[status]}>
  <title>{STATUS_LABELS[status]}</title>
  {#if status === 'done'}
    <circle cx="8" cy="8" r="7" fill="currentColor" />
    <path d="M4.8 8.2 7 10.4 11.2 5.8" fill="none" stroke="var(--surface)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
  {:else}
    <circle cx="8" cy="8" r="6.25" fill="none" stroke="currentColor" stroke-width="1.75" stroke-dasharray={status === 'backlog' ? '2.4 2.1' : undefined} />
    {#if status === 'in_progress'}
      <path d="M8 3.5 A4.5 4.5 0 0 1 8 12.5 Z" fill="currentColor" />
    {:else if status === 'blocked'}
      <path d="M4.8 8 H11.2" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" />
    {/if}
  {/if}
</svg>
