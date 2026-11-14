"""
Reads Antonina's instance (CSV files from her repository) into the format of Model II
and solves Model II on it.

Run:     python load_antonina.py PATH/TO/data-FOLDER
         python load_antonina.py PATH/TO/data-FOLDER --vehicles 5

Assumptions when reading:
  - Time window [E, L] = [earliest_start, latest_start] from her file (i.e. without a theta shift;
    uncertainty is not part of this first step yet)
  - Duration = column "duration", travel times = travel_time_matrix.csv
  - Her times are minutes since midnight; they are shifted so that the earliest E is 0
"""
import argparse
import csv
from pathlib import Path

from generator import Flight, Instance, describe
from model2 import build_arcs, solve_model2, check_solution, end_state


def load_instance(data_dir):
    data_dir = Path(data_dir)
    with open(data_dir / "synthetic_flights.csv", newline="") as fh:
        rows = list(csv.DictReader(fh))
    with open(data_dir / "travel_time_matrix.csv", newline="") as fh:
        rd = csv.reader(fh)
        header = next(rd)[1:]
        table = {}
        for row in rd:
            for to, v in zip(header, row[1:]):
                table[(row[0], to)] = int(float(v))

    rows.sort(key=lambda r: (int(r["earliest_start"]), r["flight_id"]))
    shift = min(int(r["earliest_start"]) for r in rows)
    flights, names = [], {}
    for idx, r in enumerate(rows, start=1):
        kind = "A" if r["flight_type"] == "arrival" else "D"
        flights.append(Flight(
            idx, kind, "-", int(r["q_i"]), "", int(r["scheduled_time"]) - shift,
            r["start_location"], r["end_location"],
            int(r["earliest_start"]) - shift, int(r["latest_start"]) - shift,
            int(r["duration"])))
        names[idx] = r["flight_id"]
    return Instance(flights, shift=shift, meta={"names": names}, table=table, base=0)


def compare_with_feasible_connections(inst, arcs, data_dir):
    """Compares the flight pairs for which my network has a transfer arc
    with feasible_connections.csv from her repository."""
    path = Path(data_dir) / "feasible_connections.csv"
    if not path.exists():
        return
    names = inst.meta["names"]
    mine = {(names[a.u[1]], names[a.v[1]]) for a in arcs if a.kind == "transfer"}
    with open(path, newline="") as fh:
        theirs = {(r["flight_i"], r["flight_j"]) for r in csv.DictReader(fh)}
    print(f"Flight pairs with a possible connection: my network {len(mine)}, her file {len(theirs)}, "
          f"only in mine {len(mine - theirs)}, only in hers {len(theirs - mine)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir")
    ap.add_argument("--vehicles", type=int, default=5, help="Fleet size (in her file: N_VEHICLES = 5)")
    args = ap.parse_args()

    inst = load_instance(args.data_dir)
    describe(inst)
    names = inst.meta["names"]

    arcs = build_arcs(inst, args.vehicles)
    kinds = {}
    for a in arcs:
        kinds[a.kind] = kinds.get(a.kind, 0) + 1
    print("\nNetwork G1:", kinds, f"-> {len(arcs)} arcs in total")
    compare_with_feasible_connections(inst, arcs, args.data_dir)

    total = sum(f.q for f in inst.flights)
    big = solve_model2(inst, total)
    mf = big["dispatched"]
    print(f"\nMinimum fleet so that all {total} virtual flights are served on time: {mf}")

    for V in sorted({args.vehicles, max(1, round(0.55 * mf))}):
        res = solve_model2(inst, V)
        check_solution(inst, res, V)
        unserved = {names[i]: n for i, n in res["unserved"].items()}
        print(f"\n|V| = {V}: objective {res['objective']}, served virtual flights {res['n_served']} of {total}, "
              f"ferries used {res['dispatched']}, runtime {res['runtime']:.2f} s")
        print("  flights not served on time (flight: count):", unserved)
        if V == args.vehicles:
            for n, r in enumerate(res["routes"], start=1):
                te, le = end_state(inst, r)
                txt = " -> ".join(f"{names[i]}@{inst.clock(s)}" for i, s in r)
                print(f"  Ferry {n}: {txt}   (done at {inst.clock(te)} at {le})")
