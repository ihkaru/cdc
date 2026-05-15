<template>
  <q-page class="flex flex-center">
    <q-spinner-dots color="primary" size="3em" />
  </q-page>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

onMounted(() => {
  router.push('/surveys')
})
</script>
