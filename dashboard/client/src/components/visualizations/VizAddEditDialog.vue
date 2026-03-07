<template>
  <q-dialog v-model="form.showAddDialog.value" persistent maximized transition-show="slide-up" transition-hide="slide-down">
    <q-card class="bg-dark text-white column">
      <q-card-section class="row items-center q-pb-none">
        <q-icon name="add_chart" size="md" class="q-mr-sm" />
        <span class="text-h5 text-weight-bold">{{ form.isEditing.value ? 'Edit Visualisasi' : 'Konfigurasi Visualisasi BI Advanced' }}</span>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>

      <q-card-section class="col row q-pa-lg q-col-gutter-lg" style="overflow: hidden; min-height: 0;">
        <!-- Left Column: Config Form -->
        <div class="col-12 col-md-5 column" style="height: 100%; min-height: 0; overflow-y: auto; overflow-x: hidden;">
          <q-tabs v-model="form.configTab.value" dense class="text-grey" active-color="primary" indicator-color="primary" align="left" narrow-indicator>
            <q-tab name="form" label="UI Builder" />
            <q-tab name="json" label="JSON Editor" />
          </q-tabs>
          <q-separator dark class="q-mb-md" />

          <q-tab-panels v-model="form.configTab.value" animated class="bg-transparent text-white col column">
            <!-- Panel UI Form -->
            <q-tab-panel name="form" class="q-pa-none column full-height" style="overflow-y: auto; overflow-x: hidden;">
              <div class="text-subtitle1 text-grey-4 q-mb-md font-weight-bold">Pengaturan Utama</div>
              
              <q-input v-model="form.newViz.value.name" label="Nama Visualisasi" dark filled class="q-mb-md" />
              
              <q-select 
                v-model="form.newViz.value.chartType" 
                :options="[
                  {label: 'Scorecard (Item Tunggal)', value: 'scorecard'},
                  {label: 'Tabel Data Grid', value: 'data_table'},
                  {label: 'Bar Chart (Vertikal)', value: 'bar_vertical'},
                  {label: 'Bar Chart (Horizontal)', value: 'bar_horizontal'},
                  {label: 'Peta Sebaran (WebGL)', value: 'map_point'}
                ]"
                label="Tipe Chart" 
                dark filled emit-value map-options class="q-mb-md" 
              />

              <!-- Dimensi -->
              <template v-if="form.newViz.value.chartType !== 'scorecard' && form.newViz.value.chartType !== 'map_point'">
                <div class="text-subtitle1 text-grey-4 q-mt-md q-mb-sm font-weight-bold border-top-grey pt-md">Dimensi (Kategori / Baris)</div>
                
                <q-select 
                  v-model="form.newViz.value.config.xColumn" :options="form.filteredDimensionColumns.value" 
                  label="Kolom Utama (X-Axis)" dark filled emit-value map-options
                  use-input input-debounce="0" @filter="form.filterDimension" class="q-mb-sm"
                >
                  <template v-slot:no-option><q-item><q-item-section class="text-italic text-grey">Tidak ada kolom teks/kategori</q-item-section></q-item></template>
                </q-select>

                <q-select 
                  v-model="form.newViz.value.config.groupBy" :options="form.filteredDimensionColumns.value" 
                  label="Group By / Sub-Kategori (Opsional)" dark filled clearable emit-value map-options
                  use-input input-debounce="0" @filter="form.filterDimension"
                >
                  <template v-slot:no-option><q-item><q-item-section class="text-italic text-grey">Tidak ada kolom teks/kategori</q-item-section></q-item></template>
                </q-select>
              </template>

              <!-- Map Configuration -->
              <template v-if="form.newViz.value.chartType === 'map_point'">
                <div class="text-subtitle1 text-grey-4 q-mt-md q-mb-sm font-weight-bold border-top-grey pt-md">Koordinat (Latitude & Longitude)</div>
                <div class="row q-col-gutter-sm q-mb-md">
                  <div class="col-6">
                    <q-select 
                      v-model="form.newViz.value.config.latColumn" :options="form.filteredAllColumns.value" 
                      label="Kolom Latitude" dark filled emit-value map-options
                      use-input input-debounce="0" @filter="form.filterAll"
                    >
                      <template v-slot:option="scope">
                        <q-item v-bind="scope.itemProps">
                          <q-item-section>
                            <q-item-label>{{ scope.opt.label }}</q-item-label>
                            <q-item-label caption class="text-teal" v-if="scope.opt.sample">{{ scope.opt.sample }}</q-item-label>
                          </q-item-section>
                          <q-item-section side><q-badge :color="scope.opt.type === 'measure' ? 'blue-8' : 'grey-7'" :label="scope.opt.type" /></q-item-section>
                        </q-item>
                      </template>
                    </q-select>
                  </div>
                  <div class="col-6">
                    <q-select 
                      v-model="form.newViz.value.config.lngColumn" :options="form.filteredAllColumns.value" 
                      label="Kolom Longitude" dark filled emit-value map-options
                      use-input input-debounce="0" @filter="form.filterAll"
                    >
                      <template v-slot:option="scope">
                        <q-item v-bind="scope.itemProps">
                          <q-item-section>
                            <q-item-label>{{ scope.opt.label }}</q-item-label>
                            <q-item-label caption class="text-teal" v-if="scope.opt.sample">{{ scope.opt.sample }}</q-item-label>
                          </q-item-section>
                          <q-item-section side><q-badge :color="scope.opt.type === 'measure' ? 'blue-8' : 'grey-7'" :label="scope.opt.type" /></q-item-section>
                        </q-item>
                      </template>
                    </q-select>
                  </div>
                </div>

                <div class="text-subtitle1 text-grey-4 q-mt-md q-mb-sm font-weight-bold pt-md">Custom Warna Markers</div>
                <q-select 
                  v-model="form.newViz.value.config.colorBy" :options="form.filteredAllColumns.value" 
                  label="Warnai Berdasarkan Kolom (Opsional)" dark filled clearable emit-value map-options
                  use-input input-debounce="0" @filter="form.filterAll" class="q-mb-md"
                >
                  <template v-slot:option="scope">
                    <q-item v-bind="scope.itemProps">
                      <q-item-section>
                        <q-item-label>{{ scope.opt.label }}</q-item-label>
                        <q-item-label caption class="text-teal" v-if="scope.opt.sample">{{ scope.opt.sample }}</q-item-label>
                      </q-item-section>
                      <q-item-section side><q-badge :color="scope.opt.type === 'measure' ? 'blue-8' : 'grey-7'" :label="scope.opt.type" /></q-item-section>
                    </q-item>
                  </template>
                </q-select>

                <template v-if="form.newViz.value.config.colorBy">
                  <div class="row items-center q-mb-sm">
                    <div class="text-caption text-grey-4">Aturan Warna (Format Rules)</div>
                    <q-space />
                    <q-btn flat dense color="secondary" label="+ Color Rule" size="sm" @click="form.addColorRule" />
                  </div>
                  <div v-for="(rule, rIdx) in form.newViz.value.config.colorRules" :key="rIdx" class="row q-col-gutter-xs q-mb-xs items-center">
                    <div class="col-7">
                      <q-input v-model="rule.value" label="Jika valuenya adalah..." dark filled dense />
                    </div>
                    <div class="col-3">
                      <q-input v-model="rule.color" type="text" label="Warna" dark filled dense>
                        <template v-slot:append>
                          <input type="color" :value="rule.color || '#3fb1ce'" @input="rule.color = $event.target.value" style="width: 24px; height: 24px; border: none; padding: 0; cursor: pointer;" />
                        </template>
                      </q-input>
                    </div>
                    <div class="col-2 text-right">
                      <q-btn flat round dense icon="close" color="negative" size="xs" @click="form.removeColorRule(rIdx)" />
                    </div>
                  </div>
                </template>

                <!-- Fields to show in map popup — alias list editor -->
                <div class="row items-center q-mt-md q-mb-xs">
                  <div class="text-subtitle1 text-grey-4 font-weight-bold">Info di Popup (saat klik titik)</div>
                  <q-space />
                  <q-btn flat dense color="secondary" icon="add" label="Tambah Kolom" size="sm" no-caps
                    @click="form.newViz.value.config.popupFields.push({ column: '', label: '' })" />
                </div>
                <div class="text-caption text-grey-5 q-mb-sm">
                  💡 Tentukan kolom apa yang tampil saat user klik titik peta, dan beri label yang mudah dipahami (alias).
                </div>
                <div v-for="(pf, pfIdx) in form.newViz.value.config.popupFields" :key="pfIdx"
                  class="q-mb-xs" style="display:flex;gap:4px;align-items:flex-start;width:100%;">
                  <div style="flex:5;min-width:0;">
                    <q-select
                      v-model="pf.column" :options="form.filteredAllColumns.value"
                      label="Kolom Data" dark filled dense emit-value map-options
                      use-input input-debounce="0" @filter="form.filterAll"
                      @update:model-value="val => { if (!pf.label) pf.label = val }"
                    >
                      <template v-slot:option="scope">
                        <q-item v-bind="scope.itemProps">
                          <q-item-section>
                            <q-item-label>{{ scope.opt.label }}</q-item-label>
                            <q-item-label caption class="text-teal" v-if="scope.opt.sample">{{ scope.opt.sample }}</q-item-label>
                          </q-item-section>
                          <q-item-section side><q-badge :color="scope.opt.type === 'measure' ? 'blue-8' : 'grey-7'" :label="scope.opt.type" /></q-item-section>
                        </q-item>
                      </template>
                    </q-select>
                  </div>
                  <div style="flex:6;min-width:0;">
                    <q-input v-model="pf.label" label="Label / Alias" dark filled dense
                      hint="Contoh: 'Nama KK', 'Alamat'"
                    />
                  </div>
                  <div style="flex-shrink:0;padding-top:4px;">
                    <q-btn flat round dense icon="close" color="negative" size="xs"
                      @click="form.newViz.value.config.popupFields.splice(pfIdx, 1)" />
                  </div>
                </div>
                <div v-if="!form.newViz.value.config.popupFields.length" class="text-caption text-grey-6 q-mb-md q-pa-sm bg-grey-10 rounded-borders">
                  Belum ada kolom popup. Klik "+ Tambah Kolom" untuk menambahkan informasi yang tampil saat klik titik peta.
                </div>
              </template>

              <!-- Metrics -->
              <div class="row items-center q-mt-lg q-mb-sm font-weight-bold border-top-grey pt-md">
                <div class="text-subtitle1 text-grey-4 font-weight-bold">Metrics (Nilai / Kolom)</div>
                <q-space />
                <q-btn flat dense icon="add" color="primary" label="Tambah Metric" @click="form.addMetric" no-caps />
              </div>

              <div v-for="(metric, mIdx) in form.newViz.value.config.metrics" :key="mIdx" class="q-pa-md q-mb-md bg-grey-10 rounded-borders border-card relative-position">
                <div class="row items-center q-mb-sm">
                  <div class="text-subtitle2 text-weight-bold text-primary">
                    Metrik {{ mIdx + 1 }} <span class="text-grey-5 font-monospace text-caption q-ml-sm">(Alias formula: m{{ mIdx }})</span>
                  </div>
                  <q-space />
                  <q-btn flat round dense icon="delete" color="negative" size="sm" @click="form.removeMetric(mIdx)" :disable="form.newViz.value.config.metrics.length === 1" />
                </div>

                <q-select 
                  v-model="metric.type" 
                  :options="[{label:'Regular Data Field', value:'regular'}, {label:'Calculated (Custom Formula)', value:'calculated'}]" 
                  emit-value map-options dense filled dark class="q-mb-sm" 
                />

                <template v-if="metric.type === 'regular' || !metric.type">
                  <div class="row q-col-gutter-sm q-mb-sm">
                    <div class="col-8">
                      <q-select 
                        v-model="metric.column" :options="form.filteredMeasureColumns.value" 
                        label="Kolom Data" dark filled emit-value map-options dense
                        use-input input-debounce="0" @filter="form.filterMeasure"
                      >
                        <template v-slot:no-option><q-item><q-item-section class="text-italic text-grey">Tidak ada kolom</q-item-section></q-item></template>
                      </q-select>
                    </div>
                    <div class="col-4">
                      <q-select 
                        v-model="metric.aggregation" 
                        :options="['sum', 'avg', 'count', 'min', 'max']" 
                        label="Agregasi" dark filled dense 
                      />
                    </div>
                  </div>

                  <!-- Conditional Filters (COUNTIFS equiv) -->
                  <div class="q-mt-md">
                    <div class="row items-center q-mb-xs">
                      <div class="text-caption text-grey-4">Kondisi Filter (Opsi)</div>
                      <q-space />
                      <q-btn flat dense color="secondary" label="+ Filter" size="sm" @click="form.addFilter(metric)" />
                    </div>
                    <div v-for="(f, fIdx) in metric.filters" :key="fIdx" class="row q-col-gutter-xs q-mb-xs items-center">
                      <div class="col-4">
                        <q-select 
                          v-model="f.column" :options="form.filteredDimensionColumns.value" 
                          label="Kolom" dark filled emit-value map-options dense
                          use-input input-debounce="0" @filter="form.filterDimension"
                        />
                      </div>
                      <div class="col-3">
                        <q-select v-model="f.operator" :options="filterOperators" emit-value map-options dark filled dense />
                      </div>
                      <div class="col-4">
                        <q-input v-model="f.value" label="Nilai" dark filled dense />
                      </div>
                      <div class="col-1 text-right">
                        <q-btn flat round dense icon="close" color="negative" size="xs" @click="form.removeFilter(metric, fIdx)" />
                      </div>
                    </div>
                  </div>
                </template>

                <template v-else>
                  <q-input v-model="metric.expression" label="Matematika Ekspresi, contoh: (m0 / m1) * 100" dark filled dense autogrow class="q-mb-sm font-monospace text-teal" />
                  <div class="text-caption text-grey-5">Format JS murni. Evaluasi berjalan di backend setelah data terkumpul.</div>
                </template>

                <div class="row q-col-gutter-sm q-mt-sm">
                  <div class="col-8">
                    <q-input v-model="metric.label" label="Label Tampilan Chart" dark filled dense />
                  </div>
                  <div class="col-4">
                    <q-input v-model="metric.color" type="text" label="Warna Bar" dark filled dense>
                      <template v-slot:append>
                        <input type="color" :value="metric.color || '#3fb1ce'" @input="metric.color = $event.target.value" style="width: 30px; height: 30px; border: none; padding: 0; cursor: pointer;" />
                      </template>
                    </q-input>
                  </div>
                </div>
              </div>
            </q-tab-panel>

            <!-- Panel JSON Editor -->
            <q-tab-panel name="json" class="q-pa-none column full-height">
              <div class="row q-col-gutter-sm q-mb-md">
                <div class="col-12">
                  <q-input v-model="form.newViz.value.name" label="Nama Visualisasi" dark filled class="full-width" />
                </div>
              </div>
              <q-select 
                v-model="form.newViz.value.chartType" 
                :options="[
                  {label: 'Scorecard (Item Tunggal)', value: 'scorecard'},
                  {label: 'Tabel Data Grid', value: 'data_table'},
                  {label: 'Bar Chart (Vertikal)', value: 'bar_vertical'},
                  {label: 'Bar Chart (Horizontal)', value: 'bar_horizontal'},
                  {label: 'Peta Sebaran (WebGL)', value: 'map_point'}
                ]"
                label="Tipe Chart" 
                dark filled emit-value map-options class="q-mb-md full-width" 
              />
              <div class="full-width col" style="min-height: 400px; border: 1px solid #424242; border-radius: 4px; overflow: hidden;">
                <vue-monaco-editor 
                  v-model:value="form.jsonConfigStr.value" 
                  theme="vs-dark" 
                  language="json" 
                  @change="form.onJsonChange" 
                  :options="{ minimap: { enabled: false }, formatOnPaste: true, tabSize: 2 }" 
                />
              </div>
            </q-tab-panel>
          </q-tab-panels>

          <q-space />
          <q-banner v-if="form.saveError.value" class="bg-negative text-white q-mt-md rounded-borders" rounded dense>
            {{ form.saveError.value }}
          </q-banner>
        </div>

        <!-- Right Column: Live Preview -->
        <div class="col-12 col-md-7 column" style="min-height: 0; overflow: hidden;">
          <div class="text-subtitle1 text-grey-4 q-mb-md font-weight-bold">Live Preview Canvas</div>
          
          <VizPreviewCanvas
            :newViz="form.newViz.value"
            :previewData="form.previewData.value"
            :previewLoading="form.previewLoading.value"
          />
        </div>
      </q-card-section>

      <q-separator dark />
      <q-card-actions align="right" class="q-pa-md bg-dark">
        <q-btn outline color="grey-5" label="Batal" v-close-popup no-caps padding="sm lg" />
        <q-btn
          color="primary"
          label="Simpan Visualisasi"
          icon="save"
          :loading="form.saving.value"
          @click="form.saveViz"
          unelevated
          no-caps
          padding="sm lg"
          class="q-ml-sm"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { toRef } from 'vue'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import { useVizForm } from '../../composables/visualizations/useVizForm'
import VizPreviewCanvas from './VizPreviewCanvas.vue'

const props = defineProps<{
  labelSchema: any
  visualizations: any[]
  fetchVizData: (id: number) => Promise<void>
}>()

const filterOperators = [
  { label: '=', value: 'equals' },
  { label: '!=', value: 'not_equals' },
  { label: 'Contains', value: 'contains' },
  { label: '>', value: 'greater_than' },
  { label: '<', value: 'less_than' }
]

const form = useVizForm(
  toRef(props, 'labelSchema'),
  toRef(props, 'visualizations'),
  props.fetchVizData
)

defineExpose({
  openAddDialog: form.openAddDialog,
  openEditDialog: form.openEditDialog
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
</style>
