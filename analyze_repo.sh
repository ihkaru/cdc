#!/bin/bash

# Array direktori yang akan di-exclude, disatukan jadi pipe untuk tree dan find
TARGET_DIR="."
EXCLUDES="node_modules|dist|.git|.vuepress|.quasar|vendor|__pycache__|.env|.venv|venv|out|.turbo|.next|coverage|data"

echo "================================================="
echo "📁 REPOSITORY STRUCTURE (excluding build/modules)"
echo "================================================="
if command -v tree &> /dev/null; then
  # Use tree with -h (size) or alternatively pipe to awk, but doing this natively is hard.
  # We will use a custom find approach for both since the user specifically requested *line counts*, 
  # which `tree` does not natively support (it only supports file sizes).
  
  # Recursive function to print tree with line counts
  export EXCLUDES
  print_tree() {
    local dir="$1"
    local prefix="$2"
    
    # Get items, ignoring excluded dirs
    local items=($(ls -A "$dir" 2>/dev/null | grep -Ev "^(${EXCLUDES})$"))
    local count=${#items[@]}
    
    for ((i=0; i<count; i++)); do
      local item="${items[$i]}"
      local path="$dir/$item"
      local is_last=$((i == count - 1))
      
      local branch="├── "
      local next_prefix="$prefix│   "
      if [ "$is_last" -eq 1 ]; then
        branch="└── "
        next_prefix="$prefix    "
      fi
      
      if [ -d "$path" ]; then
        echo "${prefix}${branch}${item}/"
        print_tree "$path" "$next_prefix"
      elif [ -f "$path" ]; then
        local lines=$(wc -l < "$path" 2>/dev/null || echo "?")
        echo "${prefix}${branch}${item} (${lines} lines)"
      fi
    done
  }
  
  echo "."
  print_tree "$TARGET_DIR" ""
else
  # Mocking tree using find
  find "$TARGET_DIR" -type d -regextype posix-extended -regex ".*/($EXCLUDES).*" -prune -o -print | while read -r filepath; do
    if [ -f "$filepath" ]; then
      lines=$(wc -l < "$filepath" 2>/dev/null || echo "?")
      echo "$filepath ($lines lines)" | sed -e 's;[^/]*/;|____;g;s;____|; |;g'
    else
      echo "$filepath" | sed -e 's;[^/]*/;|____;g;s;____|; |;g'
    fi
  done
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
