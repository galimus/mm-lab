
import argparse, os, subprocess, sys, time
from pathlib import Path

def run(cmd: list[str], env: dict):
    print(">>", " ".join(cmd))
    rc = subprocess.run(cmd, env=env).returncode
    if rc != 0:
        raise SystemExit(rc)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="+",
                    default=["ETHUSDT","BTCUSDT","SOLUSDT"],
                    help="Pairs to process")
    ap.add_argument("--collect", action="store_true",
                    help="Collect snapshots before plotting")
    ap.add_argument("--snapshots", type=int, default=2000,
                    help="Snapshots to collect if --collect")
    ap.add_argument("--delay", type=float, default=0.02,
                    help="Delay (s) between snapshots during collection")
    ap.add_argument("--minutes", type=int, default=0,
                    help="Use last X minutes (0 = all CSV)")
    ap.add_argument("--strategy", type=str, default="both",
                    choices=["stoikov","naivemm","both"])
    ap.add_argument("--python", type=str, default=sys.executable,
                    help="Python executable (default: current)")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent
    main_py = str(root / "main.py")

    env = os.environ.copy()
    env["PYTHONPATH"] = env.get("PYTHONPATH", ".") or "."

    for sym in args.symbols:
        print(f"\n=== {sym} ===")
        if args.collect:
          
            run([
                args.python, main_py,
                "--strategy", args.strategy,
                "--symbol", sym,
                "--collect_data",
                "--snapshots", str(args.snapshots),
                "--delay", str(args.delay),
                "--minutes", "0",
            ], env)


        run([
            args.python, main_py,
            "--strategy", args.strategy,
            "--symbol", sym,
            "--minutes", str(args.minutes)
        ], env)

        outdir = Path("figures") / sym
        print(f"saved -> {outdir}/pnl_comparison.png, {outdir}/inventory_comparison.png")
        time.sleep(0.3)

if __name__ == "__main__":
    main()
