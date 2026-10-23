<script lang="ts">
  import { api, errorText, type Project } from './lib/api'

  let { oncreated, oncancel }: { oncreated: (p: Project) => void; oncancel: () => void } = $props()

  let key = $state('')
  let name = $state('')
  let error = $state('')

  async function submit(e: SubmitEvent) {
    e.preventDefault()
    try {
      oncreated(await api.createProject(key, name))
    } catch (err) {
      error = errorText(err)
    }
  }
</script>

<form class="panel" onsubmit={submit}>
  <h2>New project</h2>
  <div class="row">
    <label>
      Key
      <input
        bind:value={() => key, (v) => (key = v.toUpperCase().replace(/[^A-Z0-9]/g, ''))}
        placeholder="SCHOOL"
        maxlength="10"
        required
      />
    </label>
    <label class="grow">
      Name
      <input bind:value={name} placeholder="School" required />
    </label>
  </div>
  <p class="hint">The key prefixes ticket numbers: {key || 'KEY'}-1, {key || 'KEY'}-2, …</p>
  {#if error}<p class="error">{error}</p>{/if}
  <div class="actions">
    <button type="button" onclick={oncancel}>Cancel</button>
    <button type="submit" class="primary">Create project</button>
  </div>
</form>
