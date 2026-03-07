<template>
  <q-card class="col bg-grey-10 flex flex-center relative-position" flat bordered style="border: 2px dashed #424242; border-radius: 8px;">
    <q-inner-loading :showing="previewLoading" dark>
      <q-spinner color="primary" size="3em" />
    </q-inner-loading>

    <div v-if="previewData && !previewData.error" class="full-width full-height flex flex-center q-pa-md">
      <!-- Scorecard Preview -->
      <div v-if="newViz.chartType === 'scorecard'" class="text-center">
        <div class="text-grey-5 text-h6">{{ previewData.label }}</div>
        <div class="text-weight-bold text-teal" style="font-size: 5rem; line-height: 1;">{{ formatNumber(previewData.value) }}</div>
      </div>

      <!-- Data Table Preview -->
      <div v-else-if="newViz.chartType === 'data_table'" class="full-width full-height">
        <q-table
          :rows="previewData.rows"
          :columns="previewData.columns"
          row-key="category"
          dark
          flat
          class="bg-transparent"
          :pagination="{ rowsPerPage: 10 }"
        />
      </div>

      <!-- Map Point Preview -->
      <div v-else-if="newViz.chartType === 'map_point'" class="full-width full-height">
        <VizMapLibre :viz="newViz" :data="previewData" :loading="previewLoading" />
      </div>
      
      <!-- Bar Chart Preview -->
      <div v-else class="full-width full-height">
        <v-chart class="chart" :option="getChartOption(newViz, previewData)" autoresize />
      </div>
    </div>
    
    <div v-else-if="previewData?.error" class="text-warning text-center">
      <q-icon name="warning" size="xl" class="q-mb-sm" />
      <div class="text-h6">Preview Gagal Dimuat</div>
      <div class="text-grey-5">Pastikan kolom yang Anda pilih valid dan memiliki format yang sesuai.</div>
    </div>
    
    <div v-else class="text-grey-6 text-center text-italic">
      <q-icon name="model_training" size="xl" class="q-mb-sm opacity-50" />
      <div class="text-h6">SQL Engine Siap</div>
      <div class="text-grey-5">Gunakan panel di kiri. Server akan merender hasil agregasi secara presisi.</div>
    </div>
  </q-card>
</template>

<script setup lang="ts">
import VChart from 'vue-echarts'
import { computed } from 'vue'
import { formatNumber, getChartOption } from '../../utils/chartOptions'
import VizMapLibre from './VizMapLibre.vue'

const props = defineProps<{
  newViz: any
  previewData: any
  previewLoading: boolean
}>()
</script>

<style scoped>
.chart {
  width: 100%;
  height: 100%;
}
</style>
