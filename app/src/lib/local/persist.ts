// Saves the on-device state as one JSON file in the app's private storage.
// (In a desktop browser, Capacitor's Filesystem plugin stores it in IndexedDB.)

import { Directory, Encoding, Filesystem } from '@capacitor/filesystem'
import type { LogEntry } from './store'
import type { People } from './sync'

export interface SavedState {
  version: 2
  deviceId: string
  serverUrl: string
  token: string // '' = signed out
  cursor: number
  epoch: number
  people: People // who I am, and who's in my projects
  lastSync?: number | null // when the last sync succeeded (ms), for Settings; missing in older files
  log: LogEntry[]
}

const FILE = 'ptrack.json'
const TEMP = 'ptrack.json.tmp'

export async function loadState(): Promise<SavedState | null> {
  try {
    const { data } = await Filesystem.readFile({ path: FILE, directory: Directory.Data, encoding: Encoding.UTF8 })
    const saved = JSON.parse(data as string)
    // Version 1 (before accounts): same data, not signed in yet.
    return { token: '', epoch: -1, people: { me: null, users: [], members: [] }, ...saved, version: 2 }
  } catch {
    return null // first run
  }
}

/** Write to a temp file, then rename over the real one, so a crash mid-write can't corrupt it. */
export async function saveState(state: SavedState): Promise<void> {
  const data = JSON.stringify(state)
  await Filesystem.writeFile({ path: TEMP, data, directory: Directory.Data, encoding: Encoding.UTF8 })
  try {
    await Filesystem.rename({ from: TEMP, to: FILE, directory: Directory.Data })
  } catch {
    await Filesystem.writeFile({ path: FILE, data, directory: Directory.Data, encoding: Encoding.UTF8 })
  }
}
