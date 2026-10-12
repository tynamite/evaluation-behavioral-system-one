"""Command line entry point."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from .config import COMPARISON_DIR, FIGURES_DIR, RAW_DIR, TABLES_DIR, Config
from .instruments import MODULES, PERSONAS, all_probes


def _with_models(cfg: Config, args: argparse.Namespace) -> Config:
    """Apply --model / --baseline-model over whatever the environment says."""
    model = getattr(args, "model", None) or cfg.model
    baseline = getattr(args, "baseline_model", None) or cfg.baseline_model
    return replace(cfg, model=model, baseline_model=baseline)


def _cmd_doctor(args: argparse.Namespace) -> int:
    """Check the key, probe the endpoint, and report exactly what came back.

    The OpenRouter decisions route is an alpha route. If it moves, this is the
    one command that says so plainly instead of surfacing a stack trace.

    Each primitive is probed in its own call, because the System One models on
    the route do not all promise to implement all three, and a model that
    rejects Score would otherwise fail every Score item of a paid run.
    """
    from .schema import Choice, Noul, Question, Score

    base = Config.from_env(args.backend)
    print(f"backend        {base.backend}")
    print(f"decisions url  {base.decisions_url}")
    print(f"baseline model {base.baseline_model}")
    key_state = "set" if base.api_key else "MISSING"
    print(f"api key        {key_state}")
    if not base.api_key and base.backend != "simulator":
        print("\nNo API key. Copy .env.example to .env, or use --backend simulator.")
        return 1

    from .client import SystemOneClient
    from .simulator import SimulatorClient

    probes: dict[str, Question] = {
        "choice": Choice(instructions="Pick one.", criteria={"a": "Option A", "b": "Option B"}),
        "noul": Noul(instructions="The sky is blue."),
        "score": Score(instructions="Rate this.", criteria=["Low", "Medium", "High"]),
    }
    failed = 0
    for model in args.model or [base.model]:
        cfg = replace(base, model=model)
        print(f"\nmodel          {cfg.model}")
        client = (
            SimulatorClient(stands_in_for=cfg.model)
            if cfg.backend == "simulator"
            else SystemOneClient(cfg)
        )
        try:
            for kind, question in probes.items():
                try:
                    resp = client.decide({"note": "connectivity check"}, {kind: question})
                except Exception as exc:
                    failed += 1
                    print(f"  {kind:7s} FAILED: {exc}")
                    continue
                ans = resp.answers[kind]
                print(
                    f"  {kind:7s} ok  served by {resp.model}  value={ans.value!r} "
                    f"confidence={ans.confidence}  cost={resp.usage.get('cost')}"
                )
        finally:
            client.close()

    if failed:
        print("\nIf every primitive fails with a 404, the alpha route has probably moved:")
        print("override it with JEVBENCH_DECISIONS_URL in .env, or use --backend typesafe.")
        print("If only one primitive fails, that model does not implement it, and a run")
        print("would lose every item of that kind.")
        return 1
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

    cfg = _with_models(Config.from_env(args.backend), args)
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
    analyse_run(path, Path(args.out) if args.out else TABLES_DIR)
    return 0


def _cmd_figures(args: argparse.Namespace) -> int:
    from .analysis import latest_run
    from .plots import build_figures

    path = Path(args.run) if args.run else latest_run(RAW_DIR)
    if path is None:
        print(f"No run files in {RAW_DIR}. Run `jevbench run` first.", file=sys.stderr)
        return 1
    build_figures(path, Path(args.out) if args.out else FIGURES_DIR)
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    from .compare import compare_runs
    from .plots import fig_model_comparison

    out = Path(args.out)
    try:
        tables = compare_runs([Path(p) for p in args.runs], out)
    except ValueError as exc:
        print(f"compare: {exc}", file=sys.stderr)
        return 1
    fig = fig_model_comparison(tables["fidelity"], out)
    if fig is not None:
        print(f"wrote {fig}")
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
    d.add_argument(
        "--model",
        nargs="*",
        default=None,
        help="System One model(s) to probe (default: JEVBENCH_MODEL)",
    )
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
    r.add_argument("--model", default=None, help="System One model (default: JEVBENCH_MODEL)")
    r.add_argument(
        "--baseline-model",
        default=None,
        help="chat model for the baseline arm (default: JEVBENCH_BASELINE_MODEL)",
    )
    r.set_defaults(func=_cmd_run)

    a = sub.add_parser("analyse", help="compute statistics and write tables")
    a.add_argument("--run", default=None, help="path to a run .jsonl (default: most recent)")
    a.add_argument("--out", default=None, help=f"output directory (default: {TABLES_DIR.name}/)")
    a.set_defaults(func=_cmd_analyse)

    f = sub.add_parser("figures", help="render figures from a run")
    f.add_argument("--run", default=None)
    f.add_argument("--out", default=None, help=f"output directory (default: {FIGURES_DIR.name}/)")
    f.set_defaults(func=_cmd_figures)

    c = sub.add_parser("compare", help="put several models' runs side by side")
    c.add_argument("runs", nargs="+", help="run .jsonl files, one per model")
    c.add_argument("--out", default=str(COMPARISON_DIR), help="output directory")
    c.set_defaults(func=_cmd_compare)

    args = parser.parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
