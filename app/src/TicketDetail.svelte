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
    type Member,
    notifiedUser,
    type Priority,
    type Status,
  } from './lib/api'
  import ReminderPicker from './ReminderPicker.svelte'
  import RepeatPicker from './RepeatPicker.svelte'
  import { ago, dueTone, exactTime, formatDue, formatTime, parseLabels, timing } from './lib/format'
  import { describeRule } from './lib/recurrence'
  import { describeOffset } from './lib/reminders'
  import { runtime } from './lib/runtime.svelte'
  import { projects, userName } from './lib/state.svelte'

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
  let members = $state<Member[]>([])

  const project = $derived(projects.list.find((p) => p.id === item?.project_id))
  const isOwner = $derived(project?.role === 'owner')
  const me = $derived(runtime.me?.id ?? '')
  const remindsMe = $derived(item ? notifiedUser(item, me) === me : false)

  async function load() {
    try {
      const [i, c, h] = await Promise.all([api.getItem(ref), api.listComments(ref), api.getHistory(ref)])
      // Take new values into the text fields, unless you're in the middle of editing one.
      if (!item || title === item.title) title = i.title
      if (!item || body === item.body) body = i.body
      if (!item || labels === item.labels.join(', ')) labels = i.labels.join(', ')
      item = i
      comments = c
      history = h
      const key = projects.list.find((p) => p.id === i.project_id)?.key
      if (key) members = await api.listMembers(key).catch(() => members)
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) notFound = true
      else error = errorText(e)
    }
  }

  // Load now, and again whenever a sync brings in changes.
  $effect(() => {
    void runtime.dataVersion
    load()
  })

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

  function saveDue(due: string) {
    // A time without a date means nothing, so clearing the date clears the time too.
    save(due ? { due } : { due: null, due_time: null })
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
  const FIELD_NAMES: Record<string, string> = {
    due: 'due date',
    due_time: 'due time',
    body: 'description',
    assigned_on: 'assigned date',
    completed_on: 'completed date',
  }

  // The server fills in the completed date whenever something is marked done;
  // "status → Done" already says that, so only hand-made changes are listed.
  function hidden(c: Change): boolean {
    return HIDDEN_FIELDS.has(c.field) || (c.field === 'completed_on' && c.device_id === 'server')
  }

  function describe(c: Change): string {
    const name = FIELD_NAMES[c.field] ?? c.field
    const v = c.value
    if (c.field === 'status') return `${name} → ${STATUS_LABELS[v as Status]}`
    if (c.field === 'priority') return `${name} → ${PRIORITY_LABELS[v as Priority]}`
    if (c.field === 'due') return v ? `${name} → ${formatDue(v as string)}` : `cleared ${name}`
    if (c.field === 'due_time') return v ? `${name} → ${formatTime(v as string)}` : `cleared ${name}`
    if (c.field === 'repeat') return v ? `repeat → ${describeRule(v as string)}` : 'stopped repeating'
    if (c.field === 'next_id') return 'created the next occurrence'
    if (c.field === 'assigned_on') return v ? `${name} → ${formatDue(v as string)}` : `${name} → created date`
    if (c.field === 'reminders') {
      const list = v as string[] | null
      if (list === null) return 'reminders → default'
      return list.length ? `reminders → ${list.map((o) => describeOffset(o, !!item?.due_time)).join(', ')}` : 'reminders → none'
    }
    if (c.field === 'assignee_id') return v ? `assigned to ${userName(v as string)}` : 'unassigned'
    if (c.field === 'completed_on') return v ? `${name} → ${formatDue(v as string)}` : `cleared ${name}`
    if (c.field === 'labels') return `${name} → ${(v as string[]).join(', ') || 'none'}`
    if (c.field === 'body') return `edited ${name}`
    if (c.field === 'deleted') return v ? 'deleted' : 'restored'
    return `${name} → “${v}”`
  }

  // "android-…" → "phone": where an edit was made, next to who made it.
  function deviceLabel(device: string): string {
    if (device === 'server') return 'automatic'
    if (device.startsWith('android-')) return 'phone'
    if (device.startsWith('browser-')) return 'browser'
    return device
  }

  const events = $derived.by(() => {
    const groups: { ts: number; device: string; user: string; changes: Change[] }[] = []
    for (const c of history) {
      const last = groups.at(-1)
      if (last && last.ts === c.ts && last.device === c.device_id) last.changes.push(c)
      else groups.push({ ts: c.ts, device: c.device_id, user: c.user_id, changes: [c] })
    }
    return groups
      .map((g, i) => ({
        ...g,
        text: i === 0 ? 'created' : g.changes.filter((c) => !hidden(c)).map(describe).join(', '),
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

    <p class="dates">
      Assigned {formatDue(item.assigned)}
      {#if item.due}· Due {formatDue(item.due)}{/if}
      {#if item.status === 'done' && item.completed_on}
        · <span class="done-text">Completed {formatDue(item.completed_on)}</span>
        {#if item.due}<span class="hint">({timing(item.due, item.completed_on)})</span>{/if}
      {/if}
    </p>

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
          onchange={(e) => saveDue(e.currentTarget.value)}
          class={item.due ? dueTone(item.due, item.status) : ''}
        />
      </label>
      <label>
        Time
        <input
          type="time"
          value={item.due_time?.slice(0, 5) ?? ''}
          onchange={(e) => save({ due_time: e.currentTarget.value || null })}
          disabled={!item.due}
        />
      </label>
      <label>
        Repeat
        <RepeatPicker value={item.repeat} onchange={(repeat) => save({ repeat })} />
      </label>
      <label class="grow">
        Labels
        <input bind:value={labels} onblur={saveLabels} placeholder="comma separated" />
      </label>
      <label>
        Assignee
        <select value={item.assignee_id ?? ''} onchange={(e) => save({ assignee_id: e.currentTarget.value || null })}>
          <option value="">Unassigned</option>
          {#each members as m (m.user_id)}
            <option value={m.user_id}>{m.user_id === me ? `${m.display_name} (you)` : m.display_name}</option>
          {/each}
        </select>
      </label>
      <label>
        Assigned
        <input
          type="date"
          value={item.assigned}
          onchange={(e) => save({ assigned_on: e.currentTarget.value || null })}
          title="Defaults to the day the ticket was created"
        />
      </label>
      {#if item.status === 'done'}
        <label>
          Completed
          <input
            type="date"
            value={item.completed_on ?? ''}
            onchange={(e) => save({ completed_on: e.currentTarget.value || null })}
          />
        </label>
      {/if}
    </div>

    {#if item.due}
      <div class="field">
        {#if remindsMe}
          <span>Remind me <span class="hint">(on the phone)</span></span>
          <ReminderPicker value={item.reminders} timed={!!item.due_time} onchange={(reminders) => save({ reminders })} />
        {:else}
          <span class="hint">Reminders for this ticket go to {userName(notifiedUser(item, me))}, who sets them.</span>
        {/if}
      </div>
    {/if}

    {#if item.next_id}
      <p class="notice">
        This repeats — the next one has been created. <a href="#/items/{item.next_id}">Go to next occurrence →</a>
      </p>
    {:else if item.repeat}
      <p class="hint">↻ {describeRule(item.repeat)}. Marking this done creates the next one.</p>
    {/if}

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
        <time title={exactTime(c.created_at)}>{c.created_by ? `${userName(c.created_by)} · ` : ''}{ago(c.created_at)}</time>
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
          <time title={exactTime(ev.ts)}>{ago(ev.ts)} · {userName(ev.user)} · {deviceLabel(ev.device)}</time>
        </li>
      {/each}
    </ul>

    {#if isOwner}
      <div class="danger-zone">
        <button class="danger" onclick={remove}>Delete ticket</button>
      </div>
    {/if}
  </article>
{:else if error}
  <p class="error">{error}</p>
{/if}
