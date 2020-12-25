from datetime import datetime, timedelta
import argparse
import csv
from collections import Counter
import requests
from typing import Any, Dict, List, Tuple

API_URL = "https://raw.githubusercontent.com/2020PB/police-brutality/data_build/all-locations-v2.json"

DELIM = "||--||"

CITY_POP_FILE = "city_pop.csv"

OUTPUT_FILE = "incidents_per_100k.csv"


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run analysis on 846 police brutality data.")
    parser.add_argument(
        "--min_incidents", type=int, default=10, help="minimum number of incidents for a city to be analyzed"
    )
    parser.add_argument(
        "--min_population",
        type=int,
        default=100000,
        help="minimum population for a city to be analyzed (city proper, not metro)",
    )
    parser.add_argument("--city", type=str, default="Portland", help="city to use for by date analysis")

    return parser


def make_city_state_key(city: str, state: str) -> str:
    return f"{state}{DELIM}{city}"


def get_city_state_from_key(city_state_key: str) -> Tuple[str, str]:
    vals = city_state_key.split(DELIM)
    return vals[0], vals[1]


def get_incidents() -> Dict[str, Any]:
    resp = requests.get(API_URL, headers={"Cache-Control": "no-cache"})
    data = resp.json()["data"]

    o_data = []
    geos = 0
    print(len(data))
    for item in data:
        if item["city"] in {"Hollywood", "Compton"}:
            item["city"] = "Los Angeles"

        if "non-protest" in item.get("tags", []):
            print(f"Skipping non protest indicident {item['id']}")
            continue

        if item.get("geolocation", None):
            geos += 1
        o_data.append(item)

    print(f"Num Geos: {geos}")
    return o_data


def get_city_by_date(data: Dict[str, Any], city: str) -> List[Dict[str, Any]]:
    date_rows: List[str] = []
    for row in data:
        if row["city"].lower() != city.lower():
            continue
        date_rows.append(row["date"])
    date_counter = Counter(date_rows)
    rows = []
    for row_date, row_count in dict(date_counter).items():
        rows.append({"Date": row_date, "Num Incidents": row_count})
    return sorted(rows, key=lambda x: x["Date"])


def write_output_file_for_dates(final_dict: List[Dict[str, Any]], city: str) -> None:
    filename = f"incidents_{city.lower()}_incidents_by_date.csv"

    print(f"Writing results to {filename}")

    with open(filename, "w") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["Date", "Num Incidents"])
        writer.writeheader()
        for row in final_dict:
            writer.writerow(row)


def write_output_file_for_tear_gas_dates(final_dict: List[Dict[str, Any]]) -> None:
    filename = f"tear_gas_incidents_by_date.csv"

    print(f"Writing results to {filename}")

    with open(filename, "w") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["Date", "Num Incidents With Tear Gas"])
        writer.writeheader()
        for row in final_dict:
            writer.writerow(row)


def write_output_file(final_dict: List[Dict[str, Any]], num_incidents: int, min_population: int) -> None:
    filename = f"incidents_per_100k_min_{num_incidents}_incidents_min_{min_population}_pop.csv"

    print(f"Writing results to {filename}")

    with open(filename, "w") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=[
                "State",
                "City",
                "Incidents",
                "Population",
                "Incidents per 100k residents",
            ],
        )
        writer.writeheader()
        for row in final_dict:
            writer.writerow(row)


def get_cities_by_pop() -> Dict[str, int]:
    city_pop_dict: Dict[str, Tuple[int, int]] = {}
    i = 0
    with open(CITY_POP_FILE) as citypopcsv:
        csvreader = csv.reader(citypopcsv)
        for row in csvreader:
            if i == 0:
                i += 1
                continue
            city_pop_dict[make_city_state_key(row[0], row[1])] = int(row[2])

    return city_pop_dict


def make_date_range(start_date: datetime, end_date: datetime) -> Dict[datetime, int]:
    delta = end_date - start_date
    all_days: Dict[datetime, int] = {}
    for i in range(delta.days + 1):
        all_days[start_date + timedelta(days=i)] = 0
    return all_days


def build_final_output(
    incident_counter: Counter, city_pop_dict: Dict[str, int], min_incidents: int, min_population: int
) -> List[Dict[str, Any]]:
    output_list = []
    i = 0
    for city_state_key, num_incidents in dict(incident_counter).items():
        if num_incidents >= min_incidents:
            i += 1

    print(f"Num with enough incidents: {i}")
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
    return sorted(output_list, key=lambda x: x["Incidents"], reverse=True)


def make_date_output(date_range: Dict[datetime, int], incidents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for incident in incidents:
        if incident["date"] == "":
            continue
        incident_date = datetime.strptime(incident["date"], "%Y-%m-%d")
        if incident_date not in date_range:
            continue
        if "tear-gas" in incident["tags"]:
            date_range[incident_date] += 1

    num_with_tear_gas = 0
    num_without_tear_gas = 0
    rows: List[Tuple[str, int]] = []
    for dt, num_tear_gas in date_range.items():
        if num_tear_gas > 0:
            num_with_tear_gas += 1
        else:
            num_without_tear_gas += 1

        rows.append({"Date": dt.strftime("%Y-%m-%d"), "Num Incidents With Tear Gas": num_tear_gas})

    print(f"Num With Tear Gas: {num_with_tear_gas}")
    print(f"Num Without Tear Gas: {num_without_tear_gas}")

    return sorted(rows, key=lambda x: x["Date"])


def main(min_incidents: int, min_population: int, city: str) -> None:
    incidents = get_incidents()

    print(f"Found {len(incidents)} total incidents.")

    incident_counter = Counter([make_city_state_key(incident["state"], incident["city"]) for incident in incidents])

    city_pop_dict = get_cities_by_pop()
    final_dict = build_final_output(incident_counter, city_pop_dict, min_incidents, min_population)

    write_output_file(final_dict, min_incidents, min_population)

    city_dict = get_city_by_date(incidents, city)
    write_output_file_for_dates(city_dict, city)

    start_date = datetime(2020, 5, 28, 0, 0, 0)
    end_date = datetime.now()

    all_dates = make_date_range(start_date, end_date)
    date_output = make_date_output(all_dates, incidents)
    write_output_file_for_tear_gas_dates(date_output)


if __name__ == "__main__":
    parser = init_argparse()
    args = parser.parse_args()
    main(args.min_incidents, args.min_population, args.city)
