#!/usr/bin/env bash
# Script wrapper benchmark kecepatan penarikan data dari FASIH-SM.
# Dijalankan di dalam container Docker cdc-rpa agar memanfaatkan tunnel VPN yang aktif.
# Sesuai pedoman operasional BPS Rule #7 (wajib menyertakan -w /app/src).

set -e

echo "======================================================================"
echo " MENGINISIASI PROSES BENCHMARK DATA FASIH-SM VIA VPN CONTAINER        "
echo "======================================================================"

# Memeriksa apakah container fasih-nexus-rpa sedang aktif
if ! docker ps --format '{{.Names}}' | grep -q "^fasih-nexus-rpa$"; then
    echo "❌ Error: Container 'fasih-nexus-rpa' tidak terdeteksi aktif."
    echo "Pastikan sistem layanan sync sudah berjalan (misal via ./start-docker.sh atau ./start-local.sh)."
    exit 1
fi

echo "📦 Menyalin script benchmark dan api_client terbaru ke dalam container fasih-nexus-rpa (tanpa rebuild)..."
docker cp rpa/src/benchmark_api.py fasih-nexus-rpa:/app/src/benchmark_api.py
docker cp rpa/src/api_client.py fasih-nexus-rpa:/app/src/api_client.py
docker cp rpa/src/main.py fasih-nexus-rpa:/app/src/main.py
docker cp rpa/src/worker/full_mode.py fasih-nexus-rpa:/app/src/worker/full_mode.py

echo "🚀 Mengirim perintah eksekusi ke dalam container fasih-nexus-rpa..."
# Menjalankan tanpa flag -t agar aman dieksekusi di background/CI pipeline tanpa error TTY
docker exec -w /app/src fasih-nexus-rpa python benchmark_api.py
