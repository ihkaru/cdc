<template>
  <q-page padding>
    <div class="row items-center q-mb-lg q-gutter-x-md">
      <q-btn round flat icon="arrow_back" :to="`/survey/${surveyId}`" />
      <div class="col">
        <h1 class="text-h4 text-weight-bold q-my-none">Custom Visualizations</h1>
        <p class="text-grey-5 q-mt-xs">{{ surveyName || 'Loading...' }}</p>
      </div>
      <div class="row q-gutter-x-sm">
        <q-btn
          :color="copySuccess ? 'positive' : 'teal-8'"
          :icon="copySuccess ? 'check_circle' : 'auto_awesome'"
          :label="copySuccess ? 'Copied!' : 'Context Prompt'"
          @click="copyAIContext"
          :loading="copyingAI"
          unelevated
          no-caps
          style="min-width: 160px; transition: all 0.3s ease;"
        >
          <q-tooltip class="bg-teal">Copy Markdown Schema Data ke Clipboard untuk AI</q-tooltip>
        </q-btn>
        <q-btn
          color="warning"
          text-color="dark"
          icon="electric_bolt"
          label="Magic Import"
          @click="openBulkDialog"
          unelevated
          no-caps
        >
          <q-tooltip class="bg-warning text-dark">Bulk Import JSON Array dari AI Sekaligus</q-tooltip>
        </q-btn>
        <q-btn
          color="primary"
          icon="add"
          label="Add Visualization"
          @click="addEditDialogRef?.openAddDialog()"
          unelevated
          no-caps
        />
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="!loading && visualizations.length === 0" class="text-center q-pa-xl">
      <q-icon name="insights" size="100px" color="grey-8" />
      <h3 class="text-h5 text-grey-5 q-mt-md">Belum ada visualisasi</h3>
      <p class="text-grey-6">Tambahkan visualisasi baru untuk melihat progress data enrichment Anda.</p>
    </div>

    <!-- Widgets Grid -->
    <draggable
      v-else
      v-model="visualizations"
      item-key="id"
      handle=".drag-handle"
      @end="onReorder"
      :animation="200"
      ghost-class="ghost-card"
      class="row q-col-gutter-md w-full"
    >
      <template #item="{ element: viz }">
        <div :class="viz.chartType === 'scorecard' ? 'col-12 col-sm-6 col-md-3' : 'col-12 col-md-6'">
          <VizCard
            :viz="viz"
            :data="vizData[viz.id]"
            :loading="loadingData[viz.id] || false"
            @edit="addEditDialogRef?.openEditDialog($event)"
            @delete="deleteViz"
          />
        </div>
      </template>
    </draggable>

    <!-- Add/Edit Dialog -->
    <VizAddEditDialog
      ref="addEditDialogRef"
      :labelSchema="labelSchema"
      :visualizations="visualizations"
      :fetchVizData="fetchVizData"
    />

    <!-- Bulk Import Dialog -->
    <VizBulkImportDialog
      v-model="showBulkDialog"
      v-model:jsonStr="bulkJsonStr"
      :loading="importingBulk"
      @submit="submitBulkImport"
    />

  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useQuasar } from 'quasar'

// ECharts setup
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
import VChart, { THEME_KEY } from 'vue-echarts'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import { provide } from 'vue'

import { useVisualizationData } from '../composables/visualizations/useVisualizationData'
import { useBulkImport } from '../composables/visualizations/useBulkImport'
import VizCard from '../components/visualizations/VizCard.vue'
import VizAddEditDialog from '../components/visualizations/VizAddEditDialog.vue'
import VizBulkImportDialog from '../components/visualizations/VizBulkImportDialog.vue'
import VizPreviewCanvas from '../components/visualizations/VizPreviewCanvas.vue'
import draggable from 'vuedraggable'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent])
provide(THEME_KEY, 'dark')

import { formatNumber, getChartOption } from '../utils/chartOptions'

const route = useRoute()
const $q = useQuasar()
const surveyId = route.params.id as string

const addEditDialogRef = ref<any>(null)

const {
  surveyName,
  loading,
  labelSchema,
  visualizations,
  vizData,
  loadingData,
  loadData,
  fetchVizData
} = useVisualizationData(surveyId)

const {
  showBulkDialog,
  bulkJsonStr,
  importingBulk,
  openBulkDialog,
  submitBulkImport
} = useBulkImport(visualizations, fetchVizData)

const filterOperators = [
  { label: '=', value: 'equals' },
  { label: '!=', value: 'not_equals' },
  { label: 'Contains', value: 'contains' },
  { label: '>', value: 'greater_than' },
  { label: '<', value: 'less_than' }
]

const showAddDialog = ref(false)
const isEditing = ref(false)
const editingVizId = ref<number | null>(null)
const configTab = ref('form')
const jsonConfigStr = ref('{}')

const previewData = ref<any>(null)
const previewLoading = ref(false)
let previewTimeout: any = null
const saving = ref(false)
const saveError = ref('')
const copyingAI = ref(false)
const copySuccess = ref(false)


async function copyAIContext() {
  copyingAI.value = true
  try {
    const res = await fetch(`/api/surveys/${surveyId}/visualizations/ai-context`)
    if (!res.ok) throw new Error('Gagal mengambil data AI')
    const json = await res.json() as any
    if (json.markdown) {
      await (navigator as any).clipboard.writeText(json.markdown)
      $q.notify({ type: 'positive', message: 'Prompt tercopy ke Clipboard! Salin ke ChatGPT / Gemini.', icon: 'auto_awesome' })
      copySuccess.value = true
      setTimeout(() => { copySuccess.value = false }, 2000)
    }
  } catch (e: any) {
    $q.notify({ type: 'negative', message: 'Gagal menyalin context: ' + e.message })
  } finally {
    copyingAI.value = false
  }
}





async function deleteViz(vizId: number) {
  $q.dialog({
    title: 'Hapus Visualisasi',
    message: 'Yakin ingin menghapus visualisasi ini?',
    cancel: true,
    persistent: true,
    dark: true
  }).onOk(async () => {
    try {
      await fetch(`/api/surveys/${surveyId}/visualizations/${vizId}`, { method: 'DELETE' })
      visualizations.value = visualizations.value.filter(v => v.id !== vizId)
      delete vizData.value[vizId]
      $q.notify({ type: 'info', message: 'Visualisasi dihapus' })
    } catch {
      $q.notify({ type: 'negative', message: 'Gagal menghapus visualisasi' })
    }
  })
}



async function onReorder() {
  const payload = visualizations.value.map((viz, index) => ({
    id: viz.id,
    sortOrder: index
  }))

  try {
    const res = await fetch(`/api/surveys/${surveyId}/visualizations/reorder`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    
    if (!res.ok) {
      throw new Error('Gagal menyimpan urutan')
    }
    
    $q.notify({ type: 'positive', message: 'Urutan visualisasi berhasil disimpan', position: 'bottom-right' })
  } catch (e: any) {
    $q.notify({ type: 'negative', message: e.message })
    // Reload data to revert to original order if API call fails
    loadData()
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.border-card {
  border: 1px solid #262b36;
}
.border-top-grey {
  border-top: 1px solid #424242;
}
.pt-md {
  padding-top: 16px;
}
.font-monospace {
  font-family: monospace;
}
.ghost-card {
  opacity: 0.5;
  background: #2a2f3b !important;
  border: 1px dashed #424242 !important;
  transform: scale(0.98);
}
.sortable-drag {
  box-shadow: 0 10px 20px rgba(0,0,0,0.5) !important;
  z-index: 1000;
}
</style>
