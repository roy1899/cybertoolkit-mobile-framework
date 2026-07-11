#!/usr/bin/env python3
"""
ctk - CyberToolkit Mobile Framework CLI.

Usage:
    ctk list-modules
    ctk [--profile PROFILE] [--authorize CIDR_OR_HOST ...] run <module> [module args]
    ctk session path
    ctk session clear

Examples:
    ctk run context_detector
    ctk --profile home_lab run port_scanner --target 192.168.1.10
    ctk --profile authorized_client --authorize 203.0.113.0/24 \\
        run port_scanner --target 203.0.113.10
    ctk run reporting --output report.md
    ctk run reporting   # auto-names: cybertoolkit_report_<network>_<date>.html

Every `ctk run` is appended to a local session log automatically (see
engine/core/session_log.py), which `ctk run reporting` then aggregates.
Use `--no-log` on `run` to skip logging a particular invocation, or
`ctk session clear` to start a fresh session.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.core.policy_client import PolicyClient  # noqa: E402
from engine.core.registry import MODULE_REGISTRY, get_module_class  # noqa: E402
from engine.core.session_log import append_entry, clear as clear_session_log, session_log_path  # noqa: E402
from engine.policy.policy_engine import PolicyEngine  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ctk", description="CyberToolkit Mobile Framework CLI")
    parser.add_argument(
        "--profile", default="safe", help="Execution policy profile (default: safe)"
    )
    parser.add_argument(
        "--authorize",
        action="append",
        default=[],
        metavar="CIDR_OR_HOST",
        help="Explicitly confirm authorization for a target/subnet for this run. Repeatable.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-modules", help="List available modules and the capability they need")

    run_p = sub.add_parser("run", help="Run a module")
    run_p.add_argument("module", choices=sorted(MODULE_REGISTRY.keys()))
    run_p.add_argument("--target", help="Target host/CIDR (required by active modules)")
    run_p.add_argument("--ports", default="1-1024", help="Port range for port_scanner")
    run_p.add_argument(
        "--output",
        help="Write the report to this file (only meaningful for `run reporting`); "
        "format is Markdown, or HTML if the filename ends in .html. If omitted "
        "for `run reporting`, an HTML file named after the detected network "
        "and timestamp is generated automatically.",
    )
    run_p.add_argument(
        "--no-log", action="store_true", help="Don't append this run to the session log"
    )

    session_p = sub.add_parser("session", help="Manage the local session log")
    session_sub = session_p.add_subparsers(dest="session_command", required=True)
    session_sub.add_parser("path", help="Print the current session log path")
    session_sub.add_parser("clear", help="Delete the current session log")

    return parser


def _sanitize_filename_component(value: str) -> str:
    """Keeps a network name usable in a filename across Termux/Android
    filesystems: alphanumerics, dash, underscore only; everything else
    becomes an underscore, and the result is capped to a sane length.
    """
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned.strip("_")[:60] or "network"


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "list-modules":
        for name, cls in sorted(MODULE_REGISTRY.items()):
            print(f"{name}: {cls.description}")
        return

    if args.command == "session":
        if args.session_command == "path":
            print(session_log_path())
        elif args.session_command == "clear":
            clear_session_log()
            print("Session log cleared.")
        return

    try:
        engine = PolicyEngine(profile_name=args.profile, authorized_scopes=args.authorize)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)

    module_cls = get_module_class(args.module)
    policy_client = PolicyClient(engine, module_cls.name)
    module = module_cls(policy_client)

    kwargs = {}
    if args.module == "port_scanner":
        if not args.target:
            print("error: port_scanner requires --target", file=sys.stderr)
            sys.exit(2)
        kwargs = {"target": args.target, "ports": args.ports}

    result = module.run(**kwargs)
    print(json.dumps(result, indent=2))

    if not args.no_log and args.module != "reporting":
        # The reporting module reads the log; it shouldn't also write to
        # it, or every report would include an entry for itself.
        append_entry(args.module, args.profile, result)

    if args.module == "reporting":
        output_path = args.output
        if not output_path:
            label = result.get("network_label")
            label_part = _sanitize_filename_component(label) if label else "session"
            date_part = datetime.now().strftime("%Y%m%d_%H%M")
            output_path = f"cybertoolkit_report_{label_part}_{date_part}.html"

        report_content = None
        if output_path.lower().endswith(".html") and result.get("report_html"):
            report_content = result["report_html"]
        elif result.get("report_markdown"):
            report_content = result["report_markdown"]

        if report_content is not None:
            Path(output_path).write_text(report_content)
            print(f"\nReport written to {output_path}", file=sys.stderr)

    if result.get("status") == "denied":
        sys.exit(1)


if __name__ == "__main__":
    main()
