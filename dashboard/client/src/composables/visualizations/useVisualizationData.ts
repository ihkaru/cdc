import { ref } from 'vue'

export function useVisualizationData(surveyId: string) {
    const surveyName = ref('')
    const loading = ref(true)
    const labelSchema = ref<any>(null)
    const visualizations = ref<any[]>([])
    const vizData = ref<Record<number, any>>({})
    const loadingData = ref<Record<number, boolean>>({})

    async function fetchVizData(vizId: number) {
        loadingData.value[vizId] = true
        try {
            const res = await fetch(`/api/surveys/${surveyId}/visualizations/${vizId}/data`)
            vizData.value[vizId] = await res.json()
        } catch (e) {
            vizData.value[vizId] = { error: true }
        } finally {
            loadingData.value[vizId] = false
        }
    }

    async function loadData() {
        try {
            const [surveyRes, schemaRes, vizRes] = await Promise.all([
                fetch(`/api/surveys/${surveyId}`),
                fetch(`/api/surveys/${surveyId}/visualizations/schema`),
                fetch(`/api/surveys/${surveyId}/visualizations`),
            ])
            const survey = await surveyRes.json() as any
            surveyName.value = survey.surveyName

            labelSchema.value = await schemaRes.json()
            visualizations.value = await vizRes.json() as any[]

            for (const viz of visualizations.value) {
                fetchVizData(viz.id)
            }
        } catch (e) {
            console.error('Failed to load visualizations page', e)
        } finally {
            loading.value = false
        }
    }

    return {
        surveyName,
        loading,
        labelSchema,
        visualizations,
        vizData,
        loadingData,
        loadData,
        fetchVizData
    }
}
