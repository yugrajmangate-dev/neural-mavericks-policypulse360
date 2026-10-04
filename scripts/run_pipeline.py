"""Run the 3 CoCo skills' SQL headlessly (same files CoCo CLI executes) — useful for CI or a warm-up
before recording the demo.

    python scripts/run_pipeline.py                 # all three skills, in chain order
    python scripts/run_pipeline.py interaction-intel
    python scripts/run_pipeline.py --fallback      # use legacy Cortex functions in Skill 2
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from sf_conn import connect, run_sql_file  # noqa: E402

SK = ROOT / ".cortex" / "skills"
CHAIN = {
    "c360-unify": [SK / "c360-unify" / "c360_unify.sql"],
    "interaction-intel": [SK / "interaction-intel" / "interaction_intel.sql"],
    "next-best-action": [SK / "next-best-action" / "churn_risk.sql", SK / "next-best-action" / "next_best_action.sql"],
}

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--fallback" in sys.argv:
        CHAIN["interaction-intel"] = [SK / "interaction-intel" / "interaction_intel_fallback.sql"]
    skills = args or list(CHAIN)
    conn = connect()
    for s in skills:
        for f in CHAIN[s]:
            print(f"▶ ${s}  ({f.name})")
            rows = run_sql_file(conn, f)
            for r in rows or []:
                print("   ", r)
    conn.close()
