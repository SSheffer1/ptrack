<script lang="ts">
  import Agenda from './Agenda.svelte'
  import CalendarMonth from './CalendarMonth.svelte'
  import TicketDetail from './TicketDetail.svelte'
  import TicketList from './TicketList.svelte'
  import { loadProjects } from './lib/state.svelte'

  // Routing via the part of the URL after '#':
  //   #/              → ticket list
  //   #/calendar      → month calendar
  //   #/agenda        → upcoming due dates by day
  //   #/items/HOME-12 → ticket detail
  // Hash URLs work from any static file server and inside the Android app,
  // with no server-side routing needed.
  let hash = $state(location.hash)
  const ref = $derived(hash.startsWith('#/items/') ? decodeURIComponent(hash.slice('#/items/'.length)) : null)
  const view = $derived(ref ? 'detail' : hash === '#/calendar' ? 'calendar' : hash === '#/agenda' ? 'agenda' : 'list')

  loadProjects()
</script>

<svelte:window onhashchange={() => (hash = location.hash)} />

<header class="topbar">
  <a href="#/" class="brand">ptrack</a>
  <nav>
    <a href="#/" class:active={view === 'list'}>List</a>
    <a href="#/calendar" class:active={view === 'calendar'}>Calendar</a>
    <a href="#/agenda" class:active={view === 'agenda'}>Agenda</a>
  </nav>
</header>

<main>
  {#if ref}
    {#key ref}
      <TicketDetail {ref} />
    {/key}
  {:else if view === 'calendar'}
    <CalendarMonth />
  {:else if view === 'agenda'}
    <Agenda />
  {:else}
    <TicketList />
  {/if}
</main>
