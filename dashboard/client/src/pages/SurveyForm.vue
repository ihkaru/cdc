<template>
  <q-page padding class="row justify-center">
    <div style="max-width: 800px; width: 100%">
      <div class="row items-center q-mb-lg q-gutter-x-md">
        <q-btn round flat icon="arrow_back" to="/" />
        <h1 class="text-h4 text-weight-bold q-my-none">{{ isEdit ? 'Edit Survey' : 'New Survey Wizard' }}</h1>
      </div>

      <div v-if="loading" class="text-center q-py-xl">
        <q-spinner size="3em" color="primary" />
        <div class="q-mt-md text-grey">Loading data...</div>
      </div>
      
      <q-card v-else class="bg-dark text-white border-card" flat bordered>
        <q-stepper
          v-model="step"
          ref="stepper"
          class="bg-dark text-white"
          dark
          animated
          active-color="primary"
          done-color="positive"
        >
          <!-- STEP 1: SSO Authentication -->
          <q-step
            :name="1"
            title="SSO Credentials"
            icon="admin_panel_settings"
            :done="step > 1"
          >
            <div class="text-subtitle1 q-mb-md">Masukkan Kredensial SSO BPS</div>
            <p class="text-grey-5 text-body2 q-mb-lg">
              Sistem akan login ke FASIH menggunakan kredensial ini untuk mengambil daftar survei dan wilayah yang tersedia.
            </p>

            <div class="row q-col-gutter-md">
              <div class="col-12 col-md-6">
                <div class="text-subtitle2 text-grey-5 q-mb-xs">Username SSO</div>
                <q-input v-model="form.ssoUsername" dark filled placeholder="NIP / Username" />
              </div>
              <div class="col-12 col-md-6">
                <div class="text-subtitle2 text-grey-5 q-mb-xs">Password SSO</div>
                <q-input v-model="form.ssoPassword" dark filled type="password" 
                  :placeholder="isEdit ? '(Dikosongkan jika tidak ingin ganti)' : 'Password'" />
              </div>
            </div>

            <q-stepper-navigation class="row justify-end q-mt-lg">
              <q-btn
                @click="onConnectFasih"
                color="primary"
                :loading="connecting"
                :disable="!form.ssoUsername || (!isEdit && !form.ssoPassword)"
                label="Hubungkan ke FASIH"
                icon-right="link"
                unelevated
              >
                <template v-slot:loading>
                  <q-spinner-hourglass class="on-left" />
                  Connecting (~15s)...
                </template>
              </q-btn>
            </q-stepper-navigation>
          </q-step>

          <!-- STEP 2: Survey & Region Selection -->
          <q-step
            :name="2"
            title="Survey & Wilayah"
            icon="map"
            :done="step > 2"
          >
            <div class="text-subtitle1 q-mb-md">Pilih Target Sinkronisasi</div>
            <p class="text-grey-5 text-body2 q-mb-lg">
              Data ditarik langsung dari API FASIH. Jika survei tidak muncul, berarti akun SSO tidak memiliki akses pada survei aktif.
            </p>

            <div class="q-col-gutter-y-md">
              <div>
                <div class="text-subtitle2 text-grey-5 q-mb-xs">Survey FASIH</div>
                <q-select
                  v-model="form.surveyName"
                  :options="surveyOptions"
                  dark filled
                  option-label="name"
                  option-value="name"
                  emit-value
                  map-options
                  use-input
                  @filter="filterSurveys"
                  hint="Pilih survei untuk disinkronkan"
                >
                  <template v-slot:no-option>
                    <q-item><q-item-section class="text-grey">No surveys found</q-item-section></q-item>
                  </template>
                </q-select>
              </div>

              <div class="row q-col-gutter-md">
                <div class="col-12 col-md-6">
                  <div class="text-subtitle2 text-grey-5 q-mb-xs">Filter Provinsi (Optional)</div>
                  <q-select
                    v-model="selectedProvinsi"
                    :options="provinsiOptions"
                    dark filled
                    clearable
                    option-label="name"
                    use-input
                    @filter="filterProvinsi"
                    @update:model-value="onProvinsiChange"
                    hint="Wilayah tingkat provinsi"
                  />
                </div>
                <div class="col-12 col-md-6">
                  <div class="text-subtitle2 text-grey-5 q-mb-xs">Filter Kabupaten (Optional)</div>
                  <q-select
                    v-model="selectedKabupaten"
                    :options="kabupatenOptions"
                    dark filled
                    clearable
                    option-label="name"
                    :loading="loadingKabupaten"
                    :disable="!selectedProvinsi || loadingKabupaten"
                    use-input
                    @filter="filterKabupaten"
                    @update:model-value="onKabupatenChange"
                    hint="Pilih provinsi terlebih dahulu"
                  />
                </div>
              </div>
            </div>

            <q-stepper-navigation class="row justify-between q-mt-lg">
              <q-btn flat @click="step = 1" color="grey" label="Back" class="q-ml-sm" />
              <q-btn
                @click="step = 3"
                color="primary"
                label="Lanjut Konfigurasi"
                :disable="!form.surveyName"
                unelevated
              />
            </q-stepper-navigation>
          </q-step>

          <!-- STEP 3: System Config -->
          <q-step
            :name="3"
            title="Konfigurasi"
            icon="settings"
          >
            <div class="text-subtitle1 q-mb-md">Pengaturan Sinkronisasi</div>

            <div class="row q-col-gutter-md">
              <div class="col-12 col-md-6">
                <div class="text-subtitle2 text-grey-5 q-mb-xs">Rotasi Filter API</div>
                <q-select 
                  v-model="form.filterRotation" 
                  :options="rotationOptions" 
                  dark filled emit-value map-options 
                  hint="Jika hasil pencarian > 1000, pilih 'Per Pencacah'"
                />
              </div>
              <div class="col-12 col-md-6">
                <div class="text-subtitle2 text-grey-5 q-mb-xs">Interval (Menit)</div>
                <q-input v-model.number="form.intervalMinutes" type="number" dark filled min="5" />
              </div>
            </div>

            <div class="row justify-between items-center q-mt-lg q-pa-md border-card rounded-borders" style="background: rgba(255,255,255,0.02)">
              <div>
                <div class="text-weight-bold">Status Aktif</div>
                <div class="text-caption text-grey-5">Izinkan penjadwalan n8n untuk trigger sinkronisasi otomatis</div>
              </div>
              <q-toggle v-model="form.isActive" color="positive" keep-color />
            </div>

            <q-stepper-navigation class="row justify-between q-mt-xl">
              <q-btn flat @click="step = 2" color="grey" label="Back" class="q-ml-sm" />
              <q-btn
                @click="save"
                color="positive"
                :loading="saving"
                label="Simpan Konfigurasi"
                icon="save"
                unelevated
              />
            </q-stepper-navigation>
          </q-step>
        </q-stepper>
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
const connecting = ref(false)
const loadingKabupaten = ref(false)
const step = ref(1)

// --- FASIH Data State ---
const rawSurveys = ref<any[]>([])
const surveyOptions = ref<any[]>([])

const rawProvinsi = ref<any[]>([])
const provinsiOptions = ref<any[]>([])

const rawKabupaten = ref<any[]>([])
const kabupatenOptions = ref<any[]>([])

// Component modeled objects for q-select
const selectedProvinsi = ref<{name: string, fullCode: string} | null>(null)
const selectedKabupaten = ref<{name: string, fullCode: string} | null>(null)

const rotationOptions = [
  { label: 'Per Pengawas (Cepat)', value: 'pengawas' },
  { label: 'Per Pencacah (Aman/Detail)', value: 'pencacah' }
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
    // Populate form
    form.value = { ...data, ssoPassword: '' }
    
    // In edit mode, if we have filter values but no API context yet, 
    // we make synthetic objects so they display nicely.
    if (form.value.filterProvinsi) {
      selectedProvinsi.value = { 
        name: form.value.filterProvinsi, 
        fullCode: form.value.filterProvinsi.match(/\[(\d+)\]/)?.[1] || '' 
      }
    }
    if (form.value.filterKabupaten) {
      selectedKabupaten.value = { 
        name: form.value.filterKabupaten, 
        fullCode: form.value.filterKabupaten.match(/\[(\d+)\]/)?.[1] || '' 
      }
    }

    // Set survey option manually (so it shows directly)
    rawSurveys.value = [{ name: form.value.surveyName }]
    surveyOptions.value = rawSurveys.value

    // Skip directly to config step 3 on edit by default
    step.value = 3
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Failed to load survey' })
    router.push('/')
  } finally {
    loading.value = false
  }
}

// === STEP 1: Connect to FASIH ===
async function onConnectFasih() {
  connecting.value = true
  try {
    const res = await fetch('/api/surveys/fasih/lookup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ssoUsername: form.value.ssoUsername,
        ssoPassword: form.value.ssoPassword
      })
    })

    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.message || 'Login FASIH gagal')
    }

    const data = await res.json()
    
    // Process Surveys
    rawSurveys.value = data.surveys || []
    surveyOptions.value = [...rawSurveys.value]
    
    // Process Provinsi
    // Prefix the name with code to match legacy string format 
    // "[61] KALIMANTAN BARAT" as requested by existing system
    rawProvinsi.value = (data.provinces || []).map((p: any) => ({
      ...p,
      name: `[${p.fullCode}] ${p.name}`
    }))
    provinsiOptions.value = [...rawProvinsi.value]

    $q.notify({ type: 'positive', message: `Berhasil login! Menemukan ${rawSurveys.value.length} survey.` })
    step.value = 2 // Move to next step
  } catch (e: any) {
    $q.notify({ type: 'negative', message: e.message || 'Terjadi kesalahan jaringan' })
  } finally {
    connecting.value = false
  }
}

// === Select Handlers ===
function onProvinsiChange(val: any) {
  form.value.filterProvinsi = val ? val.name : ''
  selectedKabupaten.value = null
  form.value.filterKabupaten = ''
  
  if (val) {
    loadKabupaten(val.fullCode)
  }
}

function onKabupatenChange(val: any) {
  form.value.filterKabupaten = val ? val.name : ''
}

async function loadKabupaten(provFullCode: string) {
  loadingKabupaten.value = true
  rawKabupaten.value = []
  kabupatenOptions.value = []
  
  try {
    const res = await fetch('/api/surveys/fasih/kabupaten', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ssoUsername: form.value.ssoUsername,
        ssoPassword: form.value.ssoPassword,
        provFullCode: provFullCode
      })
    })

    if (res.ok) {
      const data = await res.json()
      rawKabupaten.value = (data.kabupaten || []).map((k: any) => ({
        ...k,
        name: `[${k.fullCode.substring(2)}] ${k.name}` // [04] MEMPAWAH
      }))
      kabupatenOptions.value = [...rawKabupaten.value]
    }
  } catch (e) {
    console.error('Failed to load kabupaten:', e)
    $q.notify({ type: 'warning', message: 'Gagal memuat daftar kabupaten' })
  } finally {
    loadingKabupaten.value = false
  }
}

// === Filtering for Search Inputs ===
function filterSurveys(val: string, update: Function) {
  if (val === '') {
    update(() => { surveyOptions.value = rawSurveys.value })
    return
  }
  update(() => {
    const needle = val.toLowerCase()
    surveyOptions.value = rawSurveys.value.filter(v => v.name.toLowerCase().includes(needle))
  })
}

function filterProvinsi(val: string, update: Function) {
  if (val === '') {
    update(() => { provinsiOptions.value = rawProvinsi.value })
    return
  }
  update(() => {
    const needle = val.toLowerCase()
    provinsiOptions.value = rawProvinsi.value.filter(v => v.name.toLowerCase().includes(needle))
  })
}

function filterKabupaten(val: string, update: Function) {
  if (val === '') {
    update(() => { kabupatenOptions.value = rawKabupaten.value })
    return
  }
  update(() => {
    const needle = val.toLowerCase()
    kabupatenOptions.value = rawKabupaten.value.filter(v => v.name.toLowerCase().includes(needle))
  })
}

// === Save to Dashboard DB ===
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
      $q.notify({ type: 'positive', message: 'Survey berhasil disimpan' })
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
