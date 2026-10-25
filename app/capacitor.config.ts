import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'io.github.ssheffer1.ptrack',
  appName: 'PTrack',
  webDir: 'dist', // the built web app (npm run build) is bundled into the APK
  plugins: {
    // Send fetch() through Android's native HTTP stack instead of the WebView's.
    // The app's pages come from https://localhost inside the phone; the WebView
    // would block requests from there to the home server (CORS / mixed content).
    CapacitorHttp: { enabled: true },
  },
}

export default config
