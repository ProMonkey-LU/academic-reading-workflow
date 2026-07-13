#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ACTIVE_FILE="$ROOT/config/active-skills.txt"
NATURE_ROOT="$ROOT/vendor/nature-skills"
DST="${CODEX_SKILLS_DIR:-${CODEX_HOME:-$HOME/.codex}/skills}"
MANIFEST="$DST/.academic-reading-workflow-managed"

die() {
  echo "error: $*" >&2
  exit 1
}

active_names() {
  sed -e 's/[[:space:]]*#.*$//' -e '/^[[:space:]]*$/d' "$ACTIVE_FILE"
}

source_for() {
  local name="$1"
  if [ -f "$ROOT/skills/$name/SKILL.md" ]; then
    printf '%s\n' "$ROOT/skills/$name"
    return 0
  fi
  if [ -f "$NATURE_ROOT/skills/$name/SKILL.md" ]; then
    printf '%s\n' "$NATURE_ROOT/skills/$name"
    return 0
  fi
  if [ -f "$ROOT/local-vendor/$name/SKILL.md" ]; then
    printf '%s\n' "$ROOT/local-vendor/$name"
    return 0
  fi
  case "$name" in
    aminer-data-search) name="aminer-open-academic-1.0.5" ;;
    Memory|memory) name="memory-1.0.2" ;;
    research-paper-writer) name="research-paper-writer-0.1.0" ;;
    obsidian-ontology-sync) name="obsidian-ontology-sync-1.0.1" ;;
    tmux) name="tmux-1.0.0" ;;
  esac
  if [ -f "$ROOT/local-vendor/$name/SKILL.md" ]; then
    printf '%s\n' "$ROOT/local-vendor/$name"
    return 0
  fi
  return 1
}

is_previous_managed() {
  local name="$1"
  [ -f "$MANIFEST" ] && grep -Fxq "$name" "$MANIFEST"
}

install_one() {
  local name="$1" source target current
  source="$(source_for "$name")" || die "source not found for active skill: $name"
  target="$DST/$name"

  if [ -e "$target" ] || [ -L "$target" ]; then
    if [ ! -L "$target" ]; then
      die "refusing to replace unmanaged path: $target"
    fi
    current="$(readlink "$target")"
    if [ "$current" = "$source" ]; then
      return 0
    fi
    if ! is_previous_managed "$name" && [[ "$current" != "$ROOT/"* ]]; then
      die "refusing to replace unmanaged symlink: $target -> $current"
    fi
    unlink "$target"
  fi

  ln -s "$source" "$target"
  echo "linked $name"
}

install_all() {
  local name old
  mkdir -p "$DST"

  while IFS= read -r name; do
    install_one "$name"
  done < <(active_names)

  if active_names | grep -q '^nature-'; then
    [ -d "$NATURE_ROOT/skills/_shared" ] || die "nature _shared directory is missing"
    if [ -e "$DST/_shared" ] || [ -L "$DST/_shared" ]; then
      if [ ! -L "$DST/_shared" ]; then
        die "refusing to replace unmanaged path: $DST/_shared"
      fi
      rm "$DST/_shared"
    fi
    ln -s "$NATURE_ROOT/skills/_shared" "$DST/_shared"
  elif [ -L "$DST/_shared" ] && [[ "$(readlink "$DST/_shared")" == "$ROOT/"* ]]; then
    unlink "$DST/_shared"
  fi

  if [ -f "$MANIFEST" ]; then
    while IFS= read -r old; do
      [ -n "$old" ] || continue
      if ! active_names | grep -Fxq "$old"; then
        if [ -L "$DST/$old" ] && [[ "$(readlink "$DST/$old")" == "$ROOT/"* ]]; then
          rm "$DST/$old"
          echo "unlinked $old"
        fi
      fi
    done < "$MANIFEST"
  fi

  active_names > "$MANIFEST"
}

check_all() {
  local name source target failures=0
  [ -f "$ACTIVE_FILE" ] || die "missing active skill list: $ACTIVE_FILE"
  [ -d "$DST" ] || die "Codex skill directory does not exist: $DST"

  if [ "$(active_names | sort | uniq -d | wc -l | tr -d ' ')" != "0" ]; then
    echo "duplicate entries found in $ACTIVE_FILE" >&2
    failures=1
  fi

  while IFS= read -r name; do
    if ! source="$(source_for "$name")"; then
      echo "MISSING SOURCE $name" >&2
      failures=1
      continue
    fi
    [ -f "$source/SKILL.md" ] || { echo "MISSING SKILL.md $name" >&2; failures=1; }
    target="$DST/$name"
    if [ ! -L "$target" ]; then
      echo "MISSING LINK $name" >&2
      failures=1
    elif [ "$(readlink "$target")" != "$source" ]; then
      echo "WRONG LINK $name -> $(readlink "$target")" >&2
      failures=1
    else
      echo "OK $name"
    fi
  done < <(active_names)

  if active_names | grep -q '^nature-'; then
    [ -L "$DST/_shared" ] || { echo "MISSING LINK _shared" >&2; failures=1; }
  fi

  [ "$failures" -eq 0 ] || exit 1
}

list_all() {
  local name source state
  printf '%-34s %-10s %s\n' "SKILL" "STATUS" "SOURCE"
  printf '%-34s %-10s %s\n' "-----" "------" "------"
  for source in "$ROOT/skills"/* "$NATURE_ROOT/skills"/nature-* "$ROOT/local-vendor"/*; do
    [ -f "$source/SKILL.md" ] || continue
    name="$(sed -n 's/^name:[[:space:]]*//p' "$source/SKILL.md" | head -1 | tr -d '\r')"
    [ -n "$name" ] || name="$(basename "$source")"
    state="optional"
    active_names | grep -Fxq "$name" && state="active"
    active_names | grep -Fxq "$(basename "$source")" && state="active"
    printf '%-34s %-10s %s\n' "$name" "$state" "$source"
  done | sort -f
}

set_enabled() {
  local action="$1" name="$2" tmp
  source_for "$name" >/dev/null || die "unknown or unavailable skill: $name"
  tmp="$(mktemp "${TMPDIR:-/tmp}/active-skills.XXXXXX")"
  if [ "$action" = "enable" ]; then
    if ! active_names | grep -Fxq "$name"; then
      cp "$ACTIVE_FILE" "$tmp"
      printf '\n%s\n' "$name" >> "$tmp"
      mv "$tmp" "$ACTIVE_FILE"
    fi
  else
    awk -v target="$name" '
      $0 != target { lines[++count] = $0 }
      END {
        while (count > 0 && lines[count] ~ /^[[:space:]]*$/) count--
        for (i = 1; i <= count; i++) print lines[i]
      }
    ' "$ACTIVE_FILE" > "$tmp"
    mv "$tmp" "$ACTIVE_FILE"
  fi
  rm -f "$tmp"
  install_all
  check_all
}

update_nature() {
  local old new
  [ -d "$NATURE_ROOT/.git" ] || [ -f "$NATURE_ROOT/.git" ] || die "nature submodule is not initialized"
  old="$(git -C "$NATURE_ROOT" rev-parse HEAD)"
  git -C "$NATURE_ROOT" fetch origin main
  git -C "$NATURE_ROOT" merge --ff-only origin/main
  new="$(git -C "$NATURE_ROOT" rev-parse HEAD)"
  install_all
  check_all
  echo "nature-skills: $old -> $new"
  git -C "$ROOT" diff --submodule=log -- vendor/nature-skills || true
}

usage() {
  echo "Usage: $0 {list|install|check|update-nature|enable NAME|disable NAME}"
}

case "${1:-}" in
  list) list_all ;;
  install) install_all ;;
  check) check_all ;;
  update-nature) update_nature ;;
  enable|disable)
    [ "$#" -eq 2 ] || die "$1 requires one skill name"
    set_enabled "$1" "$2"
    ;;
  *) usage; exit 2 ;;
esac
