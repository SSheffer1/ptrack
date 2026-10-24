<script lang="ts">
  import Agenda from './Agenda.svelte'
  import CalendarMonth from './CalendarMonth.svelte'
  import Settings from './Settings.svelte'
  import SyncBadge from './SyncBadge.svelte'
  import TicketDetail from './TicketDetail.svelte'
  import TicketList from './TicketList.svelte'
  import { init, runtime } from './lib/runtime.svelte'
  import { loadProjects } from './lib/state.svelte'

  // Routing via the part of the URL after '#':
  //   #/              → ticket list
  //   #/calendar      → month calendar
  //   #/agenda        → upcoming due dates by day
  //   #/settings      → sync settings
  //   #/items/HOME-12 → ticket detail
  // Hash URLs work from any static file server and inside the Android app,
  // with no server-side routing needed.
  let hash = $state(location.hash)
  const ref = $derived(hash.startsWith('#/items/') ? decodeURIComponent(hash.slice('#/items/'.length)) : null)
  const view = $derived(
    ref
      ? 'detail'
      : ({ '#/calendar': 'calendar', '#/agenda': 'agenda', '#/settings': 'settings' }[hash] ?? 'list'),
  )

  init()

  // Reload projects at start and whenever a sync brings in changes.
  $effect(() => {
    if (runtime.ready) {
      void runtime.dataVersion
      loadProjects()
    }
  })
</script>

<svelte:window onhashchange={() => (hash = location.hash)} />

<header class="topbar">
  <a href="#/" class="brand">ptrack</a>
  <nav>
    <a href="#/" class:active={view === 'list'}>List</a>
    <a href="#/calendar" class:active={view === 'calendar'}>Calendar</a>
    <a href="#/agenda" class:active={view === 'agenda'}>Agenda</a>
  </nav>
  <div class="spacer"></div>
  <a href="#/settings" class="settings-link" class:active={view === 'settings'} aria-label="Settings">
    <SyncBadge />
  </a>
</header>

<main>
  {#if !runtime.ready}
    <p class="empty">Loading…</p>
  {:else if ref}
    {#key ref}
      <TicketDetail {ref} />
    {/key}
  {:else if view === 'calendar'}
    <CalendarMonth />
  {:else if view === 'agenda'}
    <Agenda />
  {:else if view === 'settings'}
    <Settings />
  {:else}
    <TicketList />
  {/if}
</main>
