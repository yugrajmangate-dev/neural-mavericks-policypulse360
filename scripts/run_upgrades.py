"""Deploy the PolicyPulse 360 upgrades to Snowflake, in dependency order:

  1. sql/semantic_view_customer360.sql   APP.CUSTOMER_360_SV (Cortex Analyst semantic view)
  2. sql/cortex_search_transcripts.sql   CURATED.TRANSCRIPT_SEARCH (Cortex Search)
  3. sql/cortex_agent_policypulse.sql    APP.POLICYPULSE_COPILOT (Cortex Agent: Analyst + Search)
  4. sql/action_log.sql                  APP.ACTION_LOG + uptake views (write-back)

Requires the base pipeline to have run (scripts/run_pipeline.py): CURATED.CUSTOMER_360,
CURATED.INTERACTION_INSIGHTS and APP.NEXT_BEST_ACTIONS must exist.

    python scripts/run_upgrades.py                  # all four steps
    python scripts/run_upgrades.py --only agent     # one step: semantic | search | agent | actions
    python scripts/run_upgrades.py --dry-run        # print the statements, no connection
    python scripts/run_upgrades.py --smoke          # also ask the agent one question
    python scripts/run_upgrades.py --teardown       # after the demo: drop the agent + search service

Connection: same as the other scripts (SNOWFLAKE_CONNECTION or the default in ~/.snowflake/connections.toml).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from io import StringIO
from pathlib import Path

from snowflake.connector.util_text import split_statements

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

STEPS = [
    ("semantic", "sql/semantic_view_customer360.sql", "Semantic view APP.CUSTOMER_360_SV"),
    ("search", "sql/cortex_search_transcripts.sql", "Cortex Search CURATED.TRANSCRIPT_SEARCH"),
    ("agent", "sql/cortex_agent_policypulse.sql", "Cortex Agent APP.POLICYPULSE_COPILOT"),
    ("actions", "sql/action_log.sql", "Write-back APP.ACTION_LOG"),
]
PREREQS = ["POLICYPULSE.CURATED.CUSTOMER_360", "POLICYPULSE.CURATED.INTERACTION_INSIGHTS",
           "POLICYPULSE.APP.NEXT_BEST_ACTIONS"]
TEARDOWN = ["DROP AGENT IF EXISTS POLICYPULSE.APP.POLICYPULSE_COPILOT",
            "DROP CORTEX SEARCH SERVICE IF EXISTS POLICYPULSE.CURATED.TRANSCRIPT_SEARCH"]
SMOKE_Q = "Why is customer C0004 at risk and what should I do today? Cite the transcripts."


def statements(path: Path) -> list[str]:
    sql = path.read_text(encoding="utf-8")
    return [s.strip() for s, _ in split_statements(StringIO(sql), remove_comments=True) if s.strip()]


def short(q: str, n: int = 100) -> str:
    q = " ".join(q.split())
    return q if len(q) <= n else q[: n - 1] + "…"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def run_step(cur, key: str, rel: str, title: str) -> bool:
    stmts = statements(ROOT / rel)
    log(f"▶ {key:<8} {title}  ({rel}, {len(stmts)} statements)")
    t0 = time.time()
    for i, q in enumerate(stmts, 1):
        t = time.time()
        try:
            cur.execute(q)
        except Exception as e:  # stop this step at the first failure: later statements depend on earlier ones
            log(f"  ✗ [{i}/{len(stmts)}] {short(q)}")
            log(f"    {type(e).__name__}: {str(e).strip().splitlines()[0][:300]}")
            return False
        rows = ""
        if q.upper().startswith(("SELECT", "SHOW")):
            try:
                res = cur.fetchall()
                rows = f" → {len(res)} row(s)"
                for r in res[:4]:
                    print("      " + short(" | ".join(str(x) for x in r), 160))
            except Exception:
                pass
        log(f"  ✓ [{i}/{len(stmts)}] {short(q)}  ({time.time() - t:.1f}s){rows}")
    log(f"✔ {key} done in {time.time() - t0:.1f}s")
    return True


def check_prereqs(cur) -> bool:
    ok = True
    for obj in PREREQS:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {obj}")
            log(f"  ✓ {obj}: {cur.fetchone()[0]} rows")
        except Exception as e:
            ok = False
            log(f"  ✗ {obj} missing ({type(e).__name__}); run scripts/run_pipeline.py first")
    return ok


def smoke(cur) -> None:
    body = json.dumps({"messages": [{"role": "user", "content": [{"type": "text", "text": SMOKE_Q}]}]})
    log(f"▶ smoke    asking the agent: {SMOKE_Q!r}")
    cur.execute("SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN('POLICYPULSE.APP.POLICYPULSE_COPILOT', %s)", (body,))
    resp = json.loads(cur.fetchone()[0])
    tools = [c.get("tool_use", {}).get("name") for c in resp.get("content", []) if c.get("type") == "tool_use"]
    text = "\n".join(c.get("text", "") for c in resp.get("content", []) if c.get("type") == "text")
    log(f"  tools used: {', '.join(t for t in tools if t) or '—'}")
    print("\n" + (text or json.dumps(resp, indent=2)[:2000]) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=[k for k, *_ in STEPS], help="run a single step")
    ap.add_argument("--dry-run", action="store_true", help="print statements without connecting")
    ap.add_argument("--smoke", action="store_true", help="run one agent question after deploying")
    ap.add_argument("--teardown", action="store_true", help="drop the agent and search service, then exit")
    ap.add_argument("--keep-going", action="store_true", help="continue to later steps after a failure")
    a = ap.parse_args()

    steps = [s for s in STEPS if not a.only or s[0] == a.only]
    if a.dry_run:
        for key, rel, title in steps:
            print(f"\n-- ===== {key}: {title} ({rel})")
            for q in statements(ROOT / rel):
                print(q.rstrip(";") + ";\n")
        if a.teardown:
            print("\n-- ===== teardown\n" + ";\n".join(TEARDOWN) + ";")
        return 0

    from sf_conn import connect

    log("Connecting to Snowflake…")
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT CURRENT_ACCOUNT(), CURRENT_USER(), CURRENT_ROLE()")
    acct, user, role = cur.fetchone()
    log(f"  account={acct} user={user} role={role}")
    cur.execute("USE WAREHOUSE POLICYPULSE_WH")

    if a.teardown:
        for q in TEARDOWN:
            cur.execute(q)
            log(f"  ✓ {q}")
        return 0

    log("Checking pipeline outputs…")
    if not check_prereqs(cur):
        return 2

    t0, failed = time.time(), []
    for key, rel, title in steps:
        if not run_step(cur, key, rel, title):
            failed.append(key)
            if not a.keep_going:
                break
    if a.smoke and not failed and (not a.only or a.only == "agent"):
        try:
            smoke(cur)
        except Exception as e:
            log(f"  ✗ smoke test failed: {type(e).__name__}: {str(e)[:300]}")
            failed.append("smoke")

    log("=" * 60)
    log(f"{'FAILED: ' + ', '.join(failed) if failed else 'All upgrade steps succeeded'} "
        f"in {time.time() - t0:.1f}s")
    if not failed:
        log("Next: python scripts/run_upgrades.py --smoke  ·  after the demo: --teardown")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
