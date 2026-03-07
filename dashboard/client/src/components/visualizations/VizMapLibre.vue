<template>
  <div class="map-container relative-position">
    <div ref="mapContainer" class="full-width full-height"></div>
    <q-inner-loading :showing="loading" dark>
      <q-spinner-gears size="50px" color="primary" />
    </q-inner-loading>
    <!-- Map Legend for custom Colors -->
    <div v-if="viz.config.colorRules && viz.config.colorRules.length > 0 && !loading" class="map-legend">
      <div v-for="(rule, i) in viz.config.colorRules" :key="i" class="row items-center q-mb-xs">
        <div class="legend-circle" :style="`background-color: ${rule.color};`"></div>
        <div class="text-caption text-white q-ml-sm">{{ rule.value }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'

// maplibre-gl is loaded via CDN script tag in index.html (externalized from Vite build)
// to prevent Web Worker scope issues when bundled by Rollup/Vite.
declare const maplibregl: any

const props = defineProps<{
  viz: any
  data: any
  loading: boolean
}>()

const mapContainer = ref<any>(null)
let map: any | null = null

// Hardcoded OpenStreetMap base via Carto Dark (no API key needed)
const styleObj: any = {
  version: 8,
  sources: {
    'carto-dark': {
      type: 'raster',
      tiles: [
        'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png',
        'https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png',
        'https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png',
        'https://d.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png'
      ],
      tileSize: 256,
      attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OSM</a>, &copy; <a href="https://carto.com/attributions">CARTO</a>'
    }
  },
  layers: [
    {
      id: 'base-tiles',
      type: 'raster',
      source: 'carto-dark',
      minzoom: 0,
      maxzoom: 19
    }
  ]
}

// Build a PLAIN (non-reactive) GeoJSON from current data
function buildPlainGeoJSON(): any {
  if (!props.data || !props.data.data || !Array.isArray(props.data.data)) {
    return { type: 'FeatureCollection', features: [] }
  }
  // JSON.parse(JSON.stringify(...)) strips Vue Proxy wrapping completely
  const rawRows = JSON.parse(JSON.stringify(props.data.data))
  return {
    type: 'FeatureCollection',
    features: rawRows.map((row: any) => ({
      type: 'Feature',
      geometry: {
        type: 'Point',
        coordinates: [Number(row.lng), Number(row.lat)]
      },
      properties: {
        ...row,
        metric_count: Number(row.metric_count) || 1
      }
    }))
  }
}

function buildColorExpression(): any {
  // Strip Vue Proxy from colorRules before building expression
  let rules: any[] = []
  try {
    rules = JSON.parse(JSON.stringify(props.viz.config.colorRules || []))
  } catch { rules = [] }

  if (!rules || rules.length === 0) return '#3fb1ce'
  
  // MapLibre 'match' expression: ['match', input, v1, c1, v2, c2, ..., fallback]
  const expr: any[] = ['match', ['get', 'color_val']]
  let hasValidRule = false
  rules.forEach((rule: any) => {
    if (rule.value != null && rule.value !== '' && rule.color) {
      expr.push(String(rule.value), String(rule.color))
      hasValidRule = true
    }
  })
  if (!hasValidRule) return '#3fb1ce'
  expr.push('#3fb1ce') // fallback for unmatched values
  return expr
}

function initMap() {
  if (!mapContainer.value) return
  console.log('[VizMapLibre] initMap called, container:', mapContainer.value)

  map = new maplibregl.Map({
    container: mapContainer.value,
    style: styleObj,
    center: [118.0149, -2.5489], // Center of Indonesia
    zoom: 4,
    minZoom: 2,
    pitchWithRotate: false,
    dragRotate: false
  })

  map.on('load', () => {
    if (!map) return

    // CRITICAL: pass plain object, NOT Vue reactive ref
    const plainGeoJSON = buildPlainGeoJSON()
    const colorExpr = buildColorExpression()
    console.log('[VizMapLibre] map loaded. GeoJSON features:', plainGeoJSON.features.length)
    console.log('[VizMapLibre] colorExpression:', JSON.stringify(colorExpr))
    console.log('[VizMapLibre] sample feature:', JSON.stringify(plainGeoJSON.features[0]))

    map.addSource('points-source', {
      type: 'geojson',
      data: plainGeoJSON
    })

    map.addLayer({
      id: 'points-layer',
      type: 'circle',
      source: 'points-source',
      paint: {
        'circle-radius': [
          'interpolate', ['linear'], ['zoom'],
          4, ['max', 4, ['min', 12, ['to-number', ['get', 'metric_count'], 1]]],
          14, ['max', 8, ['min', 30, ['*', 3, ['to-number', ['get', 'metric_count'], 1]]]]
        ],
        'circle-color': colorExpr,
        'circle-opacity': 0.8,
        'circle-stroke-width': 1,
        'circle-stroke-color': '#111'
      }
    })

    // Popup interaction — use click instead of hover for better UX on dense data
    const popup = new maplibregl.Popup({
      closeButton: true,
      closeOnClick: true,
      maxWidth: '300px',
      className: 'fasih-map-popup'
    })

    map.on('click', 'points-layer', (e: any) => {
      if (!map || !e.features || e.features.length === 0) return

      const feature = e.features[0] as any
      if (!feature.geometry?.coordinates) return

      const coords = feature.geometry.coordinates.slice()
      const p = feature.properties || {}

      // Find color for this point from color rules
      const colorRules: any[] = JSON.parse(JSON.stringify(props.viz.config.colorRules || []))
      const matchedRule = colorRules.find((r: any) => r.value && String(r.value) === String(p.color_val))
      const dotColor = matchedRule?.color || '#3fb1ce'

      // Popup fields meta — configured by user (labels + property keys)
      const popupFieldMeta: { key: string; label: string }[] = (props.data?.popupFieldMeta || [])

      // Build rows for configured popup fields
      const fieldRows = popupFieldMeta
        .filter(f => p[f.key] != null && String(p[f.key]).trim() !== '')
        .map(f => `
          <div style="display:flex;justify-content:space-between;gap:8px;padding:3px 0;border-bottom:1px solid #f0f0f0;">
            <span style="color:#666;font-size:11px;flex-shrink:0;">${f.label}</span>
            <span style="font-size:12px;font-weight:500;text-align:right;word-break:break-word;white-space:normal;">${p[f.key]}</span>
          </div>`)
        .join('')

      const countRow = `
        <div style="display:flex;justify-content:space-between;gap:8px;padding:3px 0;">
          <span style="color:#666;font-size:11px;">Jumlah Titik</span>
          <span style="font-size:12px;font-weight:600;">${p.metric_count ?? 1}</span>
        </div>`

      const coordRow = `
        <div style="color:#aaa;font-size:10px;padding-top:4px;text-align:right;">
          📍 ${Number(coords[1]).toFixed(4)}, ${Number(coords[0]).toFixed(4)}
        </div>`

      const statusHeader = p.color_val ? `
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px;">
          <div style="width:10px;height:10px;border-radius:50%;background:${dotColor};flex-shrink:0;"></div>
          <span style="font-weight:600;font-size:12px;color:#222;">${p.color_val}</span>
        </div>` : ''

      const html = `
        <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;padding:4px 2px;min-width:180px;max-width:260px;color:#1a1a1a;background:#fff;">
          ${statusHeader}
          <div style="max-height: 150px; overflow-y: auto; overflow-x: hidden; padding-right: 4px; margin-right: -4px;">
            ${fieldRows}
          </div>
          ${countRow}
          ${coordRow}
        </div>`


      while (Math.abs(e.lngLat.lng - (coords[0] ?? 0)) > 180) {
        coords[0] += e.lngLat.lng > coords[0] ? 360 : -360
      }
      popup.setLngLat([coords[0], coords[1]]).setHTML(html).addTo(map)
    })

    map.on('mouseenter', 'points-layer', () => {
      if (map) map.getCanvas().style.cursor = 'pointer'
    })
    map.on('mouseleave', 'points-layer', () => {
      if (map) map.getCanvas().style.cursor = ''
    })

    fitBoundsToData(plainGeoJSON.features)
  })
}

function updateData() {
  if (!map) return
  const source = map.getSource('points-source')
  if (!source) return

  const plainGeoJSON = buildPlainGeoJSON()
  source.setData(plainGeoJSON)
  fitBoundsToData(plainGeoJSON.features)
}

function fitBoundsToData(features: any[]) {
  if (!map || features.length === 0) return
  const bounds = new maplibregl.LngLatBounds()
  features.forEach((f: any) => {
    const c = f.geometry?.coordinates
    if (c && c[0] != null && c[1] != null) bounds.extend([c[0], c[1]])
  })
  if (!bounds.isEmpty()) {
    map.fitBounds(bounds, { padding: 50, maxZoom: 10, duration: 1000 })
  }
}

watch(() => props.data, () => {
  if (map?.isStyleLoaded()) updateData()
}, { deep: true })

// Full refresh if config changes (like color rules)
watch(() => props.viz.config, () => {
  if (map) { map.remove(); map = null }
  nextTick(() => initMap())
}, { deep: true })

onMounted(() => initMap())

onUnmounted(() => {
  if (map) { map.remove(); map = null }
})
</script>

<style scoped>
.map-container {
  width: 100%;
  height: 100%;
  min-height: 400px;
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid #424242;
}

.map-legend {
  position: absolute;
  bottom: 20px;
  right: 10px;
  background: rgba(30, 30, 30, 0.85);
  padding: 10px;
  border-radius: 6px;
  border: 1px solid #444;
  z-index: 2;
  backdrop-filter: blur(4px);
  min-width: 120px;
}

.legend-circle {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1px solid rgba(255,255,255,0.2);
}

:deep(.maplibregl-popup-content) {
  background-color: #f8f9fa;
  border-radius: 6px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.3);
  padding: 10px 14px;
}
:deep(.maplibregl-popup-anchor-bottom .maplibregl-popup-tip) {
  border-top-color: #f8f9fa;
}
</style>
