// Schedules reminders as Android notifications. The phone fires them itself,
// so they work offline and with the app closed. After any change to the data
// we cancel what's scheduled and schedule the current set again; with at most
// a few dozen upcoming reminders that's simpler than tracking each one.

import { LocalNotifications } from '@capacitor/local-notifications'
import { upcomingReminders } from './reminders'
import type { Item } from './types'

let permission: boolean | null = null

async function allowed(): Promise<boolean> {
  if (permission === null) {
    const status = await LocalNotifications.checkPermissions()
    permission =
      status.display === 'granted' || (await LocalNotifications.requestPermissions()).display === 'granted'
  }
  return permission
}

export async function scheduleReminders(items: Item[], me: string): Promise<number> {
  if (!(await allowed())) return 0
  const pending = await LocalNotifications.getPending()
  if (pending.notifications.length) {
    await LocalNotifications.cancel({ notifications: pending.notifications.map((n) => ({ id: n.id })) })
  }
  const reminders = upcomingReminders(items, new Date(), me)
  if (reminders.length) {
    await LocalNotifications.schedule({
      notifications: reminders.map((r) => ({
        id: r.id,
        title: r.title,
        body: r.body,
        schedule: { at: r.at, allowWhileIdle: true }, // fire even if the phone is dozing
        extra: { itemId: r.itemId },
      })),
    })
  }
  return reminders.length
}

/** Tapping a notification opens its ticket. */
export function openTicketOnTap() {
  LocalNotifications.addListener('localNotificationActionPerformed', (action) => {
    const itemId = action.notification.extra?.itemId
    if (itemId) location.hash = `#/items/${itemId}`
  })
}
