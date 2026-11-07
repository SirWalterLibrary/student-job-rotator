"""End-to-end smoke test for the Khidmah Roster API.

Runs the Flask app in-process (test client, throwaway database,
ALLOW_TODAY_OVERRIDE), seeds the demo roster from scripts/seed_demo.py,
then for each Saturday of 12 weekends verifies:
  (a) no student appears twice on the same day;
  (b) for every job, the pick is the first person in that job's queue
      (/api/queue as of the day the queue was still "before" the weekend)
      who is not already busy on that Saturday;
  (c) a Saturday cancel followed by a restore returns the same roles;
  (d) an absent swap leaves the absent student holding the job on Sunday.
Prints SMOKE OK when everything passes.
"""
import os
import shutil
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import seed_demo  # noqa: E402
from rotator.app import create_app  # noqa: E402
from rotator.db import connect  # noqa: E402

PIN = "1234"
START = date(2026, 11, 7)  # the demo roster's first Saturday
WEEKS = 12
HEADER = {"X-Admin-Pin": PIN}


def check(condition: bool, message: str) -> None:
    """Abort with context when an invariant breaks."""
    if not condition:
        raise SystemExit(f"SMOKE FAILED: {message}")


def role_pairs(session: dict) -> list[tuple[int, int]]:
    """The (job_id, student_id) pairs of one session view, sorted."""
    return sorted(
        (r["job"]["id"], r["student"]["id"])
        for r in session["roles"] if r["student"] is not None
    )


def unique_students(session: dict) -> list[int]:
    """The student ids of one session view (one entry per role)."""
    return [r["student"]["id"] for r in session["roles"] if r["student"] is not None]


def run_weekend(client, week: int, sat: date, prev_sat: date) -> None:
    """Run checks (a)-(d) for one weekend."""
    sun = sat + timedelta(days=1)

    # The queue as of last Saturday = exactly the state before this weekend:
    # queue_status walks to the next class day (last Sunday), so its order is
    # the order this Saturday's picks will be drawn from.
    q = client.get(f"/api/queue?today={prev_sat.isoformat()}")
    check(q.status_code == 200, f"week {week} {sat}: /api/queue -> {q.status_code} {q.get_json()}")
    queue_by_job = {
        entry["job"]["id"]: [p["student"]["id"] for p in entry["queue"]]
        for entry in q.get_json()["jobs"]
    }

    res = client.get(f"/api/today?today={sat.isoformat()}")
    check(res.status_code == 200, f"week {week} {sat}: /api/today -> {res.status_code}")
    check(res.get_json()["mode"] == "today" and len(res.get_json()["sessions"]) == 1,
          f"week {week} {sat}: expected one 'today' session, got {res.get_json()}")
    session = res.get_json()["sessions"][0]

    # (a) nobody holds two jobs on Saturday.
    ids = unique_students(session)
    check(len(ids) == len(set(ids)),
          f"week {week} {sat}: a student holds two jobs: {ids}")
    # (b) every pick is the first queued volunteer not busy elsewhere that day.
    for role in session["roles"]:
        if role["student"] is None:
            continue
        order = queue_by_job.get(role["job"]["id"], [])
        pick = role["student"]["id"]
        check(pick in order,
              f"week {week} {sat} {role['job']['name']}: pick {pick} is not in the queue {order}")
        busy = {r["student"]["id"] for r in session["roles"] if r["job"]["id"] != role["job"]["id"]}
        free = next((s for s in order if s not in busy), None)
        check(free == pick,
              f"week {week} {sat} {role['job']['name']}: picked {pick} although {free} "
              f"was older in line and free (queue {order})")
    print(f"week {week} ({sat.isoformat()}): {len(session['roles'])} roles, "
          f"no double jobs, every pick oldest-free in its queue")

    # (c) cancel Saturday then restore: the same roles come back.
    before = role_pairs(session)
    ok = client.post(f"/api/sessions/{sat.isoformat()}/cancel?today={sat.isoformat()}",
                     headers=HEADER, json={"note": "smoke: teacher away"})
    check(ok.status_code == 200, f"week {week} {sat}: cancel -> {ok.status_code} {ok.get_json()}")
    ok = client.post(f"/api/sessions/{sat.isoformat()}/restore?today={sat.isoformat()}", headers=HEADER)
    check(ok.status_code == 200, f"week {week} {sat}: restore -> {ok.status_code} {ok.get_json()}")
    restored = client.get(f"/api/today?today={sat.isoformat()}").get_json()["sessions"][0]
    check(role_pairs(restored) == before,
          f"week {week} {sat}: cancel/restore changed the roles: {before} -> {role_pairs(restored)}")
    print(f"week {week} ({sat.isoformat()}): cancel + restore returned the same roles")

    # (d) absent swap: the absent student holds the job on Sunday.
    sun_session = client.get(f"/api/today?today={sun.isoformat()}").get_json()["sessions"][0]
    ids = unique_students(sun_session)
    check(len(ids) == len(set(ids)), f"week {week} {sun}: a student holds two jobs: {ids}")
    sun_students = set(ids)
    candidates = [r for r in session["roles"]
                  if r["student"] is not None and r["student"]["id"] not in sun_students]
    check(candidates,
          f"week {week} {sat}: no swap candidate — every Saturday student also works Sunday")
    role = candidates[0]
    res = client.post(f"/api/sessions/{sat.isoformat()}/absent?today={sat.isoformat()}",
                      headers=HEADER, json={"job_id": role["job"]["id"]})
    check(res.status_code == 200,
          f"week {week} {sat}: absent swap -> {res.status_code} {res.get_json()}")
    absent = res.get_json()["absent"]["id"]
    check(absent == role["student"]["id"], f"week {week} {sat}: swap swapped the wrong student")
    sun_after = client.get(f"/api/today?today={sun.isoformat()}").get_json()["sessions"][0]
    holders = {r["job"]["id"]: r["student"]["id"] for r in sun_after["roles"]}
    check(holders.get(role["job"]["id"]) == absent,
          f"week {week} {sun}: absent student {absent} does not hold job {role['job']['id']} on Sunday")
    ids = unique_students(sun_after)
    check(len(ids) == len(set(ids)), f"week {week} {sun}: a student holds two jobs after the swap: {ids}")
    print(f"week {week} ({sun.isoformat()}): after the swap, {absent} holds the make-up role, no double jobs")


def main() -> None:
    tmp = tempfile.mkdtemp(prefix="khidmah-smoke-")
    try:
        app = create_app({"DATA_DIR": tmp, "ADMIN_PIN": PIN, "ALLOW_TODAY_OVERRIDE": True})
        conn = connect(os.path.join(tmp, "rotator.db"))
        try:
            seed_demo.seed(conn, reset=True)
        finally:
            conn.close()
        client = app.test_client()
        saturdays = [START + timedelta(weeks=k) for k in range(WEEKS)]
        for k, sat in enumerate(saturdays, start=1):
            prev = saturdays[k - 2] if k >= 2 else START - timedelta(weeks=1)
            run_weekend(client, k, sat, prev)
        print("SMOKE OK")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
