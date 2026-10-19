#!/usr/bin/env bash
# Build a jammy (Ubuntu 22.04) host runtime tarball for GoliathOmics workers.
#
#   scripts/package_host_runtime.sh [--output FILE] [--version VER]
#
# Output: goliath-align-host-linux-amd64-jammy.tar.gz containing goliath-align/
# with bin/methylGrapher, engine/, src/, scripts/, mojo-env/.
# Built inside ubuntu:22.04 so glibc matches Clara/goliath-worker.
# Needs docker or podman.

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
VERSION="" OUTPUT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output) OUTPUT="${2:-}"; shift 2 ;;
    --version) VERSION="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 1 ;;
  esac
done
log() { printf '[package-host-runtime] %s\n' "$*" >&2; }
die() { printf '[package-host-runtime] ERROR: %s\n' "$*" >&2; exit 1; }

if [[ -z "$VERSION" ]]; then
  if git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    VERSION="$(git -C "$REPO_ROOT" describe --tags --always 2>/dev/null || echo 0.0.0)"
    VERSION="${VERSION#v}"
  else
    VERSION="0.0.0"
  fi
fi
OUTPUT="${OUTPUT:-$REPO_ROOT/goliath-align-host-linux-amd64-jammy.tar.gz}"

RT=""
for c in docker podman; do command -v "$c" >/dev/null 2>&1 && { RT=$c; break; }; done
[[ -n "$RT" ]] || die "docker or podman required"

STAGE="$(mktemp -d)"
trap 'sudo rm -rf "$STAGE" 2>/dev/null || rm -rf "$STAGE" 2>/dev/null || true' EXIT
mkdir -p "$STAGE/out"

log "pulling ubuntu:22.04; building host runtime (pixi + Mojo) — this takes a while"
"$RT" pull ubuntu:22.04 >/dev/null

# Inner script written to a file so quoting stays sane.
cat >"$STAGE/inner.sh" <<'INNER'
#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq ca-certificates curl git build-essential >/dev/null
curl -fsSL https://pixi.sh/install.sh | bash
export PATH="$HOME/.pixi/bin:$PATH"
export PIXI_NO_TELEMETRY=1
export DO_NOT_TRACK=1
# /src is mounted read-only; pixi needs a writable project dir for .pixi/
rm -rf /build
mkdir -p /build
cp -a /src/. /build/
cd /build
pixi install
bash scripts/stage_flat_image_tree.sh /out/flat
PIXI_ENV="/build/.pixi/envs/default"
[[ -x "$PIXI_ENV/bin/mojo" ]] || { echo "mojo missing after pixi install" >&2; exit 1; }
DEST=/out/goliath-align
rm -rf "$DEST"
mkdir -p "$DEST"/{bin,mojo-env/bin,mojo-env/lib/mojo,mojo-env/share/max,cuda/bin,scripts}
cp -a /out/flat/engine "$DEST/"
cp -a /out/flat/src "$DEST/"
[[ -d /out/flat/scripts ]] && cp -a /out/flat/scripts/. "$DEST/scripts/" || true
cp -a "$PIXI_ENV/bin/mojo" "$DEST/mojo-env/bin/"
[[ -x "$PIXI_ENV/bin/modular-crashpad-handler" ]] \
  && cp -a "$PIXI_ENV/bin/modular-crashpad-handler" "$DEST/mojo-env/bin/"
if [[ -x "$PIXI_ENV/bin/python3" ]]; then
  cp -a "$PIXI_ENV/bin/python3" "$DEST/mojo-env/bin/" || true
  for py in python3.13 python; do
    [[ -e "$PIXI_ENV/bin/$py" ]] && cp -a "$PIXI_ENV/bin/$py" "$DEST/mojo-env/bin/" || true
  done
fi
cp -a "$PIXI_ENV/lib/mojo/." "$DEST/mojo-env/lib/mojo/"
for lib in \
  libMSupportGlobals.so libAsyncRTRuntimeGlobals.so libAsyncRTMojoBindings.so \
  libNVPTX.so libKGENCompilerRTShared.so libMGPRT.so \
  libstdc++.so.6 libgcc_s.so.1 \
  libpython3.so libpython3.13.so libpython3.13.so.1.0
do
  [[ -e "$PIXI_ENV/lib/$lib" ]] && cp -a "$PIXI_ENV/lib/$lib" "$DEST/mojo-env/lib/" || true
done
if [[ -d "$PIXI_ENV/lib/python3.13" ]]; then
  mkdir -p "$DEST/mojo-env/lib/python3.13"
  cp -a "$PIXI_ENV/lib/python3.13/." "$DEST/mojo-env/lib/python3.13/"
fi
if [[ -f "$PIXI_ENV/share/max/modular.cfg" ]]; then
  sed -e "s|${PIXI_ENV}|__GOLIATH_ALIGN_HOME__/mojo-env|g" \
    "$PIXI_ENV/share/max/modular.cfg" >"$DEST/mojo-env/share/max/modular.cfg"
fi
mkdir -p "$DEST/mojo-env/share/max/crashdb" "$DEST/mojo-env/share/max/.max_cache"
chmod -R a+rwX "$DEST/mojo-env/share/max"
cat >"$DEST/bin/methylGrapher" <<'LAUNCH'
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"
cfg="$ROOT/mojo-env/share/max/modular.cfg"
if [[ -f "$cfg" ]] && grep -q '__GOLIATH_ALIGN_HOME__' "$cfg" 2>/dev/null; then
  sed -i "s|__GOLIATH_ALIGN_HOME__|${ROOT}|g" "$cfg"
fi
_mcall_engine="$(printf '%s' "${METHYLGRAPHER_MCALL_ENGINE:-native}" | tr '[:upper:]' '[:lower:]')"
if [[ "${_mcall_engine}" == "python" ]]; then
  exec python3 -m engine.cli "$@"
fi
MOJO_BIN="${ROOT}/mojo-env/bin/mojo"
if [[ -x "${MOJO_BIN}" ]]; then
  export MODULAR_HOME="${ROOT}/mojo-env/share/max"
  export LD_LIBRARY_PATH="${ROOT}/mojo-env/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  export PATH="${ROOT}/mojo-env/bin:${PATH}"
  if [[ -z "${MODULAR_NVPTX_COMPILER_PATH:-}" ]]; then
    for _ptx in "${ROOT}/cuda/bin/ptxas" /usr/local/cuda/bin/ptxas /usr/bin/ptxas; do
      if [[ -x "${_ptx}" ]]; then export MODULAR_NVPTX_COMPILER_PATH="${_ptx}"; break; fi
    done
  fi
  export MODULAR_CACHE_DIR="${MODULAR_CACHE_DIR:-/tmp/modular_cache}"
  mkdir -p "${MODULAR_CACHE_DIR}" 2>/dev/null || true
  export PYTHONPATH="${ROOT}/scripts:${ROOT}${PYTHONPATH:+:$PYTHONPATH}"
  if [[ -e "${ROOT}/mojo-env/lib/libpython3.13.so.1.0" ]]; then
    export LD_PRELOAD="${ROOT}/mojo-env/lib/libpython3.13.so.1.0${LD_PRELOAD:+:$LD_PRELOAD}"
    export PYTHONHOME="${ROOT}/mojo-env"
  fi
  cd "${ROOT}"
  exec "${MOJO_BIN}" src/main.mojo "$@"
fi
exec python3 -m engine.cli "$@"
LAUNCH
chmod +x "$DEST/bin/methylGrapher"
for _ptx in /usr/bin/ptxas /usr/lib/cuda/bin/ptxas /usr/local/cuda/bin/ptxas; do
  if [[ -x "$_ptx" ]]; then cp -a "$_ptx" "$DEST/cuda/bin/ptxas"; break; fi
done
printf '%s\n' "${GOLIATH_ALIGN_VERSION:-0.0.0}" >"$DEST/VERSION.txt"
printf 'os=ubuntu-22.04\narch=amd64\n' >"$DEST/HOST_RUNTIME.txt"
INNER

"$RT" run --rm \
  -e GOLIATH_ALIGN_VERSION="$VERSION" \
  -v "$REPO_ROOT:/src:ro" \
  -v "$STAGE/out:/out" \
  -v "$STAGE/inner.sh:/inner.sh:ro" \
  ubuntu:22.04 bash /inner.sh

[[ -x "$STAGE/out/goliath-align/bin/methylGrapher" ]] || die "launcher missing"
[[ -x "$STAGE/out/goliath-align/mojo-env/bin/mojo" ]] || die "mojo missing"
tar -C "$STAGE/out" -czf "$OUTPUT" goliath-align
log "wrote $OUTPUT ($(du -h "$OUTPUT" | awk '{print $1}'))"
