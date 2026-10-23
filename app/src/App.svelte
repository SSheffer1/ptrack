<script lang="ts">
  import TicketDetail from './TicketDetail.svelte'
  import TicketList from './TicketList.svelte'

  // Routing via the part of the URL after '#':
  //   #/              → ticket list
  //   #/items/HOME-12 → ticket detail
  // Hash URLs work from any static file server and inside the Android app,
  // with no server-side routing needed.
  let hash = $state(location.hash)
  const ref = $derived(hash.startsWith('#/items/') ? decodeURIComponent(hash.slice('#/items/'.length)) : null)
</script>

<svelte:window onhashchange={() => (hash = location.hash)} />

<header class="topbar">
  <a href="#/" class="brand">ptrack</a>
</header>

<main>
  {#if ref}
    {#key ref}
      <TicketDetail {ref} />
    {/key}
  {:else}
    <TicketList />
  {/if}
</main>
