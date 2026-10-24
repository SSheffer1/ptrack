// Signing in and managing accounts. These always need the server (they're
// never queued offline), so they go straight to it in every mode.

import { request } from './http'
import type { User } from './types'

export interface Device {
  id: string
  name: string
  created_at: number
  last_used_at: number
  current: boolean
}

export interface AdminUser extends User {
  disabled: boolean
  created_at: number
}

export const account = {
  login: (username: string, password: string, device_name: string) =>
    request<{ token: string; user: User }>('POST', '/auth/login', { username, password, device_name }),
  logout: () => request<void>('POST', '/auth/logout'),
  me: () => request<User>('GET', '/me'),
  visibleUsers: () => request<User[]>('GET', '/users'), // everyone sharing a project with me
  changePassword: (current: string, next: string) => request<void>('POST', '/me/password', { current, new: next }),
  devices: () => request<Device[]>('GET', '/me/devices'),
  signOutDevice: (id: string) => request<void>('DELETE', `/me/devices/${encodeURIComponent(id)}`),

  // Admins only.
  listUsers: () => request<AdminUser[]>('GET', '/admin/users'),
  createUser: (body: { username: string; display_name: string; password: string; is_admin?: boolean }) =>
    request<AdminUser>('POST', '/admin/users', body),
  updateUser: (id: string, body: { display_name?: string; password?: string; disabled?: boolean; is_admin?: boolean }) =>
    request<AdminUser>('PATCH', `/admin/users/${encodeURIComponent(id)}`, body),
}
