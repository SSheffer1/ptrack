// Decides where the app's data lives and wires it up.
//
// - Online mode (desktop browser): every call goes to the server (http.ts).
// - Offline-first mode (the Android app, or a browser with it switched on in
//   Settings for testing): calls go to the on-device store (local/), and the
//   sync engine trades changes with the server in the background.

import { App as CapApp } from '@capacitor/app'
import { Capacitor } from '@capacitor/core'
import { httpBackend } from './http'
import { LocalBackend } from './local/backend'
import { loadState, saveState } from './local/persist'
import { LocalStore } from './local/store'
import { fetchTransport, initialStatus, SyncEngine } from './local/sync'
import { openTicketOnTap, scheduleReminders } from './notify'
import type { Backend } from './types'

const LOCAL_FLAG = 'ptrack.offlineMode' // browser-only testing switch, kept in localStorage
const SYNC_EVERY_MS = 30_000
const SYNC_AFTER_EDIT_MS = 1_000
const SAVE_AFTER_EDIT_MS = 300
const RESCHEDULE_AFTER_MS = 2_000

function browserFlag(): boolean {
  try {
    return localStorage.getItem(LOCAL_FLAG) === '1'
  } catch {
    return false
  }
}

export const runtime = $state({
  native: Capacitor.isNativePlatform(),
  local: Capacitor.isNativePlatform() || browserFlag(),
  ready: false,
  dataVersion: 0, // bumped whenever data changes outside the current view (e.g. a sync); views re-fetch
  deviceId: '',
  serverUrl: '',
  sync: initialStatus(),
})

const store = new LocalStore()
let engine: SyncEngine | null = null
let saveTimer: ReturnType<typeof setTimeout> | undefined
let syncTimer: ReturnType<typeof setTimeout> | undefined
let reminderTimer: ReturnType<typeof setTimeout> | undefined

// Phone only: re-plan notifications shortly after the data changes.
function scheduleReminderUpdate() {
  if (!runtime.native) return
  clearTimeout(reminderTimer)
  reminderTimer = setTimeout(async () => {
    try {
      await scheduleReminders(await localBackend.listItems())
    } catch (e) {
      console.error('scheduling reminders failed', e)
    }
  }, RESCHEDULE_AFTER_MS)
}

function scheduleSave() {
  clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    if (!engine) return
    const { deviceId, serverUrl, cursor } = engine.settings
    saveState({ version: 1, deviceId, serverUrl, cursor, log: store.entries() }).catch((e) => {
      runtime.sync.error = `Couldn't save: ${e}`
    })
  }, SAVE_AFTER_EDIT_MS)
}

const localBackend = new LocalBackend(
  store,
  () => runtime.deviceId,
  () => {
    engine?.noteLocalChange()
    scheduleSave()
    scheduleReminderUpdate()
    clearTimeout(syncTimer)
    syncTimer = setTimeout(syncNow, SYNC_AFTER_EDIT_MS)
  },
)

export const api: Backend = runtime.local ? localBackend : httpBackend

/** Load saved data and start syncing. Call once before showing data. */
export async function init() {
  if (runtime.local) {
    const saved = await loadState()
    store.load(saved?.log ?? [])
    runtime.deviceId = saved?.deviceId ?? `${runtime.native ? 'android' : 'browser'}-${crypto.randomUUID()}`
    // In a browser the page's own server is the default; the phone has to be told.
    runtime.serverUrl = saved?.serverUrl ?? ''
    engine = new SyncEngine(
      store,
      { deviceId: runtime.deviceId, serverUrl: runtime.serverUrl, cursor: saved?.cursor ?? 0 },
      fetchTransport,
      (dataChanged) => {
        scheduleSave()
        if (dataChanged) {
          runtime.dataVersion++
          scheduleReminderUpdate()
        }
      },
      runtime.sync,
    )
    if (!saved) scheduleSave()
    syncNow()
    setInterval(syncNow, SYNC_EVERY_MS)
    if (runtime.native) {
      CapApp.addListener('resume', syncNow)
      openTicketOnTap()
      scheduleReminderUpdate()
    }
  }
  runtime.ready = true
}

export function syncNow() {
  if (!engine || (runtime.native && !runtime.serverUrl)) return
  engine.sync()
}

export function setServerUrl(url: string) {
  url = url.trim().replace(/\/$/, '')
  // "192.168.1.20:8000" → "http://192.168.1.20:8000"
  if (url && !/^https?:\/\//i.test(url)) url = `http://${url}`
  runtime.serverUrl = url
  if (engine) {
    engine.settings.serverUrl = runtime.serverUrl
    runtime.sync.rejected = false
    runtime.sync.error = ''
    scheduleSave()
    syncNow()
  }
}

export function discardPending() {
  engine?.discardPending()
}

/** Browser only: switch between online and offline-first mode (reloads the page). */
export function setBrowserOfflineMode(on: boolean) {
  try {
    if (on) localStorage.setItem(LOCAL_FLAG, '1')
    else localStorage.removeItem(LOCAL_FLAG)
  } catch {
    // storage blocked; nothing to switch
  }
  location.reload()
}
