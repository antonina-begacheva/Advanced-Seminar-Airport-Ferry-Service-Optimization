
import pandas as pd
import numpy as np
from pathlib import Path

# Reproducible travel times
rng = np.random.default_rng(123)

# Read the previously generated flights
data_folder = Path("data")
data_folder.mkdir(exist_ok=True)

flights = pd.read_csv("data/synthetic_flights.csv")

# Collect all unique airport locations
locations = sorted(
    set(flights["start_location"]) |
    set(flights["end_location"])
)

# Generate a symmetric travel-time matrix
travel_matrix = pd.DataFrame(
    index=locations,
    columns=locations,
    dtype=int
)

for i, location_i in enumerate(locations):
    for j, location_j in enumerate(locations):

        if i == j:
            travel_matrix.loc[location_i, location_j] = 0

        elif j > i:
            travel_time = int(rng.integers(3, 13))

            travel_matrix.loc[location_i, location_j] = travel_time
            travel_matrix.loc[location_j, location_i] = travel_time

# Save the location-to-location matrix
travel_matrix.to_csv(data_folder / "travel_time_matrix.csv")

# --------------------------------------
# Calculate travel times between flights
# --------------------------------------

flight_connections = []

for _, flight_i in flights.iterrows():
    for _, flight_j in flights.iterrows():

        if flight_i["flight_id"] == flight_j["flight_id"]:
            continue

        origin = flight_i["end_location"]
        destination = flight_j["start_location"]

        travel_time = travel_matrix.loc[origin, destination]

        flight_connections.append({
            "flight_i": flight_i["flight_id"],
            "flight_j": flight_j["flight_id"],
            "from_location": origin,
            "to_location": destination,
            "travel_time": int(travel_time)
        })

connections_df = pd.DataFrame(flight_connections)

connections_df.to_csv(
    data_folder / "flight_travel_times.csv",
    index=False
)

print("Travel-time matrix:")
print(travel_matrix)

print("\nExample flight connections:")
print(connections_df.head(10))

print("\nNumber of locations:", len(locations))
print("Number of flight pairs:", len(connections_df))
print("Files saved in the data folder.")
