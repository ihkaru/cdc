<template>
  <q-dialog v-model="show" persistent>
    <q-card class="bg-dark text-white" style="min-width: 800px; max-width: 90vw;">
      <q-card-section class="row items-center q-pb-none">
        <q-icon name="electric_bolt" size="md" color="warning" class="q-mr-sm" />
        <span class="text-h6 text-weight-bold">⚡ Magic Batch Import</span>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>

      <q-card-section>
        <p class="text-grey-4">Tempel Arrays of JSON Configs dari hasil *generate* AI di sini. Sistem akan otomatis memecah dan membuatkan semua card _dashboard_ sekaligus.</p>
        <div v-if="show" style="height: 500px; border: 1px solid #424242; border-radius: 4px; overflow: hidden;">
          <vue-monaco-editor 
            v-model:value="jsonStr" 
            theme="vs-dark" 
            language="json" 
            :options="{ minimap: { enabled: false }, formatOnPaste: true, tabSize: 2 }" 
          />
        </div>
      </q-card-section>

      <q-card-actions align="right" class="q-pa-md">
        <q-btn outline color="grey-5" label="Batal" v-close-popup no-caps />
        <q-btn
          color="warning"
          text-color="dark"
          label="Generate All Widgets"
          icon="auto_awesome"
          :loading="loading"
          @click="$emit('submit')"
          unelevated
          no-caps
          class="q-ml-sm"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'

const show = defineModel<boolean>('modelValue', { required: true })
const jsonStr = defineModel<string>('jsonStr', { required: true })

defineProps<{
  loading: boolean
}>()

defineEmits<{
  (e: 'submit'): void
}>()
</script>
