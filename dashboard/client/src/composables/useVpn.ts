import { ref } from 'vue'

export const vpnStatus = ref<{ connected: boolean; info?: string; reason?: string } | null>(null)

export function useVpn() {
  async function checkVPN() {
    try {
      const res = await fetch('/api/surveys/vpn/status')
      vpnStatus.value = await res.json()
    } catch (e) {
      vpnStatus.value = { connected: false, reason: 'Backend unreachable' }
    }
  }

  return {
    vpnStatus,
    checkVPN
  }
}
