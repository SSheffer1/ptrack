// Decides where the app's data lives, who's signed in, and wires it up.
//
// - Online mode (desktop browser): every call goes to the server (http.ts).
//   The sign-in token is kept in the browser's localStorage.
// - Offline-first mode (the Android app, or a browser with it switched on in
//   Settings for testing): calls go to the on-device store (local/), and the
//   sync engine trades changes with the server in the background. The token
//   is kept with the data, in the app's private storage.
//
// Signing out (or being signed out from another device) clears this device's
// copy of the data, so a lost phone doesn't keep your tickets.

import { App as CapApp } from '@capacitor/app'
import { Capacitor } from '@capacitor/core'
import { account } from './account'
import { connection } from './connection'
import { httpBackend } from './http'
import { LocalBackend } from './local/backend'
import { loadState, saveState } from './local/persist'
import { LocalStore } from './local/store'
import { fetchTransport, initialStatus, type People, SyncEngine, type SyncSettings } from './local/sync'
import { openTicketOnTap, scheduleReminders } from './notify'
import type { Backend, User } from './types'

const LOCAL_FLAG = 'ptrack.offlineMode' // browser-only testing switch, kept in localStorage
const SESSION_KEY = 'ptrack.session' // browser online mode: { token, me }
const SYNC_EVERY_MS = 30_000
const SYNC_AFTER_EDIT_MS = 1_000
const SAVE_AFTER_EDIT_MS = 300
const RESCHEDULE_AFTER_MS = 2_000

function storageGet(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function storageSet(key: string, value: string | null) {
  try {
    if (value === null) localStorage.removeItem(key)
    else localStorage.setItem(key, value)
  } catch {
    // storage blocked; the session just won't survive a reload
  }
}

const noPeople = (): People => ({ me: null, users: [], members: [] })

export const runtime = $state({
  native: Capacitor.isNativePlatform(),
  local: Capacitor.isNativePlatform() || storageGet(LOCAL_FLAG) === '1',
  ready: false,
  me: null as User | null, // null = signed out
  people: noPeople(), // offline-first mode: who's in my projects (from the last sync)
  dataVersion: 0, // bumped whenever data changes outside the current view (e.g. a sync); views re-fetch
  deviceId: '',
  serverUrl: '',
  sync: initialStatus(),
})

const store = new LocalStore()
const settings: SyncSettings = { deviceId: '', serverUrl: '', token: '', cursor: 0, epoch: -1 }
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
      await scheduleReminders(runtime.me ? await localBackend.listItems() : [], runtime.me?.id ?? '')
    } catch (e) {
      console.error('scheduling reminders failed', e)
    }
  }, RESCHEDULE_AFTER_MS)
}

function saveNow() {
  const { deviceId, serverUrl, token, cursor, epoch } = settings
  const people = $state.snapshot(runtime.people) as People
  return saveState({ version: 2, deviceId, serverUrl, token, cursor, epoch, people, log: store.entries() }).catch(
    (e) => (runtime.sync.error = `Couldn't save: ${e}`),
  )
}

function scheduleSave() {
  clearTimeout(saveTimer)
  saveTimer = setTimeout(saveNow, SAVE_AFTER_EDIT_MS)
}

// Adding/removing members happens on the server right away; then sync to pick up the result.
const membersOnline: Pick<Backend, 'addMember' | 'removeMember'> = {
  async addMember(key, username) {
    const members = await httpBackend.addMember(key, username)
    syncNow()
    return members
  },
  async removeMember(key, userId) {
    await httpBackend.removeMember(key, userId)
    syncNow()
  },
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
  () => runtime.people,
  membersOnline,
)

export const api: Backend = runtime.local ? localBackend : httpBackend

/** Load saved data and start syncing. Call once before showing data. */
export async function init() {
  connection.onSignedOut = () => void forgetSession()
  if (runtime.local) {
    const saved = await loadState()
    store.load(saved?.log ?? [])
    Object.assign(settings, {
      deviceId: saved?.deviceId ?? `${runtime.native ? 'android' : 'browser'}-${crypto.randomUUID()}`,
      // In a browser the page's own server is the default; the phone has to be told.
      serverUrl: saved?.serverUrl ?? '',
      token: saved?.token ?? '',
      cursor: saved?.cursor ?? 0,
      epoch: saved?.epoch ?? -1,
    })
    runtime.deviceId = settings.deviceId
    runtime.serverUrl = connection.baseUrl = settings.serverUrl
    connection.token = settings.token
    runtime.people = saved?.people ?? noPeople()
    runtime.me = settings.token ? runtime.people.me : null
    engine = new SyncEngine(
      store,
      settings,
      fetchTransport,
      (dataChanged) => {
        scheduleSave()
        if (dataChanged) {
          runtime.dataVersion++
          scheduleReminderUpdate()
        }
      },
      runtime.sync,
      (people) => {
        runtime.people = people
        runtime.me = people.me
      },
      () => void forgetSession(),
    )
    if (!saved) scheduleSave()
    syncNow()
    setInterval(syncNow, SYNC_EVERY_MS)
    if (runtime.native) {
      CapApp.addListener('resume', syncNow)
      openTicketOnTap()
      scheduleReminderUpdate()
    }
  } else {
    const session = JSON.parse(storageGet(SESSION_KEY) ?? 'null') as { token: string; me: User } | null
    if (session) {
      connection.token = session.token
      runtime.me = session.me
      account.me().then((me) => (runtime.me = me), () => {}) // refresh the name; a 401 signs out
    }
  }
  runtime.ready = true
}

export function syncNow() {
  if (!engine || !runtime.me || (runtime.native && !runtime.serverUrl)) return
  engine.sync()
}

function normalizeUrl(url: string): string {
  url = url.trim().replace(/\/$/, '')
  // "192.168.1.20:8000" → "http://192.168.1.20:8000"
  return url && !/^https?:\/\//i.test(url) ? `http://${url}` : url
}

/** Sign in. `serverUrl` is for the phone; the browser always uses the site it came from. */
export async function signIn(username: string, password: string, serverUrl = runtime.serverUrl) {
  if (runtime.native) runtime.serverUrl = connection.baseUrl = settings.serverUrl = normalizeUrl(serverUrl)
  const device = runtime.native ? 'Android app' : runtime.local ? 'Browser (offline-first test)' : 'Browser'
  const { token, user } = await account.login(username, password, device)
  connection.token = token
  if (runtime.local) {
    // Someone else used this device before: start from an empty copy.
    if (runtime.people.me && runtime.people.me.id !== user.id) clearLocalData()
    settings.token = token
    runtime.people = { ...runtime.people, me: user }
    runtime.me = user
    await saveNow()
    syncNow()
  } else {
    storageSet(SESSION_KEY, JSON.stringify({ token, me: user }))
    runtime.me = user
  }
  runtime.dataVersion++
}

export async function signOut() {
  try {
    await account.logout()
  } catch {
    // offline or already signed out; forget it locally anyway
  }
  await forgetSession()
}

async function forgetSession() {
  connection.token = ''
  runtime.me = null
  if (runtime.local) {
    clearLocalData()
    await saveNow()
  } else {
    storageSet(SESSION_KEY, null)
  }
  runtime.dataVersion++
}

function clearLocalData() {
  store.load([])
  Object.assign(settings, { token: '', cursor: 0, epoch: -1 })
  runtime.people = noPeople()
  runtime.sync.pending = 0
  runtime.sync.rejected = false
  runtime.sync.error = ''
  scheduleReminderUpdate()
}

export function discardPending() {
  engine?.discardPending()
}

/** Browser only: switch between online and offline-first mode (reloads the page; sign in again). */
export function setBrowserOfflineMode(on: boolean) {
  storageSet(LOCAL_FLAG, on ? '1' : null)
  location.reload()
}
