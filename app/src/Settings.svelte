<script lang="ts">
  import { ago, exactTime } from './lib/format'
  import { discardPending, runtime, setBrowserOfflineMode, setServerUrl, syncNow } from './lib/runtime.svelte'

  let url = $state(runtime.serverUrl)

  function saveUrl(e: SubmitEvent) {
    e.preventDefault()
    setServerUrl(url)
    url = runtime.serverUrl // show it as saved, e.g. with http:// added
  }

  function discard() {
    const n = runtime.sync.pending
    if (confirm(`Throw away ${n} unsynced change${n === 1 ? '' : 's'} made on this device? This can't be undone.`)) {
      discardPending()
    }
  }
</script>

<h2>Sync</h2>

{#if runtime.local}
  <form class="panel" onsubmit={saveUrl}>
    <label>
      Server address
      <input bind:value={url} placeholder={runtime.native ? 'http://192.168.1.20:8000' : 'this site'} inputmode="url" />
    </label>
    <p class="hint">
      {#if runtime.native}
        The computer running the ptrack server, e.g. http://192.168.1.20:8000. The phone works offline either way and
        catches up when it can reach it.
      {:else}
        Leave empty to sync with the server this page came from.
      {/if}
    </p>
    <div class="actions">
      <button type="submit" class="primary" disabled={url.trim().replace(/\/$/, '') === runtime.serverUrl}>Save</button>
    </div>
  </form>

  <div class="panel">
    <dl class="facts">
      <dt>Status</dt>
      <dd>
        {#if runtime.sync.syncing}Syncing…{:else if runtime.sync.error}<span class="error">{runtime.sync.error}</span
          >{:else}OK{/if}
      </dd>
      <dt>Last sync</dt>
      <dd>
        {#if runtime.sync.lastSync}
          <time title={exactTime(runtime.sync.lastSync)}>{ago(runtime.sync.lastSync)}</time>
        {:else}never{/if}
      </dd>
      <dt>Unsynced changes</dt>
      <dd>{runtime.sync.pending}</dd>
      <dt>This device</dt>
      <dd class="mono">{runtime.deviceId}</dd>
    </dl>
    <div class="actions">
      {#if runtime.sync.rejected}
        <button class="danger" onclick={discard}>Discard unsynced changes</button>
      {/if}
      <button onclick={syncNow} disabled={runtime.sync.syncing}>Sync now</button>
    </div>
    {#if runtime.sync.rejected}
      <p class="hint">
        The server refused this device's unsynced changes, so syncing is paused. Discarding them lets it continue; this
        device then matches the server again.
      </p>
    {/if}
  </div>
{:else}
  <p class="panel">This browser talks to the server directly, so there's nothing to sync.</p>
{/if}

{#if !runtime.native}
  <h3>Testing</h3>
  <div class="panel">
    <p class="hint">
      Offline-first mode makes this browser work like the phone app: it keeps its own copy of the data and syncs in the
      background. Useful for testing without a phone.
    </p>
    <div class="actions">
      <button onclick={() => setBrowserOfflineMode(!runtime.local)}>
        {runtime.local ? 'Switch back to online mode' : 'Use offline-first mode in this browser'}
      </button>
    </div>
  </div>
{/if}
