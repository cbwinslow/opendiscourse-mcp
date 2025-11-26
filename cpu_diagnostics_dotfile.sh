#!/usr/bin/env bash
# =============================================================================
# Script Name   : cpu-diagnostics-dotfile.sh
# Author        : cbwinslow (generated with GPT-5.1 Thinking)
# Created       : 2025-11-20
# Description   : Collection of shell functions for quick CPU / system
#                 diagnostics, intended to be sourced from a dotfile
#                 (e.g., ~/.zshrc, ~/.bashrc, or ~/dev/dotfiles).
#
# Inputs        : Functions accept optional flags/args where noted.
# Outputs       : Human-readable diagnostic views in the terminal.
# Exit Codes    : Each helper returns non-zero on error but will never
#                 terminate your interactive shell.
#
# Usage         :
#   source /path/to/cpu-diagnostics-dotfile.sh
#   cpu_help        # show available diagnostic helpers
#   cpu_threads     # open htop (threads view)
#   cpu_ps_top      # show top processes via ps
#   cpu_irqs_watch  # watch interrupts in real time
#   ...
#
# Security Notes :
#   - No privileged modifications are made.
#   - Some functions may optionally use sudo (journald, iotop).
#
# Modification Log
#   2025-11-20  v1.0  Initial version of CPU diagnostic helper functions.
# =============================================================================

# -----------------------------------------------------------------------------
# internal: _cpu_cmd_required
#   Tiny helper to check for required commands and print a nice error if they
#   are missing. Does NOT exit the shell – only returns non-zero.
# -----------------------------------------------------------------------------
_cpu_cmd_required() {
    local cmd="$1" ; shift || true
    if ! command -v "${cmd}" >/dev/null 2>&1 ; then
        printf '\n[CPU-TOOLS] Missing dependency: "%s".\n' "${cmd}" 1>&2
        [ "$#" -gt 0 ] && printf '[CPU-TOOLS] Hint: %s\n' "$*" 1>&2
        return 127
    fi
}

# -----------------------------------------------------------------------------
# internal: _cpu_section
#   Pretty-print section headers so output is visually grouped.
# -----------------------------------------------------------------------------
_cpu_section() {
    local title="$*"
    printf '\n═══════════════════════════════════════════════════════════════\n'
    printf '  %s\n' "${title}"
    printf '═══════════════════════════════════════════════════════════════\n'
}

# -----------------------------------------------------------------------------
# cpu_help
#   Show a quick reference of all available helper functions.
# -----------------------------------------------------------------------------
cpu_help() {
    _cpu_section "CPU / System Diagnostic Helpers"
    cat <<'EOF'
  cpu_help           : Show this help menu.

  cpu_threads        : Open htop with threads visible (per-thread CPU view).
  cpu_ps_top         : Show top CPU-consuming processes via ps.
  cpu_irqs_watch     : Watch /proc/interrupts to see IRQ storm patterns.
  cpu_iotop_log      : Summarize top I/O consumers via iotop (batch mode).
  cpu_journal_tail   : Tail journald logs (live) for noisy services.
  cpu_timers         : List systemd timers that may wake up periodically.
  cpu_cron_list      : Show cron jobs for current user & system.
  cpu_docker_top     : Show live CPU usage for Docker containers.
  cpu_miner_scan     : Quick scan for common cryptominer processes.

  Tip: use these together, e.g.
    cpu_threads  # find hot PID / thread
    cpu_ps_top   # confirm process details
    cpu_irqs_watch  # see if it's hardware/interrupt related
EOF
}

# -----------------------------------------------------------------------------
# cpu_threads
#   Launch htop with threads enabled. If htop is missing, fall back to top.
# -----------------------------------------------------------------------------
cpu_threads() {
    if command -v htop >/dev/null 2>&1 ; then
        _cpu_section "Launching htop (enable threads with F2 → Display → Show threads)"
        htop
    else
        _cpu_section "htop not found – falling back to top (press 'H' to show threads)"
        _cpu_cmd_required top "Install 'htop' for a nicer per-thread view." || return $?
        top
    fi
}

# -----------------------------------------------------------------------------
# cpu_ps_top
#   Show top CPU-consuming processes using ps.
# -----------------------------------------------------------------------------
cpu_ps_top() {
    _cpu_cmd_required ps || return $?
    _cpu_section "Top CPU Processes (ps)"
    ps -eo pid,ppid,cmd,%cpu,%mem --sort=-%cpu | head
}

# -----------------------------------------------------------------------------
# cpu_irqs_watch
#   Watch /proc/interrupts to detect interrupt storms (e.g., bad drivers/NIC).
#   Optional arg: interval seconds (default 0.5).
# -----------------------------------------------------------------------------
cpu_irqs_watch() {
    local interval="${1:-0.5}"

    _cpu_cmd_required watch "Usually provided by 'procps' or similar." || return $?

    if [ ! -r /proc/interrupts ]; then
        printf '[CPU-TOOLS] Cannot read /proc/interrupts (insufficient permissions?).\n' 1>&2
        return 1
    fi

    _cpu_section "Watching /proc/interrupts every ${interval}s (Ctrl+C to exit)"
    watch -n "${interval}" cat /proc/interrupts
}

# -----------------------------------------------------------------------------
# cpu_iotop_log
#   Run iotop in accumulated batch mode to see which processes are doing the
#   most disk I/O over time.
# -----------------------------------------------------------------------------
cpu_iotop_log() {
    _cpu_cmd_required iotop "Try: sudo apt install iotop  or  sudo dnf install iotop" || return $?

    _cpu_section "iotop (accumulated I/O usage) – may require sudo"
    if [ "${EUID:-$(id -u)}" -ne 0 ]; then
        printf '[CPU-TOOLS] iotop often requires root – trying with sudo.\n' 1>&2
        sudo iotop -ao
    else
        iotop -ao
    fi
}

# -----------------------------------------------------------------------------
# cpu_journal_tail
#   Tail the systemd journal so you can see if a noisy service is spamming
#   logs and causing CPU spikes.
# -----------------------------------------------------------------------------
cpu_journal_tail() {
    _cpu_cmd_required journalctl "This helper only works on systemd-based systems." || return $?

    _cpu_section "Tailing systemd journal (last 50 lines, follow mode)"
    if [ "${EUID:-$(id -u)}" -ne 0 ]; then
        printf '[CPU-TOOLS] journalctl may need elevated permissions – trying sudo.\n' 1>&2
        sudo journalctl -fn 50
    else
        journalctl -fn 50
    fi
}

# -----------------------------------------------------------------------------
# cpu_timers
#   Show systemd timers and their next run time – great for finding services
#   that wake up every minute or so.
# -----------------------------------------------------------------------------
cpu_timers() {
    _cpu_cmd_required systemctl "Systemd not found – this helper requires systemd." || return $?

    _cpu_section "Active systemd timers (services scheduled to run periodically)"
    systemctl list-timers --all
}

# -----------------------------------------------------------------------------
# cpu_cron_list
#   Display cron jobs for the current user and system-wide cron directories.
# -----------------------------------------------------------------------------
cpu_cron_list() {
    _cpu_section "User crontab for: $(id -un)"
    if command -v crontab >/dev/null 2>&1 ; then
        crontab -l 2>/dev/null || printf '  (no user crontab set)\n'
    else
        printf '  crontab command not found.\n'
    fi

    _cpu_section "System-wide cron dirs (if present)"
    for d in /etc/cron.d /etc/cron.daily /etc/cron.hourly /etc/cron.weekly /etc/cron.monthly ; do
        [ -d "$d" ] || continue
        printf '\n[%s]\n' "$d"
        ls -1 "$d" 2>/dev/null || printf '  (no entries)\n'
    done
}

# -----------------------------------------------------------------------------
# cpu_docker_top
#   Show live CPU usage for running Docker containers using docker stats.
# -----------------------------------------------------------------------------
cpu_docker_top() {
    _cpu_cmd_required docker "Install Docker or rootless Docker to use this helper." || return $?

    _cpu_section "Docker container resource usage (docker stats) – Ctrl+C to exit"
    docker stats
}

# -----------------------------------------------------------------------------
# cpu_miner_scan
#   Quick and dirty scan for common cryptominer-related process names.
#   Non-destructive – it only prints matches.
# -----------------------------------------------------------------------------
cpu_miner_scan() {
    _cpu_cmd_required ps || return $?
    _cpu_cmd_required grep || return $?

    _cpu_section "Scanning for common cryptominer processes (xmrig / coin / mining)"

    # Note: use a subshell to avoid the grep line being the only match.
    local pattern
    pattern='xmrig\|coin\|mining'

    # shellcheck disable=SC2009
    ps aux | grep -Ei "${pattern}" | grep -v grep || {
        printf '\n[CPU-TOOLS] No obvious miner processes found.\n'
        return 0
    }
}

# -----------------------------------------------------------------------------
# Nice little banner on source (optional – can be commented out if noisy).
# -----------------------------------------------------------------------------
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    printf '\n[CPU-TOOLS] cpu-diagnostics-dotfile.sh loaded. Run cpu_help for options.\n'
fi
