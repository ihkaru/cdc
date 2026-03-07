<template>
  <q-card class="bg-dark border-card column" style="height: 100%; min-height: 200px" flat bordered>
    <q-card-section class="row items-center q-pb-none">
      <q-icon name="drag_indicator" class="q-mr-sm drag-handle cursor-grab" color="grey-6" size="sm" />
      <div class="text-h6 text-weight-medium">{{ viz.name }}</div>
      <q-space />
      <q-btn flat round dense icon="edit" color="primary" class="q-mr-sm" @click="$emit('edit', viz)" />
      <q-btn flat round dense icon="delete" color="grey-6" @click="$emit('delete', viz.id)" />
    </q-card-section>
    
    <q-card-section v-if="loading" class="col flex flex-center">
      <q-spinner color="primary" size="2em" />
    </q-card-section>
    
    <q-card-section v-else-if="data && !data.error" class="col column justify-center q-pa-md">
      <!-- Scorecard -->
      <div v-if="viz.chartType === 'scorecard'" class="text-center">
        <div class="text-grey-5">{{ data.label }}</div>
        <div class="text-h3 text-weight-bold text-teal q-mt-sm">{{ formatNumber(data.value) }}</div>
      </div>
      
      <!-- Data Table -->
      <div v-else-if="viz.chartType === 'data_table'" style="height: 350px; width: 100%; max-height: 350px; overflow: auto;">
        <q-table
          :rows="data.rows"
          :columns="data.columns"
          row-key="category"
          dark
          flat
          hide-bottom
          :pagination="{ rowsPerPage: 0 }"
          class="bg-transparent"
        />
      </div>
      <template v-else-if="viz.chartType === 'map_point'">
        <VizMapLibre :viz="viz" :data="data" :loading="loading" />
      </template>
      <template v-else>
        <!-- Bar Charts -->
        <div style="height: 350px; width: 100%;">
          <v-chart class="chart" :option="getChartOption(viz, data)" autoresize />
        </div>
      </template>
    </q-card-section>

    <q-card-section v-else class="col flex flex-center text-negative">
      Error loading data
    </q-card-section>
  </q-card>
</template>

<script setup lang="ts">
import VChart from 'vue-echarts'
import { getChartOption, formatNumber } from '../../utils/chartOptions'
import VizMapLibre from './VizMapLibre.vue'

const props = defineProps<{
  viz: any
  data: any
  loading: boolean
}>()

defineEmits<{
  (e: 'edit', viz: any): void
  (e: 'delete', vizId: number): void
}>()
</script>

<style scoped>
.border-card {
  border: 1px solid #262b36;
}
.chart {
  width: 100%;
  height: 100%;
}
.drag-handle {
  pointer-events: auto !important;
  cursor: grab !important;
}
.drag-handle:active {
  cursor: grabbing !important;
}
</style>
