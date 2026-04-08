<template>
  <q-layout view="hHh lpR fFf" class="bg-dark text-white">
    <q-header elevated class="bg-dark text-white shadow-2">
      <q-toolbar>
        <q-toolbar-title class="text-weight-bold row items-center no-wrap">
          <q-icon name="sync" size="sm" class="q-mr-sm text-primary" />
          <span class="text-primary">FASIH</span> Sync
        </q-toolbar-title>

        <!-- VPN Status Chip (clickable to open cookie dialog) -->
        <q-chip
          v-if="vpnStatus"
          :color="vpnStatus.connected ? 'positive' : 'negative'"
          text-color="white"
          size="sm"
          outline
          clickable
          @click="showCookieDialog = true"
          class="q-mr-md cursor-pointer"
        >
          <q-icon :name="vpnStatus.connected ? 'vpn_lock' : 'vpn_off'" class="q-mr-xs" />
          VPN: {{ vpnStatus.connected ? 'Connected' : 'Disconnected' }}
          <q-tooltip>Click to update VPN cookie</q-tooltip>
        </q-chip>

        <q-btn flat dense label="Surveys" to="/" />
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view v-slot="{ Component }">
        <transition name="q-transition--fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </q-page-container>

    <!-- VPN Cookie Update Dialog -->
    <q-dialog v-model="showCookieDialog" persistent>
      <q-card style="min-width: 500px" class="bg-grey-10 text-white">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">
            <q-icon name="vpn_key" class="q-mr-sm" />
            Update VPN Cookie
          </div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section>
          <div class="q-mb-md">
            <q-btn
              type="a"
              href="https://akses.bps.go.id/remote/saml/start"
              target="_blank"
              color="primary"
              icon="open_in_new"
              label="Buka VPN Portal (Login SSO)"
              class="full-width q-mb-sm"
              no-caps
            />
            <div class="text-caption text-grey-5 q-mt-sm">
              <ol class="q-pl-md q-my-none" style="line-height: 1.8">
                <li>Klik tombol di atas → login SSO hingga muncul halaman portal</li>
                <li>Tekan <kbd class="bg-grey-8 q-px-xs rounded-borders">F12</kbd> → buka tab <b>Network</b></li>
                <li>Klik request apapun ke <code>akses.bps.go.id</code></li>
                <li>Di <b>Request Headers</b>, copy seluruh isi <b>Cookie</b></li>
                <li>Paste di bawah lalu klik <b>Update & Connect</b></li>
              </ol>
            </div>
          </div>
          <q-input
            v-model="cookieInput"
            type="textarea"
            outlined
            dark
            autogrow
            placeholder="__cf_bm=...; SVPNCOOKIE=...; fgt_sslvpn_csrf=..."
            :error="!!cookieError"
            :error-message="cookieError"
            input-style="font-family: monospace; font-size: 12px"
          />
        </q-card-section>

        <q-card-actions align="right" class="q-px-md q-pb-md">
          <q-btn
            flat
            label="Auto-Fix (Smart)"
            color="secondary"
            icon="auto_fix_high"
            @click="triggerAutoFix"
            :loading="cookieLoading"
            class="q-mr-auto"
          />
          <q-btn flat label="Clear Cookie" color="warning" @click="clearCookie" :loading="cookieLoading" />
          <q-btn
            label="Update & Connect"
            color="primary"
            @click="submitCookie"
            :loading="cookieLoading"
            :disable="!cookieInput || cookieInput.length < 10"
          />
        </q-card-actions>

        <q-card-section v-if="cookieSuccess" class="q-pt-none">
          <q-banner dense class="bg-positive text-white rounded-borders">
            <template v-slot:avatar>
              <q-icon name="check_circle" />
            </template>
            {{ cookieSuccess }}
          </q-banner>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { vpnStatus, useVpn } from '../composables/useVpn'

const { checkVPN } = useVpn()

const showCookieDialog = ref(false)
const cookieInput = ref('')
const cookieLoading = ref(false)
const cookieError = ref('')
const cookieSuccess = ref('')
let timer: any = null
let rapidTimer: any = null

function startRapidPolling() {
  // Clear any existing rapid poll
  if (rapidTimer) clearInterval(rapidTimer)
  // Poll every 3s for 30s, stop early if connected
  let elapsed = 0
  rapidTimer = setInterval(async () => {
    elapsed += 3000
    await checkVPN()
    if (vpnStatus.value?.connected || elapsed >= 30000) {
      clearInterval(rapidTimer)
      rapidTimer = null
    }
  }, 3000)
}

async function submitCookie() {
  cookieLoading.value = true
  cookieError.value = ''
  cookieSuccess.value = ''
  try {
    const res = await fetch('/api/surveys/vpn/cookie', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cookie: cookieInput.value })
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.message || 'Failed to update cookie')
    cookieSuccess.value = data.message || 'Cookie updated!'
    cookieInput.value = ''
    // Start rapid polling to quickly detect VPN reconnect
    startRapidPolling()
  } catch (e: any) {
    cookieError.value = e.message || 'Unknown error'
  } finally {
    cookieLoading.value = false
  }
}

async function clearCookie() {
  cookieLoading.value = true
  cookieError.value = ''
  cookieSuccess.value = ''
  try {
    const res = await fetch('/api/surveys/vpn/cookie', { method: 'DELETE' })
    const data = await res.json()
    cookieSuccess.value = data.message || 'Cookie cleared!'
  } catch (e: any) {
    cookieError.value = e.message || 'Unknown error'
  } finally {
    cookieLoading.value = false
  }
}

async function triggerAutoFix() {
  cookieLoading.value = true
  cookieError.value = ''
  cookieSuccess.value = ''
  try {
    const res = await fetch('/api/surveys/vpn/auto-fetch', { method: 'POST' })
    const data = await res.json()
    if (!res.ok) throw new Error(data.message || 'Auto-fix failed')
    cookieSuccess.value = 'Auto-fix triggered! RPA is grabbing the cookie...'
    startRapidPolling()
  } catch (e: any) {
    cookieError.value = e.message || 'Unknown error'
  } finally {
    cookieLoading.value = false
  }
}

onMounted(() => {
  checkVPN()
  timer = setInterval(checkVPN, 30000)
})

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<style lang="scss">
.bg-dark {
  background-color: #0f1115 !important;
}
.text-primary {
  color: #3b82f6 !important;
}
</style>
