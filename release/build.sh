#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

usage() {
  echo "Usage: release/build.sh <component|all> [--dev] [--push] [--version <x.x.x>] [docker-build-args...]"
  echo "Components: cli, ui, sync"
  exit 1
}

[[ $# -lt 1 ]] && usage

component="$1"
shift

dev_suffix=""
push_images=false
version_tag=""
build_args=()
while [[ $# -gt 0 ]]; do
  arg="$1"
  if [[ "$arg" == "--dev" ]]; then
    dev_suffix="-dev"
  elif [[ "$arg" == "--push" ]]; then
    push_images=true
  elif [[ "$arg" == "--version" ]]; then
    shift
    [[ $# -lt 1 ]] && usage
    version_tag="$1"
  else
    build_args+=("$arg")
  fi
  shift
done

image_cli="privxsshcom/privx-reporter-cli${dev_suffix}:latest"
image_ui="privxsshcom/privx-reporter-ui${dev_suffix}:latest"
image_sync="privxsshcom/privx-reporter-sync${dev_suffix}:latest"

buildx_output_flag="--load"
if [[ "$push_images" == true ]]; then
  buildx_output_flag="--push"
fi

cmd_cli=(docker buildx build --sbom=true "${buildx_output_flag}" -f release/reporter_cli/Dockerfile-cli -t "${image_cli}")
cmd_ui=(docker buildx build --sbom=true "${buildx_output_flag}" -f release/reporter_ui/Dockerfile-ui -t "${image_ui}")
cmd_sync=(docker buildx build --sbom=true "${buildx_output_flag}" -f release/reporter_sync/Dockerfile-sync -t "${image_sync}")

if [[ -n "$version_tag" ]]; then
  cmd_cli+=(-t "privxsshcom/privx-reporter-cli${dev_suffix}:${version_tag}")
  cmd_ui+=(-t "privxsshcom/privx-reporter-ui${dev_suffix}:${version_tag}")
  cmd_sync+=(-t "privxsshcom/privx-reporter-sync${dev_suffix}:${version_tag}")
fi

pids=()

case "$component" in
  cli)
    "${cmd_cli[@]}" "${build_args[@]}" .
    ;;
  ui)
    "${cmd_ui[@]}" "${build_args[@]}" .
    ;;
  sync)
    "${cmd_sync[@]}" "${build_args[@]}" .
    ;;
  all)
    "${cmd_cli[@]}" "${build_args[@]}" . & pids=($!)
    "${cmd_ui[@]}" "${build_args[@]}" . & pids+=($!)
    "${cmd_sync[@]}" "${build_args[@]}" . & pids+=($!)
    ;;
  *)
    echo "Unknown component: $component" >&2
    usage
    ;;
esac

if [[ ${#pids[@]} -gt 0 ]]; then
  wait "${pids[@]}" # wait for all processes to finish
fi

echo "Build complete"
echo