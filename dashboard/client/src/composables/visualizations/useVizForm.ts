import { ref, computed, watch } from 'vue'
import type { Ref } from 'vue'
import { useQuasar } from 'quasar'
import { useRoute } from 'vue-router'

export function useVizForm(
    labelSchema: Ref<any>,
    visualizations: Ref<any[]>,
    fetchVizData: (vizId: number) => Promise<void>
) {
    const route = useRoute()
    const $q = useQuasar()
    const surveyId = route.params.id as string

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

    const defaultMetric = () => ({
        id: `m${Date.now()}`,
        type: 'regular',
        column: '',
        aggregation: 'sum',
        label: '',
        color: '',
        filters: []
    })

    const newViz = ref({
        name: '',
        chartType: 'scorecard',
        config: {
            xColumn: '',
            groupBy: null,
            latColumn: '',
            lngColumn: '',
            colorBy: '',
            colorRules: [],
            popupFields: [] as { column: string; label: string }[],
            metrics: [defaultMetric()]
        } as { xColumn: string; groupBy: any; latColumn: string; lngColumn: string; colorBy: string; colorRules: any[]; popupFields: { column: string; label: string }[]; metrics: any[];[key: string]: any }
    })

    const defaultColorRule = () => ({
        value: '',
        color: '#3fb1ce'
    })

    function addColorRule() {
        if (!newViz.value.config.colorRules) newViz.value.config.colorRules = []
        newViz.value.config.colorRules.push(defaultColorRule())
    }

    function removeColorRule(index: number | string) {
        newViz.value.config.colorRules.splice(Number(index), 1)
    }

    const measureColumns = computed(() => {
        if (!labelSchema.value?.columns) return []
        return labelSchema.value.columns
            .filter((c: any) => c.type === 'measure')
            .map((c: any) => ({ label: `🔢 ${c.name}`, value: c.name, sample: c.sample }))
    })

    const dimensionColumns = computed(() => {
        if (!labelSchema.value?.columns) return []
        return labelSchema.value.columns
            .filter((c: any) => c.type === 'dimension')
            .map((c: any) => ({ label: `🏷️ ${c.name}`, value: c.name, sample: c.sample }))
    })

    // All columns (measure + dimension) with sample values — used in map pickers
    const allColumns = computed(() => {
        if (!labelSchema.value?.columns) return []
        return labelSchema.value.columns.map((c: any) => ({
            label: c.name,
            value: c.name,
            sample: c.sample ?? null,
            type: c.type
        }))
    })

    const filteredMeasureColumns = ref<any[]>([])
    const filteredDimensionColumns = ref<any[]>([])
    const filteredAllColumns = ref<any[]>([])

    function filterMeasure(val: string, update: (cb: () => void) => void) {
        update(() => {
            const needle = val.toLowerCase()
            filteredMeasureColumns.value = measureColumns.value.filter(
                (v: any) => v.label.toLowerCase().includes(needle)
            )
        })
    }

    function filterDimension(val: string, update: (cb: () => void) => void) {
        update(() => {
            const needle = val.toLowerCase()
            filteredDimensionColumns.value = dimensionColumns.value.filter(
                (v: any) => v.label.toLowerCase().includes(needle)
            )
        })
    }

    function filterAll(val: string, update: (cb: () => void) => void) {
        update(() => {
            const needle = val.toLowerCase()
            filteredAllColumns.value = allColumns.value.filter(
                (v: any) => v.label.toLowerCase().includes(needle) ||
                    (v.sample && String(v.sample).toLowerCase().includes(needle))
            )
        })
    }

    function addMetric() {
        const m = defaultMetric();
        m.id = `m${newViz.value.config.metrics.length}`;
        newViz.value.config.metrics.push(m)
    }

    function removeMetric(index: number | string) {
        newViz.value.config.metrics.splice(Number(index), 1)
    }

    function addFilter(metric: any) {
        if (!metric.filters) metric.filters = []
        metric.filters.push({ column: '', operator: 'equals', value: '' })
    }

    function removeFilter(metric: any, index: number | string) {
        metric.filters.splice(Number(index), 1)
    }

    function openAddDialog() {
        if (!labelSchema.value || !labelSchema.value.columns || labelSchema.value.columns.length === 0) {
            $q.notify({ type: 'warning', message: 'Belum ada kolom yang tersedia untuk dibuat visualisasi.' })
            return
        }

        isEditing.value = false
        editingVizId.value = null
        configTab.value = 'form'

        const m = defaultMetric();
        m.id = 'm0';
        m.column = measureColumns.value[0]?.value || dimensionColumns.value[0]?.value || '';
        newViz.value = {
            name: '',
            chartType: 'data_table',
            config: {
                xColumn: dimensionColumns.value[0]?.value || '',
                groupBy: null,
                latColumn: '',
                lngColumn: '',
                colorBy: '',
                colorRules: [],
                popupFields: [],
                metrics: [m]
            }
        }
        jsonConfigStr.value = JSON.stringify(newViz.value.config, null, 2)
        previewData.value = null
        saveError.value = ''
        showAddDialog.value = true
    }

    function openEditDialog(viz: any) {
        if (!labelSchema.value || !labelSchema.value.columns || labelSchema.value.columns.length === 0) {
            $q.notify({ type: 'warning', message: 'Belum ada kolom yang tersedia untuk dibuat visualisasi.' })
            return
        }

        isEditing.value = true
        editingVizId.value = viz.id
        configTab.value = 'form'

        const normalizedConfig = JSON.parse(JSON.stringify(viz.config))

        // Normalize legacy config without metrics array
        if (!normalizedConfig.metrics || normalizedConfig.metrics.length === 0) {
            if (viz.chartType === 'scorecard') {
                normalizedConfig.metrics = [{ id: "m0", type: "regular", label: normalizedConfig.label || normalizedConfig.metricColumn, column: normalizedConfig.metricColumn, aggregation: normalizedConfig.aggregation }];
            } else if (viz.chartType !== 'map_point') {
                normalizedConfig.metrics = [{ id: "m0", type: "regular", label: normalizedConfig.label || normalizedConfig.yColumn, column: normalizedConfig.yColumn, aggregation: normalizedConfig.aggregation }];
            } else {
                normalizedConfig.metrics = [defaultMetric()];
            }
        }

        // Normalize missing arrays to prevent v-for loop crashes
        normalizedConfig.metrics.forEach((m: any) => {
            if (!m.filters) m.filters = []
        })
        if (!normalizedConfig.colorRules) normalizedConfig.colorRules = []
        if (!normalizedConfig.popupFields) normalizedConfig.popupFields = []

        newViz.value = {
            name: viz.name,
            chartType: viz.chartType,
            config: normalizedConfig
        }
        jsonConfigStr.value = JSON.stringify(newViz.value.config, null, 2)
        previewData.value = null
        saveError.value = ''
        showAddDialog.value = true
    }

    function onJsonChange(value: string) {
        try {
            const parsed = JSON.parse(value)

            // Auto-map if user pastes the exact AI output structure
            if (parsed.config && parsed.chartType) {
                if (parsed.name) newViz.value.name = parsed.name
                newViz.value.chartType = parsed.chartType
                newViz.value.config = parsed.config
            } else {
                newViz.value.config = parsed
            }

            saveError.value = ''
        } catch (e) {
            saveError.value = 'Format JSON tidak valid'
        }
    }

    watch(() => newViz.value.config, (newVal) => {
        if (configTab.value === 'form') {
            jsonConfigStr.value = JSON.stringify(newVal, null, 2)
        }
    }, { deep: true })

    async function loadPreview() {
        if (!newViz.value.chartType) return

        const isMap = newViz.value.chartType === 'map_point'
        const isScorecard = newViz.value.chartType === 'scorecard'

        // Map requires lat/lng columns
        if (isMap) {
            if (!newViz.value.config.latColumn || !newViz.value.config.lngColumn) return
        } else {
            // Other chart types (except scorecard) require xColumn
            if (!isScorecard && !newViz.value.config.xColumn) return
            // Non-scorecard regular metrics need a column
            const invalidM = newViz.value.config.metrics.find((m: any) => m.type === 'regular' && !m.column)
            if (invalidM && !isScorecard) return
        }

        previewLoading.value = true
        try {
            const payload = {
                chartType: newViz.value.chartType,
                config: newViz.value.config
            }
            const res = await fetch(`/api/surveys/${surveyId}/visualizations/preview`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            previewData.value = await res.json()
        } catch (e) {
            previewData.value = { error: true }
        } finally {
            previewLoading.value = false
        }
    }

    watch(newViz, () => {
        if (!showAddDialog.value) return
        clearTimeout(previewTimeout)
        previewTimeout = setTimeout(() => {
            loadPreview()
        }, 1000) // Increase debounce to 1s to allow typing formula
    }, { deep: true })

    async function saveViz() {
        if (!newViz.value.name) {
            saveError.value = 'Nama visualisasi wajib diisi'
            return
        }

        saving.value = true
        saveError.value = ''

        try {
            const payload = {
                name: newViz.value.name,
                chartType: newViz.value.chartType,
                config: newViz.value.config
            }

            let url = `/api/surveys/${surveyId}/visualizations`
            let method = 'POST'
            if (isEditing.value && editingVizId.value) {
                url = `/api/surveys/${surveyId}/visualizations/${editingVizId.value}`
                method = 'PUT'
            }

            const res = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })

            if (!res.ok) throw new Error('Gagal menyimpan visualisasi')

            const saved = await res.json() as any

            if (isEditing.value) {
                const idx = visualizations.value.findIndex(v => v.id === saved.id)
                if (idx !== -1) visualizations.value[idx] = saved
            } else {
                visualizations.value.push(saved)
            }

            showAddDialog.value = false
            fetchVizData(saved.id)
        } catch (e: any) {
            saveError.value = e.message
        } finally {
            saving.value = false
        }
    }

    return {
        showAddDialog,
        isEditing,
        editingVizId,
        configTab,
        jsonConfigStr,
        previewData,
        previewLoading,
        saving,
        saveError,
        newViz,
        filteredMeasureColumns,
        filteredDimensionColumns,
        filteredAllColumns,
        filterMeasure,
        filterDimension,
        filterAll,
        addMetric,
        removeMetric,
        addFilter,
        removeFilter,
        openAddDialog,
        openEditDialog,
        onJsonChange,
        saveViz,
        addColorRule,
        removeColorRule
    }
}
