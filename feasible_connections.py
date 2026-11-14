
import pandas as pd

flights = pd.read_csv("data/synthetic_flights.csv")
travel = pd.read_csv("data/flight_travel_times.csv")

feasible_connections = []

for _, connection in travel.iterrows():

    flight_i = flights[
        flights["flight_id"] == connection["flight_i"]
    ].iloc[0]

    flight_j = flights[
        flights["flight_id"] == connection["flight_j"]
    ].iloc[0]

    # Earliest possible completion of flight i,
    # followed by travel to flight j
    earliest_available = (
        flight_i["earliest_start"]
        + flight_i["duration"]
        + connection["travel_time"]
    )

    # Is there enough time to start flight j
    # within its permitted service window?
    if earliest_available <= flight_j["latest_start"]:

        feasible_connections.append({
            "flight_i": connection["flight_i"],
            "flight_j": connection["flight_j"],
            "travel_time": connection["travel_time"],
            "earliest_available": earliest_available,
            "latest_start_j": flight_j["latest_start"]
        })

result = pd.DataFrame(feasible_connections)

result.to_csv(
    "data/feasible_connections.csv",
    index=False
)

print("Number of feasible connections:", len(result))
print(result.head(10))
