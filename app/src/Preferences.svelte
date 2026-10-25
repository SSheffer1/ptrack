<script lang="ts">
  import { errorText, SORT_LABELS, STATUS_LABELS, STATUSES, type SortOrder, type Status } from './lib/api'
  import { formatTime } from './lib/format'
  import { ownPrefs, type Prefs, prefs } from './lib/prefs.svelte'
  import { describeOffset, normalizeReminders, reminderChoices } from './lib/reminders'
  import { savePrefs } from './lib/state.svelte'

  // Each preference saves as soon as it changes, and syncs to your other devices.
  let error = $state('')

  async function set(name: keyof Prefs, value: unknown) {
    error = ''
    try {
      await savePrefs({ [name]: value })
    } catch (e) {
      error = errorText(e)
    }
  }

  const isOwn = (name: keyof Prefs) => name in ownPrefs.values

  function toggleIn<T>(list: T[], value: T): T[] {
    return list.includes(value) ? list.filter((x) => x !== value) : [...list, value]
  }

  const hours = Array.from({ length: 24 }, (_, h) => h)
  const hourLabel = (h: number) => formatTime(`${String(h).padStart(2, '0')}:00`)
</script>

{#snippet reset(name: keyof Prefs)}
  {#if isOwn(name)}
    <button type="button" class="link" onclick={() => set(name, null)}>reset</button>
  {:else}
    <span class="hint">default</span>
  {/if}
{/snippet}

<div class="panel prefs">
  {#each [true, false] as timed (timed)}
    {@const name = timed ? 'reminders_timed' : 'reminders_untimed'}
    <div class="field">
      <span>Default reminders, tickets {timed ? 'with' : 'without'} a time {@render reset(name)}</span>
      <div class="chips">
        {#each normalizeReminders([...reminderChoices(timed), ...prefs[name]])! as offset (offset)}
          <button
            type="button"
            class="chip"
            class:on={prefs[name].includes(offset)}
            onclick={() => set(name, normalizeReminders(toggleIn(prefs[name], offset)))}
          >
            {describeOffset(offset, timed)}
          </button>
        {/each}
      </div>
    </div>
  {/each}

  <div class="row">
    <label>
      <span>Untimed tickets are due at {@render reset('untimed_hour')}</span>
      <select value={prefs.untimed_hour} onchange={(e) => set('untimed_hour', Number(e.currentTarget.value))}>
        {#each hours as h (h)}<option value={h}>{hourLabel(h)}</option>{/each}
      </select>
    </label>
    <label>
      <span>Weeks start on {@render reset('week_start')}</span>
      <select value={prefs.week_start} onchange={(e) => set('week_start', e.currentTarget.value)}>
        <option value="sunday">Sunday</option>
        <option value="monday">Monday</option>
      </select>
    </label>
    <label>
      <span>Due dates turn orange {@render reset('soon_days')}</span>
      <select value={prefs.soon_days} onchange={(e) => set('soon_days', Number(e.currentTarget.value))}>
        {#each [0, 1, 2, 3, 5, 7, 14] as d (d)}
          <option value={d}>{d === 0 ? 'only on the day' : `${d} day${d === 1 ? '' : 's'} ahead`}</option>
        {/each}
      </select>
    </label>
  </div>

  <label>
    <span>Sync in the background {@render reset('sync_minutes')}</span>
    <select value={prefs.sync_minutes} onchange={(e) => set('sync_minutes', Number(e.currentTarget.value))}>
      {#each [1, 5, 15, 30, 60] as m (m)}
        <option value={m}>every {m === 60 ? 'hour' : m === 1 ? 'minute' : `${m} minutes`}</option>
      {/each}
      <option value={0}>never (only after edits, on opening the app, and with Sync now)</option>
    </select>
  </label>

  <div class="field">
    <span>Statuses shown when the app opens {@render reset('default_statuses')}</span>
    <div class="chips">
      {#each STATUSES as s (s)}
        <button
          type="button"
          class="chip status-{s}"
          class:on={prefs.default_statuses.includes(s)}
          onclick={() => set('default_statuses', STATUSES.filter((x) => toggleIn<Status>(prefs.default_statuses, s).includes(x)))}
        >
          {STATUS_LABELS[s]}
        </button>
      {/each}
    </div>
  </div>

  <label>
    <span>List sorted by {@render reset('default_sort')}</span>
    <select value={prefs.default_sort} onchange={(e) => set('default_sort', e.currentTarget.value as SortOrder)}>
      {#each Object.entries(SORT_LABELS) as [value, label] (value)}<option {value}>{label}</option>{/each}
    </select>
  </label>

  {#if error}<p class="error">{error}</p>{/if}
  <p class="hint">
    Saved as you change them, and synced to your other devices. Default reminders apply to every ticket whose reminders
    you haven't picked yourself.
  </p>
</div>
