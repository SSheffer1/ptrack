<script lang="ts">
  import Filters from './Filters.svelte'
  import NewTicket from './NewTicket.svelte'
  import { api, errorText, STATUSES, type Item } from './lib/api'
  import { addDays, dueTone, formatTime, toISODate } from './lib/format'
  import { prefs } from './lib/prefs.svelte'
  import { commonFilters, filters, projects } from './lib/state.svelte'
  import { runtime } from './lib/runtime.svelte'

  const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
  // 0 = weeks start on Sunday, 1 = Monday (your preference).
  const weekStart = $derived(prefs.week_start === 'monday' ? 1 : 0)
  const weekdays = $derived([...DAY_NAMES.slice(weekStart), ...DAY_NAMES.slice(0, weekStart)])
  const todayISO = toISODate(new Date())

  const now = new Date()
  let month = $state(new Date(now.getFullYear(), now.getMonth(), 1)) // first day of the shown month
  let items = $state<Item[]>([])
  let error = $state('')
  let addingOn = $state<string | null>(null) // date of the day clicked to add a ticket

  // The grid runs from the first day of the week on or before the 1st to the last day of the week on or after the month's end.
  const days = $derived.by(() => {
    const first = addDays(month, -((month.getDay() - weekStart + 7) % 7))
    const last = new Date(month.getFullYear(), month.getMonth() + 1, 0)
    const end = addDays(last, 6 - ((last.getDay() - weekStart + 7) % 7))
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
    // Same status filter as the List (nothing ticked = everything). Finished tickets
    // show on the day they were completed, struck through, when Done is ticked.
    const shown = filters.statuses.length ? filters.statuses : STATUSES
    const openStatuses = shown.filter((s) => s !== 'done')
    const common = { ...commonFilters(), q: undefined } // no search box here, so don't apply the List's search
    try {
      const [open, done] = await Promise.all([
        openStatuses.length
          ? api.listItems({ ...common, status: openStatuses, due_from: range.from, due_to: range.to })
          : [],
        shown.includes('done')
          ? api.listItems({ ...common, status: ['done'], completed_from: range.from, completed_to: range.to })
          : [],
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

<Filters search={false} />

<div class="month-nav">
  <button onclick={() => shift(-1)} aria-label="Previous month">‹</button>
  <h2 class="month-title">{month.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}</h2>
  <button onclick={() => shift(1)} aria-label="Next month">›</button>
</div>

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
  {#each weekdays as w (w)}<div class="weekday">{w}</div>{/each}
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
