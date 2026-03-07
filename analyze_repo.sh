#!/bin/bash

# Array direktori yang akan di-exclude, disatukan jadi pipe untuk tree dan find
TARGET_DIR="."
EXCLUDES="node_modules|dist|.git|.vuepress|.quasar|vendor|__pycache__|.env|.venv|venv|out|.turbo|.next|coverage|data"

echo "================================================="
echo "📁 REPOSITORY STRUCTURE (excluding build/modules)"
echo "================================================="
if command -v tree &> /dev/null; then
  tree -I "$EXCLUDES" -aC "$TARGET_DIR" | less -F -X
else
  # Mocking tree using find
  find "$TARGET_DIR" -type d -regextype posix-extended -regex ".*/($EXCLUDES).*" -prune -o -print | sed -e 's;[^/]*/;|____;g;s;____|; |;g'
fi

echo ""
echo "================================================="
echo "🗄️ LARGE FILES (>400 LINES)"
echo "================================================="
echo "Finding files..."

# Mencari seluruh file, mengecualikan folder-folder berat
find "$TARGET_DIR" \
    -type d -regextype posix-extended -regex ".*/($EXCLUDES).*" -prune \
    -o -type f -not -name "package*.json" -not -name "*bun.lock*" -not -name "yarn.lock" -not -name "pnpm-lock.yaml" -print0 | xargs -0 -I{} wc -l "{}" 2>/dev/null | \
    awk '$1 > 400 && $2 != "total" {print $0}' | \
    sort -nr | \
    awk '{printf "\033[31m[%d lines]\033[0m %s\n", $1, $2}'

echo "================================================="
echo "✅ Analysis Complete."
