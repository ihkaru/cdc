import { ref } from 'vue'
import { api } from 'src/boot/axios'

export const vpnStatus = ref<{ connected: boolean; info?: string; reason?: string; is_fetching?: boolean } | null>(null)

export function useVpn() {
  async function checkVPN() {
    try {
      const res = await api.get('/surveys/vpn/status')
      vpnStatus.value = res.data
    } catch (e) {
      vpnStatus.value = { connected: false, reason: 'Backend unreachable' }
    }
  }

  return {
    vpnStatus,
    checkVPN
  }
}
