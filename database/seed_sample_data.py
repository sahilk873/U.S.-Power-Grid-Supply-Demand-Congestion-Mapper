import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from config.settings import settings
from utils.logging_utils import logger


def generate_sample_data(output_dir: str | Path = "data/sample") -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base = datetime(2024, 1, 1)
    hours_2024 = 8784
    random.seed(42)
    np.random.seed(42)

    files = {}

    iso_regions = pd.DataFrame(
        {
            "code": ["PJM", "MISO", "CAISO", "ERCOT", "ISO-NE", "NYISO", "SPP"],
            "name": [
                "PJM Interconnection",
                "Midcontinent Independent System Operator",
                "California Independent System Operator",
                "Electric Reliability Council of Texas",
                "ISO New England",
                "New York Independent System Operator",
                "Southwest Power Pool",
            ],
        }
    )
    iso_regions.to_csv(output_dir / "iso_regions.csv", index=False)
    files["iso_regions"] = str(output_dir / "iso_regions.csv")

    fuel_types = pd.DataFrame(
        {
            "code": [
                "solar",
                "wind",
                "hydro",
                "geothermal",
                "biomass",
                "natural gas",
                "coal",
                "nuclear",
                "oil",
                "other",
            ],
            "name": [
                "Solar",
                "Wind",
                "Hydroelectric",
                "Geothermal",
                "Biomass",
                "Natural Gas",
                "Coal",
                "Nuclear",
                "Petroleum",
                "Other",
            ],
            "category": [
                "renewable",
                "renewable",
                "renewable",
                "renewable",
                "renewable",
                "thermal",
                "thermal",
                "thermal",
                "thermal",
                "other",
            ],
        }
    )
    fuel_types.to_csv(output_dir / "fuel_types.csv", index=False)
    files["fuel_types"] = str(output_dir / "fuel_types.csv")

    balancing_authorities = pd.DataFrame(
        {
            "code": ["PJM", "MISO", "CAISO", "ERCOT", "ISONE", "NYISO", "SPP"],
            "name": [
                "PJM Interconnection LLC",
                "Midcontinent ISO",
                "California ISO",
                "ERCOT ISO",
                "ISO New England",
                "New York ISO",
                "Southwest Power Pool",
            ],
            "iso_region_id": [1, 2, 3, 4, 5, 6, 7],
        }
    )
    balancing_authorities.to_csv(output_dir / "balancing_authorities.csv", index=False)
    files["balancing_authorities"] = str(output_dir / "balancing_authorities.csv")

    plants = []
    plant_fuel = {
        1: "natural gas",
        2: "coal",
        3: "nuclear",
        4: "wind",
        5: "solar",
        6: "hydro",
        7: "natural gas",
        8: "natural gas",
        9: "coal",
        10: "solar",
    }
    plant_ba = {
        1: "PJM",
        2: "PJM",
        3: "PJM",
        4: "MISO",
        5: "CAISO",
        6: "CAISO",
        7: "ERCOT",
        8: "ERCOT",
        9: "MISO",
        10: "CAISO",
    }
    plant_cap = {
        1: 1200,
        2: 2500,
        3: 1800,
        4: 800,
        5: 500,
        6: 600,
        7: 900,
        8: 1500,
        9: 2000,
        10: 300,
    }
    for pid in range(1, 11):
        plants.append(
            {
                "plant_code": 50000 + pid,
                "name": f"Sample Plant {pid}",
                "state": random.choice(["PA", "OH", "CA", "TX", "IL", "NY", "MA"]),
                "balancing_authority_code": plant_ba[pid],
                "primary_fuel_type": plant_fuel[pid],
                "net_summer_capacity_mw": plant_cap[pid],
                "status": "active",
            }
        )
    plants_df = pd.DataFrame(plants)
    plants_df.to_csv(output_dir / "plants.csv", index=False)
    files["plants"] = str(output_dir / "plants.csv")

    generators = []
    for pid in range(1, 11):
        for g in range(random.randint(1, 4)):
            generators.append(
                {
                    "generator_id": f"GEN_{50000 + pid}_{g + 1}",
                    "plant_code": 50000 + pid,
                    "name": f"Gen {g + 1} Plant {pid}",
                    "fuel_type_code": plant_fuel[pid],
                    "capacity_mw": round(plant_cap[pid] / random.randint(1, 4), 1),
                    "status": "active",
                }
            )
    generators_df = pd.DataFrame(generators)
    generators_df.to_csv(output_dir / "generators.csv", index=False)
    files["generators"] = str(output_dir / "generators.csv")

    ba_codes = ["PJM", "MISO", "CAISO", "ERCOT", "ISONE", "NYISO", "SPP"]
    load_records = []
    mix_records = []
    price_records = []
    weather_records = []
    outage_records = []
    spread_records = []

    fuel_type_codes = fuel_types["code"].tolist()
    ba_fuel_mix = {
        "PJM": {
            "coal": 0.30,
            "nuclear": 0.35,
            "natural gas": 0.25,
            "solar": 0.02,
            "wind": 0.05,
            "hydro": 0.03,
        },
        "MISO": {
            "coal": 0.40,
            "natural gas": 0.25,
            "nuclear": 0.10,
            "wind": 0.20,
            "solar": 0.03,
            "hydro": 0.02,
        },
        "CAISO": {
            "natural gas": 0.35,
            "solar": 0.25,
            "hydro": 0.10,
            "wind": 0.10,
            "nuclear": 0.08,
            "geothermal": 0.05,
            "biomass": 0.02,
            "coal": 0.05,
        },
        "ERCOT": {
            "natural gas": 0.45,
            "wind": 0.25,
            "coal": 0.15,
            "solar": 0.10,
            "nuclear": 0.05,
        },
        "ISONE": {
            "natural gas": 0.50,
            "nuclear": 0.20,
            "hydro": 0.10,
            "wind": 0.08,
            "solar": 0.05,
            "coal": 0.07,
        },
        "NYISO": {
            "natural gas": 0.40,
            "nuclear": 0.25,
            "hydro": 0.15,
            "wind": 0.08,
            "solar": 0.05,
            "coal": 0.07,
        },
        "SPP": {
            "wind": 0.40,
            "natural gas": 0.25,
            "coal": 0.25,
            "solar": 0.05,
            "hydro": 0.05,
        },
    }
    ba_base_load = {
        "PJM": 45000,
        "MISO": 35000,
        "CAISO": 28000,
        "ERCOT": 40000,
        "ISONE": 13000,
        "NYISO": 17000,
        "SPP": 15000,
    }

    for h in range(hours_2024):
        dt = base + timedelta(hours=h)
        hour_of_day = dt.hour
        month = dt.month
        is_summer = month in [6, 7, 8]
        is_winter = month in [12, 1, 2]

        for ba_code in ba_codes:
            base_load = ba_base_load[ba_code]
            load_factor = (
                0.6
                + 0.3
                * (
                    1
                    if is_summer and hour_of_day in range(14, 19)
                    else 0.8
                    if is_winter and hour_of_day in range(7, 10)
                    else 0.5
                )
                + 0.1 * random.random()
            )
            load = round(base_load * load_factor)

            is_estimated = random.random() < 0.05

            load_records.append(
                {
                    "balancing_authority_code": ba_code,
                    "interval_start_utc": dt,
                    "interval_end_utc": dt + timedelta(hours=1),
                    "load_mw": load,
                    "is_estimated": is_estimated,
                }
            )

            mix = ba_fuel_mix[ba_code]
            total_gen = load * (1 + random.uniform(-0.02, 0.05))
            for fuel, share in mix.items():
                noise = random.uniform(-0.02, 0.02)
                actual_share = max(0, share + noise)
                gen_mw = round(total_gen * actual_share, 2)
                if gen_mw > 0:
                    mix_records.append(
                        {
                            "balancing_authority_code": ba_code,
                            "interval_start_utc": dt,
                            "interval_end_utc": dt + timedelta(hours=1),
                            "fuel_type_code": fuel,
                            "generation_mw": gen_mw,
                            "is_estimated": is_estimated,
                        }
                    )

            base_price = 30 + 10 * np.sin(2 * np.pi * hour_of_day / 24)
            if is_summer:
                base_price += 15 + 10 * random.random()
            if load > base_load * 0.9:
                base_price += 20 * random.random()

            congestion = max(0, base_price * 0.1 * random.random())
            if load > base_load * 0.95:
                congestion += 15 * random.random()

            price_records.append(
                {
                    "balancing_authority_code": ba_code,
                    "interval_start_utc": dt,
                    "interval_end_utc": dt + timedelta(hours=1),
                    "lmp_price_usd_per_mwh": round(base_price + congestion, 2),
                    "energy_component": round(base_price, 2),
                    "congestion_component": round(congestion, 2),
                    "loss_component": round(base_price * 0.02, 2),
                    "is_estimated": is_estimated,
                }
            )

            region_base_temp = {
                "PJM": 12,
                "MISO": 10,
                "CAISO": 18,
                "ERCOT": 20,
                "ISONE": 8,
                "NYISO": 10,
                "SPP": 14,
            }
            temp = (
                region_base_temp[ba_code]
                + 10 * np.sin(2 * np.pi * (month - 1) / 12)
                + random.uniform(-5, 5)
            )
            is_extreme = temp > 38 or temp < -15 or random.random() < 0.02
            weather_records.append(
                {
                    "balancing_authority_code": ba_code,
                    "interval_start_utc": dt,
                    "interval_end_utc": dt + timedelta(hours=1),
                    "temperature_c": round(temp, 1),
                    "humidity_pct": round(50 + 20 * random.random(), 1),
                    "wind_speed_ms": round(random.uniform(1, 15), 1),
                    "precipitation_mm": round(random.uniform(0, 5), 1),
                    "is_extreme": is_extreme,
                }
            )

        if random.random() < 0.02:
            ba_code = random.choice(ba_codes)
            outage_records.append(
                {
                    "generator_id": f"GEN_{50000 + random.randint(1, 10)}_{random.randint(1, 3)}",
                    "balancing_authority_code": ba_code,
                    "outage_start_utc": dt,
                    "outage_end_utc": dt + timedelta(hours=random.randint(1, 24)),
                    "outage_type": random.choice(["planned", "forced", "maintenance"]),
                    "capacity_affected_mw": round(random.uniform(50, 500), 1),
                }
            )

    pd.DataFrame(load_records).to_csv(output_dir / "hourly_load.csv", index=False)
    files["hourly_load"] = str(output_dir / "hourly_load.csv")

    pd.DataFrame(mix_records).to_csv(output_dir / "generation_mix.csv", index=False)
    files["generation_mix"] = str(output_dir / "generation_mix.csv")

    pd.DataFrame(price_records).to_csv(output_dir / "prices.csv", index=False)
    files["prices"] = str(output_dir / "prices.csv")

    pd.DataFrame(weather_records).to_csv(output_dir / "weather.csv", index=False)
    files["weather"] = str(output_dir / "weather.csv")

    pd.DataFrame(outage_records).to_csv(output_dir / "outages.csv", index=False)
    files["outages"] = str(output_dir / "outages.csv")

    hubs = [
        "AEP",
        "PJM_WEST",
        "PJM_EAST",
        "MISO_IL",
        "MISO_IN",
        "NP15",
        "SP15",
        "ZON_1",
        "ZON_2",
        "ZON_3",
        "ERCOT_HB_NORTH",
        "ERCOT_HB_SOUTH",
        "MAINE",
        "BOSTON",
    ]
    hub_records = []
    for hc, hub_name in enumerate(hubs[:14], 1):
        hub_records.append(
            {
                "name": hub_name,
                "code": hub_name,
                "iso_region_id": hc % 7 + 1,
            }
        )
    pd.DataFrame(hub_records).to_csv(output_dir / "hubs.csv", index=False)
    files["hubs"] = str(output_dir / "hubs.csv")

    zones_records = []
    for z in range(1, 21):
        zones_records.append(
            {
                "name": f"Zone_{z}",
                "code": f"Z{z:02d}",
                "iso_region_id": z % 7 + 1,
            }
        )
    pd.DataFrame(zones_records).to_csv(output_dir / "load_zones.csv", index=False)
    files["load_zones"] = str(output_dir / "load_zones.csv")

    for h in range(min(hours_2024, 1000)):
        dt = base + timedelta(hours=h)
        for i in range(len(hubs) - 1):
            spread_records.append(
                {
                    "interval_start_utc": dt,
                    "interval_end_utc": dt + timedelta(hours=1),
                    "hub_from_code": hubs[i],
                    "hub_to_code": hubs[i + 1],
                    "spread_usd_per_mwh": round(random.uniform(-10, 25), 2),
                    "spread_type": "hub_to_hub",
                }
            )
    pd.DataFrame(spread_records).to_csv(output_dir / "price_spreads.csv", index=False)
    files["price_spreads"] = str(output_dir / "price_spreads.csv")

    logger.info("Sample data generated in %s: %s", output_dir, files)
    return files


if __name__ == "__main__":
    generate_sample_data()
