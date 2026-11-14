# Generating Instances
import numpy as np
import pandas as pd

# Reproducibility: same seed = same instance
rng = np.random.default_rng(42)

# -----------------------------
# 1. General instance settings
# -----------------------------

N_FLIGHTS = 30
N_STANDS = 8
N_TERMINALS = 2

# Morning peak: 06:00–10:00
START_TIME = 6 * 60
END_TIME = 10 * 60

# Initial fleet size
N_VEHICLES = 5

# Illustrative assumptions (not empirical values)
ARRIVAL_DEVIATIONS = [-10, -5, 0, 5, 10, 15]
DEPARTURE_DEVIATIONS = [-5, 0, 5, 10, 15, 20]

# -----------------------------
# 2. Generate flight data
# -----------------------------

flights = []

for i in range(N_FLIGHTS):

    flight_type = rng.choice(["arrival", "departure"])

    scheduled_time = int(
        rng.integers(START_TIME, END_TIME)
    )

    stand = int(rng.integers(1, N_STANDS + 1))
    terminal = int(rng.integers(1, N_TERMINALS + 1))

    # Arrival: stand -> terminal
    # Departure: terminal -> stand
    if flight_type == "arrival":
        start_location = f"Stand_{stand}"
        end_location = f"Terminal_{terminal}"

        deviation = int(
            rng.choice(ARRIVAL_DEVIATIONS)
        )

    else:
        start_location = f"Terminal_{terminal}"
        end_location = f"Stand_{stand}"

        deviation = int(
            rng.choice(DEPARTURE_DEVIATIONS)
        )

    actual_time = scheduled_time + deviation

    # Initial assumptions for service requirements
    q_i = int(rng.integers(1, 3))
    duration = int(rng.integers(15, 31))

    # Initial service window around scheduled time
    earliest_start = scheduled_time - 15
    latest_start = scheduled_time + 15

    flights.append({
        "flight_id": f"F{i+1:03d}",
        "flight_type": flight_type,
        "scheduled_time": scheduled_time,
        "actual_time": actual_time,
        "deviation": deviation,
        "start_location": start_location,
        "end_location": end_location,
        "q_i": q_i,
        "earliest_start": earliest_start,
        "latest_start": latest_start,
        "duration": duration
    })

# -----------------------------
# 3. Create a DataFrame
# -----------------------------

df = pd.DataFrame(flights)

# Sort flights chronologically
df = df.sort_values("scheduled_time")

# -----------------------------
# 4. Save the instance
# -----------------------------

df.to_csv("synthetic_flights.csv", index=False)

print(df.head(10))
print("\nNumber of flights:", len(df))
print("Number of vehicles:", N_VEHICLES)
print("\nFile saved as synthetic_flights.csv")

