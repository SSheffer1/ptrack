<script lang="ts">
  import NewProject from './NewProject.svelte'
  import { api, errorText, type Member, type Project } from './lib/api'
  import { runtime } from './lib/runtime.svelte'
  import { addProject, loadProjects, projects } from './lib/state.svelte'

  // One project open at a time, to see and manage who's in it.
  let openKey = $state<string | null>(null)
  let members = $state<Member[]>([])
  let newName = $state('')
  let addUsername = $state('')
  let error = $state('')
  let adding = $state(false)

  const open = $derived(projects.list.find((p) => p.key === openKey) ?? null)
  const owner = $derived(open?.role === 'owner')

  async function show(p: Project) {
    openKey = openKey === p.key ? null : p.key
    error = ''
    addUsername = ''
    newName = p.name
    if (openKey) members = await api.listMembers(p.key).catch(() => [])
  }

  async function run(action: () => Promise<unknown>) {
    error = ''
    try {
      await action()
      await loadProjects()
      if (open) members = await api.listMembers(open.key).catch(() => [])
    } catch (e) {
      error = errorText(e)
    }
  }

  const rename = (e: SubmitEvent) => {
    e.preventDefault()
    run(() => api.updateProject(open!.key, { name: newName.trim() }))
  }

  const share = (e: SubmitEvent) => {
    e.preventDefault()
    run(async () => {
      members = await api.addMember(open!.key, addUsername.trim())
      addUsername = ''
    })
  }

  function remove(m: Member) {
    const leaving = m.user_id === runtime.me?.id
    const question = leaving
      ? `Leave ${open!.key}? You'll lose access to its tickets.`
      : `Remove ${m.display_name} from ${open!.key}? Their tickets there become unassigned.`
    if (!confirm(question)) return
    run(async () => {
      await api.removeMember(open!.key, m.user_id)
      if (leaving) openKey = null
    })
  }

  function del() {
    if (!confirm(`Delete project ${open!.key} and all its tickets for everyone in it?`)) return
    run(async () => {
      await api.deleteProject(open!.key)
      openKey = null
    })
  }
</script>

<section class="toolbar">
  <h2>Projects</h2>
  <div class="spacer"></div>
  <button class="primary" onclick={() => (adding = true)}>+ Project</button>
</section>

{#if adding}
  <NewProject
    oncancel={() => (adding = false)}
    oncreated={(p) => {
      addProject(p)
      adding = false
    }}
  />
{/if}

{#if projects.list.length === 0}
  <p class="empty">No projects yet.</p>
{/if}

<ul class="tickets">
  {#each projects.list as p (p.id)}
    <li>
      <button class="ticket project-row" onclick={() => show(p)}>
        <span class="key">{p.key}</span>
        <span class="title">{p.name}</span>
        <span class="role">{p.role === 'owner' ? 'Owner' : 'Editor'}</span>
      </button>

      {#if openKey === p.key}
        <div class="panel project-panel">
          {#if owner}
            <form class="inline-form" onsubmit={rename}>
              <label>
                Name
                <input bind:value={newName} required />
              </label>
              <button type="submit" disabled={!newName.trim() || newName.trim() === p.name}>Rename</button>
            </form>
          {/if}

          <h3>People</h3>
          <ul class="people">
            {#each members as m (m.user_id)}
              <li>
                <span class="grow">{m.display_name} <span class="hint">@{m.username}</span></span>
                <span class="role">{m.role === 'owner' ? 'Owner' : 'Editor'}</span>
                {#if m.user_id === runtime.me?.id && m.role !== 'owner'}
                  <button onclick={() => remove(m)}>Leave</button>
                {:else if owner && m.role !== 'owner'}
                  <button onclick={() => remove(m)}>Remove</button>
                {/if}
              </li>
            {/each}
          </ul>

          {#if owner}
            <form class="inline-form" onsubmit={share}>
              <label>
                Share with <span class="hint">(their username; they become an editor)</span>
                <input bind:value={addUsername} placeholder="username" autocapitalize="off" required />
              </label>
              <button type="submit" class="primary" disabled={!addUsername.trim()}>Add</button>
            </form>
            <p class="hint">Editors can create, edit and comment on tickets. Only you can rename or delete the project,
              delete tickets, and manage people.</p>
          {/if}

          {#if error}<p class="error">{error}</p>{/if}

          {#if owner}
            <div class="danger-zone">
              <button class="danger" onclick={del}>Delete project</button>
            </div>
          {/if}
        </div>
      {/if}
    </li>
  {/each}
</ul>
