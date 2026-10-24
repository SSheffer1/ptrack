// Where the server is and how this device proves who it is. Set by
// runtime.svelte.ts; used by every request to the server.

export const connection = {
  baseUrl: '', // '' = the site the page came from (desktop browser); the phone sets the server address
  token: '', // this device's sign-in token; '' = signed out
  onSignedOut: () => {}, // called when the server says the token is no longer valid
}

export function serverUrl(path: string): string {
  return `${connection.baseUrl.replace(/\/$/, '')}/api${path}`
}

export function authHeaders(): Record<string, string> {
  return connection.token ? { Authorization: `Bearer ${connection.token}` } : {}
}
