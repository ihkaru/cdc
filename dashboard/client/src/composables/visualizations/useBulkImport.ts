import { ref } from 'vue'
import type { Ref } from 'vue'
import { useQuasar } from 'quasar'
import { useRoute } from 'vue-router'

export function useBulkImport(
    visualizations: Ref<any[]>,
    fetchVizData: (id: number) => Promise<void>
) {
    const $q = useQuasar()
    const route = useRoute()
    const surveyId = route.params.id as string

    const showBulkDialog = ref(false)
    const bulkJsonStr = ref('[\n  \n]')
    const importingBulk = ref(false)

    function openBulkDialog() {
        bulkJsonStr.value = '[\n  \n]'
        showBulkDialog.value = true
    }

    async function submitBulkImport() {
        if (!bulkJsonStr.value.trim()) return

        importingBulk.value = true
        try {
            const payloads = JSON.parse(bulkJsonStr.value)

            if (!Array.isArray(payloads)) {
                throw new Error("Format harus berupa Array of JSON Objects [...]")
            }

            let successCount = 0
            let failCount = 0

            for (const item of payloads) {
                try {
                    if (!item.name || !item.chartType || !item.config) {
                        failCount++
                        continue
                    }

                    const res = await fetch(`/api/surveys/${surveyId}/visualizations`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            name: item.name,
                            chartType: item.chartType,
                            config: item.config
                        })
                    })

                    if (res.ok) {
                        const saved = await res.json() as any
                        visualizations.value.push(saved)
                        fetchVizData(saved.id)
                        successCount++
                    } else {
                        failCount++
                    }
                } catch (err) {
                    failCount++
                }
            }

            $q.notify({
                type: successCount > 0 ? (failCount > 0 ? 'warning' : 'positive') : 'negative',
                message: `Magic Import Selesai. Sukses: ${successCount}, Gagal/Invalid: ${failCount}`,
                icon: 'electric_bolt'
            })

            if (successCount > 0) {
                showBulkDialog.value = false
            }

        } catch (e: any) {
            $q.notify({ type: 'negative', message: 'JSON Parse Error: ' + e.message })
        } finally {
            importingBulk.value = false
        }
    }

    return {
        showBulkDialog,
        bulkJsonStr,
        importingBulk,
        openBulkDialog,
        submitBulkImport
    }
}
