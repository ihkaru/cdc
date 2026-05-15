#!/bin/bash

# FasihNexus Project Dumper
# Generates a comprehensive project overview in Markdown format.

OUTPUT_FILE="project_snapshot.md"

echo "# Project Snapshot: FasihNexus" > $OUTPUT_FILE
echo "Generated at: $(date)" >> $OUTPUT_FILE
echo "" >> $OUTPUT_FILE

# 1. Project Structure (Tree)
echo "## 📂 Project Structure" >> $OUTPUT_FILE
echo "\`\`\`text" >> $OUTPUT_FILE
if command -v git >/dev/null 2>&1; then
    # Respect .gitignore using git ls-files
    echo "Listing files respecting .gitignore:" >> $OUTPUT_FILE
    git ls-files -co --exclude-standard >> $OUTPUT_FILE
elif command -v tree >/dev/null 2>&1; then
    # Use tree --gitignore if available
    tree -a --gitignore >> $OUTPUT_FILE
else
    # Fallback to find with some common ignores
    find . -maxdepth 4 -not -path '*/.*' -not -path './node_modules*' -not -path './venv*' >> $OUTPUT_FILE
fi
echo "\`\`\`" >> $OUTPUT_FILE
echo "" >> $OUTPUT_FILE

# 2. Docker Compose
echo "## 🐳 Docker Compose Configuration" >> $OUTPUT_FILE
if [ -f "docker-compose.yml" ]; then
    echo "\`\`\`yaml" >> $OUTPUT_FILE
    cat docker-compose.yml >> $OUTPUT_FILE
    echo "\`\`\`" >> $OUTPUT_FILE
else
    echo "*docker-compose.yml not found*" >> $OUTPUT_FILE
fi
echo "" >> $OUTPUT_FILE

# 3. Dockerfiles
echo "## 🏗️ Dockerfiles" >> $OUTPUT_FILE
find . -name "Dockerfile" | while read -r df; do
    echo "### File: \`$df\`" >> $OUTPUT_FILE
    echo "\`\`\`dockerfile" >> $OUTPUT_FILE
    cat "$df" >> $OUTPUT_FILE
    echo "\`\`\`" >> $OUTPUT_FILE
    echo "" >> $OUTPUT_FILE
done

# 4. Environment Examples
echo "## 🔑 Environment Configuration (Examples)" >> $OUTPUT_FILE
find . -name ".env.example" | while read -r env; do
    echo "### File: \`$env\`" >> $OUTPUT_FILE
    echo "\`\`\`text" >> $OUTPUT_FILE
    cat "$env" >> $OUTPUT_FILE
    echo "\`\`\`" >> $OUTPUT_FILE
    echo "" >> $OUTPUT_FILE
done

# 5. Core Entrypoints (Summary)
echo "## 🚀 Core Entrypoints" >> $OUTPUT_FILE
CORE_FILES=("rpa/src/app.py" "rpa/src/main.py" "dashboard/server/index.ts")
for f in "${CORE_FILES[@]}"; do
    if [ -f "$f" ]; then
        echo "### File: \`$f\`" >> $OUTPUT_FILE
        echo "\`\`\`python" >> $OUTPUT_FILE
        # Show first 50 lines only to keep dump manageable
        head -n 50 "$f" >> $OUTPUT_FILE
        echo "..." >> $OUTPUT_FILE
        echo "\`\`\`" >> $OUTPUT_FILE
        echo "" >> $OUTPUT_FILE
    fi
done

echo "✅ Snapshot generated in $OUTPUT_FILE"
