<script lang="ts">
  import Agenda from './Agenda.svelte'
  import CalendarMonth from './CalendarMonth.svelte'
  import Projects from './Projects.svelte'
  import Settings from './Settings.svelte'
  import SignIn from './SignIn.svelte'
  import SyncBadge from './SyncBadge.svelte'
  import TicketDetail from './TicketDetail.svelte'
  import TicketList from './TicketList.svelte'
  import { init, refreshNow, runtime } from './lib/runtime.svelte'
  import { loadPrefs, loadProjects, loadUsers } from './lib/state.svelte'

  // Routing via the part of the URL after '#':
  //   #/              → ticket list
  //   #/calendar      → month calendar
  //   #/agenda        → upcoming due dates by day
  //   #/projects      → projects and who they're shared with
  //   #/settings      → account, sync, family accounts
  //   #/items/HOME-12 → ticket detail
  // Hash URLs work from any static file server and inside the Android app,
  // with no server-side routing needed.
  let hash = $state(location.hash)
  const ref = $derived(hash.startsWith('#/items/') ? decodeURIComponent(hash.slice('#/items/'.length)) : null)
  const view = $derived(
    ref
      ? 'detail'
      : ({ '#/calendar': 'calendar', '#/agenda': 'agenda', '#/projects': 'projects', '#/settings': 'settings' }[hash] ??
        'list'),
  )

  init()

  // Reload projects (and people's names) at start, after signing in, and whenever a sync brings in changes.
  $effect(() => {
    if (runtime.ready && runtime.me) {
      void runtime.dataVersion
      loadProjects()
      loadUsers()
      loadPrefs()
    }
  })
</script>

<svelte:window onhashchange={() => (hash = location.hash)} />

<!-- Two rows: the ribbon (name, sync, settings), then the tabs. -->
<header class="topbar">
  <div class="ribbon">
    <a href="#/" class="brand">PTrack</a>
    <div class="spacer"></div>
    {#if runtime.me}
      <SyncBadge />
      <button onclick={refreshNow} disabled={runtime.sync.syncing} title="Sync with the server now">
        <span class:spinning={runtime.sync.syncing}>↻</span> Sync now
      </button>
      <a href="#/settings" class="button gear" class:active={view === 'settings'} aria-label="Settings" title="Settings"
        >⚙&#xFE0E;</a
      >
    {/if}
  </div>
  {#if runtime.me}
    <nav class="tabs">
      <a href="#/" class:active={view === 'list'}>List</a>
      <a href="#/calendar" class:active={view === 'calendar'}>Calendar</a>
      <a href="#/agenda" class:active={view === 'agenda'}>Agenda</a>
      <a href="#/projects" class:active={view === 'projects'}>Projects</a>
    </nav>
  {/if}
</header>

<main>
  {#if !runtime.ready}
    <p class="empty">Loading…</p>
  {:else if !runtime.me}
    <SignIn />
  {:else if ref}
    {#key ref}
      <TicketDetail {ref} />
    {/key}
  {:else if view === 'calendar'}
    <CalendarMonth />
  {:else if view === 'agenda'}
    <Agenda />
  {:else if view === 'projects'}
    <Projects />
  {:else if view === 'settings'}
    <Settings />
  {:else}
    <TicketList />
  {/if}
</main>
