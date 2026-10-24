<script lang="ts">
  import Preferences from './Preferences.svelte'
  import { account, type AdminUser, type Device } from './lib/account'
  import { errorText } from './lib/api'
  import { ago, exactTime } from './lib/format'
  import { discardPending, runtime, setBrowserOfflineMode, signOut, syncNow } from './lib/runtime.svelte'

  let devices = $state<Device[]>([])
  let family = $state<AdminUser[]>([])
  let error = $state('')
  let notice = $state('')

  // Change password
  let currentPw = $state('')
  let newPw = $state('')

  // New family account
  let newUser = $state({ username: '', display_name: '', password: '' })

  async function refresh() {
    devices = await account.devices().catch(() => [])
    if (runtime.me?.is_admin) family = await account.listUsers().catch(() => [])
  }
  refresh()

  async function run(action: () => Promise<unknown>, done = '') {
    error = notice = ''
    try {
      await action()
      notice = done
      await refresh()
    } catch (e) {
      error = errorText(e)
    }
  }

  function changePassword(e: SubmitEvent) {
    e.preventDefault()
    run(async () => {
      await account.changePassword(currentPw, newPw)
      currentPw = newPw = ''
    }, 'Password changed.')
  }

  function addFamily(e: SubmitEvent) {
    e.preventDefault()
    run(async () => {
      await account.createUser({ ...newUser, username: newUser.username.trim().toLowerCase() })
      newUser = { username: '', display_name: '', password: '' }
    }, 'Account created. Give them their username and password; they can change the password in Settings.')
  }

  function resetPassword(u: AdminUser) {
    const password = prompt(`New password for ${u.display_name} (at least 8 characters):`)
    if (password) run(() => account.updateUser(u.id, { password }), `Password reset for ${u.display_name}.`)
  }

  function toggleDisabled(u: AdminUser) {
    if (!u.disabled && !confirm(`Disable ${u.display_name}? They're signed out everywhere until you enable them again.`)) return
    run(() => account.updateUser(u.id, { disabled: !u.disabled }))
  }

  function confirmSignOut() {
    const n = runtime.sync.pending
    const lost = n ? `\n\n${n} change${n === 1 ? '' : 's'} on this device haven't synced yet and will be lost.` : ''
    if (confirm(`Sign out on this device? Its copy of your tickets is removed.${lost}`)) signOut()
  }

  function discard() {
    const n = runtime.sync.pending
    if (confirm(`Throw away ${n} unsynced change${n === 1 ? '' : 's'} made on this device? This can't be undone.`)) {
      discardPending()
    }
  }
</script>

<h2>Settings</h2>
{#if error}<p class="error">{error}</p>{/if}
{#if notice}<p class="notice">{notice}</p>{/if}

<h3>Account</h3>
<div class="panel">
  <p>Signed in as <strong>{runtime.me?.display_name}</strong> <span class="hint">@{runtime.me?.username}</span></p>
  <form class="inline-form" onsubmit={changePassword}>
    <label>
      Current password
      <input type="password" bind:value={currentPw} autocomplete="current-password" required />
    </label>
    <label>
      New password <span class="hint">(8+ characters)</span>
      <input type="password" bind:value={newPw} autocomplete="new-password" minlength="8" required />
    </label>
    <button type="submit">Change password</button>
  </form>

  <h3>Signed-in devices</h3>
  <ul class="people">
    {#each devices as d (d.id)}
      <li>
        <span class="grow">{d.name}{#if d.current} <span class="hint">(this device)</span>{/if}</span>
        <time class="hint" title={exactTime(d.last_used_at)}>used {ago(d.last_used_at)}</time>
        {#if !d.current}
          <button onclick={() => run(() => account.signOutDevice(d.id), `Signed out ${d.name}.`)}>Sign out</button>
        {/if}
      </li>
    {/each}
  </ul>
  <p class="hint">Lost a phone? Sign it out here; it forgets its copy of your tickets the next time it connects.</p>
  <div class="actions">
    <button class="danger" onclick={confirmSignOut}>Sign out on this device</button>
  </div>
</div>

<h3>Preferences</h3>
<Preferences />

{#if runtime.local}
  <h3>Sync</h3>
  <div class="panel">
    <dl class="facts">
      <dt>Server</dt>
      <dd class="mono">{runtime.serverUrl || 'this site'}</dd>
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
    <p class="hint">To use a different server, sign out and sign in again with its address.</p>
  </div>
{/if}

{#if runtime.me?.is_admin}
  <h3>Family accounts</h3>
  <div class="panel">
    <ul class="people">
      {#each family as u (u.id)}
        <li>
          <span class="grow">
            {u.display_name} <span class="hint">@{u.username}</span>
            {#if u.is_admin}<span class="role">Admin</span>{/if}
            {#if u.disabled}<span class="role">Disabled</span>{/if}
          </span>
          <button onclick={() => resetPassword(u)}>Reset password</button>
          {#if u.id !== runtime.me?.id}
            <button onclick={() => toggleDisabled(u)}>{u.disabled ? 'Enable' : 'Disable'}</button>
          {/if}
        </li>
      {/each}
    </ul>
    <form class="inline-form" onsubmit={addFamily}>
      <label>
        Username
        <input bind:value={newUser.username} placeholder="sam" autocapitalize="off" required />
      </label>
      <label>
        Name
        <input bind:value={newUser.display_name} placeholder="Sam" />
      </label>
      <label>
        Password <span class="hint">(8+)</span>
        <input bind:value={newUser.password} minlength="8" required />
      </label>
      <button type="submit" class="primary">Add account</button>
    </form>
    <p class="hint">
      New accounts start with no projects. Share a project with them from the Projects page.
    </p>
  </div>
{/if}

{#if !runtime.native}
  <h3>Testing</h3>
  <div class="panel">
    <p class="hint">
      Offline-first mode makes this browser work like the phone app: it keeps its own copy of the data and syncs in the
      background. Useful for testing without a phone. Switching asks you to sign in again.
    </p>
    <div class="actions">
      <button onclick={() => setBrowserOfflineMode(!runtime.local)}>
        {runtime.local ? 'Switch back to online mode' : 'Use offline-first mode in this browser'}
      </button>
    </div>
  </div>
{/if}
