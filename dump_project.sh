#!/bin/bash
# dump_project.sh - Highly Optimized Snapshot (Architecture & Core Logic Only)
# This version avoids bloating the context with repetitive or non-essential code.

OUTPUT_FILE="project_snapshot.md"
TARGET_DIR="."

# Strict exclusion pattern
EXCLUDES="node_modules|dist|.git|.quasar|vendor|__pycache__|venv|*.lock|migrations|references|artifacts|tmp|*.log|*.txt|*.jpg|*.png|*.pdf|*.json|*.html"

echo "🚀 Generating HIGHLY OPTIMIZED project dump to $OUTPUT_FILE..."

{
  echo "# FasihNexus Architecture Snapshot"
  echo "Generated at: $(date)"
  echo "Scope: Infrastructure, Entrypoints, and Critical Business Logic."
  echo ""
  
  echo "## 📂 High-Level Structure"
  echo '```text'
  if command -v tree &> /dev/null; then
    tree -L 2 -I "node_modules|dist|.git|venv|data"
  else
    find . -maxdepth 2 -not -path '*/.*' | grep -Ev "node_modules|dist|.git" | sed -e 's;[^/]*/;|____;g;s;____|; |;g'
  fi
  echo '```'
  echo ""

  echo "## 🐳 Docker & Infrastructure (The Foundation)"
  find . -maxdepth 1 -name "docker-compose*.yml" -o -name "*.sh" | while read -r file; do
    echo "### $file"
    echo '```yaml'
    cat "$file"
    echo '```'
    echo ""
  done

  echo "## 📜 Project Documentation"
  [ -f "GEMINI.md" ] && echo "### GEMINI.md" && echo '```markdown' && cat GEMINI.md && echo '```' && echo ""
  [ -f "README.md" ] && echo "### README.md" && echo '```markdown' && cat README.md && echo '```' && echo ""

  echo "## ⚙️ Configuration & Environment"
  # Include .env (raw as requested) and main package definitions
  [ -f ".env" ] && echo "### .env" && echo '```bash' && cat .env && echo '```'
  find . -maxdepth 2 -name "package.json" -o -name "requirements.txt" | while read -r file; do
    echo "### $file"
    echo '```json'
    cat "$file"
    echo '```'
  done

  echo "## 🏗️ Essential Code (Entrypoints & Schema)"
  # We only include the most critical files to keep the dump under a reasonable limit.
  CRITICAL_FILES=(
    "dashboard/server/index.ts"
    "dashboard/server/db/schema.ts"
    "dashboard/server/db/index.ts"
    "rpa/src/app.py"
    "rpa/src/auth.py"
    "rpa/src/routes/sync.py"
    "rpa/src/worker/scheduler.py"
    "rpa/src/worker/queue.py"
    "rpa/src/main.py"
    "vpn/entrypoint.sh"
    "dashboard/entrypoint.sh"
  )

  for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
      echo "### $file"
      # Determine block type
      case "$file" in
        *.py) echo '```python' ;;
        *.ts) echo '```typescript' ;;
        *.sh) echo '```bash' ;;
        *) echo '```' ;;
      esac
      cat "$file"
      echo '```'
      echo ""
    fi
  done

  echo "## 📜 Recent Activity"
  echo "Last 5 Git Commits:"
  echo '```'
  git log -n 5 --oneline 2>/dev/null || echo "Git history unavailable."
  echo '```'

} > "$OUTPUT_FILE"

echo "✅ Optimized Dump complete! Saved to $OUTPUT_FILE"
