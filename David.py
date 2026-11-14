"""
Model II (min-cost flow on capacity network G1) from Han, Zhao, Kong (2023), Section 2.2.

Nodes:  source "s", sink "t", and for every flight i and every possible start minute k = 0..L_i-E_i
        a start node ("p", i, k) and an end node ("d", i, k).
Arcs:   Dispatch  s -> p(i,k)           capacity q_i, cost +1
        Service   p(i,k) -> d(i,k)      capacity q_i, cost -2
        Transfer  d(i,h) -> p(j,k)      capacity q_i, cost 0   if E_i+h+dur_i+t_ij <= E_j+k
        Return    d(i,k) -> t           capacity q_i, cost 0
        Virtual   s -> t                capacity |V|, cost 0
Additional constraint (22): the sum of the service arcs of a flight is <= q_i.
"""
from collections import namedtuple

import gurobipy as gp
from gurobipy import GRB

from generator import generate, describe

Arc = namedtuple("Arc", "u v cap cost kind flight k")


def build_arcs(inst, n_vehicles):
    arcs = []
    for f in inst.flights:
        for k in range(f.L - f.E + 1):
            arcs.append(Arc("s", ("p", f.i, k), f.q, 1, "dispatch", f.i, k))
            arcs.append(Arc(("p", f.i, k), ("d", f.i, k), f.q, -2, "service", f.i, k))
            arcs.append(Arc(("d", f.i, k), "t", f.q, 0, "return", f.i, k))
    for fi in inst.flights:
        for fj in inst.flights:
            if fi.i == fj.i:  # a ferry does not serve the same flight twice
                continue
            tij = inst.travel(fi, fj)
            for h in range(fi.L - fi.E + 1):
                for k in range(fj.L - fj.E + 1):
                    if fi.E + h + fi.dur + tij <= fj.E + k:
                        arcs.append(Arc(("d", fi.i, h), ("p", fj.i, k), fi.q, 0, "transfer", None, None))
    arcs.append(Arc("s", "t", n_vehicles, 0, "virtual", None, None))
    return arcs


def solve_model2(inst, n_vehicles, verbose=False):
    arcs = build_arcs(inst, n_vehicles)
    m = gp.Model("model2")
    m.Params.OutputFlag = 1 if verbose else 0
    x = [m.addVar(lb=0, ub=a.cap, vtype=GRB.INTEGER) for a in arcs]

    out_arcs, in_arcs = {}, {}
    for idx, a in enumerate(arcs):
        out_arcs.setdefault(a.u, []).append(idx)
        in_arcs.setdefault(a.v, []).append(idx)

    # Objective (20)
    m.setObjective(gp.quicksum(a.cost * x[i] for i, a in enumerate(arcs)), GRB.MINIMIZE)

    # Flow balance (21)
    nodes = set(out_arcs) | set(in_arcs)
    for n in nodes:
        sup = n_vehicles if n == "s" else (-n_vehicles if n == "t" else 0)
        m.addConstr(gp.quicksum(x[i] for i in out_arcs.get(n, []))
                    - gp.quicksum(x[i] for i in in_arcs.get(n, [])) == sup)

    # Additional constraint (22): at most q_i flow over the service arcs of each flight
    for f in inst.flights:
        m.addConstr(gp.quicksum(x[i] for i, a in enumerate(arcs)
                                if a.kind == "service" and a.flight == f.i) <= f.q)

    m.optimize()
    if m.Status != GRB.OPTIMAL:
        raise RuntimeError(f"Gurobi status {m.Status}")

    flow = {i: round(x[i].X) for i in range(len(arcs))}
    served = {f.i: 0 for f in inst.flights}
    dispatched = 0
    for i, a in enumerate(arcs):
        if a.kind == "service":
            served[a.flight] += flow[i]
        elif a.kind == "dispatch":
            dispatched += flow[i]
    routes = decompose(arcs, flow, out_arcs, inst)
    return {
        "objective": round(m.ObjVal),
        "served": served,                       # served virtual flights per flight
        "n_served": sum(served.values()),
        "unserved": {f.i: f.q - served[f.i] for f in inst.flights if f.q > served[f.i]},
        "dispatched": dispatched,
        "routes": routes,                       # list of routes: [(flight_i, start_minute), ...]
        "runtime": m.Runtime,
    }


def decompose(arcs, flow, out_arcs, inst):
    """Splits the integer flow into single ferry routes (the network is acyclic)."""
    rem = dict(flow)
    flights = {f.i: f for f in inst.flights}
    routes = []
    for first in out_arcs["s"]:
        if arcs[first].kind != "dispatch":
            continue
        while rem[first] > 0:
            rem[first] -= 1
            node, route = arcs[first].v, []
            while node != "t":
                nxt = next(i for i in out_arcs[node] if rem[i] > 0)
                rem[nxt] -= 1
                a = arcs[nxt]
                if a.kind == "service":
                    route.append((a.flight, flights[a.flight].E + a.k))
                node = a.v
            routes.append(route)
    return routes


def check_solution(inst, res, n_vehicles):
    """Independent check of the routes against the original rules (time windows, travel times, q_i)."""
    flights = {f.i: f for f in inst.flights}
    assert len(res["routes"]) <= n_vehicles, "more ferries than allowed"
    count = {i: 0 for i in flights}
    for r in res["routes"]:
        assert len({i for i, _ in r}) == len(r), "flight appears twice in one route"
        for i, s in r:
            f = flights[i]
            assert f.E <= s <= f.L, f"start time outside the window for flight {i}"
            count[i] += 1
        for (i, si), (j, sj) in zip(r, r[1:]):
            fi, fj = flights[i], flights[j]
            assert si + fi.dur + inst.travel(fi, fj) <= sj, f"time conflict {i}->{j}"
    for i, f in flights.items():
        assert count[i] <= f.q, f"flight {i} served too often"
        assert count[i] == res["served"][i], "route and flow do not match"
    return True


def end_state(inst, route):
    """End time T^E_v and end location L^E_v of a ferry (needed for stage 2)."""
    flights = {f.i: f for f in inst.flights}
    i, s = route[-1]
    return s + flights[i].dur, flights[i].d


def min_fleet(inst):
    big = sum(f.q for f in inst.flights)
    return solve_model2(inst, big)["dispatched"]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--flights", type=int, default=12)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--share", type=float, default=0.55,
                    help="Fleet size as a share of the minimum fleet (paper: 48/88 = 0.55)")
    args = ap.parse_args()

    inst = generate(args.flights, args.seed)
    describe(inst)

    mf = min_fleet(inst)
    V = max(1, round(args.share * mf))
    print(f"\nMinimum fleet to serve all flights: {mf}  ->  fleet used |V| = {V}")

    res = solve_model2(inst, V)
    check_solution(inst, res, V)
    total = sum(f.q for f in inst.flights)
    print(f"Objective value: {res['objective']}  (runtime {res['runtime']:.2f} s)")
    print(f"Served virtual flights: {res['n_served']} of {total}, ferries used: {res['dispatched']}")
    print(f"Flights not served on time (flight: count): {res['unserved']}")
    print("\nRoutes (flight@start time):")
    for n, r in enumerate(res["routes"], start=1):
        te, le = end_state(inst, r)
        txt = " -> ".join(f"{i}@{inst.clock(s)}" for i, s in r)
        print(f"  Ferry {n}: {txt}   (done at {inst.clock(te)} at {le})")

    print("\nCheck: more ferries must serve at least as many flights")
    prev = -1
    for v in range(0, mf + 1):
        r = solve_model2(inst, v)
        check_solution(inst, r, v)
        print(f"  |V| = {v:>2}: served virtual flights = {r['n_served']:>3}, unserved flights = {sum(r['unserved'].values()):>3}")
        assert r["n_served"] >= prev
        prev = r["n_served"]
    print("All checks passed.")
