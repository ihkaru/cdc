<template>
  <q-page padding>
    <div class="row justify-between items-center q-mb-xl">
      <div>
        <h1 class="text-h3 text-weight-bold q-my-none">Survey Configurations</h1>
        <p class="text-grey-5 q-mt-sm">Manage your FASIH surveys and trigger data sync.</p>
      </div>
      <q-btn
        color="primary"
        icon="add"
        label="Add Survey"
        to="/survey/new"
        unelevated
      />
    </div>

    <!-- RPA Status Banner -->
    <q-banner
      v-if="rpaStatus.is_running"
      class="bg-primary text-white q-mb-md rounded-borders"
      rounded
    >
      <template v-slot:avatar>
        <q-spinner color="white" size="2em" />
      </template>
      <div class="text-subtitle1 text-weight-bold">Sync sedang berjalan</div>
      <div class="text-body2">Memproses: {{ rpaStatus.current_survey }}</div>
    </q-banner>

    <!-- Queue Banner -->
    <q-banner
      v-if="rpaStatus.queue && rpaStatus.queue.length > 0"
      class="bg-grey-9 text-white q-mb-xl rounded-borders"
      rounded
    >
      <template v-slot:avatar>
        <q-icon name="queue" color="amber" />
      </template>
      <div class="text-subtitle2 text-weight-bold q-mb-xs">
        {{ rpaStatus.queue.length }} survey dalam antrian
      </div>
      <div v-for="q in rpaStatus.queue" :key="q.job_id" class="row items-center q-mb-xs">
        <q-badge color="amber-8" class="q-mr-sm">#{{ q.position }}</q-badge>
        <span class="text-body2">{{ q.survey_name }}</span>
        <q-btn
          flat dense round
          icon="close"
          size="xs"
          color="negative"
          class="q-ml-sm"
          @click="cancelJob(q.job_id, q.survey_name)"
        />
      </div>
    </q-banner>

    <div v-if="loading" class="text-center text-grey-6 q-py-xl">
      <q-spinner size="3em" />
      <div class="q-mt-md">Loading data...</div>
    </div>
    
    <q-card v-else-if="surveys.length === 0" class="text-center q-pa-xl bg-dark text-grey-5 border-card" flat bordered>
      <q-icon name="assignment" size="4rem" class="q-mb-md opacity-50" />
      <p class="text-h6 q-mb-md">No surveys configured yet.</p>
      <q-btn color="primary" to="/survey/new" class="q-mt-sm" unelevated>Add your first survey</q-btn>
    </q-card>

    <div v-else class="row q-col-gutter-lg">
      <div v-for="s in surveys" :key="s.id" class="col-12 col-md-4">
        <q-card class="bg-dark text-white border-card my-card transition-hover" flat bordered>
          <q-card-section>
            <div class="row justify-between items-start q-mb-sm">
              <div class="text-h6 text-weight-bold ellipsis" style="max-width: 70%">{{ s.surveyName }}</div>
              <q-badge :color="s.isActive ? 'positive' : 'grey-8'" rounded class="q-px-sm q-py-xs">
                {{ s.isActive ? 'Active' : 'Inactive' }}
              </q-badge>
            </div>
            
            <q-list dense class="text-grey-4">
              <q-item class="q-px-none">
                <q-item-section>SSO User:</q-item-section>
                <q-item-section side class="text-white text-weight-medium">{{ s.ssoUsername }}</q-item-section>
              </q-item>
              <q-item v-if="s.filterKabupaten" class="q-px-none">
                <q-item-section>Kabupaten:</q-item-section>
                <q-item-section side class="text-white text-weight-medium">{{ s.filterKabupaten }}</q-item-section>
              </q-item>
              <q-item class="q-px-none">
                <q-item-section>Interval:</q-item-section>
                <q-item-section side class="text-white text-weight-medium">{{ s.intervalMinutes }} min</q-item-section>
              </q-item>
            </q-list>
          </q-card-section>

          <q-separator dark inset />

          <q-card-actions vertical class="q-pa-md q-gutter-y-sm">
            <div class="row q-gutter-x-sm">
              <q-btn 
                class="col"
                :color="getSyncButtonColor(s.id)"
                :label="getSyncButtonLabel(s.id)" 
                :loading="syncingId === s.id"
                :disable="syncingId === s.id || isJobActive(s.id)"
                @click="triggerSync(s.id)"
                unelevated
              />
              <q-btn class="col" color="grey-9" text-color="white" :to="`/survey/${s.id}`" label="View Data" unelevated />
            </div>
            <div class="row q-gutter-x-sm row-sm-btns">
              <q-btn class="col" size="sm" color="accent" text-color="white" :to="`/survey/${s.id}/visualizations`" label="Viz" outline />
              <q-btn class="col" size="sm" color="grey-9" text-color="white" :to="`/survey/${s.id}/logs`" label="Logs" outline />
              <q-btn class="col" size="sm" color="grey-9" text-color="white" :to="`/survey/${s.id}/edit`" label="Edit" outline />
              <q-btn class="col" size="sm" color="negative" @click="deleteSurvey(s.id)" label="Del" outline />
            </div>
          </q-card-actions>
        </q-card>
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useQuasar } from 'quasar'

const $q = useQuasar()
const surveys = ref<any[]>([])
const loading = ref(true)
const syncingId = ref<string | null>(null)
const rpaStatus = ref<any>({})
let pollTimer: any = null

async function loadData() {
  loading.value = true
  try {
    const [surveysRes, statusRes] = await Promise.all([
      fetch('/api/surveys'),
      fetch('/api/surveys/sync/status')
    ])
    surveys.value = await surveysRes.json()
    rpaStatus.value = await statusRes.json()
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function refreshStatus() {
  try {
    const res = await fetch('/api/surveys/sync/status')
    rpaStatus.value = await res.json()
  } catch {}
}

function isJobActive(surveyId: string): boolean {
  // Check if this survey is currently running
  if (rpaStatus.value.is_running && rpaStatus.value.current_survey) {
    const survey = surveys.value.find(s => s.id === surveyId)
    if (survey && survey.surveyName === rpaStatus.value.current_survey) return true
  }
  // Check if queued
  if (rpaStatus.value.queue) {
    // We don't have survey_config_id in queue, so can't check directly
    // The RPA endpoint handles dedup, so this is just a UI hint
  }
  return false
}

function getSyncButtonColor(surveyId: string): string {
  return 'primary'
}

function getSyncButtonLabel(surveyId: string): string {
  if (syncingId.value === surveyId) return 'Queueing...'
  if (rpaStatus.value.is_running) return 'Queue Sync'
  return 'Sync Now'
}

async function triggerSync(id: string) {
  if (syncingId.value) return
  syncingId.value = id
  try {
    const res = await fetch(`/api/surveys/${id}/sync`, { method: 'POST' })
    const data = await res.json()
    if (res.ok) {
      if (data.status === 'already_queued') {
        $q.notify({ type: 'warning', message: data.message })
      } else {
        $q.notify({ type: 'positive', message: data.message || 'Sync queued!' })
      }
      refreshStatus()
    } else {
      $q.notify({ type: 'negative', message: 'Error: ' + (data.message || data.detail) })
    }
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Failed to trigger sync' })
  } finally {
    syncingId.value = null
  }
}

async function cancelJob(jobId: number, surveyName: string) {
  try {
    const res = await fetch(`/api/surveys/sync/${jobId}`, { method: 'DELETE' })
    if (res.ok) {
      $q.notify({ type: 'info', message: `Sync "${surveyName}" dibatalkan` })
      refreshStatus()
    }
  } catch {
    $q.notify({ type: 'negative', message: 'Gagal membatalkan job' })
  }
}

function deleteSurvey(id: string) {
  $q.dialog({
    title: 'Confirm Deletion',
    message: 'Hapus survey ini beserta semua datanya?',
    cancel: true,
    persistent: true,
    dark: true
  }).onOk(async () => {
    try {
      const res = await fetch(`/api/surveys/${id}`, { method: 'DELETE' })
      if (res.ok) {
        $q.notify({ type: 'info', message: 'Survey deleted' })
        loadData()
      }
    } catch (e) {
      $q.notify({ type: 'negative', message: 'Failed to delete' })
    }
  })
}

onMounted(() => {
  loadData()
  // Poll status every 5s when syncing, 30s otherwise
  pollTimer = setInterval(refreshStatus, 5000)
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.border-card {
  border-color: #262b36;
}
.transition-hover {
  transition: all 0.2s ease-in-out;
}
.transition-hover:hover {
  transform: translateY(-2px);
  border-color: rgba(59, 130, 246, 0.4);
  box-shadow: 0 8px 24px rgba(0,0,0,0.3);
}
.opacity-50 {
  opacity: 0.5;
}
</style>
