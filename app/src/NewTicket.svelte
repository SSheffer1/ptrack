<script lang="ts">
  import { api, errorText, PRIORITIES, PRIORITY_LABELS, type Item, type Priority, type Project } from './lib/api'
  import { parseLabels } from './lib/format'

  interface Props {
    projects: Project[]
    initialProject: string
    oncreated: (item: Item) => void
    oncancel: () => void
  }
  let { projects, initialProject, oncreated, oncancel }: Props = $props()

  let project = $state('')
  let title = $state('')
  let priority = $state<Priority>('none')
  let due = $state('')
  let labels = $state('')
  let error = $state('')

  // Start with the project the list is filtered to, or the first one.
  $effect.pre(() => {
    if (!project) project = initialProject || projects[0]?.key || ''
  })

  async function submit(e: SubmitEvent) {
    e.preventDefault()
    try {
      const item = await api.createItem({
        project,
        title: title.trim(),
        priority,
        due: due || null,
        labels: parseLabels(labels),
      })
      oncreated(item)
    } catch (err) {
      error = errorText(err)
    }
  }
</script>

<form class="panel" onsubmit={submit}>
  <h2>New ticket</h2>
  <label>
    Title
    <!-- svelte-ignore a11y_autofocus -->
    <input bind:value={title} placeholder="Study for circuits exam" required autofocus />
  </label>
  <div class="row">
    <label>
      Project
      <select bind:value={project} required>
        {#each projects as p (p.id)}
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
    <label>
      Due
      <input type="date" bind:value={due} />
    </label>
  </div>
  <label>
    Labels <span class="hint">(comma separated)</span>
    <input bind:value={labels} placeholder="circuits, exam" />
  </label>
  {#if error}<p class="error">{error}</p>{/if}
  <div class="actions">
    <button type="button" onclick={oncancel}>Cancel</button>
    <button type="submit" class="primary">Create ticket</button>
  </div>
</form>
