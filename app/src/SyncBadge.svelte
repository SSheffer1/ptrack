<script lang="ts">
  import { ago } from './lib/format'
  import { runtime } from './lib/runtime.svelte'

  // Re-render every 30 s so "2 min ago" stays current.
  let now = $state(Date.now())
  $effect(() => {
    const timer = setInterval(() => (now = Date.now()), 30_000)
    return () => clearInterval(timer)
  })

  const s = $derived(runtime.sync)
  const tone = $derived(s.rejected || s.error ? 'bad' : s.pending ? 'busy' : 'ok')
  const text = $derived.by(() => {
    void now
    if (!runtime.local) return 'Online'
    if (runtime.native && !runtime.serverUrl) return 'Set up sync'
    if (s.rejected) return 'Sync blocked'
    if (s.syncing) return 'Syncing…'
    if (s.error) return s.pending ? `Offline · ${s.pending} unsynced` : 'Offline'
    if (s.pending) return `${s.pending} unsynced`
    return s.lastSync ? `Synced ${ago(s.lastSync)}` : 'Not synced yet'
  })
</script>

<span class="sync-badge {tone}" title={s.error || 'Sync settings'}>
  <span class="dot"></span><span class="badge-text">{text}</span>
</span>
