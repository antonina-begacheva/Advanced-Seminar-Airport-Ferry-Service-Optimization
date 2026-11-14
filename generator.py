"""
Instance generator v1 for the ferry problem (Han, Zhao, Kong 2023, EJOR 307).

All times are whole minutes. The earliest value (smallest E_i) is shifted to 0,
as Model II requires (non-negative integers).

VALUES FROM THE PAPERS (reliable):
  - Q_i per aircraft type (Omega 2021 / Annals 2020)
  - Time window offsets T1..T4 and waiting times T5, T6 (Table 3 Omega, Table 4 Annals)
  - Travel time matrix (Table 7 Annals / Table 6 Omega)
  - theta values (Table 7 EJOR 2023) for alpha1 = 0.6 and alpha2 = 0.7

OWN ASSUMPTIONS (NOT stated in the papers, please justify/change later):
  - Distribution of aircraft types (chosen so that the mean of Q_i is about 2.55,
    as in the example day: 253 virtual / 99 real flights)
  - Uniform distribution of flights over the 7 aprons
  - 2 minutes for passengers to get off (derived backwards from the durations in Table 6)
  - Time profile of the flight times (triangular distribution with its peak towards the end)
  - Share of arrivals 76 % (example day: 75 of 99)
"""
import random
from dataclasses import dataclass, field

# ----------------------------------------------------------- values from the papers
LOCATIONS = ["A2", "A6", "A7", "A8", "N1", "W1", "W2", "T"]  # T = terminal
_UPPER = {  # upper half of the travel time matrix in minutes
    "A2": [0, 11, 6, 5, 10, 8, 6, 13],
    "A6": [None, 0, 6, 13, 18, 16, 11, 17],
    "A7": [None, None, 0, 9, 14, 12, 8, 14],
    "A8": [None, None, None, 0, 7, 5, 6, 11],
    "N1": [None, None, None, None, 0, 6, 11, 19],
    "W1": [None, None, None, None, None, 0, 7, 15],
    "W2": [None, None, None, None, None, None, 0, 11],
    "T":  [None, None, None, None, None, None, None, 0],
}
TRAVEL = {}
for a in LOCATIONS:
    for j, b in enumerate(LOCATIONS):
        v = _UPPER[a][j]
        if v is not None:
            TRAVEL[(a, b)] = v
            TRAVEL[(b, a)] = v  # completed symmetrically (the paper only shows one half)

TYPE_Q = {"B": 2, "C": 2, "D": 3, "E": 4, "F": 5}
WAIT = {"A": 35, "D": 20}      # T5 (arrival) or T6 (departure), first ferry
WINDOW = {"A": (20, 10), "D": (60, 40)}  # (T1,T2) or (T3,T4): e = time - T1, l = time - T2
THETA = {"A": (-3, -13), "D": (30, 14)}  # (theta1,theta2) for alpha1=0.6, (theta3,theta4) for alpha2=0.7
DROP = 2                        # time for passengers to get off (derived, see above)

# ------------------------------------------------------------------- own assumptions
TYPE_PROB = {"B": 0.30, "C": 0.35, "D": 0.20, "E": 0.10, "F": 0.05}
APRONS = ["A2", "A6", "A7", "A8", "N1", "W1", "W2"]
P_ARRIVAL = 0.76
HORIZON = 240  # minutes after 21:00 (evening peak 21:00-01:00)


@dataclass
class Flight:
    i: int
    kind: str      # "A" arrival, "D" departure
    typ: str
    q: int         # number of ferries required
    apron: str
    sched: int     # STA/STD in minutes after 21:00
    p: str         # start location of the ferry trip
    d: str         # end location
    E: int         # earliest start (incl. theta, shifted)
    L: int         # latest start (incl. theta, shifted)
    dur: int       # duration of the ferry trip


@dataclass
class Instance:
    flights: list
    shift: int = 0   # time t on the model axis corresponds to base + t + shift (minutes since midnight)
    meta: dict = field(default_factory=dict)
    table: dict = None   # own travel time table {(from, to): minutes}; None = table from the papers
    base: int = 21 * 60  # clock time (minute of the day) that shift refers to

    def travel(self, fi, fj):
        """Travel time from d_i to p_j."""
        return (self.table if self.table is not None else TRAVEL)[(fi.d, fj.p)]

    def clock(self, t):
        m = (self.base + t + self.shift) % (24 * 60)
        return f"{m // 60:02d}:{m % 60:02d}"


def generate(n_flights=12, seed=1, p_arrival=P_ARRIVAL):
    rnd = random.Random(seed)
    types, weights = list(TYPE_PROB), list(TYPE_PROB.values())
    raw = []
    for _ in range(n_flights):
        kind = "A" if rnd.random() < p_arrival else "D"
        typ = rnd.choices(types, weights)[0]
        apron = rnd.choice(APRONS)
        sched = 5 * round(rnd.triangular(0, HORIZON, 180) / 5)
        t1, t2 = WINDOW[kind]
        th1, th2 = THETA[kind]
        e, l = sched - t1, sched - t2
        E, L = e + th1, l + th2
        if L < E:
            raise ValueError("Time window is empty: theta does not match the window width")
        p, d = (apron, "T") if kind == "A" else ("T", apron)
        dur = WAIT[kind] + TRAVEL[(apron, "T")] + DROP
        raw.append((E, L, kind, typ, apron, sched, p, d, dur))
    raw.sort()
    shift = raw[0][0]
    flights = []
    for idx, (E, L, kind, typ, apron, sched, p, d, dur) in enumerate(raw, start=1):
        flights.append(Flight(idx, kind, typ, TYPE_Q[typ], apron, sched, p, d,
                              E - shift, L - shift, dur))
    return Instance(flights, shift, {"seed": seed, "n_flights": n_flights})


def describe(inst):
    print(f"{'i':>3} {'Kind':>4} {'Typ':>3} {'q':>2} {'Apron':>5} {'E':>5} {'L':>5} {'dur':>4}   Window (clock)")
    for f in inst.flights:
        print(f"{f.i:>3} {f.kind:>4} {f.typ:>3} {f.q:>2} {f.apron:>5} {f.E:>5} {f.L:>5} {f.dur:>4}   "
              f"{inst.clock(f.E)} - {inst.clock(f.L)}")
    print(f"Real flights: {len(inst.flights)}, virtual flights: {sum(f.q for f in inst.flights)}")


if __name__ == "__main__":
    describe(generate())