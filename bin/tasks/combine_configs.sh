#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

combine_config() {
  local source_dir="$1"
  local output_file="$2"
  local tmp_file
  tmp_file="$(mktemp)"

  _append_file() {
    cat "$1" >> "${tmp_file}"
    printf '\n' >> "${tmp_file}"
  }

  # 1. Emit ALL group.toml files first (sorted), matching original behaviour.
  while IFS= read -r -d '' file; do
    _append_file "$file"
  done < <(find "${source_dir}" -type f -name 'group.toml' -print0 | sort -z)

  # 2. Walk subdirectories emitting non-group toml files, respecting _order.
  _process_dir() {
    local dir="$1"

    # Emit toml files in this directory (sorted, excluding group/config)
    while IFS= read -r -d '' file; do
      _append_file "$file"
    done < <(find "${dir}" -maxdepth 1 -type f -name '*.toml' \
      -not -name 'group.toml' -not -name 'config.toml' -print0 | sort -z)

    # Collect actual subdirectories (excluding _-prefixed)
    local all_subdirs=()
    for d in "${dir}"/*/; do
      [[ -d "$d" ]] || continue
      local name
      name="$(basename "$d")"
      [[ "${name}" == _* ]] && continue
      all_subdirs+=("${name}")
    done

    # No subdirectories — nothing more to do
    if [[ ${#all_subdirs[@]} -eq 0 ]]; then
      return
    fi

    # Determine subdirectory order
    local subdirs=()
    local order_file="${dir}/_order"

    if [[ -f "${order_file}" ]]; then
      # Read ordered entries
      local ordered=()
      while IFS= read -r line; do
        [[ -z "${line}" || "${line}" == \#* ]] && continue
        ordered+=("${line}")
      done < "${order_file}"

      # Emit ordered entries first (if they exist as directories)
      for name in "${ordered[@]+"${ordered[@]}"}"; do
        if [[ -d "${dir}/${name}" ]]; then
          subdirs+=("${name}")
        fi
      done

      # Append remaining subdirectories alphabetically
      for name in $(printf '%s\n' "${all_subdirs[@]}" | sort); do
        local already=false
        for o in "${ordered[@]+"${ordered[@]}"}"; do
          if [[ "${name}" == "${o}" ]]; then
            already=true
            break
          fi
        done
        if [[ "${already}" == false ]]; then
          subdirs+=("${name}")
        fi
      done
    else
      # No _order file — alphabetical
      while IFS= read -r name; do
        subdirs+=("${name}")
      done < <(printf '%s\n' "${all_subdirs[@]}" | sort)
    fi

    # Recurse into subdirectories in order
    for name in "${subdirs[@]}"; do
      _process_dir "${dir}/${name}"
    done
  }

  _process_dir "${source_dir}"

  mv "${tmp_file}" "${output_file}"
  echo "Combined configuration written to: ${output_file}"
}

if [[ $# -ne 0 ]]; then
  echo "Usage: $0" >&2
  echo "This command always combines both reports and administration configs." >&2
  exit 1
fi

combine_config "${ROOT_DIR}/reports" "${ROOT_DIR}/reports/config.toml"
combine_config "${ROOT_DIR}/administration" "${ROOT_DIR}/administration/config.toml"
