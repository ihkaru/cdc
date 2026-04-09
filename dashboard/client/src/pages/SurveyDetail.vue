<template>
  <q-page padding>
    <div class="row items-center q-mb-lg q-gutter-x-md">
      <q-btn round flat icon="arrow_back" to="/" />
      <div class="col">
        <h1 class="text-h4 text-weight-bold q-my-none">Survey Data</h1>
        <p class="text-grey-5 q-mt-xs">{{ surveyName || 'Loading...' }}</p>
      </div>
      <div class="q-gutter-x-sm">
        <q-btn
          color="accent"
          icon="insights"
          label="Visualizations"
          :to="`/survey/${surveyId}/visualizations`"
          unelevated
          no-caps
        />
        <q-btn
          color="teal"
          icon="download"
          label="Download Template"
          @click="downloadTemplate"
          :loading="downloading"
          unelevated
          no-caps
        />
        <q-btn
          color="green-7"
          icon="file_download"
          label="Export Excel"
          @click="exportToExcel"
          :loading="exporting"
          unelevated
          no-caps
        />
        <q-btn
          color="primary"
          icon="upload_file"
          label="Upload Label"
          @click="showUploadDialog = true"
          unelevated
          no-caps
        />
      </div>
    </div>

    <!-- Stats Banner -->
    <div class="row q-col-gutter-md q-mb-lg" v-if="stats">
      <div class="col-6 col-sm-3">
        <q-card class="bg-dark border-card text-center q-pa-md" flat bordered>
          <div class="text-grey-5 text-uppercase text-caption">Total Assignments</div>
          <div class="text-h4 text-weight-bold text-white">{{ stats.total }}</div>
        </q-card>
      </div>
      <div class="col-6 col-sm-3">
        <q-card class="bg-dark border-card text-center q-pa-md" flat bordered>
          <div class="text-grey-5 text-uppercase text-caption">Open / Draft</div>
          <div class="text-h4 text-weight-bold text-warning">{{ stats.open }}</div>
        </q-card>
      </div>
      <div class="col-6 col-sm-3">
        <q-card class="bg-dark border-card text-center q-pa-md" flat bordered>
          <div class="text-grey-5 text-uppercase text-caption">Submitted</div>
          <div class="text-h4 text-weight-bold text-positive">{{ stats.submitted }}</div>
        </q-card>
      </div>
      <div class="col-6 col-sm-3">
        <q-card class="bg-dark border-card text-center q-pa-md" flat bordered>
          <div class="text-grey-5 text-uppercase text-caption">Rejected / Error</div>
          <div class="text-h4 text-weight-bold text-negative">{{ stats.rejected }}</div>
        </q-card>
      </div>
    </div>

    <!-- Label stats -->
    <q-banner v-if="labelCount > 0" class="bg-grey-9 text-white q-mb-md rounded-borders" rounded>
      <template v-slot:avatar>
        <q-icon name="label" color="teal" />
      </template>
      <span class="text-body2">
        <b>{{ labelCount }}</b> data row(s) aktif untuk survey ini
        <span v-if="labelSchema"> dengan <b>{{ labelSchema.columns.length }}</b> kolom enrichment</span>
      </span>
      <template v-slot:action>
        <q-btn flat color="negative" label="Hapus Semua Label" size="sm" @click="clearLabels" no-caps />
      </template>
    </q-banner>

    <div class="row q-mb-md flex items-center justify-between">
      <q-input
        v-model="searchQuery"
        dense
        outlined
        dark
        placeholder="Cari data (identitas, user, atau isian data)..."
        debounce="500"
        class="col-12 col-sm-4 bg-dark"
        @update:model-value="onSearch"
      >
        <template v-slot:append>
          <q-icon name="search" />
        </template>
      </q-input>

      <div class="q-ml-sm row">
        <q-btn outline icon="view_column" label="Columns" no-caps color="primary" class="bg-dark">
          <q-menu dark class="bg-dark border-card" :offset="[0, 8]">
            <q-list style="min-width: 300px; max-height: 400px;" class="q-py-none">
              <q-item-label header class="text-grey-5 q-pb-sm sticky-header bg-dark">
                Tampilkan Kolom Data
                <q-input
                  v-model="colSearchQuery"
                  dense
                  outlined
                  dark
                  placeholder="Cari kolom..."
                  class="q-mt-xs bg-dark"
                  autofocus
                >
                  <template v-slot:prepend>
                    <q-icon name="search" size="xs" />
                  </template>
                  <template v-slot:append v-if="colSearchQuery">
                    <q-icon name="clear" size="xs" class="cursor-pointer" @click="colSearchQuery = ''" />
                  </template>
                </q-input>
              </q-item-label>
              
              <q-separator dark />
              
              <div class="scroll" style="max-height: 300px;">
                <q-item v-for="col in filteredAvailableColumns" :key="col.name" tag="label" v-ripple dense>
                  <q-item-section side top>
                    <q-checkbox v-model="visibleColumnKeys" :val="col.name" dark @update:model-value="saveColumnPreferences" size="sm" />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label class="text-body2">
                      {{ col.name }}
                      <!-- Icon Indicator for Image/Media columns -->
                      <q-icon v-if="col.name.toLowerCase().includes('foto') || col.name.toLowerCase().includes('image') || col.name.toLowerCase().includes('media')" name="image" size="xs" color="blue-4" class="q-ml-xs">
                        <q-tooltip>Kolom Gambar/Media</q-tooltip>
                      </q-icon>
                    </q-item-label>
                    <q-item-label caption class="text-grey-6">{{ col.type }}</q-item-label>
                  </q-item-section>
                </q-item>
                
                <q-item v-if="filteredAvailableColumns.length === 0" class="text-center q-pa-md text-grey-6">
                  <q-item-section>Kolom tidak ditemukan</q-item-section>
                </q-item>
              </div>
            </q-list>
          </q-menu>
        </q-btn>
      </div>
    </div>

    <q-card class="bg-dark border-card" flat bordered>
      <q-table
        dark
        flat
        :rows="assignments"
        :columns="computedColumns"
        row-key="id"
        :loading="loading"
        v-model:pagination="pagination"
        @request="onRequest"
        class="bg-transparent"
        :rows-per-page-options="[10, 20, 50]"
      >
        <template v-slot:body="props">
          <q-tr :props="props">
            <q-td v-for="col in props.cols" :key="col.name" :props="props">
              <!-- Column: Label Data / Enrichment -->
              <template v-if="col.name === 'labelData'">
                <div v-if="props.row.labelData && Object.keys(props.row.labelData).length > 0" class="row q-gutter-xs">
                  <q-badge
                    v-for="(val, key) in props.row.labelData"
                    :key="key"
                    color="teal"
                    rounded
                    class="q-px-sm q-py-xs"
                  >
                    {{ key }}: {{ val }}
                  </q-badge>
                </div>
                <span v-else class="text-grey-7">—</span>
              </template>

              <!-- Column: Status -->
              <template v-else-if="col.name === 'status'">
                <q-badge :color="badgeColor(props.row.assignmentStatusAlias)" rounded class="q-px-sm q-py-xs">
                  {{ props.row.assignmentStatusAlias }}
                </q-badge>
              </template>

              <!-- Column: Date -->
              <template v-else-if="col.name === 'date'">
                {{ formatDate(props.row.dateModifiedRemote) }}
              </template>

              <!-- Column: Attachments (Aggregated Media) -->
              <template v-else-if="col.name === 'attachments'">
                <div v-if="props.row.localImagePaths && Object.keys(props.row.localImagePaths).length > 0" class="row q-gutter-xs">
                  <q-btn 
                    v-for="(path, key) in props.row.localImagePaths" 
                    :key="key"
                    flat 
                    dense 
                    color="positive" 
                    icon="image" 
                    :label="key"
                    type="a" 
                    :href="`/storage/view/${path}`" 
                    target="_blank"
                    no-caps
                    size="sm"
                    class="bg-dark"
                    style="border: 1px solid #2ecc71"
                  >
                    <q-tooltip>View Image (Secured in Vault): {{ key }}</q-tooltip>
                  </q-btn>
                </div>
                <div v-else-if="hasUnmirroredImages(props.row)" class="row q-gutter-xs">
                   <!-- Fallback if there are image URLs in flatData but not yet mirrored -->
                   <q-btn
                     v-for="img in getUnmirroredImages(props.row)"
                     :key="img.key"
                     flat dense color="blue-4" icon="photo_library" :label="img.key"
                     type="a" :href="img.url" target="_blank" no-caps size="sm" class="bg-dark"
                     style="border: 1px solid #4ebaf0"
                   >
                     <q-tooltip>BPS Link (Not Mirrored Yet): {{ img.key }}</q-tooltip>
                   </q-btn>
                </div>
                <span v-else class="text-grey-7">—</span>
              </template>

              <!-- Generic Logic for Dynamic Columns (Detect URLs) -->
              <template v-else>
                <div v-if="typeof col.value === 'string' && col.value.startsWith('http')" class="ellipsis" style="max-width: 300px">
                  <q-btn 
                    flat 
                    dense 
                    :color="isMirrored(props.row, col.name) ? 'positive' : 'blue-4'" 
                    :icon="isMirrored(props.row, col.name) ? 'check_circle' : 'open_in_new'" 
                    :label="getImageLabel(props.row, col.name, col.value)"
                    type="a" 
                    :href="getImageUrl(props.row, col.name, col.value)" 
                    target="_blank"
                    no-caps
                    size="sm"
                  >
                    <q-tooltip>{{ isMirrored(props.row, col.name) ? 'Mirrored to CDC Vault (Verified)' : 'BPS Link (Likely 403 / Expired)' }}</q-tooltip>
                  </q-btn>
                </div>
                <span v-else>{{ col.value }}</span>
              </template>
            </q-td>
          </q-tr>
        </template>
      </q-table>
    </q-card>

    <!-- Workload Leaderboard -->
    <q-card class="bg-dark border-card q-mt-lg" flat bordered v-if="workloads && workloads.length > 0">
      <div class="q-pa-md row items-center no-wrap">
        <q-icon name="leaderboard" size="sm" class="q-mr-sm text-primary" />
        <div class="text-h6 text-white text-weight-medium">User Workload</div>
        <q-space />
        <div class="text-caption text-grey-5">Ranked by Pending (Open + Rejected)</div>
      </div>
      
      <q-table
        :rows="workloads"
        :columns="workloadCols"
        row-key="username"
        flat
        class="bg-dark text-white table-dark"
        hide-bottom
        :pagination="{ rowsPerPage: 0 }"
      >
        <template v-slot:body-cell-index="props">
          <q-td :props="props" class="text-grey-5">
            {{ props.rowIndex + 1 }}
          </q-td>
        </template>
        <template v-slot:body-cell-pending="props">
          <q-td :props="props">
            <q-badge color="negative" class="text-weight-bold" transparent>{{ props.row.pending }}</q-badge>
          </q-td>
        </template>
        <template v-slot:body-cell-open="props">
          <q-td :props="props">
            <span class="text-warning">{{ props.row.open }}</span>
          </q-td>
        </template>
        <template v-slot:body-cell-rejected="props">
          <q-td :props="props">
            <span class="text-negative">{{ props.row.rejected }}</span>
          </q-td>
        </template>
        <template v-slot:body-cell-completed="props">
          <q-td :props="props">
            <span class="text-positive">{{ props.row.completed }}</span>
          </q-td>
        </template>
      </q-table>
    </q-card>

    <!-- Upload Dialog -->
    <q-dialog v-model="showUploadDialog" persistent>
      <q-card style="min-width: 450px" class="bg-dark text-white">
        <q-card-section class="row items-center">
          <q-icon name="upload_file" size="sm" class="q-mr-sm" />
          <span class="text-h6">Upload Label Excel</span>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section>
          <div class="text-caption text-grey-5 q-mb-md">
            <ol class="q-pl-md q-my-none" style="line-height: 1.8">
              <li>Klik <b>"Download Template"</b> untuk mendapatkan file Excel</li>
              <li>Kolom pertama wajib bernama <b>code_identity</b></li>
              <li>Tambahkan kolom-kolom baru sesuka hati (misal: wilayah, skor, target) untuk enrichment & visualisasi</li>
              <li>Upload file yang sudah diisi di bawah</li>
            </ol>
          </div>

          <q-file
            v-model="uploadFile"
            label="Pilih file Excel (.xlsx)"
            accept=".xlsx,.xls"
            filled
            dark
            class="q-mb-md"
          >
            <template v-slot:prepend>
              <q-icon name="attach_file" />
            </template>
          </q-file>

          <q-banner v-if="uploadError" class="bg-negative text-white q-mb-sm rounded-borders" rounded dense>
            {{ uploadError }}
          </q-banner>
          <q-banner v-if="uploadSuccess" class="bg-positive text-white q-mb-sm rounded-borders" rounded dense>
            {{ uploadSuccess }}
          </q-banner>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Batal" v-close-popup no-caps />
          <q-btn
            color="primary"
            label="Upload"
            :loading="uploading"
            :disable="!uploadFile"
            @click="uploadLabels"
            unelevated
            no-caps
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useQuasar } from 'quasar'

interface ApiResponse<T> {
  data: T;
  pagination: {
    total: number;
    nextCursor?: string;
  };
}

const route = useRoute()
const $q = useQuasar()
const surveyId = route.params.id as string

const loading = ref(true)
const assignments = ref<any[]>([])
const stats = ref<any>(null)
const workloads = ref<any[]>([])
const surveyName = ref('')
const labelCount = ref(0)
const labelSchema = ref<any>(null)

// Upload state
const showUploadDialog = ref(false)
const uploadFile = ref<File | null>(null)
const uploading = ref(false)
const uploadError = ref('')
const uploadSuccess = ref('')
const downloading = ref(false)
const exporting = ref(false)

const pagination = ref({
  page: 1,
  rowsPerPage: 10,
  rowsNumber: 0
})

// Cursor history for prev/next navigation
// cursors[0] = undefined (first page), cursors[1] = cursor for page 2, etc.
const cursorHistory = ref<(string | undefined)[]>([undefined])

const searchQuery = ref('')
const colSearchQuery = ref('')
const allAvailableColumns = ref<any[]>([])
const visibleColumnKeys = ref<string[]>([])

const PREF_KEY = computed(() => `cdc_cols_${surveyId}`)

function loadColumnPreferences() {
  const saved = localStorage.getItem(PREF_KEY.value)
  if (saved) {
    try {
      visibleColumnKeys.value = JSON.parse(saved)
    } catch {}
  }
}

function saveColumnPreferences() {
  localStorage.setItem(PREF_KEY.value, JSON.stringify(visibleColumnKeys.value))
}

async function fetchSchema() {
  try {
     const res = await fetch(`/api/surveys/${surveyId}/visualizations/schema`)
     const data = await res.json()
     allAvailableColumns.value = data.columns || []
  } catch(e) { console.error('Failed to load full schema for columns') }
}

const filteredAvailableColumns = computed(() => {
  if (!colSearchQuery.value) return allAvailableColumns.value
  const q = colSearchQuery.value.toLowerCase()
  return allAvailableColumns.value.filter(col => 
    col.name.toLowerCase().includes(q)
  )
})

function onSearch() {
  pagination.value.page = 1
  cursorHistory.value = [undefined]
  onRequest({ pagination: pagination.value })
}

const computedColumns = computed(() => {
  const baseCols = [
    { name: 'identity', required: true, label: 'Code Identity', align: 'left' as const, field: 'codeIdentity' },
    { name: 'user', align: 'left' as const, label: 'Assigned User', field: 'currentUserUsername' },
    { name: 'status', align: 'left' as const, label: 'Status', field: 'assignmentStatusAlias' },
    { name: 'date', align: 'left' as const, label: 'Last Modified', field: 'dateModifiedRemote' },
    { name: 'attachments', align: 'left' as const, label: 'Attachments', field: 'attachments' }
  ]

  const dyCols = visibleColumnKeys.value
    .filter(key => key !== 'codeIdentity' && key !== 'assignmentStatusAlias' && key !== 'currentUserUsername' && key !== 'dateModifiedRemote')
    .map(key => {
      return {
        name: key,
        align: 'left' as const,
        label: key,
        field: (row: any) => {
           if (row.flatData && row.flatData[key] !== undefined) return row.flatData[key]
           if (row.labelData && row.labelData[key] !== undefined) return row.labelData[key]
           if (row[key] !== undefined) return row[key]
           return '-'
        }
      }
    })

  const enrichmentCol = { name: 'labelData', align: 'left' as const, label: 'Enrichment', field: 'labelData' }
  
  return [...baseCols, ...dyCols, enrichmentCol]
})

const workloadCols = [
  { name: 'index', label: '#', field: 'index', align: 'left' as const },
  { name: 'username', label: 'Assigned User', field: 'username', align: 'left' as const, sortable: true },
  { name: 'pending', label: 'Pending Action', field: 'pending', align: 'center' as const, sortable: true, sortOrder: 'dd' as const },
  { name: 'open', label: 'Open / Draft', field: 'open', align: 'center' as const, sortable: true },
  { name: 'rejected', label: 'Rejected', field: 'rejected', align: 'center' as const, sortable: true },
  { name: 'completed', label: 'Completed / Submitted', field: 'completed', align: 'center' as const, sortable: true },
  { name: 'total', label: 'Total Handled', field: 'total', align: 'center' as const, sortable: true }
]

function badgeColor(status: string) {
  if (status.includes('COMPLETED') || status.includes('UPLOADED')) return 'positive'
  if (status.includes('IN_PROGRESS') || status.includes('DRAFT')) return 'warning'
  return 'grey-8'
}

function formatDate(dateStr: string) {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return dateStr // Try to just return original if invalid
    return d.toLocaleString('id-ID')
  } catch {
    return dateStr
  }
}

function isMirrored(row: any, colName: string) {
  return row.localImageMirrored && row.localImagePaths && row.localImagePaths[colName]
}

function getImageLabel(row: any, colName: string, originalUrl: string) {
  const isImage = originalUrl.includes('foto') || colName.toLowerCase().includes('foto')
  if (isMirrored(row, colName)) return isImage ? 'View (Vault)' : 'Link (Vault)'
  return isImage ? 'View Image' : 'Link'
}

function getImageUrl(row: any, colName: string, originalUrl: string) {
  if (isMirrored(row, colName)) {
    // SeaweedFS path is bucket/key, proxy expects /storage/view/bucket/key
    return `/storage/view/${row.localImagePaths[colName]}`
  }
  return originalUrl
}

function getUnmirroredImages(row: any) {
  if (!row.flatData) return []
  const imgs = []
  for (const [key, value] of Object.entries(row.flatData)) {
    if (typeof value === 'string' && value.startsWith('http')) {
      const vLower = value.toLowerCase()
      const kLower = key.toLowerCase()
      if (vLower.includes('.jpg') || vLower.includes('.jpeg') || vLower.includes('.png') || 
          kLower.includes('foto') || kLower.includes('image') || kLower.includes('media')) {
        // Skip if this image is already in the mirrored vault
        if (row.localImagePaths && row.localImagePaths[key]) continue
        imgs.push({ key, url: value })
      }
    }
  }
  return imgs
}

function hasUnmirroredImages(row: any) {
  return getUnmirroredImages(row).length > 0
}

async function loadStatsAndSurvey() {
  try {
    const [statsRes, surveyRes, labelsRes, schemaRes, workloadRes] = await Promise.all([
      fetch(`/api/surveys/${surveyId}/stats`),
      fetch(`/api/surveys/${surveyId}`),
      fetch(`/api/surveys/${surveyId}/labels?limit=1`),
      fetch(`/api/surveys/${surveyId}/labels/schema`),
      fetch(`/api/surveys/${surveyId}/workload`)
    ])
    stats.value = await statsRes.json()
    const survey = await surveyRes.json()
    surveyName.value = survey.surveyName
    const labelsData = await labelsRes.json() as ApiResponse<any>
    labelCount.value = labelsData?.pagination?.total || 0
    labelSchema.value = await schemaRes.json()
    workloads.value = await workloadRes.json()
  } catch (e) {
    console.error('Failed to load stats')
  }
}

async function onRequest(props: any) {
  const { page, rowsPerPage } = props.pagination
  loading.value = true
  try {
    // If rowsPerPage changed, reset all cursor history (cursors are page-size-specific)
    if (rowsPerPage !== pagination.value.rowsPerPage) {
      cursorHistory.value = [undefined]
    }

    // Determine which cursor to use based on page direction
    // cursors are tracked in cursorHistory array indexed by page number (0-based)
    const pageIdx = page - 1
    
    // Grow cursor history array if needed
    while (cursorHistory.value.length <= pageIdx) {
      cursorHistory.value.push(undefined)
    }
    
    const cursor = cursorHistory.value[pageIdx]
    const cursorParam = cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''
    const searchParam = searchQuery.value ? `&q=${encodeURIComponent(searchQuery.value)}` : ''
    
    const res = await fetch(`/api/surveys/${surveyId}/assignments?limit=${rowsPerPage}${cursorParam}${searchParam}&page=${page}`)
    const data = await res.json() as ApiResponse<any[]>
    console.log('🔍 CDC Debug: Assignments payload:', data.data)
    if (data.data.length > 0) {
      const first = data.data[0]
      console.log('🔍 CDC Debug: First record mirror status:', {
        id: first.id,
        localImageMirrored: first.localImageMirrored,
        hasPaths: !!first.localImagePaths,
        keys: first.localImagePaths ? Object.keys(first.localImagePaths) : []
      })
    }
    assignments.value = data.data
    pagination.value.rowsNumber = data.pagination.total
    pagination.value.page = page
    pagination.value.rowsPerPage = rowsPerPage
    
    // Store the next cursor for the NEXT page
    if (data.pagination.nextCursor) {
      cursorHistory.value[pageIdx + 1] = data.pagination.nextCursor
    }
  } catch (e) {
    console.error('Failed to load assignments')
  } finally {
    loading.value = false
  }
}


async function downloadTemplate() {
  downloading.value = true
  try {
    // Use same-window navigation — Content-Disposition: attachment prevents
    // page replacement and triggers a proper download with correct filename
    window.location.href = `/api/surveys/${surveyId}/labels/template`
  } catch {
    $q.notify({ type: 'negative', message: 'Gagal download template' })
  } finally {
    setTimeout(() => { downloading.value = false }, 1000)
  }
}

async function exportToExcel() {
  exporting.value = true
  try {
    const searchParam = searchQuery.value ? `?q=${encodeURIComponent(searchQuery.value)}` : ''
    // Directly trigger download via window.location.href to handle Buffer response
    window.location.href = `/api/surveys/${surveyId}/assignments/export${searchParam}`
  } catch {
    $q.notify({ type: 'negative', message: 'Gagal export data' })
  } finally {
    setTimeout(() => { exporting.value = false }, 2000)
  }
}

async function uploadLabels() {
  if (!uploadFile.value) return
  uploading.value = true
  uploadError.value = ''
  uploadSuccess.value = ''

  const formData = new FormData()
  formData.append('file', uploadFile.value)

  try {
    const res = await fetch(`/api/surveys/${surveyId}/labels/upload`, {
      method: 'POST',
      body: formData,
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Upload gagal')
    uploadSuccess.value = data.message
    uploadFile.value = null
    // Refresh data
    loadStatsAndSurvey()
    onRequest({ pagination: pagination.value })
  } catch (e: any) {
    uploadError.value = e.message
  } finally {
    uploading.value = false
  }
}

async function clearLabels() {
  $q.dialog({
    title: 'Hapus Semua Label',
    message: 'Yakin ingin menghapus semua label untuk survey ini?',
    cancel: true,
    persistent: true,
    dark: true
  }).onOk(async () => {
    try {
      await fetch(`/api/surveys/${surveyId}/labels`, { method: 'DELETE' })
      $q.notify({ type: 'info', message: 'Semua label dihapus' })
      labelCount.value = 0
      onRequest({ pagination: pagination.value })
    } catch {
      $q.notify({ type: 'negative', message: 'Gagal menghapus label' })
    }
  })
}

onMounted(() => {
  loadColumnPreferences()
  fetchSchema()
  loadStatsAndSurvey()
  onRequest({ pagination: pagination.value })
})
</script>

<style scoped>
.border-card {
  border: 1px solid #262b36;
}
.sticky-header {
  position: sticky;
  top: 0;
  z-index: 1;
  border-bottom: 1px solid #262b36;
}
</style>
