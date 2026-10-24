<script lang="ts">
  import Filters from './Filters.svelte'
  import TicketRow from './TicketRow.svelte'
  import { api, errorText, type Item } from './lib/api'
  import { formatDue, parseDate, toISODate } from './lib/format'
  import { runtime } from './lib/runtime.svelte'
  import { filters } from './lib/state.svelte'

  // Upcoming due dates grouped by day, with anything overdue on top.
  // Tickets without a due date don't appear here (they're in the List).

  let items = $state<Item[]>([])
  let error = $state('')

  let latestRequest = 0
  $effect(() => {
    void runtime.dataVersion // also refresh after a sync
    const request = ++latestRequest
    api.listItems({ project: filters.project, status: [...filters.statuses], q: filters.q }).then(
      (result) => {
        if (request === latestRequest) {
          items = result
          error = ''
        }
      },
      (e) => (error = errorText(e)),
    )
  })

  const groups = $derived.by(() => {
    const today = toISODate(new Date())
    const dated = items
      .filter((i) => i.due)
      .sort((a, b) => `${a.due} ${a.due_time ?? '99'}`.localeCompare(`${b.due} ${b.due_time ?? '99'}`))

    const overdue = dated.filter((i) => i.due! < today && i.status !== 'done')
    const result: { heading: string; sub: string; overdue: boolean; items: Item[] }[] = []
    if (overdue.length) result.push({ heading: 'Overdue', sub: '', overdue: true, items: overdue })

    for (const item of dated.filter((i) => i.due! >= today)) {
      const last = result.at(-1)
      if (last && !last.overdue && last.items[0].due === item.due) last.items.push(item)
      else {
        const date = parseDate(item.due!)
        result.push({
          heading: formatDue(item.due!),
          sub: date.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' }),
          overdue: false,
          items: [item],
        })
      }
    }
    return result
  })
</script>

<Filters />

{#if error}<p class="error">{error}</p>{/if}

{#if groups.length === 0}
  <p class="empty">Nothing due. Tickets with a due date show up here.</p>
{/if}

{#each groups as group (group.heading)}
  <h3 class="agenda-day" class:overdue={group.overdue}>
    {group.heading}
    {#if group.sub && group.sub !== group.heading}<span class="hint">{group.sub}</span>{/if}
  </h3>
  <ul class="tickets">
    {#each group.items as item (item.id)}
      <li><TicketRow {item} showDate={group.overdue} /></li>
    {/each}
  </ul>
{/each}
