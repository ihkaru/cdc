<template>
  <q-layout view="Lhh Lpr lFf">
    <q-page-container>
      <q-page class="fn-page flex flex-center">

        <!-- Grid background -->
        <div class="fn-grid-bg" aria-hidden="true" />
        <div class="fn-glow" aria-hidden="true" />
        <div class="fn-glow-2" aria-hidden="true" />

        <div class="fn-card">

          <!-- Success overlay -->
          <transition name="fn-fade">
            <div v-if="authenticated" class="fn-success-overlay" role="status">
              <div class="fn-check-circle">
                <q-icon name="check" size="24px" color="green-5" />
              </div>
              <span class="fn-success-text">authenticated</span>
            </div>
          </transition>

          <!-- Header -->
          <div class="fn-header">
            <div class="fn-logo-mark" aria-hidden="true">
              <q-icon name="sync_alt" size="22px" style="color: #0d1117" />
            </div>
            <div>
              <div class="fn-brand-title">FasihNexus</div>
              <div class="fn-brand-sub">FASIH-SM Sync Platform</div>
              <span class="fn-tag">BPS · Kab. Mempawah</span>
            </div>
          </div>

          <!-- Body -->
          <div class="fn-body">
            <div class="fn-section-label">Autentikasi SSO</div>

            <!-- Error alert -->
            <transition name="fn-slide">
              <div v-if="errorMsg" class="fn-error-box" role="alert">
                <q-icon name="error_outline" size="14px" />
                <span>{{ errorMsg }}</span>
              </div>
            </transition>

            <q-form @submit.prevent="onSubmit" class="fn-form">
              <div class="fn-field">
                <label class="fn-label" for="fn-email">Email BPS</label>
                <div class="fn-input-wrap">
                  <q-icon name="mail_outline" size="15px" class="fn-input-icon" aria-hidden="true" />
                  <input
                    id="fn-email"
                    v-model="email"
                    class="fn-input"
                    type="email"
                    placeholder="nip@bps.go.id"
                    autocomplete="email"
                    spellcheck="false"
                    required
                  />
                </div>
              </div>

              <div class="fn-field">
                <label class="fn-label" for="fn-password">Password</label>
                <div class="fn-input-wrap">
                  <q-icon name="lock_outline" size="15px" class="fn-input-icon" aria-hidden="true" />
                  <input
                    id="fn-password"
                    v-model="password"
                    class="fn-input"
                    :type="showPass ? 'text' : 'password'"
                    placeholder="••••••••"
                    autocomplete="current-password"
                    style="padding-right: 40px;"
                    required
                  />
                  <button
                    type="button"
                    class="fn-pass-toggle"
                    :aria-label="showPass ? 'Sembunyikan password' : 'Tampilkan password'"
                    @click="showPass = !showPass"
                  >
                    <q-icon :name="showPass ? 'visibility_off' : 'visibility'" size="15px" />
                  </button>
                </div>
              </div>

              <div class="fn-divider" />

              <button class="fn-btn" type="submit" :disabled="loading">
                <span v-if="loading" class="fn-btn-spinner" aria-hidden="true" />
                <span>{{ loading ? 'Memverifikasi...' : 'Sign In' }}</span>
                <q-icon v-if="!loading" name="arrow_forward" size="15px" aria-hidden="true" />
              </button>
            </q-form>
          </div>

          <!-- Footer -->
          <div class="fn-footer">
            <div class="fn-status">
              <span class="fn-status-dot" aria-hidden="true" />
              <span>VPN terhubung</span>
            </div>
            <span class="fn-version">v2.4.1</span>
          </div>

        </div>
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { useQuasar } from "quasar";
import { useAuthStore } from "src/stores/auth";
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();
const $q = useQuasar();

const email = ref("");
const password = ref("");
const loading = ref(false);
const showPass = ref(false);
const errorMsg = ref("");
const authenticated = ref(false);

async function onSubmit() {
	errorMsg.value = "";
	loading.value = true;
	try {
		await auth.login(email.value, password.value);
		authenticated.value = true;
		$q.notify({ type: "positive", message: "Welcome back!", position: "top" });
		const redirectPath = (route.query.redirect as string) || "/";
		await router.push(redirectPath);
	} catch (err: any) {
		errorMsg.value = err.message || "Kredensial tidak valid. Periksa kembali email dan password.";
	} finally {
		loading.value = false;
	}
}
</script>

<style lang="scss" scoped>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500&display=swap');

.fn-page {
  background: #0d1117;
  min-height: 100vh;
  position: relative;
  overflow: hidden;
  font-family: 'DM Sans', sans-serif;
}

.fn-grid-bg {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(30, 217, 150, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(30, 217, 150, 0.04) 1px, transparent 1px);
  background-size: 32px 32px;
}

.fn-glow {
  position: absolute;
  width: 400px;
  height: 400px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(30, 217, 150, 0.07) 0%, transparent 70%);
  top: -100px;
  left: -100px;
  pointer-events: none;
}

.fn-glow-2 {
  position: absolute;
  width: 300px;
  height: 300px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(55, 138, 221, 0.06) 0%, transparent 70%);
  bottom: -60px;
  right: -60px;
  pointer-events: none;
}

.fn-card {
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 420px;
  background: #161b22;
  border: 1px solid #21262d;
  border-radius: 12px;
  overflow: hidden;
}

.fn-success-overlay {
  position: absolute;
  inset: 0;
  background: #161b22;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 12px;
}

.fn-check-circle {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: rgba(30, 217, 150, 0.12);
  border: 1px solid rgba(30, 217, 150, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
}

.fn-success-text {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 13px;
  color: #1ed996;
  letter-spacing: 0.5px;
}

.fn-header {
  padding: 2rem 2rem 1.5rem;
  border-bottom: 1px solid #21262d;
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.fn-logo-mark {
  width: 40px;
  height: 40px;
  background: #1ed996;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
}

.fn-brand-title {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 20px;
  font-weight: 500;
  color: #e6edf3;
  line-height: 1.2;
  letter-spacing: -0.3px;
}

.fn-brand-sub {
  font-size: 12px;
  color: #7d8590;
  font-weight: 300;
  letter-spacing: 0.3px;
  margin-top: 3px;
  font-family: 'IBM Plex Mono', monospace;
}

.fn-tag {
  display: inline-block;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px;
  color: #1ed996;
  background: rgba(30, 217, 150, 0.08);
  border: 1px solid rgba(30, 217, 150, 0.2);
  border-radius: 4px;
  padding: 1px 7px;
  margin-top: 6px;
  letter-spacing: 0.5px;
}

.fn-body {
  padding: 1.75rem 2rem 2rem;
}

.fn-section-label {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px;
  color: #7d8590;
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-bottom: 1.25rem;
}

.fn-error-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(224, 75, 74, 0.08);
  border: 1px solid rgba(224, 75, 74, 0.25);
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 12px;
  color: #f47067;
  margin-bottom: 14px;
}

.fn-form {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.fn-field {
  margin-bottom: 14px;
}

.fn-label {
  display: block;
  font-size: 12px;
  color: #7d8590;
  font-weight: 400;
  margin-bottom: 6px;
  letter-spacing: 0.2px;
}

.fn-input-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.fn-input-icon {
  position: absolute;
  left: 12px;
  color: #484f58;
  pointer-events: none;
  transition: color 0.2s;
}

.fn-input {
  width: 100%;
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: 8px;
  color: #e6edf3;
  font-family: 'DM Sans', sans-serif;
  font-size: 14px;
  font-weight: 300;
  padding: 10px 12px 10px 40px;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.2s;

  &::placeholder { color: #484f58; }

  &:focus {
    border-color: #1ed996;
    & ~ .fn-input-icon { color: #1ed996; }
  }
}

.fn-input-wrap:focus-within .fn-input-icon {
  color: #1ed996;
}

.fn-pass-toggle {
  position: absolute;
  right: 12px;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  color: #484f58;
  display: flex;
  align-items: center;
  transition: color 0.2s;
  &:hover { color: #8b949e; }
}

.fn-divider {
  height: 1px;
  background: #21262d;
  margin: 1.5rem 0;
}

.fn-btn {
  width: 100%;
  background: #1ed996;
  border: none;
  border-radius: 8px;
  color: #0d1117;
  font-family: 'DM Sans', sans-serif;
  font-size: 14px;
  font-weight: 500;
  padding: 11px 0;
  cursor: pointer;
  letter-spacing: 0.2px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: background 0.15s, transform 0.1s;

  &:hover:not(:disabled) { background: #26ffb0; }
  &:active:not(:disabled) { transform: scale(0.99); }
  &:disabled { background: #21262d; color: #484f58; cursor: not-allowed; }
}

.fn-btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(13, 17, 23, 0.2);
  border-top-color: #0d1117;
  border-radius: 50%;
  animation: fn-spin 0.6s linear infinite;
}

@keyframes fn-spin { to { transform: rotate(360deg); } }

.fn-footer {
  padding: 0.75rem 2rem 1.25rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid #21262d;
}

.fn-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #7d8590;
  font-family: 'IBM Plex Mono', monospace;
}

.fn-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #1ed996;
  flex-shrink: 0;
  animation: fn-pulse 2.5s ease-in-out infinite;
}

@keyframes fn-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.fn-version {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px;
  color: #484f58;
}

// Transitions
.fn-fade-enter-active, .fn-fade-leave-active { transition: opacity 0.3s; }
.fn-fade-enter-from, .fn-fade-leave-to { opacity: 0; }

.fn-slide-enter-active, .fn-slide-leave-active { transition: all 0.2s ease; }
.fn-slide-enter-from, .fn-slide-leave-to { opacity: 0; transform: translateY(-4px); }
</style>