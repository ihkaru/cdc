<template>
  <q-layout view="Lhh Lpr lFf">
    <q-page-container>
      <q-page class="flex flex-center login-bg">
        <q-card class="login-card shadow-24">
          <q-card-section class="bg-primary text-white q-pa-lg text-center">
            <div class="text-h4 text-weight-bolder">CDC</div>
            <div class="text-subtitle2 op-80">FASIH-SM Sync Platform</div>
          </q-card-section>

          <q-card-section class="q-pa-xl">
            <q-form @submit="onSubmit" class="q-gutter-md">
              <q-input
                v-model="email"
                label="Email BPS"
                type="email"
                filled
                dark
                lazy-rules
                :rules="[val => !!val || 'Email is required']"
                prepend-inner-icon="email"
              >
                <template v-slot:prepend>
                  <q-icon name="person" />
                </template>
              </q-input>

              <q-input
                v-model="password"
                label="Password"
                type="password"
                filled
                dark
                lazy-rules
                :rules="[val => !!val || 'Password is required']"
              >
                <template v-slot:prepend>
                  <q-icon name="lock" />
                </template>
              </q-input>

              <div class="q-mt-xl">
                <q-btn
                  label="Sign In"
                  type="submit"
                  color="primary"
                  class="full-width q-py-md text-weight-bold"
                  size="lg"
                  :loading="loading"
                  rounded
                  unelevated
                />
              </div>
            </q-form>
          </q-card-section>
        </q-card>
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from 'src/stores/auth'
import { useRouter, useRoute } from 'vue-router'
import { useQuasar } from 'quasar'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const $q = useQuasar()

const email = ref('')
const password = ref('')
const loading = ref(false)

async function onSubmit() {
  console.log('[LoginPage] Sign In button clicked');
  loading.value = true
  try {
    console.log('[LoginPage] Calling auth.login...');
    await auth.login(email.value, password.value)
    
    console.log('[LoginPage] Login successful. Notifying user...');
    $q.notify({
      type: 'positive',
      message: 'Welcome back!',
      position: 'top'
    })
    
    const redirectPath = (route.query.redirect as string) || '/'
    console.log(`[LoginPage] Redirecting to: ${redirectPath}`);
    await router.push(redirectPath)
    console.log('[LoginPage] router.push() called');
  } catch (err: any) {
    console.error('[LoginPage] Login failed:', err);
    $q.notify({
      type: 'negative',
      message: err.message || 'Login failed. Check your credentials.',
      position: 'top'
    })
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.login-bg {
  background: linear-gradient(135deg, #1a1a1a 0%, #2c3e50 100%);
}

.login-card {
  width: 100%;
  max-width: 450px;
  border-radius: 24px;
  overflow: hidden;
  background: rgba(30, 30, 30, 0.8);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.op-80 {
  opacity: 0.8;
}
</style>
