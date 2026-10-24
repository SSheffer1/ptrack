<script lang="ts">
  import Filters from './Filters.svelte'
  import NewTicket from './NewTicket.svelte'
  import { api, errorText, STATUSES, type Item } from './lib/api'
  import { addDays, dueTone, formatTime, toISODate } from './lib/format'
  import { filters, projects } from './lib/state.svelte'
  import { runtime } from './lib/runtime.svelte'

  const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
  const todayISO = toISODate(new Date())

  const now = new Date()
  let month = $state(new Date(now.getFullYear(), now.getMonth(), 1)) // first day of the shown month
  let items = $state<Item[]>([])
  let error = $state('')
  let addingOn = $state<string | null>(null) // date of the day clicked to add a ticket

  // The grid runs from the Sunday on or before the 1st to the Saturday on or after the last day.
  const days = $derived.by(() => {
    const first = addDays(month, -month.getDay())
    const last = new Date(month.getFullYear(), month.getMonth() + 1, 0)
    const end = addDays(last, 6 - last.getDay())
    const result: { date: Date; iso: string; inMonth: boolean }[] = []
    for (let d = first; d <= end; d = addDays(d, 1)) {
      result.push({ date: d, iso: toISODate(d), inMonth: d.getMonth() === month.getMonth() })
    }
    return result
  })

  // Open tickets sit on their due date; finished ones on the day they were
  // completed. Each day lists open tickets first (timed ones in time order),
  // then finished ones.
  const dayOf = (item: Item) => (item.status === 'done' ? (item.completed_on ?? item.due) : item.due)
  const sortKey = (item: Item) => `${item.status === 'done' ? 1 : 0} ${item.due_time ?? '99'}`

  const byDay = $derived.by(() => {
    const map = new Map<string, Item[]>()
    for (const item of items) {
      const day = dayOf(item)
      if (day) map.set(day, [...(map.get(day) ?? []), item])
    }
    for (const list of map.values()) list.sort((a, b) => sortKey(a).localeCompare(sortKey(b)))
    return map
  })

  let latestRequest = 0
  async function load(range: { from: string; to: string }) {
    const request = ++latestRequest
    // The status chips filter open tickets; finished ones always show, struck through.
    const chosen = filters.statuses.filter((s) => s !== 'done')
    const openStatuses = chosen.length ? chosen : STATUSES.filter((s) => s !== 'done')
    const common = { project: filters.project, q: filters.q }
    try {
      const [open, done] = await Promise.all([
        api.listItems({ ...common, status: openStatuses, due_from: range.from, due_to: range.to }),
        api.listItems({ ...common, status: ['done'], completed_from: range.from, completed_to: range.to }),
      ])
      if (request === latestRequest) {
        items = [...open, ...done]
        error = ''
      }
    } catch (e) {
      error = errorText(e)
    }
  }

  const reload = () => load({ from: days[0].iso, to: days[days.length - 1].iso })
  $effect(() => {
    void runtime.dataVersion // also refresh after a sync
    reload()
  })

  function shift(months: number) {
    month = new Date(month.getFullYear(), month.getMonth() + months, 1)
  }
</script>

<Filters>
  {#snippet actions()}
    <button onclick={() => shift(-1)} aria-label="Previous month">‹</button>
    <button onclick={() => (month = new Date(now.getFullYear(), now.getMonth(), 1))}>Today</button>
    <button onclick={() => shift(1)} aria-label="Next month">›</button>
  {/snippet}
</Filters>

<h2 class="month-title">{month.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}</h2>

{#if addingOn}
  <NewTicket
    initialDue={addingOn}
    oncancel={() => (addingOn = null)}
    oncreated={() => {
      addingOn = null
      reload()
    }}
  />
{/if}

{#if error}<p class="error">{error}</p>{/if}

<div class="month">
  {#each WEEKDAYS as w (w)}<div class="weekday">{w}</div>{/each}
  {#each days as day (day.iso)}
    <div class="day" class:other-month={!day.inMonth} class:today={day.iso === todayISO}>
      <button
        class="day-num"
        onclick={() => (addingOn = day.iso)}
        disabled={projects.list.length === 0}
        title="Add a ticket due this day"
      >
        {day.date.getDate()}
      </button>
      {#each byDay.get(day.iso) ?? [] as item (item.id)}
        <a
          href="#/items/{item.key ?? item.id}"
          class="cal-item status-{item.status} {dueTone(day.iso, item.status)}"
          title="{item.key} {item.title}{item.status === 'done' ? ' (done)' : ''}"
        >
          {#if item.due_time}<span class="cal-time">{formatTime(item.due_time)}</span>{/if}
          {item.title}
        </a>
      {/each}
    </div>
  {/each}
</div>
