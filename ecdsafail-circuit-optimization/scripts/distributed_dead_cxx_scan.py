#!/usr/bin/env python3
"""
Distributed dead-CXX gate screening helper for ECDSA Fail circuit optimization.

Runs target/release/screen_dead_ccx over N random inputs distributed across M
SSH hosts, with K worker processes per host, then collects shard .idx files and
builds candidate dead-CXX support/intersection lists.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Host:
    name: str
    target: str
    port: int
    identity: str | None = None


def parse_host(spec: str) -> Host:
    # Format: [name=]user@host[:port][,identity=/path/to/key]
    identity = None
    if "," in spec:
        parts = spec.split(",")
        spec = parts[0]
        for item in parts[1:]:
            if item.startswith("identity="):
                identity = item.split("=", 1)[1]
            else:
                raise ValueError(f"unknown host option in {item!r}")
    if "=" in spec:
        name, target = spec.split("=", 1)
    else:
        target = spec
        name = target.replace("@", "_").replace(":", "_").replace(".", "_")
    if ":" in target.rsplit("@", 1)[-1]:
        user_host, port_txt = target.rsplit(":", 1)
        port = int(port_txt)
        target = user_host
    else:
        port = 22
    return Host(name=name, target=target, port=port, identity=identity)


def ssh_base(host: Host, extra_opts: list[str]) -> list[str]:
    cmd = ["ssh", "-p", str(host.port), "-o", "BatchMode=yes"]
    if host.identity:
        cmd += ["-i", host.identity]
    cmd += extra_opts
    cmd.append(host.target)
    return cmd


def scp_base(host: Host, extra_opts: list[str]) -> list[str]:
    cmd = ["scp", "-P", str(host.port)]
    if host.identity:
        cmd += ["-i", host.identity]
    cmd += extra_opts
    return cmd


def run(cmd: list[str], *, input_text: str | None = None, stdout=None) -> None:
    proc = subprocess.run(
        cmd,
        input=input_text,
        text=input_text is not None,
        stdout=stdout,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        detail = proc.stderr.decode() if isinstance(proc.stderr, bytes) else proc.stderr
        raise RuntimeError(f"command failed rc={proc.returncode}: {shlex.join(cmd)}\n{detail}")


def shell_quote_args(items: Iterable[str]) -> str:
    return " ".join(shlex.quote(x) for x in items)


def make_remote_script(
    *,
    challenge_dir: str,
    remote_workdir: str,
    mode: str,
    jobs: list[tuple[str, int, str]],
    build: bool,
    include_ccz: bool,
    only_ccz: bool,
    check_output: bool,
    seed_drop_remote: str | None,
    simulate_drop_remote: str | None,
    extra_screen_args: list[str],
) -> str:
    common = ["--mode", mode]
    if include_ccz:
        common.append("--include-ccz")
    if only_ccz:
        common.append("--only-ccz")
    if check_output:
        common.append("--check-output")
    if seed_drop_remote:
        common += ["--seed-drop", seed_drop_remote]
    if simulate_drop_remote:
        common += ["--simulate-drop", simulate_drop_remote]
    common += extra_screen_args

    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        f"CHALLENGE_DIR={shlex.quote(challenge_dir)}",
        f"REMOTE_WORKDIR={shlex.quote(remote_workdir)}",
        'mkdir -p "$REMOTE_WORKDIR/shards" "$REMOTE_WORKDIR/logs"',
        'cd "$CHALLENGE_DIR"',
    ]
    if build:
        lines.append("cargo build --release --bin screen_dead_ccx")
    lines.append('printf "shard\tshots\tseed\tpid\n" > "$REMOTE_WORKDIR/manifest.tsv"')
    for shard_name, shots, seed in jobs:
        out_idx = f"{remote_workdir}/shards/{shard_name}.idx"
        out_log = f"{remote_workdir}/logs/{shard_name}.out"
        err_log = f"{remote_workdir}/logs/{shard_name}.err"
        status = f"{remote_workdir}/logs/{shard_name}.status"
        args = common + ["--shots", str(shots), "--seed", seed, "--out", out_idx]
        lines += [
            "(",
            "  set +e",
            f"  target/release/screen_dead_ccx {shell_quote_args(args)} > {shlex.quote(out_log)} 2> {shlex.quote(err_log)}",
            "  rc=$?",
            f"  printf '%s\\t%s\\n' {shlex.quote(shard_name)} \"$rc\" > {shlex.quote(status)}",
            "  exit \"$rc\"",
            ") &",
            "pid=$!",
            f"printf '%s\\t%s\\t%s\\t%s\\n' {shlex.quote(shard_name)} {shots} {shlex.quote(seed)} \"$pid\" >> \"$REMOTE_WORKDIR/manifest.tsv\"",
        ]
    lines += [
        "set +e",
        "wait",
        "wait_rc=$?",
        "set -e",
        'cd "$REMOTE_WORKDIR"',
        "tar -czf results_bundle.tgz shards logs manifest.tsv",
        'exit "$wait_rc"',
    ]
    return "\n".join(lines) + "\n"


def read_idx(path: Path) -> set[int]:
    vals: set[int] = set()
    for line in path.read_text().splitlines():
        t = line.strip()
        if not t or t.startswith("idx"):
            continue
        vals.add(int(t.split("\t", 1)[0]))
    return vals


def write_idx(path: Path, vals: Iterable[int]) -> None:
    ordered = sorted(set(vals))
    path.write_text("idx\n" + "\n".join(map(str, ordered)) + ("\n" if ordered else ""))


def collect_support(out_dir: Path, thresholds: list[int]) -> dict[str, int]:
    shard_paths = sorted(out_dir.glob("*/shards/*.idx"))
    if not shard_paths:
        raise RuntimeError(f"no shard idx files found under {out_dir}")
    support: dict[int, int] = {}
    for path in shard_paths:
        for idx in read_idx(path):
            support[idx] = support.get(idx, 0) + 1

    support_tsv = out_dir / "dead_cxx_support.tsv"
    with support_tsv.open("w") as f:
        f.write("idx\tsupport\n")
        for idx, count in sorted(support.items()):
            f.write(f"{idx}\t{count}\n")

    summary: dict[str, int] = {
        "shards": len(shard_paths),
        "unique_candidate_indices": len(support),
    }
    for threshold in thresholds:
        effective = threshold if threshold > 0 else len(shard_paths) + threshold
        effective = max(1, min(len(shard_paths), effective))
        vals = [idx for idx, count in support.items() if count >= effective]
        name = f"dead_cxx_support_ge{effective}.idx"
        write_idx(out_dir / name, vals)
        summary[name] = len(vals)
    write_idx(out_dir / "dead_cxx_intersection.idx", [idx for idx, count in support.items() if count == len(shard_paths)])
    summary["dead_cxx_intersection.idx"] = len(read_idx(out_dir / "dead_cxx_intersection.idx"))
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--total-shots", type=int, required=True, help="Total random inputs N to screen across all workers.")
    ap.add_argument("--host", action="append", required=True, help="Remote host spec [name=]user@host[:port][,identity=/path]. Repeat M times.")
    ap.add_argument("--threads-per-host", type=int, required=True, help="Worker processes K to run on each host.")
    ap.add_argument("--challenge-dir", required=True, help="Remote challenge repo directory containing target/release/screen_dead_ccx.")
    ap.add_argument("--remote-workdir", required=True, help="Remote output directory for shards/logs.")
    ap.add_argument("--out-dir", required=True, help="Local directory for fetched shard bundles and merged support lists.")
    ap.add_argument("--mode", default="random", choices=["random", "fiat-shamir"])
    ap.add_argument("--seed-prefix", default="dead-cxx")
    ap.add_argument("--build", action="store_true", help="Run cargo build --release --bin screen_dead_ccx on every host before screening.")
    ap.add_argument("--include-ccz", action="store_true", help="Also screen charged CCZ phase gates.")
    ap.add_argument("--only-ccz", action="store_true", help="Screen only CCZ phase gates.")
    ap.add_argument("--check-output", action="store_true", help="Ask screen_dead_ccx to compare dropped-stream output.")
    ap.add_argument("--seed-drop", help="Local idx file to copy to remote and pass as --seed-drop.")
    ap.add_argument("--simulate-drop", help="Local idx file to copy to remote and pass as --simulate-drop.")
    ap.add_argument("--support-threshold", action="append", type=int, default=[], help="Support threshold to emit. Negative values are relative to total shards, e.g. -1 = all-but-one.")
    ap.add_argument("--ssh-option", action="append", default=[], help="Extra option passed to ssh, e.g. -o StrictHostKeyChecking=accept-new.")
    ap.add_argument("--scp-option", action="append", default=[], help="Extra option passed to scp.")
    ap.add_argument("--screen-arg", action="append", default=[], help="Extra argument passed through to screen_dead_ccx. Repeat for each token.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    hosts = [parse_host(h) for h in args.host]
    total_workers = len(hosts) * args.threads_per_host
    if total_workers <= 0:
        raise ValueError("need at least one worker")
    base = args.total_shots // total_workers
    rem = args.total_shots % total_workers
    if base <= 0:
        raise ValueError("total-shots must be at least host_count * threads_per_host")

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    thresholds = args.support_threshold or [total_workers, -1, -2]
    manifest = {
        "total_shots": args.total_shots,
        "hosts": [h.__dict__ for h in hosts],
        "threads_per_host": args.threads_per_host,
        "total_workers": total_workers,
        "challenge_dir": args.challenge_dir,
        "remote_workdir": args.remote_workdir,
        "mode": args.mode,
        "support_thresholds": thresholds,
    }

    prepared_hosts: list[tuple[Host, Path, str]] = []
    global_worker = 0
    for hi, host in enumerate(hosts):
        local_host_dir = out_dir / host.name
        local_host_dir.mkdir(parents=True, exist_ok=True)

        remote_seed_drop = f"{args.remote_workdir}/seed_drop.idx" if args.seed_drop else None
        remote_sim_drop = f"{args.remote_workdir}/simulate_drop.idx" if args.simulate_drop else None

        jobs: list[tuple[str, int, str]] = []
        for local_thread in range(args.threads_per_host):
            shots = base + (1 if global_worker < rem else 0)
            shard = f"h{hi:02d}_t{local_thread:02d}"
            seed = f"{args.seed_prefix}-{shard}"
            jobs.append((shard, shots, seed))
            global_worker += 1

        script = make_remote_script(
            challenge_dir=args.challenge_dir,
            remote_workdir=args.remote_workdir,
            mode=args.mode,
            jobs=jobs,
            build=args.build,
            include_ccz=args.include_ccz,
            only_ccz=args.only_ccz,
            check_output=args.check_output,
            seed_drop_remote=remote_seed_drop,
            simulate_drop_remote=remote_sim_drop,
            extra_screen_args=args.screen_arg,
        )
        (local_host_dir / "run_remote_dead_cxx_scan.sh").write_text(script)
        manifest.setdefault("remote_jobs", {})[host.name] = jobs
        if args.dry_run:
            continue

        # Copy optional idx inputs to remote workdir.
        run(ssh_base(host, args.ssh_option) + [f"mkdir -p {shlex.quote(args.remote_workdir)}"])
        if args.seed_drop:
            run(scp_base(host, args.scp_option) + [args.seed_drop, f"{host.target}:{remote_seed_drop}"])
        if args.simulate_drop:
            run(scp_base(host, args.scp_option) + [args.simulate_drop, f"{host.target}:{remote_sim_drop}"])

        remote_script = f"{args.remote_workdir}/run_remote_dead_cxx_scan.sh"
        run(ssh_base(host, args.ssh_option) + [f"cat > {shlex.quote(remote_script)} && chmod +x {shlex.quote(remote_script)}"], input_text=script)
        prepared_hosts.append((host, local_host_dir, remote_script))

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    if args.dry_run:
        print(f"dry-run wrote remote scripts under {out_dir}")
        return 0

    # Run all hosts concurrently. Each remote script then fans out to K local
    # screen_dead_ccx workers on that host.
    procs: list[tuple[Host, Path, subprocess.Popen[bytes]]] = []
    for host, local_host_dir, remote_script in prepared_hosts:
        proc = subprocess.Popen(
            ssh_base(host, args.ssh_option) + [remote_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        procs.append((host, local_host_dir, proc))

    failures: list[str] = []
    for host, local_host_dir, proc in procs:
        stdout_b, stderr_b = proc.communicate()
        (local_host_dir / "remote_runner.out").write_bytes(stdout_b or b"")
        (local_host_dir / "remote_runner.err").write_bytes(stderr_b or b"")
        if proc.returncode != 0:
            failures.append(f"{host.name} rc={proc.returncode}; see {local_host_dir / 'remote_runner.err'}")

    for host, local_host_dir, _remote_script in prepared_hosts:
        archive = local_host_dir / "results_bundle.tgz"
        with archive.open("wb") as f:
            run(ssh_base(host, args.ssh_option) + [f"cat {shlex.quote(args.remote_workdir)}/results_bundle.tgz"], stdout=f)
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(local_host_dir)
    if failures:
        raise RuntimeError("remote screening failed; fetched available logs first:\n" + "\n".join(failures))

    summary = collect_support(out_dir, thresholds)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
