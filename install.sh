#!/usr/bin/env bash
set -euo pipefail

PLATFORM=""
SOURCE_ROOT="./kuno-workflow-onboard-skills"
PROJECT_ROOT=""
ACTION=""
SKILLS_SCOPE=""
SKIP_PROJECT_AGENTS=0
NO_MCP=0
DRY_RUN=0
YES=0
NO_COLOR=0
GLOBAL_AGENTS_PATH=""
GLOBAL_SKILLS_DIR=""
PROJECT_SKILLS_DIR=""
TRELLIS_USER=""
TRELLIS_PLATFORMS=()
SKIP_TRELLIS_INIT=0
SKIP_TRELLIS_BOOTSTRAP=0
CHECK_JSON=""

EXTERNAL_SKILLS=(
  diagnosing-bugs
  tdd
  grill-me
  grill-with-docs
  grilling
  domain-modeling
  codebase-design
  handoff
  writing-great-skills
  to-spec
  to-tickets
  impeccable
  ui-ux-pro-max
  web-ui-autotest-generator
  shadcn
)

usage() {
  cat <<'EOF'
Kuno workflow installer

Usage:
  ./install.sh [options]

Options:
  --platform <codex|claude|kimi|oh-my-pi|omp>
      Target coding agent tool. "omp" is an alias for "oh-my-pi".
  --source-root <path>
      Path to the kuno-workflow-onboard-skills directory.
      Defaults to ./kuno-workflow-onboard-skills.
  --project-root <path>
      Target project root for project AGENTS.md, .gitignore, and project skills.
  --action <init|reset>
      Onboard operation to run.
  --skills-scope <global|project|none>
      Install bundled skills globally, into the project, or skip them.
  --skip-project-agents
      Do not install project AGENTS.md.
  --global-agents-path <path>
      Override the global AGENTS.md target.
  --global-skills-dir <path>
      Override global skills directory.
  --project-skills-dir <path>
      Override project-level skills directory.
  --trellis-user <name>
      Developer username for trellis init -u when the project has no .trellis/.
  --trellis-platform <name[,name...]>
      Trellis init platform flag without leading dashes. May be repeated.
      Examples: codex, claude, cursor, opencode, gemini, pi.
  --skip-trellis-init
      Skip post-install trellis init for project roots without .trellis/.
  --skip-trellis-bootstrap
      Skip post-install bootstrap task detection.
  --no-mcp
      Skip MCP configuration.
  --dry-run
      Print commands and MCP writes without making changes.
  --yes
      Skip the final execution confirmation.
  --no-color
      Disable ANSI color.
  -h, --help
      Show this help.
EOF
}

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

warn() {
  printf 'Warning: %s\n' "$*" >&2
}

is_tty() {
  [[ -t 0 && -t 1 ]]
}

supports_color() {
  [[ "$NO_COLOR" -eq 0 && -z "${NO_COLOR:-}" && -t 1 ]]
}

color() {
  local code="$1"
  shift
  if supports_color; then
    printf '\033[%sm%s\033[0m' "$code" "$*"
  else
    printf '%s' "$*"
  fi
}

print_logo() {
  if supports_color; then
    printf '\033[38;5;141m    ██╗  ██╗\033[0m\n'
    printf '\033[38;5;141m    ██║ ██╔╝\033[0m\n'
    printf '\033[38;5;171m    █████╔╝ \033[0m\n'
    printf '\033[38;5;171m    ██╔═██╗ \033[0m\n'
    printf '\033[38;5;213m    ██║  ██╗\033[0m\n'
    printf '\033[38;5;213m    ╚═╝  ╚═╝\033[0m\n'
  else
    printf '    K  K\n'
    printf '    K K\n'
    printf '    KK\n'
    printf '    K K\n'
    printf '    K  K\n'
  fi
  printf '\n'
  color '1;35' 'Kuno Workflow Installer'
  printf '\n\n'
}

normalize_platform() {
  local value
  value="$(printf '%s' "$1" | tr '[:upper:]_' '[:lower:]-')"
  case "$value" in
    codex) printf 'codex' ;;
    claude|claude-code|claudecode) printf 'claude' ;;
    kimi|kimi-code|kimicode) printf 'kimi' ;;
    oh-my-pi|ohmypi|omp) printf 'oh-my-pi' ;;
    *) return 1 ;;
  esac
}

platform_label() {
  case "$1" in
    codex) printf 'Codex' ;;
    claude) printf 'Claude Code' ;;
    kimi) printf 'Kimi Code' ;;
    oh-my-pi) printf 'Oh My Pi' ;;
    *) printf '%s' "$1" ;;
  esac
}

prompt_text() {
  local prompt="$1"
  local default="${2:-}"
  local value
  if [[ -n "$default" ]]; then
    read -r -p "$prompt [$default]: " value
    printf '%s' "${value:-$default}"
  else
    read -r -p "$prompt: " value
    printf '%s' "$value"
  fi
}

prompt_yes_no() {
  local prompt="$1"
  local default="${2:-n}"
  local suffix answer
  if [[ "$default" == "y" ]]; then
    suffix='[Y/n]'
  else
    suffix='[y/N]'
  fi
  while true; do
    read -r -p "$prompt $suffix " answer
    answer="${answer:-$default}"
    answer="$(printf '%s' "$answer" | tr '[:upper:]' '[:lower:]')"
    case "$answer" in
      y|yes) return 0 ;;
      n|no) return 1 ;;
      *) printf 'Please answer y or n.\n' ;;
    esac
  done
}

select_one() {
  local prompt="$1"
  shift
  local options=("$@")
  local choice
  printf '%s\n' "$prompt" >&2
  for index in "${!options[@]}"; do
    printf '  %d) %s\n' "$((index + 1))" "${options[$index]}" >&2
  done
  while true; do
    read -r -p 'Select one: ' choice
    if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#options[@]} )); then
      printf '%s' "${options[$((choice - 1))]}"
      return 0
    fi
    printf 'Invalid choice.\n' >&2
  done
}

split_csv_numbers() {
  local raw="$1"
  local max="$2"
  local item trimmed
  CSV_SELECTIONS=()
  raw="${raw// /}"
  [[ -z "$raw" ]] && return 0
  IFS=',' read -ra parts <<< "$raw"
  for item in "${parts[@]}"; do
    trimmed="$item"
    if [[ ! "$trimmed" =~ ^[0-9]+$ ]] || (( trimmed < 1 || trimmed > max )); then
      return 1
    fi
    CSV_SELECTIONS+=("$trimmed")
  done
}

resolve_existing_dir() {
  local path="$1"
  [[ -d "$path" ]] || return 1
  (cd "$path" && pwd -P)
}

validate_source_root() {
  local source="$1"
  if [[ ! -d "$source" ]]; then
    cat >&2 <<EOF
Kuno Onboard skill was not found.

Expected:
  $source

This installer requires --source-root to point directly to the
kuno-workflow-onboard-skills directory.
EOF
    exit 1
  fi

  local resolved
  resolved="$(resolve_existing_dir "$source")" || die "Unable to resolve source root: $source"
  local missing=()
  local required=(
    "SKILL.md"
    "REFERENCE.md"
    "scripts/onboard.py"
    "templates/agents/AGENTS.global.md"
    "templates/agents/AGENTS.project.md"
    "templates/skills"
  )
  for item in "${required[@]}"; do
    if [[ ! -e "$resolved/$item" ]]; then
      missing+=("$item")
    fi
  done
  if (( ${#missing[@]} > 0 )); then
    cat >&2 <<EOF
Kuno Onboard skill was not found or is incomplete.

Provided:
  $resolved

Missing:
EOF
    for item in "${missing[@]}"; do
      printf '  %s\n' "$item" >&2
    done
    printf '\nPlease pass a valid kuno-workflow-onboard-skills directory.\n' >&2
    exit 1
  fi
  SOURCE_ROOT="$resolved"
}

find_python() {
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
  else
    die "python3 or python is required to run $SOURCE_ROOT/scripts/onboard.py"
  fi
}

command_string() {
  local quoted=()
  local arg
  for arg in "$@"; do
    quoted+=("$(printf '%q' "$arg")")
  done
  printf '%s' "${quoted[*]}"
}

run_cmd() {
  printf '+ %s\n' "$(command_string "$@")"
  if [[ "$DRY_RUN" -eq 0 ]]; then
    "$@"
  fi
}

onboard_common_args() {
  local args=()
  if [[ -n "$PROJECT_ROOT" ]]; then
    args+=(--project-root "$PROJECT_ROOT")
  fi
  if [[ "$SKIP_PROJECT_AGENTS" -eq 1 ]]; then
    args+=(--skip-project-agents)
  fi
  if [[ -n "$SKILLS_SCOPE" ]]; then
    args+=(--skills-scope "$SKILLS_SCOPE")
  fi
  if [[ -n "$GLOBAL_AGENTS_PATH" ]]; then
    args+=(--global-agents-path "$GLOBAL_AGENTS_PATH")
  fi
  if [[ -n "$GLOBAL_SKILLS_DIR" ]]; then
    args+=(--global-skills-dir "$GLOBAL_SKILLS_DIR")
  fi
  if [[ -n "$PROJECT_SKILLS_DIR" ]]; then
    args+=(--project-skills-dir "$PROJECT_SKILLS_DIR")
  fi
  if [[ -n "$TRELLIS_USER" ]]; then
    args+=(--trellis-user "$TRELLIS_USER")
  fi
  local trellis_platform
  for trellis_platform in ${TRELLIS_PLATFORMS[@]+"${TRELLIS_PLATFORMS[@]}"}; do
    args+=(--trellis-platform "$trellis_platform")
  done
  if [[ "$SKIP_TRELLIS_INIT" -eq 1 ]]; then
    args+=(--skip-trellis-init)
  fi
  if [[ "$SKIP_TRELLIS_BOOTSTRAP" -eq 1 ]]; then
    args+=(--skip-trellis-bootstrap)
  fi
  if (( ${#args[@]} > 0 )); then
    printf '%s\0' "${args[@]}"
  fi
}

read_common_args() {
  COMMON_ARGS_OUT=()
  while IFS= read -r -d '' arg; do
    COMMON_ARGS_OUT+=("$arg")
  done < <(onboard_common_args)
}

run_onboard() {
  local mode="$1"
  shift
  if [[ "$mode" == "check" || "$mode" == "plan" ]]; then
    printf '+ %s\n' "$(command_string "$PYTHON_BIN" "$SOURCE_ROOT/scripts/onboard.py" "$mode" "$@")"
    "$PYTHON_BIN" "$SOURCE_ROOT/scripts/onboard.py" "$mode" "$@"
  else
    run_cmd "$PYTHON_BIN" "$SOURCE_ROOT/scripts/onboard.py" "$mode" "$@"
  fi
}

refresh_check_json() {
  local args=()
  read_common_args
  args=(${COMMON_ARGS_OUT[@]+"${COMMON_ARGS_OUT[@]}"})
  CHECK_JSON="$(mktemp "${TMPDIR:-/tmp}/kuno-onboard-check.XXXXXX")"
  "$PYTHON_BIN" "$SOURCE_ROOT/scripts/onboard.py" check ${args[@]+"${args[@]}"} --json > "$CHECK_JSON"
}

print_check() {
  local args=()
  read_common_args
  args=(${COMMON_ARGS_OUT[@]+"${COMMON_ARGS_OUT[@]}"})
  run_onboard check ${args[@]+"${args[@]}"}
}

json_python() {
  "$PYTHON_BIN" - "$CHECK_JSON" "$@" <<'PY'
import json
import sys

path = sys.argv[1]
mode = sys.argv[2]
args = sys.argv[3:]
data = json.load(open(path, encoding="utf-8"))

def find_tool(name):
    for item in data.get("tools", []):
        if item.get("name") == name:
            return item
    return {}

def find_skill(name):
    for item in data.get("skills", []):
        if item.get("name") == name:
            return item
    return {}

def find_manual_check(name):
    for item in data.get("manualChecks", []):
        if item.get("name") == name:
            return item
    return {}

if mode == "runtime-installed":
    print("true" if data.get("runtime", {}).get(args[0], {}).get("installed") else "false")
elif mode == "tool-installed":
    print("true" if find_tool(args[0]).get("installed") else "false")
elif mode == "tool-flag":
    print("true" if find_tool(args[0]).get(args[1]) else "false")
elif mode == "skill-installed":
    print("true" if find_skill(args[0]).get("installed") else "false")
elif mode == "missing-external-skills":
    external = set(args)
    missing = [
        item.get("name")
        for item in data.get("skills", [])
        if item.get("name") in external and not item.get("installed")
    ]
    print(",".join(missing))
elif mode == "mcp-command":
    config = find_manual_check(args[0]).get("mcpServerConfig") or {}
    print(config.get("command") or "")
elif mode == "mcp-args-json":
    config = find_manual_check(args[0]).get("mcpServerConfig") or {}
    print(json.dumps(config.get("args") or [], ensure_ascii=False))
elif mode == "mcp-env-json":
    config = find_manual_check(args[0]).get("mcpServerConfig") or {}
    print(json.dumps(config.get("env") or {}, ensure_ascii=False))
elif mode == "maestro-env-json":
    config = find_manual_check("Maestro MCP").get("mcpServerConfig") or {}
    print(json.dumps(config.get("env") or {}, ensure_ascii=False))
elif mode == "tool-field":
    value = find_tool(args[0]).get(args[1])
    if value is None:
        value = ""
    print(value)
else:
    raise SystemExit(f"unknown json query: {mode}")
PY
}

normalize_project_root() {
  local path="$1"
  [[ -z "$path" ]] && return 0
  [[ -d "$path" ]] || die "Project root does not exist: $path"
  PROJECT_ROOT="$(resolve_existing_dir "$path")"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --platform)
        [[ $# -ge 2 ]] || die "--platform requires a value"
        PLATFORM="$2"
        shift 2
        ;;
      --platform=*)
        PLATFORM="${1#*=}"
        shift
        ;;
      --source-root)
        [[ $# -ge 2 ]] || die "--source-root requires a value"
        SOURCE_ROOT="$2"
        shift 2
        ;;
      --source-root=*)
        SOURCE_ROOT="${1#*=}"
        shift
        ;;
      --project-root)
        [[ $# -ge 2 ]] || die "--project-root requires a value"
        PROJECT_ROOT="$2"
        shift 2
        ;;
      --project-root=*)
        PROJECT_ROOT="${1#*=}"
        shift
        ;;
      --action)
        [[ $# -ge 2 ]] || die "--action requires a value"
        ACTION="$2"
        shift 2
        ;;
      --action=*)
        ACTION="${1#*=}"
        shift
        ;;
      --skills-scope)
        [[ $# -ge 2 ]] || die "--skills-scope requires a value"
        SKILLS_SCOPE="$2"
        shift 2
        ;;
      --skills-scope=*)
        SKILLS_SCOPE="${1#*=}"
        shift
        ;;
      --skip-project-agents)
        SKIP_PROJECT_AGENTS=1
        shift
        ;;
      --global-agents-path)
        [[ $# -ge 2 ]] || die "--global-agents-path requires a value"
        GLOBAL_AGENTS_PATH="$2"
        shift 2
        ;;
      --global-agents-path=*)
        GLOBAL_AGENTS_PATH="${1#*=}"
        shift
        ;;
      --global-skills-dir)
        [[ $# -ge 2 ]] || die "--global-skills-dir requires a value"
        GLOBAL_SKILLS_DIR="$2"
        shift 2
        ;;
      --global-skills-dir=*)
        GLOBAL_SKILLS_DIR="${1#*=}"
        shift
        ;;
      --project-skills-dir)
        [[ $# -ge 2 ]] || die "--project-skills-dir requires a value"
        PROJECT_SKILLS_DIR="$2"
        shift 2
        ;;
      --project-skills-dir=*)
        PROJECT_SKILLS_DIR="${1#*=}"
        shift
        ;;
      --trellis-user)
        [[ $# -ge 2 ]] || die "--trellis-user requires a value"
        TRELLIS_USER="$2"
        shift 2
        ;;
      --trellis-user=*)
        TRELLIS_USER="${1#*=}"
        shift
        ;;
      --trellis-platform)
        [[ $# -ge 2 ]] || die "--trellis-platform requires a value"
        TRELLIS_PLATFORMS+=("$2")
        shift 2
        ;;
      --trellis-platform=*)
        TRELLIS_PLATFORMS+=("${1#*=}")
        shift
        ;;
      --skip-trellis-init)
        SKIP_TRELLIS_INIT=1
        shift
        ;;
      --skip-trellis-bootstrap)
        SKIP_TRELLIS_BOOTSTRAP=1
        shift
        ;;
      --no-mcp)
        NO_MCP=1
        shift
        ;;
      --dry-run)
        DRY_RUN=1
        shift
        ;;
      --yes)
        YES=1
        shift
        ;;
      --no-color)
        NO_COLOR=1
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        die "Unknown option: $1"
        ;;
    esac
  done
}

resolve_interactive_inputs() {
  if [[ -n "$PLATFORM" ]]; then
    PLATFORM="$(normalize_platform "$PLATFORM")" || die "Unsupported platform: $PLATFORM"
  else
    local selected
    selected="$(select_one 'Target coding agent tool:' 'Codex' 'Claude Code' 'Kimi Code' 'Oh My Pi')"
    case "$selected" in
      Codex) PLATFORM="codex" ;;
      'Claude Code') PLATFORM="claude" ;;
      'Kimi Code') PLATFORM="kimi" ;;
      'Oh My Pi') PLATFORM="oh-my-pi" ;;
    esac
  fi

  if [[ -n "$ACTION" ]]; then
    case "$ACTION" in
      init|reset) ;;
      *) die "--action must be init or reset" ;;
    esac
  else
    ACTION="$(select_one 'Onboard action:' 'init' 'reset')"
  fi

  if [[ -n "$PROJECT_ROOT" ]]; then
    normalize_project_root "$PROJECT_ROOT"
  else
    local cwd provided
    cwd="$(pwd -P)"
    if prompt_yes_no "Is $cwd the target project root?" "y"; then
      PROJECT_ROOT="$cwd"
    else
      provided="$(prompt_text 'Enter target project root, or leave blank to skip project AGENTS' '')"
      if [[ -n "$provided" ]]; then
        normalize_project_root "$provided"
      else
        SKIP_PROJECT_AGENTS=1
      fi
    fi
  fi

  if [[ -n "$PROJECT_ROOT" && "$SKIP_PROJECT_AGENTS" -eq 0 ]]; then
    if ! prompt_yes_no "Install project AGENTS.md into $PROJECT_ROOT?" "y"; then
      SKIP_PROJECT_AGENTS=1
    fi
  fi
  if [[ -z "$PROJECT_ROOT" ]]; then
    SKIP_PROJECT_AGENTS=1
  fi

  if [[ -n "$SKILLS_SCOPE" ]]; then
    case "$SKILLS_SCOPE" in
      global|project|none) ;;
      *) die "--skills-scope must be global, project, or none" ;;
    esac
  else
    SKILLS_SCOPE="$(select_one 'Bundled skills install scope:' 'global' 'project' 'none')"
  fi

  if [[ "$SKILLS_SCOPE" == "project" && -z "$PROJECT_ROOT" && -z "$PROJECT_SKILLS_DIR" ]]; then
    local path
    path="$(prompt_text 'Project root is required for project skills. Enter project root' '')"
    [[ -n "$path" ]] || die "Project skills require --project-root or --project-skills-dir"
    normalize_project_root "$path"
  fi
}

split_trellis_platforms() {
  local raw="$1"
  local item trimmed
  local -a parts=()
  raw="${raw// /}"
  [[ -z "$raw" ]] && return 0
  IFS=',' read -ra parts <<< "$raw"
  for item in "${parts[@]}"; do
    trimmed="${item#--}"
    [[ -n "$trimmed" ]] && TRELLIS_PLATFORMS+=("$trimmed")
  done
}

resolve_trellis_project_setup_inputs() {
  [[ "$SKIP_TRELLIS_INIT" -eq 1 ]] && return 0
  [[ -n "$PROJECT_ROOT" ]] || return 0
  [[ ! -e "$PROJECT_ROOT/.trellis" ]] || return 0

  refresh_check_json
  if [[ "$(json_python tool-installed trellis)" != "true" ]]; then
    warn "Trellis CLI is required before project trellis init; onboard.py will report the setup as blocked."
    return 0
  fi

  while [[ -z "$TRELLIS_USER" ]]; do
    TRELLIS_USER="$(prompt_text 'Trellis developer username for trellis init -u' '')"
    if [[ -z "$TRELLIS_USER" ]]; then
      if prompt_yes_no "Skip trellis init for this project?" "n"; then
        SKIP_TRELLIS_INIT=1
        return 0
      fi
    fi
  done

  if (( ${#TRELLIS_PLATFORMS[@]} == 0 )); then
    local raw_platforms
    raw_platforms="$(prompt_text 'Trellis platform flags, comma-separated without --, or blank for none' '')"
    split_trellis_platforms "$raw_platforms"
  fi
}

install_missing_runtime_and_skills() {
  printf '\n'
  color '1;36' 'Preflight check'
  printf '\n'
  print_check
  refresh_check_json

  if [[ "$(json_python runtime-installed npm)" != "true" ]]; then
    if prompt_yes_no "npm is missing. Install nvm + Node.js LTS now?" "n"; then
      run_onboard ensure-npm --yes
      refresh_check_json
    else
      warn "npm install skipped. npm-backed CLI checks may remain not-checked."
    fi
  fi

  if [[ "$(json_python tool-installed rtk)" != "true" ]]; then
    local wrong verification
    wrong="$(json_python tool-flag rtk wrongPackageSuspected)"
    verification="$(json_python tool-flag rtk verificationFailed)"
    if [[ "$wrong" == "true" ]]; then
      if prompt_yes_no "rtk exists but may be the wrong package. Replace with rtk-ai/rtk?" "n"; then
        run_onboard install-rtk --replace-wrong --yes
      fi
    elif [[ "$verification" == "true" ]]; then
      if prompt_yes_no "rtk verification failed. Reinstall rtk-ai/rtk?" "n"; then
        run_onboard install-rtk --reinstall --yes
      fi
    elif prompt_yes_no "rtk is missing. Install rtk-ai/rtk?" "n"; then
      run_onboard install-rtk --yes
    fi
    refresh_check_json
  fi

  if [[ "$(json_python tool-installed trellis)" != "true" ]] && [[ "$(json_python runtime-installed npm)" == "true" ]]; then
    if prompt_yes_no "Trellis CLI is missing. Install @mindfoldhq/trellis globally?" "n"; then
      run_cmd npm install -g @mindfoldhq/trellis@latest
      refresh_check_json
    fi
  fi

  if [[ "$(json_python tool-installed gitnexus)" != "true" ]] && [[ "$(json_python runtime-installed npm)" == "true" ]]; then
    if prompt_yes_no "GitNexus CLI is missing. Install gitnexus globally?" "n"; then
      run_cmd npm install -g gitnexus
      refresh_check_json
    fi
  fi

  if [[ "$(json_python skill-installed caveman)" != "true" ]]; then
    if prompt_yes_no "caveman skill is missing. Install it as a user-level global skill?" "n"; then
      run_onboard install-caveman --yes
      refresh_check_json
    fi
  fi

  local missing_external
  missing_external="$(json_python missing-external-skills "${EXTERNAL_SKILLS[@]}")"
  if [[ -n "$missing_external" ]]; then
    printf '\nMissing external skills: %s\n' "$missing_external"
    if [[ "$SKILLS_SCOPE" == "none" ]]; then
      warn "Bundled skills scope is none, so external skill installation is skipped."
      return
    fi
    local selected mode
    mode="$(select_one 'External skills install decision:' 'install recommended missing skills' 'custom select skills' 'skip external skills')"
    case "$mode" in
      'install recommended missing skills')
        selected="$missing_external"
        ;;
      'custom select skills')
        printf 'Known missing external skills: %s\n' "$missing_external"
        selected="$(prompt_text 'Enter comma-separated skill names to install' '')"
        ;;
      *)
        selected=""
        ;;
    esac
    if [[ -n "$selected" ]]; then
      local args=(--skills "$selected" --scope "$SKILLS_SCOPE" --yes)
      if [[ "$SKILLS_SCOPE" == "project" ]]; then
        if [[ -n "$PROJECT_ROOT" ]]; then
          args+=(--project-root "$PROJECT_ROOT")
        fi
        if [[ -n "$PROJECT_SKILLS_DIR" ]]; then
          args+=(--project-skills-dir "$PROJECT_SKILLS_DIR")
        fi
      else
        if [[ -n "$GLOBAL_SKILLS_DIR" ]]; then
          args+=(--global-skills-dir "$GLOBAL_SKILLS_DIR")
        fi
      fi
      run_onboard install-external-skills ${args[@]+"${args[@]}"}
      refresh_check_json
    fi
  fi
}

prompt_env_pairs() {
  ENV_PAIRS_OUT=()
  local key value secret
  while true; do
    key="$(prompt_text 'Env key for this MCP server, or blank to finish' '')"
    [[ -z "$key" ]] && break
    if [[ "$key" =~ (TOKEN|PASSWORD|SECRET|KEY) ]]; then
      read -r -s -p "Value for $key: " value
      printf '\n'
    else
      value="$(prompt_text "Value for $key" '')"
    fi
    ENV_PAIRS_OUT+=("$key=$value")
  done
}

ensure_maestro_ready() {
  refresh_check_json
  if [[ "$(json_python tool-installed java)" != "true" ]]; then
    if prompt_yes_no "Maestro MCP requires Java 17+. Install Temurin 21 JDK now?" "n"; then
      run_onboard install-java --major 21 --yes
      refresh_check_json
    else
      warn "Java 17+ is unavailable; skipping Maestro MCP."
      return 1
    fi
  fi

  if [[ "$(json_python tool-installed maestro)" != "true" ]]; then
    local failed
    failed="$(json_python tool-flag maestro verificationFailed)"
    if [[ "$failed" == "true" ]]; then
      if prompt_yes_no "A maestro command exists but failed verification. Reinstall Maestro CLI?" "n"; then
        run_onboard install-maestro --reinstall --yes
      else
        warn "Maestro CLI verification failed; skipping Maestro MCP."
        return 1
      fi
    elif prompt_yes_no "Maestro CLI is missing. Install Maestro CLI now?" "n"; then
      run_onboard install-maestro --yes
    else
      warn "Maestro CLI is unavailable; skipping Maestro MCP."
      return 1
    fi
    refresh_check_json
  fi

  if [[ "$(json_python tool-installed java)" != "true" || "$(json_python tool-installed maestro)" != "true" ]]; then
    warn "Java 17+ and Maestro CLI are required; skipping Maestro MCP."
    return 1
  fi
  return 0
}

env_array_to_json() {
  "$PYTHON_BIN" - "$@" <<'PY'
import json
import sys

env = {}
for item in sys.argv[1:]:
    if "=" not in item:
        continue
    key, value = item.split("=", 1)
    env[key] = value
print(json.dumps(env, ensure_ascii=False))
PY
}

args_array_to_json() {
  "$PYTHON_BIN" - "$@" <<'PY'
import json
import sys
print(json.dumps(sys.argv[1:], ensure_ascii=False))
PY
}

json_env_to_array() {
  local json="$1"
  ENV_ARRAY_OUT=()
  while IFS= read -r line; do
    [[ -n "$line" ]] && ENV_ARRAY_OUT+=("$line")
  done < <("$PYTHON_BIN" - "$json" <<'PY'
import json
import sys
env = json.loads(sys.argv[1])
for key, value in env.items():
    print(f"{key}={value}")
PY
)
}

configure_stdio_mcp() {
  local name="$1"
  local command="$2"
  local args_json="$3"
  local env_json="$4"
  local args=()
  local env_pairs=()
  while IFS= read -r line; do
    [[ -n "$line" ]] && args+=("$line")
  done < <("$PYTHON_BIN" - "$args_json" <<'PY'
import json
import sys
for item in json.loads(sys.argv[1]):
    print(item)
PY
)
  json_env_to_array "$env_json"
  env_pairs=(${ENV_ARRAY_OUT[@]+"${ENV_ARRAY_OUT[@]}"})

  case "$PLATFORM" in
    codex)
      command -v codex >/dev/null 2>&1 || { warn "codex CLI not found; skipped MCP server $name."; return 1; }
      local cmd=(codex mcp add "$name")
      local pair
      for pair in ${env_pairs[@]+"${env_pairs[@]}"}; do
        cmd+=(--env "$pair")
      done
      cmd+=(-- "$command")
      cmd+=(${args[@]+"${args[@]}"})
      run_cmd "${cmd[@]}"
      ;;
    claude)
      command -v claude >/dev/null 2>&1 || { warn "claude CLI not found; skipped MCP server $name."; return 1; }
      local scope="user"
      [[ "$SKILLS_SCOPE" == "project" ]] && scope="project"
      local cmd=(claude mcp add --transport stdio --scope "$scope")
      local pair
      for pair in ${env_pairs[@]+"${env_pairs[@]}"}; do
        cmd+=(--env "$pair")
      done
      cmd+=("$name" -- "$command")
      cmd+=(${args[@]+"${args[@]}"})
      run_cmd "${cmd[@]}"
      ;;
    kimi)
      command -v kimi >/dev/null 2>&1 || { warn "kimi CLI not found; skipped MCP server $name."; return 1; }
      local cmd=(kimi mcp add --transport stdio)
      local pair
      for pair in ${env_pairs[@]+"${env_pairs[@]}"}; do
        cmd+=(--env "$pair")
      done
      cmd+=("$name" -- "$command")
      cmd+=(${args[@]+"${args[@]}"})
      run_cmd "${cmd[@]}"
      ;;
    oh-my-pi)
      configure_omp_stdio "$name" "$command" "$args_json" "$env_json"
      ;;
  esac
}

configure_omp_stdio() {
  local name="$1"
  local command="$2"
  local args_json="$3"
  local env_json="$4"
  local target
  if [[ "$SKILLS_SCOPE" == "project" ]]; then
    [[ -n "$PROJECT_ROOT" ]] || { warn "Project root is required for project-level Oh My Pi MCP config."; return 1; }
    target="$PROJECT_ROOT/.omp/mcp.json"
  else
    target="$HOME/.omp/agent/mcp.json"
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '+ write Oh My Pi MCP server %s to %s\n' "$name" "$target"
    return 0
  fi

  "$PYTHON_BIN" - "$target" "$name" "$command" "$args_json" "$env_json" <<'PY'
import json
import pathlib
import sys

target = pathlib.Path(sys.argv[1]).expanduser()
name = sys.argv[2]
command = sys.argv[3]
args = json.loads(sys.argv[4])
env = json.loads(sys.argv[5])

if target.exists():
    data = json.loads(target.read_text(encoding="utf-8"))
else:
    data = {}
servers = data.setdefault("mcpServers", {})
servers[name] = {
    "type": "stdio",
    "command": command,
    "args": args,
    "env": env,
}
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"wrote {name} MCP server to {target}")
PY
}

select_and_configure_mcp() {
  if [[ "$NO_MCP" -eq 1 ]]; then
    printf '\nMCP configuration skipped by --no-mcp.\n'
    return 0
  fi
  if ! prompt_yes_no "Configure MCP servers for $(platform_label "$PLATFORM") now?" "y"; then
    printf 'MCP configuration skipped by user.\n'
    return 0
  fi

  printf '\nAvailable MCP options:\n'
  printf '  1) Chrome DevTools MCP\n'
  printf '  2) Playwright MCP\n'
  printf '  3) Maestro MCP\n'
  printf '  4) GitNexus MCP (auto from gitnexus CLI)\n'
  printf '  5) Custom stdio MCP server\n'
  local raw selections=()
  read -r -p 'Select comma-separated options, or blank for none: ' raw
  split_csv_numbers "$raw" 5 || die "Invalid MCP selection: $raw"
  selections=(${CSV_SELECTIONS[@]+"${CSV_SELECTIONS[@]}"})
  (( ${#selections[@]} == 0 )) && return 0

  local selected
  for selected in ${selections[@]+"${selections[@]}"}; do
    case "$selected" in
      1)
        configure_stdio_mcp "chrome-devtools" "npx" "$(args_array_to_json -y chrome-devtools-mcp@latest)" "{}" || true
        ;;
      2)
        configure_stdio_mcp "playwright" "npx" "$(args_array_to_json -y @playwright/mcp@latest)" "{}" || true
        ;;
      3)
        if ensure_maestro_ready; then
          local env_json
          env_json="$(json_python maestro-env-json)"
          configure_stdio_mcp "maestro" "maestro" "$(args_array_to_json mcp)" "$env_json" || true
        fi
        ;;
      4)
        local command args_json env_json args_line env_pairs=()
        command="$(json_python mcp-command 'GitNexus MCP')"
        if [[ -n "$command" ]]; then
          args_json="$(json_python mcp-args-json 'GitNexus MCP')"
          env_json="$(json_python mcp-env-json 'GitNexus MCP')"
          configure_stdio_mcp "gitnexus" "$command" "$args_json" "$env_json" || true
        else
          warn "GitNexus CLI path was not detected; falling back to manual MCP command input."
          command="$(prompt_text 'GitNexus MCP command, or blank to skip' '')"
          [[ -n "$command" ]] || { warn "Skipped GitNexus MCP: command is required."; continue; }
          args_line="$(prompt_text 'GitNexus MCP args as a simple space-separated list' '')"
          prompt_env_pairs
          env_pairs=(${ENV_PAIRS_OUT[@]+"${ENV_PAIRS_OUT[@]}"})
          # shellcheck disable=SC2206
          local command_args=( $args_line )
          configure_stdio_mcp "gitnexus" "$command" "$(args_array_to_json ${command_args[@]+"${command_args[@]}"})" "$(env_array_to_json ${env_pairs[@]+"${env_pairs[@]}"})" || true
        fi
        ;;
      5)
        local name command args_line env_pairs=()
        name="$(prompt_text 'MCP server name' '')"
        command="$(prompt_text 'MCP command' '')"
        [[ -n "$name" && -n "$command" ]] || { warn "Skipped custom MCP: name and command are required."; continue; }
        args_line="$(prompt_text 'MCP args as a simple space-separated list' '')"
        prompt_env_pairs
        env_pairs=(${ENV_PAIRS_OUT[@]+"${ENV_PAIRS_OUT[@]}"})
        # shellcheck disable=SC2206
        local command_args=( $args_line )
        configure_stdio_mcp "$name" "$command" "$(args_array_to_json ${command_args[@]+"${command_args[@]}"})" "$(env_array_to_json ${env_pairs[@]+"${env_pairs[@]}"})" || true
        ;;
    esac
  done
}

show_plan_and_execute() {
  local common=()
  read_common_args
  common=(${COMMON_ARGS_OUT[@]+"${COMMON_ARGS_OUT[@]}"})

  printf '\n'
  color '1;36' 'Final plan'
  printf '\n'
  run_onboard plan ${common[@]+"${common[@]}"}

  printf '\nTarget platform: %s\n' "$(platform_label "$PLATFORM")"
  printf 'Source root: %s\n' "$SOURCE_ROOT"
  printf 'Action: %s\n' "$ACTION"
  printf 'Project root: %s\n' "${PROJECT_ROOT:-<none>}"
  printf 'Project AGENTS: %s\n' "$([[ "$SKIP_PROJECT_AGENTS" -eq 1 ]] && printf 'skip' || printf 'install')"
  printf 'Skills scope: %s\n' "$SKILLS_SCOPE"
  printf 'MCP: %s\n' "$([[ "$NO_MCP" -eq 1 ]] && printf 'skip' || printf 'configure interactively')"

  if [[ "$YES" -eq 0 ]]; then
    prompt_yes_no "Proceed with onboard $ACTION?" "n" || die "Installation cancelled."
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '\nDry run: skipped onboard %s writes.\n' "$ACTION"
  else
    run_onboard "$ACTION" ${common[@]+"${common[@]}"} --yes
  fi
}

final_checks() {
  local common=()
  read_common_args
  common=(${COMMON_ARGS_OUT[@]+"${COMMON_ARGS_OUT[@]}"})
  printf '\n'
  color '1;36' 'Final check'
  printf '\n'
  run_onboard check ${common[@]+"${common[@]}"}

  case "$PLATFORM" in
    codex)
      command -v codex >/dev/null 2>&1 && run_cmd codex mcp list || warn "codex CLI not found; MCP list skipped."
      ;;
    claude)
      command -v claude >/dev/null 2>&1 && run_cmd claude mcp list || warn "claude CLI not found; MCP list skipped."
      ;;
    kimi)
      command -v kimi >/dev/null 2>&1 && run_cmd kimi mcp list || warn "kimi CLI not found; MCP list skipped."
      ;;
    oh-my-pi)
      if [[ "$SKILLS_SCOPE" == "project" && -n "$PROJECT_ROOT" ]]; then
        printf 'Oh My Pi MCP config: %s\n' "$PROJECT_ROOT/.omp/mcp.json"
      else
        printf 'Oh My Pi MCP config: %s\n' "$HOME/.omp/agent/mcp.json"
      fi
      ;;
  esac
}

cleanup() {
  if [[ -n "${CHECK_JSON:-}" && -f "$CHECK_JSON" ]]; then
    rm -f "$CHECK_JSON"
  fi
}

main() {
  trap cleanup EXIT
  parse_args "$@"
  validate_source_root "$SOURCE_ROOT"
  find_python
  print_logo
  resolve_interactive_inputs
  install_missing_runtime_and_skills
  select_and_configure_mcp
  resolve_trellis_project_setup_inputs
  show_plan_and_execute
  final_checks
}

main "$@"
