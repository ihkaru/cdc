<template>
  <q-page padding>
    <div class="row items-center q-mb-lg q-gutter-x-md">
      <q-btn round flat icon="arrow_back" to="/" />
      <div>
        <h1 class="text-h4 text-weight-bold q-my-none">Sync Logs</h1>
        <p class="text-grey-5 q-mt-xs">Riwayat eksekusi RPA untuk survey ini</p>
      </div>
      <q-space />
      <q-btn flat dense round icon="refresh" @click="fetchLogs" :loading="loading" />
    </div>

    <!-- Live Progress Card — shows only when a job is running -->
    <q-card v-if="liveStatus?.is_running" class="q-mb-md live-card" flat>
      <q-card-section>
        <div class="row items-center q-mb-sm">
          <q-spinner-rings color="primary" size="1.5em" class="q-mr-sm" />
          <span class="text-weight-bold text-primary">Sync Berjalan</span>
          <q-space />
          <span class="text-caption text-grey-5">{{ elapsedLabel }}</span>
        </div>

        <div class="text-h6 text-white q-mb-xs">{{ liveStatus.current_survey }}</div>

        <!-- Phase label -->
        <div class="text-body2 text-grey-4 q-mb-md">
          {{ liveStatus.progress?.phase_label || 'Memulai...' }}
        </div>

        <!-- User iteration progress bar -->
        <template v-if="liveStatus.progress?.users_total > 0">
          <div class="row items-center q-mb-xs">
            <span class="text-caption text-grey-5">Iterasi User</span>
            <q-space />
            <span class="text-caption text-primary">
              {{ liveStatus.progress.users_done }} / {{ liveStatus.progress.users_total }}
            </span>
          </div>
          <q-linear-progress
            :value="liveStatus.progress.users_done / liveStatus.progress.users_total"
            color="primary"
            track-color="grey-9"
            rounded
            class="q-mb-md"
            size="8px"
          />
        </template>

        <!-- Assignment fetch progress -->
        <template v-if="liveStatus.progress?.assignments_total > 0">
          <div class="row items-center q-mb-xs">
            <span class="text-caption text-grey-5">Fetch Detail Assignment</span>
            <q-space />
            <span class="text-caption text-positive">
              {{ liveStatus.progress.assignments_fetched }} / {{ liveStatus.progress.assignments_total }}
            </span>
          </div>
          <q-linear-progress
            :value="liveStatus.progress.assignments_fetched / liveStatus.progress.assignments_total"
            color="positive"
            track-color="grey-9"
            rounded
            size="8px"
          />
        </template>

        <!-- Phase pills -->
        <div class="row q-gutter-xs q-mt-md">
          <q-badge
            v-for="phase in phases"
            :key="phase.key"
            :color="getPhaseColor(phase.key)"
            class="q-px-sm q-py-xs"
          >
            <q-icon :name="phase.icon" size="xs" class="q-mr-xs" />
            {{ phase.label }}
          </q-badge>
        </div>
      </q-card-section>
    </q-card>

    <!-- Log history list -->
    <q-card class="bg-dark border-card" flat bordered>
      <q-list dark separator>
        <q-item v-if="loading && logs.length === 0" class="q-pa-xl text-center">
          <q-item-section><q-spinner size="3em" class="q-mx-auto" /></q-item-section>
        </q-item>
        
        <q-item v-else-if="logs.length === 0" class="q-pa-xl text-center text-grey-6">
          <q-item-section>Belum ada riwayat sync.</q-item-section>
        </q-item>

        <q-item v-for="log in logs" :key="log.id" class="q-py-md">
          <q-item-section avatar>
            <q-icon 
              :name="statusIcon(log.status)" 
              :color="statusColor(log.status)" 
              size="md" 
              :class="log.status === 'running' ? 'rotate-anim' : ''"
            />
          </q-item-section>
          
          <q-item-section>
            <q-item-label class="text-weight-bold text-white q-mb-xs">
              {{ formatDate(log.startedAt) }}
              <q-badge v-if="log.status === 'running'" color="primary" class="q-ml-sm">Running</q-badge>
              <q-badge v-if="log.status === 'queued'" color="grey" class="q-ml-sm">Queued</q-badge>
            </q-item-label>
            <q-item-label caption class="text-grey-4">
              Duration: {{ calculateDuration(log.startedAt, log.finishedAt) }}
            </q-item-label>
            <q-item-label v-if="log.notes && log.status !== 'success'" class="text-caption text-negative q-mt-xs" style="word-break: break-all; max-width: 500px">
              {{ log.notes }}
            </q-item-label>
          </q-item-section>
          
          <q-item-section side v-if="log.status === 'success'">
            <div class="row q-gutter-x-sm text-center">
              <div>
                <div class="text-caption text-grey">Fetched</div>
                <div class="text-weight-bold text-white">{{ log.totalFetched }}</div>
              </div>
              <div>
                <div class="text-caption text-grey">New</div>
                <div class="text-weight-bold text-positive">{{ log.totalNew }}</div>
              </div>
              <div>
                <div class="text-caption text-grey">Updated</div>
                <div class="text-weight-bold text-warning">{{ log.totalUpdated }}</div>
              </div>
              <div>
                <div class="text-caption text-grey">Skipped</div>
                <div class="text-weight-bold text-grey-4">{{ log.totalSkipped }}</div>
              </div>
            </div>
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const logs = ref<any[]>([])
const loading = ref(true)
const liveStatus = ref<any>(null)
let pollTimer: any = null
let startedAt: Date | null = null

const phases = [
  { key: 'login', icon: 'lock', label: 'Login SSO' },
  { key: 'resolve', icon: 'search', label: 'Resolve Survey' },
  { key: 'fetch_users', icon: 'group', label: 'Fetch Users' },
  { key: 'fetch_assignments', icon: 'download', label: 'Fetch Assignments' },
  { key: 'upsert', icon: 'save', label: 'Simpan DB' },
]

const phaseOrder = phases.map(p => p.key)

function getPhaseColor(phaseKey: string) {
  const current = liveStatus.value?.progress?.phase
  if (!current) return 'grey-8'
  const currentIdx = phaseOrder.indexOf(current)
  const thisIdx = phaseOrder.indexOf(phaseKey)
  if (thisIdx < currentIdx) return 'positive'
  if (thisIdx === currentIdx) return 'primary'
  return 'grey-8'
}

const elapsedLabel = computed(() => {
  if (!liveStatus.value?.started_at) return ''
  const start = new Date(liveStatus.value.started_at)
  const now = new Date()
  const sec = Math.floor((now.getTime() - start.getTime()) / 1000)
  if (sec < 60) return `${sec}s`
  return `${Math.floor(sec / 60)}m ${sec % 60}s`
})

function formatDate(dateStr: string) {
  if (!dateStr) return '-'
  const utcDateStr = dateStr.endsWith('Z') ? dateStr : `${dateStr}Z`
  return new Date(utcDateStr).toLocaleString('id-ID')
}

function calculateDuration(start: string, end: string) {
  if (!start) return '-'
  if (!end) return 'In progress...'
  const ms = new Date(end).getTime() - new Date(start).getTime()
  if (ms < 1000) return `${ms}ms`
  const sec = Math.floor(ms / 1000)
  if (sec < 60) return `${sec}s`
  return `${Math.floor(sec / 60)}m ${sec % 60}s`
}

function statusIcon(status: string) {
  return status === 'success' ? 'check_circle' : status === 'running' ? 'sync' : status === 'queued' ? 'hourglass_empty' : 'error'
}

function statusColor(status: string) {
  return status === 'success' ? 'positive' : status === 'running' ? 'primary' : status === 'queued' ? 'grey' : 'negative'
}

async function fetchLogs() {
  try {
    const res = await fetch(`/api/surveys/${route.params.id}/logs`)
    logs.value = await res.json()
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function pollStatus() {
  try {
    const res = await fetch('/api/surveys/sync/status')
    const data = await res.json()
    liveStatus.value = data

    // If a job just finished, refresh the log list
    if (!data.is_running && liveStatus.value?.is_running === false) {
      await fetchLogs()
    }
  } catch {
    liveStatus.value = null
  }
}

onMounted(async () => {
  await fetchLogs()
  await pollStatus()
  // Poll every 3s for live updates
  pollTimer = setInterval(pollStatus, 3000)
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.border-card {
  border: 1px solid #262b36;
}
.live-card {
  background: linear-gradient(135deg, #0f1823 0%, #0a1628 100%);
  border: 1px solid #1e3a5f;
}
.rotate-anim {
  animation: rotation 2s infinite linear;
}
@keyframes rotation {
  from { transform: rotate(0deg); }
  to { transform: rotate(359deg); }
}
</style>
