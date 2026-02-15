import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    EIA_API_KEY = os.getenv("EIA_API_KEY", "")
    NOAA_API_KEY = os.getenv("NOAA_API_KEY", "")
    RAW_DATA_DIR = os.getenv("RAW_DATA_DIR", "data/raw")
    PROCESSED_DATA_DIR = os.getenv("PROCESSED_DATA_DIR", "data/processed")
    SAMPLE_DATA_DIR = os.getenv("SAMPLE_DATA_DIR", "data/sample")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # Fuel categories mapped to standardized groups
    RENEWABLE_FUELS = {
        "solar",
        "photovoltaic",
        "solar thermal",
        "wind",
        "onshore wind",
        "offshore wind",
        "hydro",
        "hydroelectric",
        "geothermal",
        "biomass",
        "biogenic",
        "municipal solid waste (biogenic)",
        "landfill gas",
        "other renewable",
        "renewable",
        "hydroelectric pumped storage",
    }

    THERMAL_FUELS = {
        "coal",
        "bituminous coal",
        "subbituminous coal",
        "lignite",
        "waste coal",
        "coal-derived syngas",
        "natural gas",
        "natural gas (combined cycle)",
        "natural gas (combustion turbine)",
        "natural gas (steam)",
        "natural gas fired",
        "oil",
        "petroleum",
        "distillate fuel oil",
        "residual fuel oil",
        "jet fuel",
        "petroleum coke",
        "diesel",
        "nuclear",
        "uranium",
    }

    # Map common naming variations to canonical names
    BA_ALIASES = {
        "pjm": "PJM",
        "pjm interconnection": "PJM",
        "pjm interconnection llc": "PJM",
        "miso": "MISO",
        "midcontinent iso": "MISO",
        "midcontinent independent system operator": "MISO",
        "caiso": "CAISO",
        "caiso - california iso": "CAISO",
        "california iso": "CAISO",
        "california independent system operator": "CAISO",
        "ercot": "ERCOT",
        "electric reliability council of texas": "ERCOT",
        "isone": "ISO-NE",
        "iso new england": "ISO-NE",
        "nyiso": "NYISO",
        "new york iso": "NYISO",
        "new york independent system operator": "NYISO",
        "spp": "SPP",
        "southwest power pool": "SPP",
    }

    ISO_REGIONS = {
        "PJM": "PJM Interconnection",
        "MISO": "Midcontinent Independent System Operator",
        "CAISO": "California Independent System Operator",
        "ERCOT": "Electric Reliability Council of Texas",
        "ISO-NE": "ISO New England",
        "NYISO": "New York Independent System Operator",
        "SPP": "Southwest Power Pool",
    }


settings = Settings()
