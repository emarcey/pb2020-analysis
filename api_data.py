import csv
from collections import Counter
import requests

API_URL = "https://api.846policebrutality.com/api/incidents"

DELIM = "||--||"

CITY_POP_FILE = "city_pop.csv"

OUTPUT_FILE = "incidents_per_100k.csv"


def make_city_state_key(city, state):
    return f"{state}{DELIM}{city}"


def get_city_state_from_key(city_state_key):
    vals = city_state_key.split(DELIM)
    return vals[0], vals[1]


def get_incidents():
    resp = requests.get(API_URL)
    data = resp.json()["data"]

    for item in data:
        if item["city"] in {"Hollywood", "Compton", "Huntington Beach"}:
            item["city"] = "Los Angeles"
    return data


def get_cities_by_pop():
    city_pop_dict = {}
    i = 0
    with open(CITY_POP_FILE) as citypopcsv:
        csvreader = csv.reader(citypopcsv)
        for row in csvreader:
            if i == 0:
                i += 1
                continue
            city_pop_dict[make_city_state_key(row[0], row[1])] = int(row[2])

    return city_pop_dict


def build_final_output(incident_counter, city_pop_dict, min_incidents, min_population):
    output_list = []
    for city_state_key, num_incidents in dict(incident_counter).items():
        if "Unknown" in city_state_key or num_incidents < min_incidents:
            continue
        city_population = city_pop_dict[city_state_key]
        city, state = get_city_state_from_key(city_state_key)
        if city_population < min_population:
            continue
        output_list.append(
            {
                "City": city,
                "State": state,
                "Incidents": num_incidents,
                "Population": city_population,
                "Incidents per 100k residents": round(num_incidents / (city_population / 100000), 5),
            }
        )
    return sorted(output_list, key=lambda x: x["Incidents per 100k residents"], reverse=True)


def main(min_incidents: int = 10, min_population: int = 100000):
    incidents = get_incidents()

    print(len(incidents))

    incident_counter = Counter([make_city_state_key(incident["state"], incident["city"]) for incident in incidents])

    print(incident_counter.most_common(10))

    city_pop_dict = get_cities_by_pop()
    final_dict = build_final_output(incident_counter, city_pop_dict, min_incidents, min_population)
    print(final_dict)
    print(len(final_dict))

    with open(OUTPUT_FILE, "w") as csvfile:
        writer = csv.DictWriter(
            csvfile, fieldnames=["State", "City", "Incidents", "Population", "Incidents per 100k residents"]
        )
        writer.writeheader()
        for data in final_dict:
            writer.writerow(data)


if __name__ == "__main__":
    main()
