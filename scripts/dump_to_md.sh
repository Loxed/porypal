#!/bin/bash

# dump_to_md.sh -- dump a project's source files into a single markdown file
# for pasting into AI chat contexts.
#
# Usage:
#   ./dump_to_md.sh                              # dump everything
#   ./dump_to_md.sh src lib                      # only src/ and lib/
#   ./dump_to_md.sh --since                      # only files changed since last commit
#   ./dump_to_md.sh --ext ts tsx rs              # override extensions
#   ./dump_to_md.sh --copy                       # copy result to clipboard
#   ./dump_to_md.sh --build                      # include build/deploy files (.spec, workflows, Dockerfile, etc.)
#   ./dump_to_md.sh src --since --copy --build   # combine freely

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_NAME="$(basename "$ROOT")"
OUT="$ROOT/${PROJECT_NAME}_dump.md"

DEFAULT_EXTENSIONS=("py" "js" "jsx" "ts" "tsx" "css" "scss"
                    "html" "yaml" "yml" "toml" "json" "sh" "bash"
                    "rs" "go" "java" "cpp" "c" "h" "cs" "rb" "php"
                    "swift" "kt" "vue" "svelte" "mdx")

BUILD_EXTENSIONS=("spec" "cfg" "ini" "env")

BUILD_FILENAMES=("Dockerfile" "Makefile" "docker-compose.yml" "docker-compose.yaml"
                 ".dockerignore" ".gitignore" "Procfile" "fly.toml" "railway.toml"
                 "render.yaml" "netlify.toml" "vercel.json" ".env.example")

DEFAULT_EXCLUDE_DIRS=(".venv" "venv" "env" "__pycache__" ".git"
                      "build" "dist" "out" "target" "node_modules"
                      ".next" ".nuxt" ".svelte-kit" "coverage" ".cache")

DEFAULT_EXCLUDE_FILES=("package-lock.json" "yarn.lock" "pnpm-lock.yaml"
                       "Cargo.lock" "poetry.lock" "*.min.js" "*.min.css")

FOLDERS=()
EXTENSIONS=()
SINCE=false
COPY=false
BUILD=false

# -- Parse args ----------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --since)  SINCE=true;  shift ;;
        --copy)   COPY=true;   shift ;;
        --build)  BUILD=true;  shift ;;
        --ext)
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                EXTENSIONS+=("$1")
                shift
            done
            ;;
        *) FOLDERS+=("$1"); shift ;;
    esac
done

if [ ${#EXTENSIONS[@]} -eq 0 ]; then
    EXTENSIONS=("${DEFAULT_EXTENSIONS[@]}")
fi

if $BUILD; then
    EXTENSIONS+=("${BUILD_EXTENSIONS[@]}")
fi

# -- Check clipboard availability ----------------------------------------------
CLIPBOARD_CMD=""
if $COPY; then
    if grep -qi microsoft /proc/version 2>/dev/null; then
        CLIPBOARD_CMD="clip.exe"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        CLIPBOARD_CMD="pbcopy"
    elif command -v xclip &>/dev/null; then
        CLIPBOARD_CMD="xclip -selection clipboard"
    elif command -v xsel &>/dev/null; then
        CLIPBOARD_CMD="xsel --clipboard --input"
    else
        echo "  x --copy requires xclip or xsel on Linux."
        echo "    Install with:  sudo apt install xclip"
        exit 1
    fi
fi

# -- Add output file to .gitignore if not already there -----------------------
GITIGNORE="$ROOT/.gitignore"
OUTPUT_FILENAME="${PROJECT_NAME}_dump.md"
if [ -f "$GITIGNORE" ]; then
    if ! grep -qxF "$OUTPUT_FILENAME" "$GITIGNORE"; then
        echo "" >> "$GITIGNORE"
        echo "$OUTPUT_FILENAME" >> "$GITIGNORE"
        echo "  + Added $OUTPUT_FILENAME to .gitignore"
    fi
else
    echo "$OUTPUT_FILENAME" > "$GITIGNORE"
    echo "  + Created .gitignore with $OUTPUT_FILENAME"
fi

# -- If --since, build set of changed files ------------------------------------
CHANGED_FILES=""
if $SINCE; then
    CHANGED_FILES=$(git -C "$ROOT" diff --name-only HEAD 2>/dev/null)
    STAGED=$(git -C "$ROOT" diff --name-only --cached 2>/dev/null)
    UNTRACKED=$(git -C "$ROOT" ls-files --others --exclude-standard 2>/dev/null)
    CHANGED_FILES=$(printf "%s\n%s\n%s" "$CHANGED_FILES" "$STAGED" "$UNTRACKED" | sort -u | grep -v '^$')
    if [ -z "$CHANGED_FILES" ]; then
        echo "  No changed files since last commit."
        exit 0
    fi
fi

# -- Dump files ----------------------------------------------------------------
> "$OUT"

find "$ROOT" -type f | sort | while read -r file; do
    rel="${file#$ROOT/}"

    # Skip excluded dirs.
    # --build: allow .github/ through (catches CI workflows), but still block .git/
    skip=false
    for dir in "${DEFAULT_EXCLUDE_DIRS[@]}"; do
        if $BUILD && [[ "$dir" == ".git" ]]; then
            # Block .git/ exactly but allow .github/
            if [[ "$rel" == ".git/"* || "$rel" == ".git" ]]; then
                skip=true; break
            fi
        else
            if [[ "$rel" == *"$dir"* ]]; then
                skip=true; break
            fi
        fi
    done
    $skip && continue

    # Skip excluded files
    filename="$(basename "$rel")"
    for pattern in "${DEFAULT_EXCLUDE_FILES[@]}"; do
        if [[ "$filename" == $pattern ]]; then
            skip=true; break
        fi
    done
    $skip && continue

    # Skip this script and the output file
    [[ "$file" == "$0" ]] && continue
    [[ "$file" == "$OUT" ]] && continue

    # If --since, skip files not in the changed list
    if $SINCE; then
        echo "$CHANGED_FILES" | grep -qx "$rel" || continue
    fi

    # If folders were specified, only include files under those folders
    if [ ${#FOLDERS[@]} -gt 0 ]; then
        match_folder=false
        for folder in "${FOLDERS[@]}"; do
            if [[ "$rel" == "$folder"* ]]; then
                match_folder=true; break
            fi
        done
        $match_folder || continue
    fi

    # Check extension match
    ext="${file##*.}"
    match_ext=false
    for e in "${EXTENSIONS[@]}"; do
        [[ "$ext" == "$e" ]] && match_ext=true && break
    done

    # --build: also match exact filenames (Dockerfile, Makefile, etc.)
    if ! $match_ext && $BUILD; then
        for name in "${BUILD_FILENAMES[@]}"; do
            if [[ "$filename" == "$name" ]]; then
                match_ext=true; break
            fi
        done
    fi

    $match_ext || continue

    # Language hint for syntax highlighting
    case "$ext" in
        py)          lang="python" ;;
        js|jsx)      lang="jsx" ;;
        ts|tsx)      lang="tsx" ;;
        sh|bash)     lang="bash" ;;
        rs)          lang="rust" ;;
        go)          lang="go" ;;
        java)        lang="java" ;;
        cpp|c|h)     lang="cpp" ;;
        cs)          lang="csharp" ;;
        rb)          lang="ruby" ;;
        swift)       lang="swift" ;;
        kt)          lang="kotlin" ;;
        html)        lang="html" ;;
        css|scss)    lang="css" ;;
        yaml|yml)    lang="yaml" ;;
        toml)        lang="toml" ;;
        json)        lang="json" ;;
        spec|cfg)    lang="python" ;;
        ini)         lang="ini" ;;
        *)           lang="$ext" ;;
    esac

    echo "# $rel" >> "$OUT"
    echo '```'"$lang" >> "$OUT"
    cat "$file" >> "$OUT"
    echo "" >> "$OUT"
    echo '```' >> "$OUT"
    echo "" >> "$OUT"
    echo "----" >> "$OUT"
    echo "" >> "$OUT"
done

# -- Token estimate ------------------------------------------------------------
CHARS=$(wc -c < "$OUT")
TOKENS=$(( CHARS / 4 ))

echo "Written to ${OUTPUT_FILENAME}"
echo "~${TOKENS} tokens"
$BUILD && echo "  (--build: included .spec, .github/workflows, Dockerfile, Makefile, etc.)"

# -- Copy to clipboard ---------------------------------------------------------
if $COPY; then
    $CLIPBOARD_CMD < "$OUT"
    echo "Copied to clipboard"
fi