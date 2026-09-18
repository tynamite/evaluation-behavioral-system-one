"""Command line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import FIGURES_DIR, RAW_DIR, TABLES_DIR, Config
from .instruments import MODULES, PERSONAS, all_probes


def _cmd_doctor(args: argparse.Namespace) -> int:
    """Check the key, probe the endpoint, and report exactly what came back.

    The OpenRouter decisions route is an alpha route. If it moves, this is the
    one command that says so plainly instead of surfacing a stack trace.
    """
    from .schema import Choice, Noul, Score

    cfg = Config.from_env(args.backend)
    print(f"backend        {cfg.backend}")
    print(f"decisions url  {cfg.decisions_url}")
    print(f"model          {cfg.model}")
    print(f"baseline model {cfg.baseline_model}")
    key_state = "set" if cfg.api_key else "MISSING"
    print(f"api key        {key_state}")
    if not cfg.api_key and cfg.backend != "simulator":
        print("\nNo API key. Copy .env.example to .env, or use --backend simulator.")
        return 1

    from .client import SystemOneClient
    from .simulator import SimulatorClient

    client = SimulatorClient() if cfg.backend == "simulator" else SystemOneClient(cfg)
    try:
        resp = client.decide(
            {"note": "connectivity check"},
            {
                "pick": Choice(
                    instructions="Pick one.", criteria={"a": "Option A", "b": "Option B"}
                ),
                "claim": Noul(instructions="The sky is blue."),
                "level": Score(instructions="Rate this.", criteria=["Low", "Medium", "High"]),
            },
        )
    except Exception as exc:
        print(f"\nFAILED: {exc}")
        print("\nIf this is a 404, the alpha route has probably moved. Override it with")
        print("JEVBENCH_DECISIONS_URL in .env, or switch to --backend typesafe.")
        return 1
    finally:
        client.close()

    print(f"\nOK — served by {resp.model}")
    for qid, ans in resp.answers.items():
        print(f"  {qid:8s} {ans.kind:7s} value={ans.value!r} confidence={ans.confidence}")
    print(f"  usage: {resp.usage}")
    return 0


def _cmd_probes(args: argparse.Namespace) -> int:
    probes = all_probes(args.modules)
    from collections import Counter

    counts = Counter(p.instrument for p in probes)
    print(f"{len(probes)} probes across {len(counts)} instruments")
    for name, n in sorted(counts.items()):
        print(f"  {name:28s} {n:3d}")
    n_calls = len(probes) * len(args.personas or PERSONAS) * args.replicates
    print(f"\nJev arm would issue {n_calls} calls at {args.replicates} replicate(s).")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    from .runner import run_battery

    cfg = Config.from_env(args.backend)
    run_battery(
        cfg,
        modules=args.modules,
        personas=args.personas,
        replicates=args.replicates,
        baseline_samples=args.baseline_samples,
        workers=args.workers,
    )
    return 0


def _cmd_analyse(args: argparse.Namespace) -> int:
    from .analysis import analyse_run, latest_run

    path = Path(args.run) if args.run else latest_run(RAW_DIR)
    if path is None:
        print(f"No run files in {RAW_DIR}. Run `jevbench run` first.", file=sys.stderr)
        return 1
    analyse_run(path, TABLES_DIR)
    return 0


def _cmd_figures(args: argparse.Namespace) -> int:
    from .analysis import latest_run
    from .plots import build_figures

    path = Path(args.run) if args.run else latest_run(RAW_DIR)
    if path is None:
        print(f"No run files in {RAW_DIR}. Run `jevbench run` first.", file=sys.stderr)
        return 1
    build_figures(path, FIGURES_DIR)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="jevbench",
        description="Behavioural-economics and psychometric battery for System One models.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--backend", choices=["openrouter", "typesafe", "simulator"], default=None)
        p.add_argument("--modules", nargs="*", choices=sorted(MODULES), default=None)
        p.add_argument("--personas", nargs="*", choices=sorted(PERSONAS), default=None)
        p.add_argument("--replicates", type=int, default=3)

    d = sub.add_parser("doctor", help="check credentials and endpoint reachability")
    d.add_argument("--backend", choices=["openrouter", "typesafe", "simulator"], default=None)
    d.set_defaults(func=_cmd_doctor)

    p = sub.add_parser("probes", help="list the battery without calling anything")
    add_common(p)
    p.set_defaults(func=_cmd_probes)

    r = sub.add_parser("run", help="run the battery and write raw records")
    add_common(r)
    r.add_argument(
        "--baseline-samples",
        type=int,
        default=0,
        help="resamples per probe for the autoregressive baseline arm (0 = skip)",
    )
    r.add_argument("--workers", type=int, default=8)
    r.set_defaults(func=_cmd_run)

    a = sub.add_parser("analyse", help="compute statistics and write tables")
    a.add_argument("--run", default=None, help="path to a run .jsonl (default: most recent)")
    a.set_defaults(func=_cmd_analyse)

    f = sub.add_parser("figures", help="render figures from a run")
    f.add_argument("--run", default=None)
    f.set_defaults(func=_cmd_figures)

    args = parser.parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
