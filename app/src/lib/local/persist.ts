// Saves the on-device state as one JSON file in the app's private storage.
// (In a desktop browser, Capacitor's Filesystem plugin stores it in IndexedDB.)

import { Directory, Encoding, Filesystem } from '@capacitor/filesystem'
import type { LogEntry } from './store'

export interface SavedState {
  version: 1
  deviceId: string
  serverUrl: string
  cursor: number
  log: LogEntry[]
}

const FILE = 'ptrack.json'
const TEMP = 'ptrack.json.tmp'

export async function loadState(): Promise<SavedState | null> {
  try {
    const { data } = await Filesystem.readFile({ path: FILE, directory: Directory.Data, encoding: Encoding.UTF8 })
    return JSON.parse(data as string) as SavedState
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
