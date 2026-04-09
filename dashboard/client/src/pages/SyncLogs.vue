<template>
  <q-page padding>
    <div class="row items-center q-mb-lg q-gutter-x-md">
      <q-btn round flat icon="arrow_back" to="/" />
      <div>
        <h1 class="text-h4 text-weight-bold q-my-none">Sync Logs</h1>
        <p class="text-grey-5 q-mt-xs">Riwayat eksekusi RPA untuk survey ini</p>
      </div>
      <q-space />
      <div class="q-gutter-x-sm">
        <q-btn 
          color="accent" 
          icon="download" 
          label="Export Log" 
          no-caps 
          unelevated 
          :loading="exporting"
          @click="exportLogs" 
        />
        <q-btn 
          color="primary" 
          icon="content_copy" 
          label="Copy for AI" 
          no-caps 
          unelevated 
          @click="copyForAI" 
        />
        <q-btn flat dense round icon="refresh" @click="fetchLogsAndStatus" :loading="loading" />
      </div>
    </div>

    <!-- Mirroring Vault Status Card -->
    <q-card v-if="mirroringStatus" class="q-mb-md bg-dark border-card vault-card" flat bordered>
      <q-card-section>
        <div class="row items-center q-mb-sm">
          <q-icon name="cloud_done" color="positive" size="sm" class="q-mr-sm" />
          <span class="text-weight-bold text-white">CDC Image Vault Status</span>
          <q-space />
          <span class="text-caption text-grey-5">
            {{ mirroringStatus.mirrored }} / {{ mirroringStatus.total - mirroringStatus.skipped }} Assignments Processed
          </span>
        </div>
        
        <q-linear-progress
          :value="mirroringStatus.total - mirroringStatus.skipped > 0 ? mirroringStatus.mirrored / (mirroringStatus.total - mirroringStatus.skipped) : 0"
          color="positive"
          track-color="grey-9"
          rounded
          size="10px"
          class="q-mb-sm"
        />
        
        <div class="row items-center justify-between">
          <div class="text-caption text-grey-6 italic">
            Robot Archiver bekerja di background untuk mengamankan link foto BPS ke penyimpanan permanen.
          </div>
          <q-btn 
            v-if="mirroringStatus.skipped > 0"
            flat 
            dense 
            color="warning" 
            size="sm" 
            label="Lihat Data Tanpa Foto" 
            icon="visibility_off"
            @click="showSkippedDialog = true"
            no-caps
          >
            <q-badge color="orange" floating>{{ mirroringStatus.skipped }}</q-badge>
          </q-btn>
        </div>
      </q-card-section>
    </q-card>

    <!-- Skipped Assignments Dialog -->
    <q-dialog v-model="showSkippedDialog">
      <q-card style="min-width: 600px; max-width: 90vw" class="bg-dark text-white">
        <q-card-section class="row items-center">
          <div class="text-h6">Data Tanpa Foto (Source BPS NULL)</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section class="q-pt-none">
          <div class="text-caption text-grey-5 q-mb-md">
            Identitas berikut tidak memiliki data foto di dalam server FASIH-SM BPS (link NULL dari asal). 
            Ini bukan kesalahan sistem sinkronisasi.
          </div>
          
          <q-table
            dark
            dense
            flat
            bordered
            :rows="mirroringStatus?.skippedList || []"
            :columns="[
              { name: 'codeIdentity', label: 'Code Identity', field: 'codeIdentity', align: 'left', sortable: true },
              { name: 'user', label: 'User Pencacah', field: 'user', align: 'left', sortable: true },
              { name: 'status', label: 'Status BPS', field: 'status', align: 'left', sortable: true }
            ]"
            row-key="id"
            binary-state-sort
            class="bg-transparent"
            :pagination="{ rowsPerPage: 10 }"
          >
            <template v-slot:body-cell-status="props">
              <q-td :props="props">
                <q-badge color="grey-8">{{ props.row.status }}</q-badge>
              </q-td>
            </template>
          </q-table>
        </q-card-section>
      </q-card>
    </q-dialog>

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

            <!-- Timing Breakdown Chart -->
            <div v-if="log.timings && log.status === 'success'" class="q-mt-sm" style="max-width: 300px">
              <div class="row q-gutter-x-xs items-center q-mb-xs">
                <span class="text-caption text-grey-5">Performance:</span>
                <span class="text-caption text-weight-bold text-white">{{ log.timings.total || 0 }}ms</span>
              </div>
              <div class="row no-wrap rounded-borders overflow-hidden" style="height: 6px; background: #333">
                <div 
                  v-for="phase in timingPhases" 
                  :key="phase.key"
                  :style="{
                    width: getPhaseWidth(log, phase.key),
                    background: phase.color
                  }"
                >
                   <q-tooltip>{{ phase.label }}: {{ log.timings[phase.key] || 0 }}ms</q-tooltip>
                </div>
              </div>
              <div class="row q-gutter-x-sm q-mt-xs">
                <div v-for="phase in timingPhases" :key="phase.key" class="row items-center q-gutter-x-xs">
                   <div :style="{ width: '8px', height: '8px', background: phase.color, borderRadius: '2px' }"></div>
                   <span style="font-size: 9px" class="text-grey-5">{{ phase.alias }}</span>
                </div>
              </div>
            </div>
          </q-item-section>
          
          <q-item-section side v-if="log.status === 'success' || log.status === 'running'">
            <div class="row q-gutter-x-md no-wrap items-center">
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
                <div v-if="log.totalSkipped > 0">
                  <div class="text-caption text-grey">Skip</div>
                  <div class="text-weight-bold text-grey-4">{{ log.totalSkipped }}</div>
                </div>
              </div>

              <!-- Vertical Separator -->
              <div style="width: 1px; height: 30px; background: #333"></div>

              <!-- Image Mirroring Progress -->
              <div style="min-width: 140px">
                <div class="row items-center justify-between q-mb-xs">
                  <div class="text-caption text-grey">🖼️ Images</div>
                  <div class="text-caption text-weight-bold" :class="log.totalImages > 0 && log.imagesMirrored >= log.totalImages ? 'text-positive' : 'text-blue'">
                    <template v-if="log.totalImages > 0">
                      {{ log.imagesMirrored }} / {{ log.totalImages }}
                    </template>
                    <template v-else-if="log.status === 'success'">
                      No media
                    </template>
                    <template v-else>
                      -
                    </template>
                  </div>
                </div>
                <q-linear-progress
                  v-if="log.totalImages > 0"
                  :value="Math.min(1, log.imagesMirrored / log.totalImages)"
                  :color="log.imagesMirrored >= log.totalImages ? 'positive' : 'blue'"
                  track-color="grey-10"
                  rounded
                  size="6px"
                />
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
import { useQuasar, copyToClipboard } from 'quasar'

const route = useRoute()
const $q = useQuasar()
const logs = ref<any[]>([])
const loading = ref(true)
const exporting = ref(false)
const liveStatus = ref<any>(null)
const mirroringStatus = ref<any>(null)
const showSkippedDialog = ref(false)
let pollTimer: any = null

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

const timingPhases = [
  { key: 'login', label: 'Login SSO', alias: 'SSO', color: '#3498db' },
  { key: 'metadata', label: 'Metadata Resolve', alias: 'Meta', color: '#9b59b6' },
  { key: 'fetch', label: 'API Fetching', alias: 'Fetch', color: '#e67e22' },
  { key: 'upsert', label: 'Database Save', alias: 'DB', color: '#2ecc71' },
]

function getPhaseWidth(log: any, key: string) {
  if (!log.timings || !log.timings.total) return '0%'
  const val = log.timings[key] || 0
  return `${(val / log.timings.total) * 100}%`
}

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

// Unified State Fetch: Replaces pollStatus, fetchLogs, fetchMirroring
async function fetchDashboardState() {
  try {
    const res = await fetch(`/api/surveys/${route.params.id}/sync-dashboard-state`)
    const data = await res.json()
    
    // Smooth update to avoid UI flickering
    liveStatus.value = data.robotStatus
    mirroringStatus.value = data.mirroring
    logs.value = data.logs
  } catch (e) {
    console.error('Failed to fetch unified dashboard state', e)
  } finally {
    loading.value = false
  }
}

async function fetchLogsAndStatus() {
  loading.value = true
  await fetchDashboardState()
}

async function exportLogs() {
  exporting.value = true
  try {
    window.location.href = `/api/surveys/${route.params.id}/logs/export`
  } catch {
    $q.notify({ type: 'negative', message: 'Gagal ekspor log' })
  } finally {
    setTimeout(() => { exporting.value = false }, 1000)
  }
}



function copyForAI() {
  if (!logs.value.length) return
  
  let md = `# Sync Log Report - Survey ID: ${route.params.id}\n`
  md += `Generated at: ${new Date().toLocaleString()}\n\n`
  
  if (mirroringStatus.value) {
    const s = mirroringStatus.value
    md += `## Image Vault Status\n`
    md += `- Combined Progress: ${s.mirrored} / ${s.total - s.skipped} assignments processed\n`
    md += `- Skipped (No Image): ${s.skipped}\n`
    md += `- Completion: ${(((s.mirrored) / (s.total - s.skipped)) * 100).toFixed(1)}%\n\n`
  }
  
  md += `## Execution History (Last 5 cycles)\n\n`
  md += `| Time | Status | New | Upd | Skip | Timing (L/M/F/D) |\n`
  md += `|---|---|---|---|---|---|\n`
  
  logs.value.slice(0, 5).forEach(l => {
    const t = l.timings || {}
    const tStr = `${t.login || 0}/${t.metadata || 0}/${t.fetch || 0}/${t.upsert || 0}ms`
    md += `| ${formatDate(l.startedAt)} | ${l.status} | ${l.totalNew} | ${l.totalUpdated} | ${l.totalSkipped} | ${tStr} |\n`
  })
  
  md += `\n*Timing Legend: L=Login, M=Metadata, F=Fetch, D=Database Save*`
  
  copyToClipboard(md).then(() => {
    $q.notify({ type: 'positive', message: 'Log report copied to clipboard for AI analysis', icon: 'auto_awesome' })
  })
}

onMounted(async () => {
  await fetchLogsAndStatus()
  // Poll every 3s for comprehensive dashboard state
  pollTimer = setInterval(fetchDashboardState, 3000)
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
.vault-card {
  background: linear-gradient(135deg, #0f231a 0%, #0a2816 100%);
  border: 1px solid #1e5f3e;
}
.rotate-anim {
  animation: rotation 2s infinite linear;
}
@keyframes rotation {
  from { transform: rotate(0deg); }
  to { transform: rotate(359deg); }
}
</style>
