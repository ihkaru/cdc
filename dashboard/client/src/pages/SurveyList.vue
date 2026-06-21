<template>
  <q-page padding>
    <div class="row justify-between items-center q-mb-xl">
      <div>
        <h1 class="text-h3 text-weight-bold q-my-none">Survey Configurations</h1>
        <p class="text-grey-5 q-mt-sm">Manage your FASIH surveys and trigger data sync.</p>
      </div>
    </div>

    <div class="row q-mb-lg flex items-center justify-between">
      <q-input
        v-model="searchQuery"
        dense
        outlined
        dark
        placeholder="Cari survey (nama, user, atau kabupaten)..."
        class="col-12 col-sm-5 bg-dark"
      >
        <template v-slot:prepend>
          <q-icon name="search" />
        </template>
        <template v-slot:append v-if="searchQuery">
          <q-icon name="clear" class="cursor-pointer" @click="searchQuery = ''" />
        </template>
      </q-input>

      <q-btn
        color="primary"
        icon="add"
        label="Add Survey"
        to="/surveys/new"
        unelevated
        :disable="!vpnStatus?.connected"
      >
        <q-tooltip v-if="!vpnStatus?.connected">Membutuhkan koneksi VPN aktif</q-tooltip>
      </q-btn>
    </div>

    <!-- RPA Status Banner -->
    <q-banner
      v-if="rpaStatus.is_running"
      class="bg-primary text-white q-mb-md rounded-borders relative-position overflow-hidden"
      rounded
      style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%) !important; border: 1px solid #3b82f6;"
    >
      <template v-slot:avatar>
        <q-spinner-oval color="white" size="2.5em" />
      </template>
      
      <div class="row no-wrap items-center justify-between">
        <div>
          <div class="text-subtitle1 text-weight-bold row items-center q-gutter-x-sm">
            <span>Sinkronisasi Sedang Berjalan</span>
            <q-badge color="amber" text-color="dark" class="text-weight-bold" v-if="rpaStatus.progress?.phase_label">
              {{ rpaStatus.progress.phase_label }}
            </q-badge>
          </div>
          <div class="text-body2 text-blue-2 q-mt-xs">
            Survey: <span class="text-white text-weight-medium">{{ rpaStatus.current_survey }}</span>
          </div>
        </div>
        
        <div>
          <q-btn
            color="negative"
            :label="rpaStatus.job_status === 'stopping' ? 'Stopping...' : 'Stop Sync'"
            icon="stop"
            unelevated
            class="q-px-md text-weight-bold"
            style="border-radius: 6px;"
            :loading="stoppingJobId === rpaStatus.current_job_id"
            :disable="rpaStatus.job_status === 'stopping'"
            @click="confirmStopSync(rpaStatus.current_job_id, rpaStatus.current_survey)"
          />
        </div>
      </div>

      <!-- Live progress bar based on active phase -->
      <div class="q-mt-md" v-if="rpaStatus.progress">
        <!-- If in fetch_assignments phase -->
        <template v-if="rpaStatus.progress.users_total > 0 && (rpaStatus.progress.phase === 'fetch_assignments' || rpaStatus.progress.phase === 'fetch_users')">
          <div class="row justify-between text-caption text-blue-2 q-mb-xs">
            <span>Iterasi Petugas</span>
            <span>{{ rpaStatus.progress.users_done }} / {{ rpaStatus.progress.users_total }}</span>
          </div>
          <q-linear-progress
            :value="rpaStatus.progress.users_done / rpaStatus.progress.users_total"
            color="amber"
            track-color="blue-9"
            size="6px"
            rounded
          />
        </template>
        
        <!-- If in streaming_sync phase -->
        <template v-else-if="rpaStatus.progress.assignments_total > 0 && rpaStatus.progress.phase === 'streaming_sync'">
          <div class="row justify-between text-caption text-blue-2 q-mb-xs">
            <span>Mengunduh Detail Assignment</span>
            <span>{{ rpaStatus.progress.assignments_fetched }} / {{ rpaStatus.progress.assignments_total }}</span>
          </div>
          <q-linear-progress
            :value="rpaStatus.progress.assignments_fetched / rpaStatus.progress.assignments_total"
            color="positive"
            track-color="blue-9"
            size="6px"
            rounded
          />
        </template>
      </div>
    </q-banner>

    <!-- Queue Banner -->
    <q-banner
      v-if="rpaStatus.queue && rpaStatus.queue.length > 0"
      class="bg-grey-9 text-white q-mb-xl rounded-borders"
      rounded
    >
      <template v-slot:avatar>
        <q-icon name="queue" color="amber" />
      </template>
      <div class="text-subtitle2 text-weight-bold q-mb-xs">
        {{ rpaStatus.queue.length }} survey dalam antrian
      </div>
      <div v-for="q in rpaStatus.queue" :key="q.job_id" class="row items-center q-mb-xs">
        <q-badge color="amber-8" class="q-mr-sm">#{{ q.position }}</q-badge>
        <span class="text-body2">{{ q.survey_name }}</span>
        <q-btn
          flat dense round
          icon="close"
          size="xs"
          color="negative"
          class="q-ml-sm"
          @click="cancelJob(q.job_id, q.survey_name)"
        />
      </div>
    </q-banner>

    <div v-if="loading" class="text-center text-grey-6 q-py-xl">
      <q-spinner size="3em" />
      <div class="q-mt-md">Loading data...</div>
    </div>
    
    <q-card v-else-if="surveys.length === 0" class="text-center q-pa-xl bg-dark text-grey-5 border-card" flat bordered>
      <q-icon name="assignment" size="4rem" class="q-mb-md opacity-50" />
      <p class="text-h6 q-mb-md">No surveys configured yet.</p>
      <q-btn color="primary" to="/surveys/new" class="q-mt-sm" unelevated>Add your first survey</q-btn>
    </q-card>

    <div v-else class="row q-col-gutter-lg">
      <div v-for="s in filteredSurveys" :key="s.id" class="col-12 col-md-4">
        <q-card class="bg-dark text-white border-card my-card transition-hover" flat bordered>
          <q-card-section>
            <div class="row justify-between items-start q-mb-sm">
              <div class="text-h6 text-weight-bold ellipsis" style="max-width: 60%">{{ s.surveyName }}</div>
              <div class="row q-gutter-x-xs">
                <q-badge v-if="isSurveyIncomplete(s)" color="warning" text-color="dark" rounded class="q-px-sm q-py-xs text-weight-bold">
                  Incomplete
                </q-badge>
                <q-badge :color="s.isActive ? 'positive' : 'grey-8'" rounded class="q-px-sm q-py-xs">
                  {{ s.isActive ? 'Active' : 'Inactive' }}
                </q-badge>
              </div>
            </div>
            
            <q-list dense class="text-grey-4">
              <q-item class="q-px-none">
                <q-item-section>SSO User:</q-item-section>
                <q-item-section side class="text-white text-weight-medium">{{ s.ssoUsername }}</q-item-section>
              </q-item>
              <q-item v-if="s.filterKabupaten" class="q-px-none">
                <q-item-section>Kabupaten:</q-item-section>
                <q-item-section side class="text-white text-weight-medium">{{ s.filterKabupaten }}</q-item-section>
              </q-item>
              <q-item class="q-px-none">
                <q-item-section>Interval:</q-item-section>
                <q-item-section side class="text-white text-weight-medium">{{ s.intervalMinutes }} min</q-item-section>
              </q-item>
            </q-list>
          </q-card-section>

          <q-separator dark inset />

          <q-card-actions vertical class="q-pa-md q-gutter-y-sm">
            <div class="row q-gutter-x-sm">
              <q-btn 
                class="col"
                :color="getSyncButtonColor(s.id)"
                :text-color="getSyncButtonTextColor(s.id)"
                :label="getSyncButtonLabel(s.id)" 
                :loading="syncingId === s.id"
                :disable="syncingId === s.id || isJobActive(s.id) || !vpnStatus?.connected"
                @click="triggerSync(s.id)"
                unelevated
              >
                <q-tooltip v-if="!vpnStatus?.connected">VPN tidak terhubung</q-tooltip>
              </q-btn>
              <q-btn class="col" color="grey-9" text-color="white" :to="`/surveys/${s.id}`" label="View Data" unelevated />
            </div>
            <div class="row q-gutter-x-sm row-sm-btns">
              <q-btn class="col" size="sm" color="accent" text-color="white" :to="`/surveys/${s.id}/visualizations`" label="Viz" outline />
              <q-btn class="col" size="sm" color="grey-9" text-color="white" :to="`/surveys/${s.id}/logs`" label="Logs" outline />
              <q-btn class="col" size="sm" color="grey-9" text-color="white" :to="`/surveys/${s.id}/edit`" label="Edit" outline />
              <q-btn class="col" size="sm" color="negative" @click="deleteSurvey(s.id)" label="Del" outline />
            </div>
          </q-card-actions>
        </q-card>
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { useQuasar } from "quasar";
import { api } from "src/boot/axios";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { vpnStatus } from "../composables/useVpn";

const $q = useQuasar();
const searchQuery = ref("");
const surveys = ref<any[]>([]);
const loading = ref(true);
const syncingId = ref<string | null>(null);
const rpaStatus = ref<any>({});
const stoppingJobId = ref<number | null>(null);
let pollTimer: any = null;

function confirmStopSync(jobId: number, surveyName: string) {
	$q.dialog({
		title: "Konfirmasi Penghentian",
		message: `Apakah Anda yakin ingin menghentikan sinkronisasi untuk survey "${surveyName}"? Data yang sudah diunduh akan tetap disimpan.`,
		persistent: true,
		dark: true,
		ok: {
			label: "Stop",
			color: "negative",
			unelevated: true,
		},
		cancel: {
			label: "Batal",
			flat: true,
			color: "white",
		},
	}).onOk(async () => {
		stoppingJobId.value = jobId;
		try {
			const res = await api.delete(`/surveys/sync/${jobId}`);
			$q.notify({
				type: "info",
				message: res.data.message || `Proses penghentian dikirim`,
			});
			refreshStatus();
		} catch (e: any) {
			const msg = e.response?.data?.detail || e.message || "Gagal menghentikan sinkronisasi";
			$q.notify({ type: "negative", message: `Error: ${msg}` });
		} finally {
			stoppingJobId.value = null;
		}
	});
}

const filteredSurveys = computed(() => {
	if (!searchQuery.value) return surveys.value;
	const q = searchQuery.value.toLowerCase();
	return surveys.value.filter(
		(s) =>
			(s.surveyName && s.surveyName.toLowerCase().includes(q)) ||
			(s.ssoUsername && s.ssoUsername.toLowerCase().includes(q)) ||
			(s.filterKabupaten && s.filterKabupaten.toLowerCase().includes(q)),
	);
});

async function loadData() {
	loading.value = true;
	try {
		const [surveysRes, statusRes] = await Promise.all([
			api.get("/surveys"),
			api.get("/surveys/sync/status"),
		]);
		surveys.value = surveysRes.data;
		rpaStatus.value = statusRes.data;
	} catch (e) {
		console.error(e);
	} finally {
		loading.value = false;
	}
}

async function refreshStatus() {
	try {
		const res = await api.get("/surveys/sync/status");
		rpaStatus.value = res.data;
	} catch {}
}

function isJobActive(surveyId: string): boolean {
	// Check if this survey is currently running
	if (rpaStatus.value.is_running && rpaStatus.value.current_survey_config_id === surveyId) {
		return true;
	}
	// Check if queued
	if (rpaStatus.value.queue) {
		// We don't have survey_config_id in queue, so can't check directly
		// The RPA endpoint handles dedup, so this is just a UI hint
	}
	return false;
}

function isSurveyIncomplete(survey: any): boolean {
	if (!survey.latestLog) return false;
	const log = survey.latestLog;
	if (log.status === "partial") return true;
	const totalFetched = log.totalFetched || 0;
	const totalSkipped = log.totalSkipped || 0;
	const totalTargetRemote = log.totalTargetRemote || 0;
	return totalTargetRemote > 0 && totalFetched + totalSkipped < totalTargetRemote;
}

function getSyncButtonColor(surveyId: string): string {
	const s = surveys.value.find((survey) => survey.id === surveyId);
	if (
		s &&
		isSurveyIncomplete(s) &&
		!isJobActive(surveyId) &&
		syncingId.value !== surveyId &&
		!rpaStatus.value.is_running
	) {
		return "warning";
	}
	return "primary";
}

function getSyncButtonTextColor(surveyId: string): string {
	const s = surveys.value.find((survey) => survey.id === surveyId);
	if (
		s &&
		isSurveyIncomplete(s) &&
		!isJobActive(surveyId) &&
		syncingId.value !== surveyId &&
		!rpaStatus.value.is_running
	) {
		return "dark";
	}
	return "white";
}

function getSyncButtonLabel(surveyId: string): string {
	if (syncingId.value === surveyId) return "Queueing...";
	if (rpaStatus.value.is_running) return "Queue Sync";
	const s = surveys.value.find((survey) => survey.id === surveyId);
	if (s && isSurveyIncomplete(s)) {
		return "Resume Sync";
	}
	return "Sync Now";
}

async function triggerSync(id: string) {
	if (syncingId.value) return;
	syncingId.value = id;
	try {
		const res = await api.post(`/surveys/${id}/sync`);
		const data = res.data;
		if (data.status === "already_queued") {
			$q.notify({ type: "warning", message: data.message });
		} else {
			$q.notify({ type: "positive", message: data.message || "Sync queued!" });
		}
		refreshStatus();
	} catch (e: any) {
		const msg =
			e.response?.data?.message ||
			e.response?.data?.detail ||
			e.message ||
			"Failed to trigger sync";
		$q.notify({ type: "negative", message: `Error: ${msg}` });
	} finally {
		syncingId.value = null;
	}
}

async function cancelJob(jobId: number, surveyName: string) {
	try {
		const res = await api.delete(`/surveys/sync/${jobId}`);
		$q.notify({ type: "info", message: `Sync "${surveyName}" dibatalkan` });
		refreshStatus();
	} catch {
		$q.notify({ type: "negative", message: "Gagal membatalkan job" });
	}
}

function deleteSurvey(id: string) {
	$q.dialog({
		title: "Confirm Deletion",
		message: "Hapus survey ini beserta semua datanya?",
		cancel: true,
		persistent: true,
		dark: true,
	}).onOk(async () => {
		try {
			await api.delete(`/surveys/${id}`);
			$q.notify({
				type: "info",
				message:
					"Survey sedang dihapus di latar belakang. Semua data dan media terkait akan segera dibersihkan.",
				timeout: 5000,
				position: "top",
			});
			loadData();
		} catch (e) {
			$q.notify({ type: "negative", message: "Failed to delete" });
		}
	});
}

onMounted(() => {
	loadData();
	// Poll status every 10s
	pollTimer = setInterval(refreshStatus, 10000);
});

onBeforeUnmount(() => {
	if (pollTimer) clearInterval(pollTimer);
});
</script>

<style scoped>
.border-card {
  border-color: #262b36;
}
.transition-hover {
  transition: all 0.2s ease-in-out;
}
.transition-hover:hover {
  transform: translateY(-2px);
  border-color: rgba(59, 130, 246, 0.4);
  box-shadow: 0 8px 24px rgba(0,0,0,0.3);
}
.opacity-50 {
  opacity: 0.5;
}
</style>
