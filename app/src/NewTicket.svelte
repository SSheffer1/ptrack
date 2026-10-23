<script lang="ts">
  import RepeatPicker from './RepeatPicker.svelte'
  import { api, errorText, PRIORITIES, PRIORITY_LABELS, type Item, type Priority } from './lib/api'
  import { formatDue, parseLabels } from './lib/format'
  import { filters, projects } from './lib/state.svelte'

  interface Props {
    initialDue?: string // e.g. when started by clicking a day on the calendar
    oncreated: (item: Item) => void
    oncancel: () => void
  }
  let { initialDue = '', oncreated, oncancel }: Props = $props()

  // Start with the project the views are filtered to, or the first one.
  let project = $state(filters.project || projects.list[0]?.key || '')
  let title = $state('')
  let priority = $state<Priority>('none')
  let due = $state('')
  let dueTime = $state('')
  let repeat = $state<string | null>(null)
  let labels = $state('')
  let assignedOn = $state('')
  let error = $state('')

  $effect.pre(() => {
    due = initialDue
  })

  async function submit(e: SubmitEvent) {
    e.preventDefault()
    try {
      const item = await api.createItem({
        project,
        title: title.trim(),
        priority,
        due: due || null,
        due_time: (due && dueTime) || null,
        repeat,
        labels: parseLabels(labels),
        assigned_on: assignedOn || null,
      })
      oncreated(item)
    } catch (err) {
      error = errorText(err)
    }
  }
</script>

<form class="panel" onsubmit={submit}>
  <h2>New ticket{initialDue ? ` due ${formatDue(initialDue)}` : ''}</h2>
  <label>
    Title
    <!-- svelte-ignore a11y_autofocus -->
    <input bind:value={title} placeholder="Study for circuits exam" required autofocus />
  </label>
  <div class="row">
    <label>
      Project
      <select bind:value={project} required>
        {#each projects.list as p (p.id)}
          <option value={p.key}>{p.key} · {p.name}</option>
        {/each}
      </select>
    </label>
    <label>
      Priority
      <select bind:value={priority}>
        {#each PRIORITIES as p (p)}
          <option value={p}>{PRIORITY_LABELS[p]}</option>
        {/each}
      </select>
    </label>
  </div>
  <div class="row">
    <label>
      Due
      <input type="date" bind:value={due} />
    </label>
    <label>
      Time <span class="hint">(optional)</span>
      <input type="time" bind:value={dueTime} disabled={!due} />
    </label>
    <label>
      Repeat
      <RepeatPicker value={repeat} onchange={(r) => (repeat = r)} />
    </label>
  </div>
  <div class="row">
    <label class="grow">
      Labels <span class="hint">(comma separated)</span>
      <input bind:value={labels} placeholder="circuits, exam" />
    </label>
    <label>
      Assigned <span class="hint">(if not today)</span>
      <input type="date" bind:value={assignedOn} />
    </label>
  </div>
  {#if error}<p class="error">{error}</p>{/if}
  <div class="actions">
    <button type="button" onclick={oncancel}>Cancel</button>
    <button type="submit" class="primary">Create ticket</button>
  </div>
</form>
