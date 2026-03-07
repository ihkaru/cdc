<template>
  <q-page padding>
    <div class="row items-center q-mb-lg q-gutter-x-md">
      <q-btn round flat icon="arrow_back" to="/" />
      <div>
        <h1 class="text-h4 text-weight-bold q-my-none">Sync Logs</h1>
        <p class="text-grey-5 q-mt-xs">History of RPA executions for this survey</p>
      </div>
    </div>

    <q-card class="bg-dark border-card" flat bordered>
      <q-list dark separator>
        <q-item v-if="loading" class="q-pa-xl text-center">
          <q-item-section><q-spinner size="3em" class="q-mx-auto" /></q-item-section>
        </q-item>
        
        <q-item v-else-if="logs.length === 0" class="q-pa-xl text-center text-grey-6">
          <q-item-section>No sync history found.</q-item-section>
        </q-item>

        <q-item v-for="log in logs" :key="log.id" class="q-py-md">
          <q-item-section avatar>
            <q-icon 
              :name="log.status === 'success' ? 'check_circle' : (log.status === 'running' ? 'sync' : 'error')" 
              :color="log.status === 'success' ? 'positive' : (log.status === 'running' ? 'primary' : 'negative')" 
              size="md" 
              :class="log.status === 'running' ? 'rotate-anim' : ''"
            />
          </q-item-section>
          
          <q-item-section>
            <q-item-label class="text-weight-bold text-white q-mb-xs">
              {{ formatDate(log.startedAt) }}
              <q-badge v-if="log.status === 'running'" color="primary" class="q-ml-sm">Running</q-badge>
            </q-item-label>
            <q-item-label caption class="text-grey-4">
              Duration: {{ calculateDuration(log.startedAt, log.finishedAt) }}
            </q-item-label>
            <q-item-label v-if="log.notes" class="text-caption text-grey-5 q-mt-xs">
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
                <div class="text-caption text-grey">Upd</div>
                <div class="text-weight-bold text-warning">{{ log.totalUpdated }}</div>
              </div>
            </div>
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const logs = ref<any[]>([])
const loading = ref(true)

function formatDate(dateStr: string) {
  if (!dateStr) return '-'
  // Drizzle pg timestamp returns without 'Z'. Force UTC parsing before localizing.
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

onMounted(async () => {
  try {
    const res = await fetch(`/api/surveys/${route.params.id}/logs`)
    logs.value = await res.json()
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.border-card {
  border: 1px solid #262b36;
}
.rotate-anim {
  animation: rotation 2s infinite linear;
}
@keyframes rotation {
  from { transform: rotate(0deg); }
  to { transform: rotate(359deg); }
}
</style>
