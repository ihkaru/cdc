export function formatNumber(num: number) {
    if (num === null || num === undefined) return '-'
    return new Intl.NumberFormat('id-ID', { maximumFractionDigits: 2 }).format(num)
}

export function getChartOption(viz: any, data: any) {
    if (!data || !data.categories) return {}

    const isHorizontal = viz.chartType === 'bar_horizontal'

    const xAxis = {
        type: isHorizontal ? 'value' : 'category',
        data: isHorizontal ? null : data.categories,
        axisLabel: { color: '#a0aabf' },
        splitLine: { show: isHorizontal, lineStyle: { color: '#262b36' } }
    }

    const yAxis = {
        type: isHorizontal ? 'category' : 'value',
        data: isHorizontal ? data.categories : null,
        axisLabel: { color: '#a0aabf' },
        splitLine: { show: !isHorizontal, lineStyle: { color: '#262b36' } }
    }

    return {
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        legend: { show: data.series.length > 1, textStyle: { color: '#a0aabf' }, type: 'scroll' },
        grid: { left: '3%', right: '4%', bottom: '3%', top: data.series.length > 1 ? '40px' : '20px', containLabel: true },
        xAxis,
        yAxis,
        series: data.series.map((s: any, idx: number) => {
            // Find the metric config that matches this series name to extract its color
            const metricConfig = viz.config.metrics.find((m: any) =>
                m.label === s.name ||
                m.column === s.name ||
                (m.expression && m.expression.includes(s.name))
            );

            const seriesColor = metricConfig?.color || undefined;

            return {
                name: s.name,
                type: 'bar',
                data: s.data,
                itemStyle: {
                    borderRadius: isHorizontal ? [0, 4, 4, 0] : [4, 4, 0, 0],
                    ...(seriesColor && { color: seriesColor })
                },
                label: {
                    show: true,
                    position: isHorizontal ? 'right' : 'top',
                    color: '#fff',
                    formatter: (params: any) => {
                        const val = params.value;
                        if (val === 0 || val === null || val === undefined) return '';
                        // Heuristic: If it's a small float or explicitly named percentage metric, format as %
                        if ((typeof val === 'number' && val > 0 && val <= 100 && val % 1 !== 0) || s.name.toLowerCase().includes('%')) {
                            return new Intl.NumberFormat('id-ID', { maximumFractionDigits: 1 }).format(val) + '%';
                        }
                        // Large numbers grouping
                        if (val >= 1000) {
                            return new Intl.NumberFormat('id-ID', { maximumFractionDigits: 0 }).format(val);
                        }
                        // Normal numbers
                        return new Intl.NumberFormat('id-ID', { maximumFractionDigits: 2 }).format(val);
                    }
                }
            }
        })
    }
}
