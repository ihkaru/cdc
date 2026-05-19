#!/usr/bin/env bash
# Script wrapper benchmark kecepatan SSO Login BPS.
# Dijalankan di dalam container Docker cdc-rpa agar memanfaatkan tunnel VPN yang aktif.

set -e

echo "======================================================================"
echo " MENGINISIASI PROSES BENCHMARK KECEPATAN SSO LOGIN VIA VPN CONTAINER  "
echo "======================================================================"

# Memeriksa apakah container fasih-nexus-rpa sedang aktif
if ! docker ps --format '{{.Names}}' | grep -q "^fasih-nexus-rpa$"; then
    echo "❌ Error: Container 'fasih-nexus-rpa' tidak terdeteksi aktif."
    echo "Pastikan sistem layanan sync sudah berjalan (misal via ./start-docker.sh atau ./start-local.sh)."
    exit 1
fi

echo "🚀 Mengirim perintah eksekusi ke dalam container fasih-nexus-rpa..."
# Menjalankan tanpa flag -t agar aman dieksekusi di background/CI pipeline tanpa error TTY
docker exec -w /app/src fasih-nexus-rpa python benchmark_sso.py
