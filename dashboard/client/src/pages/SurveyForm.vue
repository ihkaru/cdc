<template>
  <q-page padding class="row justify-center">
    <div style="max-width: 700px; width: 100%">
      <div class="row items-center q-mb-xl q-gutter-x-md">
        <q-btn round flat icon="arrow_back" to="/" />
        <h1 class="text-h3 text-weight-bold q-my-none">{{ isEdit ? 'Edit Survey' : 'New Survey' }}</h1>
      </div>

      <div v-if="loading" class="text-center q-py-xl">
        <q-spinner size="3em" color="primary" />
      </div>
      
      <q-card v-else class="bg-dark text-white border-card q-pa-md" flat bordered>
        <q-form @submit="save" class="q-gutter-y-md">
          
          <div>
            <div class="text-subtitle2 text-grey-5 q-mb-xs">Survey Name (seperti di FASIH)</div>
            <q-input v-model="form.surveyName" dark filled placeholder="e.g. SAKERNAS NOV 2025 - PENDATAAN" 
              :rules="[val => !!val || 'Field is required']" />
          </div>

          <div class="row q-col-gutter-md">
            <div class="col-12 col-md-6">
              <div class="text-subtitle2 text-grey-5 q-mb-xs">SSO Username</div>
              <q-input v-model="form.ssoUsername" dark filled placeholder="NIP/Username BPS" 
                :rules="[val => !!val || 'Field is required']" />
            </div>
            <div class="col-12 col-md-6">
              <div class="text-subtitle2 text-grey-5 q-mb-xs">SSO Password</div>
              <q-input v-model="form.ssoPassword" dark filled type="password" 
                :placeholder="isEdit ? '(Leave empty to keep current)' : 'Password'" 
                :rules="[val => isEdit || !!val || 'Field is required']" />
            </div>
          </div>

          <div class="row q-col-gutter-md">
            <div class="col-12 col-md-6">
              <div class="text-subtitle2 text-grey-5 q-mb-xs">Filter Provinsi (Optional)</div>
              <q-input v-model="form.filterProvinsi" dark filled placeholder="e.g. KALIMANTAN BARAT" />
            </div>
            <div class="col-12 col-md-6">
              <div class="text-subtitle2 text-grey-5 q-mb-xs">Filter Kabupaten (Optional)</div>
              <q-input v-model="form.filterKabupaten" dark filled placeholder="e.g. MEMPAWAH" />
            </div>
          </div>

          <div class="row q-col-gutter-md">
            <div class="col-12 col-md-6">
              <div class="text-subtitle2 text-grey-5 q-mb-xs">Rotasi Iterasi API</div>
              <q-select v-model="form.filterRotation" :options="rotationOptions" dark filled emit-value map-options />
            </div>
            <div class="col-12 col-md-6">
              <div class="text-subtitle2 text-grey-5 q-mb-xs">Sync Interval (via n8n) - Minutes</div>
              <q-input v-model.number="form.intervalMinutes" type="number" dark filled min="5" />
            </div>
          </div>

          <div class="row justify-between items-center q-mt-lg q-pa-md border-card rounded-borders" style="background: rgba(255,255,255,0.02)">
            <div>
              <div class="text-weight-bold">Active Status</div>
              <div class="text-caption text-grey-5">Enable or disable auto-sync for this survey</div>
            </div>
            <q-toggle v-model="form.isActive" color="positive" keep-color />
          </div>

          <div class="row justify-end q-mt-xl q-gutter-x-md">
            <q-btn label="Cancel" to="/" color="grey-8" unelevated />
            <q-btn type="submit" color="primary" :label="saving ? 'Saving...' : 'Save Configuration'" :loading="saving" unelevated />
          </div>
        </q-form>
      </q-card>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useQuasar } from 'quasar'

const $q = useQuasar()
const router = useRouter()
const route = useRoute()

const isEdit = computed(() => !!route.params.id)
const loading = ref(false)
const saving = ref(false)

const rotationOptions = [
  { label: 'Per Pengawas (cepat, limit 1000/pengawas)', value: 'pengawas' },
  { label: 'Per Pencacah (aman, limit 1000/pencacah)', value: 'pencacah' }
]

const form = ref({
  surveyName: '',
  ssoUsername: '',
  ssoPassword: '',
  filterProvinsi: '',
  filterKabupaten: '',
  filterRotation: 'pengawas',
  intervalMinutes: 30,
  isActive: true
})

async function loadData() {
  if (!isEdit.value) return
  loading.value = true
  try {
    const res = await fetch(`/api/surveys/${route.params.id}`)
    const data = await res.json()
    form.value = { ...data, ssoPassword: '' }
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Failed to load survey' })
    router.push('/')
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const url = isEdit.value ? `/api/surveys/${route.params.id}` : '/api/surveys'
    const method = isEdit.value ? 'PUT' : 'POST'
    
    const payload = { ...form.value }
    if (isEdit.value && !payload.ssoPassword) delete payload.ssoPassword

    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    
    if (res.ok) {
      $q.notify({ type: 'positive', message: 'Survey saved successfully' })
      router.push('/')
    } else {
      const err = await res.json()
      $q.notify({ type: 'negative', message: 'Error: ' + err.message })
    }
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Network error' })
  } finally {
    saving.value = false
  }
}

onMounted(() => loadData())
</script>

<style scoped>
.border-card {
  border: 1px solid #262b36;
}
</style>
