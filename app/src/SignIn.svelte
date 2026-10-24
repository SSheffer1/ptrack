<script lang="ts">
  import { errorText } from './lib/api'
  import { runtime, signIn } from './lib/runtime.svelte'

  let server = $state(runtime.serverUrl)
  let username = $state('')
  let password = $state('')
  let error = $state('')
  let busy = $state(false)

  async function submit(e: SubmitEvent) {
    e.preventDefault()
    busy = true
    error = ''
    try {
      await signIn(username, password, server)
    } catch (err) {
      error = errorText(err)
    } finally {
      busy = false
    }
  }
</script>

<form class="panel sign-in" onsubmit={submit}>
  <h2>Sign in to ptrack</h2>
  {#if runtime.native}
    <label>
      Server address
      <input bind:value={server} placeholder="http://192.168.1.20:8000" inputmode="url" autocapitalize="off" required />
    </label>
  {/if}
  <label>
    Username
    <input bind:value={username} autocomplete="username" autocapitalize="off" required />
  </label>
  <label>
    Password
    <input type="password" bind:value={password} autocomplete="current-password" required />
  </label>
  {#if error}<p class="error">{error}</p>{/if}
  <div class="actions">
    <button type="submit" class="primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
  </div>
  <p class="hint">No account? Ask whoever runs your ptrack server to create one.</p>
</form>
