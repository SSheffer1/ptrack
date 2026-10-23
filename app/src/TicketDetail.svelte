<script lang="ts">
  import {
    api,
    ApiError,
    errorText,
    PRIORITIES,
    PRIORITY_LABELS,
    STATUS_LABELS,
    STATUSES,
    type Change,
    type Comment,
    type Item,
    type ItemUpdate,
    type Priority,
    type Status,
  } from './lib/api'
  import { ago, dueTone, exactTime, formatDue, parseLabels } from './lib/format'

  let { ref }: { ref: string } = $props()

  let item = $state<Item | null>(null)
  let comments = $state<Comment[]>([])
  let history = $state<Change[]>([])
  let error = $state('')
  let notFound = $state(false)

  // Drafts for the free-text fields; saved when you leave the field (or press Save).
  let title = $state('')
  let body = $state('')
  let labels = $state('')
  let newComment = $state('')

  async function load() {
    try {
      const [i, c, h] = await Promise.all([api.getItem(ref), api.listComments(ref), api.getHistory(ref)])
      item = i
      comments = c
      history = h
      title = i.title
      body = i.body
      labels = i.labels.join(', ')
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) notFound = true
      else error = errorText(e)
    }
  }
  load()

  async function save(fields: ItemUpdate) {
    if (!item) return
    try {
      item = await api.updateItem(item.id, fields)
      history = await api.getHistory(item.id)
      error = ''
    } catch (e) {
      error = errorText(e)
    }
  }

  function saveTitle() {
    if (!item) return
    const t = title.trim()
    if (!t) title = item.title // can't be empty; put it back
    else if (t !== item.title) save({ title: t })
  }

  function saveLabels() {
    if (!item) return
    const next = parseLabels(labels)
    labels = next.join(', ')
    if (next.join() !== item.labels.join()) save({ labels: next })
  }

  async function addComment(e: SubmitEvent) {
    e.preventDefault()
    if (!item || !newComment.trim()) return
    try {
      const c = await api.addComment(item.id, newComment.trim())
      comments = [...comments, c]
      newComment = ''
    } catch (err) {
      error = errorText(err)
    }
  }

  async function remove() {
    if (!item || !confirm(`Delete ${item.key ?? 'this ticket'}?`)) return
    try {
      await api.deleteItem(item.id)
      location.hash = '#/'
    } catch (e) {
      error = errorText(e)
    }
  }

  // History: every field edit is one change. Changes made together (same time,
  // same device) are shown as one event; the first event is the creation.
  const HIDDEN_FIELDS = new Set(['type', 'project_id', 'number'])
  const FIELD_NAMES: Record<string, string> = { due: 'due date', body: 'description' }

  function describe(c: Change): string {
    const name = FIELD_NAMES[c.field] ?? c.field
    const v = c.value
    if (c.field === 'status') return `${name} → ${STATUS_LABELS[v as Status]}`
    if (c.field === 'priority') return `${name} → ${PRIORITY_LABELS[v as Priority]}`
    if (c.field === 'due') return v ? `${name} → ${formatDue(v as string)}` : `cleared ${name}`
    if (c.field === 'labels') return `${name} → ${(v as string[]).join(', ') || 'none'}`
    if (c.field === 'body') return `edited ${name}`
    if (c.field === 'deleted') return v ? 'deleted' : 'restored'
    return `${name} → “${v}”`
  }

  const events = $derived.by(() => {
    const groups: { ts: number; device: string; changes: Change[] }[] = []
    for (const c of history) {
      const last = groups.at(-1)
      if (last && last.ts === c.ts && last.device === c.device_id) last.changes.push(c)
      else groups.push({ ts: c.ts, device: c.device_id, changes: [c] })
    }
    return groups
      .map((g, i) => ({
        ...g,
        text: i === 0 ? 'created' : g.changes.filter((c) => !HIDDEN_FIELDS.has(c.field)).map(describe).join(', '),
      }))
      .filter((g) => g.text)
      .reverse()
  })
</script>

<a href="#/" class="back">← All tickets</a>

{#if notFound}
  <p class="empty">Ticket {ref} doesn't exist (or was deleted).</p>
{:else if item}
  <article class="detail">
    <div class="detail-head">
      <span class="key">{item.key ?? '…'}</span>
      <input
        class="title-input"
        bind:value={title}
        onblur={saveTitle}
        onkeydown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
        aria-label="Title"
      />
    </div>

    <div class="fields">
      <label>
        Status
        <select value={item.status} onchange={(e) => save({ status: e.currentTarget.value as Status })}>
          {#each STATUSES as s (s)}<option value={s}>{STATUS_LABELS[s]}</option>{/each}
        </select>
      </label>
      <label>
        Priority
        <select value={item.priority} onchange={(e) => save({ priority: e.currentTarget.value as Priority })}>
          {#each PRIORITIES as p (p)}<option value={p}>{PRIORITY_LABELS[p]}</option>{/each}
        </select>
      </label>
      <label>
        Due
        <input
          type="date"
          value={item.due ?? ''}
          onchange={(e) => save({ due: e.currentTarget.value || null })}
          class={item.due ? dueTone(item.due, item.status) : ''}
        />
      </label>
      <label class="grow">
        Labels
        <input bind:value={labels} onblur={saveLabels} placeholder="comma separated" />
      </label>
    </div>

    <label>
      Description
      <textarea bind:value={body} rows="8" placeholder="Notes, links, checklists… (Markdown)"></textarea>
    </label>
    {#if body !== item.body}
      <div class="actions">
        <button onclick={() => item && (body = item.body)}>Discard</button>
        <button class="primary" onclick={() => save({ body })}>Save description</button>
      </div>
    {/if}

    {#if error}<p class="error">{error}</p>{/if}

    <h3>Comments</h3>
    {#each comments as c (c.id)}
      <div class="comment">
        <p>{c.body}</p>
        <time title={exactTime(c.created_at)}>{ago(c.created_at)}</time>
      </div>
    {:else}
      <p class="hint">No comments yet.</p>
    {/each}
    <form class="comment-form" onsubmit={addComment}>
      <input bind:value={newComment} placeholder="Add a comment…" aria-label="New comment" />
      <button type="submit" disabled={!newComment.trim()}>Comment</button>
    </form>

    <h3>History</h3>
    <ul class="history">
      {#each events as ev (ev.ts + ev.device)}
        <li>
          <span>{ev.text}</span>
          <time title={exactTime(ev.ts)}>{ago(ev.ts)} · {ev.device}</time>
        </li>
      {/each}
    </ul>

    <div class="danger-zone">
      <button class="danger" onclick={remove}>Delete ticket</button>
    </div>
  </article>
{:else if error}
  <p class="error">{error}</p>
{/if}
