-- ============================================================================
-- Power Grid Supply-Demand-Congestion Mapper — MySQL Schema
-- ============================================================================
-- This schema models the U.S. power grid as a set of related entities:
--   generators, plants, fuel types, balancing authorities, ISO/RTO regions,
--   load zones, hubs, nodes, transmission regions, hourly demand,
--   generation mix, outages, prices, spreads, and weather.
-- ============================================================================

CREATE DATABASE IF NOT EXISTS power_grid_mapper
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE power_grid_mapper;

-- ---------------------------------------------------------------------------
-- 1. Reference / Lookup tables (loaded first, no FK dependencies)
-- ---------------------------------------------------------------------------

CREATE TABLE iso_regions (
    id              INT             AUTO_INCREMENT PRIMARY KEY,
    code            VARCHAR(10)     NOT NULL UNIQUE,
    name            VARCHAR(128)    NOT NULL,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE fuel_types (
    id              INT             AUTO_INCREMENT PRIMARY KEY,
    code            VARCHAR(40)     NOT NULL UNIQUE,
    name            VARCHAR(128)    NOT NULL,
    category        ENUM('renewable','thermal','other','storage','hybrid') NOT NULL,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE balancing_authorities (
    id              INT             AUTO_INCREMENT PRIMARY KEY,
    code            VARCHAR(10)     NOT NULL UNIQUE,
    name            VARCHAR(256)    NOT NULL,
    iso_region_id   INT             DEFAULT NULL,
    is_iso          BOOLEAN         NOT NULL DEFAULT FALSE,
    timezone        VARCHAR(40)     DEFAULT NULL,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (iso_region_id) REFERENCES iso_regions(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE transmission_regions (
    id              INT             AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(128)    NOT NULL,
    iso_region_id   INT             DEFAULT NULL,
    description     TEXT            DEFAULT NULL,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (iso_region_id) REFERENCES iso_regions(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------------
-- 2. Asset tables
-- ---------------------------------------------------------------------------

CREATE TABLE plants (
    id                      INT             AUTO_INCREMENT PRIMARY KEY,
    plant_code              INT             NOT NULL UNIQUE,
    name                    VARCHAR(256)    NOT NULL,
    street_address          VARCHAR(256)    DEFAULT NULL,
    city                    VARCHAR(128)    DEFAULT NULL,
    county                  VARCHAR(128)    DEFAULT NULL,
    state                   CHAR(2)         DEFAULT NULL,
    zip                     VARCHAR(10)     DEFAULT NULL,
    latitude                DECIMAL(10,7)   DEFAULT NULL,
    longitude               DECIMAL(10,7)   DEFAULT NULL,
    balancing_authority_id  INT             DEFAULT NULL,
    iso_region_id           INT             DEFAULT NULL,
    transmission_region_id  INT             DEFAULT NULL,
    primary_fuel_type_id    INT             DEFAULT NULL,
    prime_mover            VARCHAR(20)     DEFAULT NULL,
    status                  ENUM('active','retired','planned','standby','other') DEFAULT 'active',
    net_summer_capacity_mw  DECIMAL(12,4)   DEFAULT NULL,
    net_winter_capacity_mw  DECIMAL(12,4)   DEFAULT NULL,
    commercial_online_date  DATE            DEFAULT NULL,
    retirement_date         DATE            DEFAULT NULL,
    created_at              TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (balancing_authority_id) REFERENCES balancing_authorities(id) ON DELETE SET NULL,
    FOREIGN KEY (iso_region_id)           REFERENCES iso_regions(id)           ON DELETE SET NULL,
    FOREIGN KEY (transmission_region_id)  REFERENCES transmission_regions(id)  ON DELETE SET NULL,
    FOREIGN KEY (primary_fuel_type_id)    REFERENCES fuel_types(id)            ON DELETE SET NULL,
    INDEX idx_plants_state (state),
    INDEX idx_plants_ba (balancing_authority_id),
    INDEX idx_plants_iso (iso_region_id),
    INDEX idx_plants_status (status)
) ENGINE=InnoDB;

CREATE TABLE generators (
    id                  INT             AUTO_INCREMENT PRIMARY KEY,
    generator_id        VARCHAR(64)     NOT NULL,
    plant_id            INT             NOT NULL,
    unit_code           VARCHAR(32)     DEFAULT NULL,
    name                VARCHAR(256)    DEFAULT NULL,
    fuel_type_id        INT             DEFAULT NULL,
    prime_mover         VARCHAR(20)     DEFAULT NULL,
    status              ENUM('active','retired','planned','standby','other') DEFAULT 'active',
    capacity_mw         DECIMAL(12,4)   DEFAULT NULL,
    summer_capacity_mw  DECIMAL(12,4)   DEFAULT NULL,
    winter_capacity_mw  DECIMAL(12,4)   DEFAULT NULL,
    commercial_online_date DATE         DEFAULT NULL,
    retirement_date     DATE            DEFAULT NULL,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (plant_id)     REFERENCES plants(id)    ON DELETE CASCADE,
    FOREIGN KEY (fuel_type_id) REFERENCES fuel_types(id) ON DELETE SET NULL,
    INDEX idx_generators_plant (plant_id),
    INDEX idx_generators_fuel (fuel_type_id),
    INDEX idx_generators_status (status)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------------
-- 3. Market topology tables
-- ---------------------------------------------------------------------------

CREATE TABLE load_zones (
    id              INT             AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(128)    NOT NULL,
    code            VARCHAR(40)     DEFAULT NULL,
    iso_region_id   INT             DEFAULT NULL,
    balancing_authority_id INT      DEFAULT NULL,
    peak_load_mw    DECIMAL(12,4)   DEFAULT NULL,
    FOREIGN KEY (iso_region_id)           REFERENCES iso_regions(id)           ON DELETE SET NULL,
    FOREIGN KEY (balancing_authority_id)  REFERENCES balancing_authorities(id) ON DELETE SET NULL,
    INDEX idx_zones_iso (iso_region_id)
) ENGINE=InnoDB;

CREATE TABLE hubs (
    id              INT             AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(128)    NOT NULL,
    code            VARCHAR(40)     DEFAULT NULL,
    iso_region_id   INT             DEFAULT NULL,
    node_id         VARCHAR(64)     DEFAULT NULL,
    FOREIGN KEY (iso_region_id) REFERENCES iso_regions(id) ON DELETE SET NULL,
    INDEX idx_hubs_iso (iso_region_id)
) ENGINE=InnoDB;

CREATE TABLE nodes (
    id              INT             AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(128)    NOT NULL,
    code            VARCHAR(64)     DEFAULT NULL UNIQUE,
    iso_region_id   INT             DEFAULT NULL,
    load_zone_id    INT             DEFAULT NULL,
    hub_id          INT             DEFAULT NULL,
    voltage_kv      INT             DEFAULT NULL,
    latitude        DECIMAL(10,7)   DEFAULT NULL,
    longitude       DECIMAL(10,7)   DEFAULT NULL,
    FOREIGN KEY (iso_region_id) REFERENCES iso_regions(id) ON DELETE SET NULL,
    FOREIGN KEY (load_zone_id)  REFERENCES load_zones(id)  ON DELETE SET NULL,
    FOREIGN KEY (hub_id)        REFERENCES hubs(id)        ON DELETE SET NULL,
    INDEX idx_nodes_iso (iso_region_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------------
-- 4. Time-series data tables
-- ---------------------------------------------------------------------------

CREATE TABLE hourly_load (
    id                      BIGINT      AUTO_INCREMENT PRIMARY KEY,
    balancing_authority_id  INT         NOT NULL,
    interval_start_utc      DATETIME    NOT NULL,
    interval_end_utc        DATETIME    NOT NULL,
    load_mw                 DECIMAL(12,4) NOT NULL,
    load_percentile         DECIMAL(5,4) DEFAULT NULL,
    is_estimated            BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (balancing_authority_id) REFERENCES balancing_authorities(id) ON DELETE CASCADE,
    UNIQUE KEY uq_hourly_load (balancing_authority_id, interval_start_utc),
    INDEX idx_load_ba_time (balancing_authority_id, interval_start_utc),
    INDEX idx_load_time (interval_start_utc)
) ENGINE=InnoDB;

CREATE TABLE generation_mix (
    id                      BIGINT      AUTO_INCREMENT PRIMARY KEY,
    balancing_authority_id  INT         NOT NULL,
    interval_start_utc      DATETIME    NOT NULL,
    interval_end_utc        DATETIME    NOT NULL,
    fuel_type_id            INT         NOT NULL,
    generation_mw           DECIMAL(12,4) NOT NULL,
    is_estimated            BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (balancing_authority_id) REFERENCES balancing_authorities(id) ON DELETE CASCADE,
    FOREIGN KEY (fuel_type_id)           REFERENCES fuel_types(id)            ON DELETE CASCADE,
    UNIQUE KEY uq_genmix (balancing_authority_id, interval_start_utc, fuel_type_id),
    INDEX idx_genmix_ba_time (balancing_authority_id, interval_start_utc),
    INDEX idx_genmix_fuel (fuel_type_id)
) ENGINE=InnoDB;

CREATE TABLE prices (
    id                      BIGINT      AUTO_INCREMENT PRIMARY KEY,
    node_id                 INT         DEFAULT NULL,
    hub_id                  INT         DEFAULT NULL,
    load_zone_id            INT         DEFAULT NULL,
    balancing_authority_id  INT         DEFAULT NULL,
    interval_start_utc      DATETIME    NOT NULL,
    interval_end_utc        DATETIME    NOT NULL,
    lmp_price_usd_per_mwh   DECIMAL(12,4) NOT NULL,
    energy_component        DECIMAL(12,4) DEFAULT NULL,
    congestion_component    DECIMAL(12,4) DEFAULT NULL,
    loss_component          DECIMAL(12,4) DEFAULT NULL,
    is_estimated            BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (node_id)             REFERENCES nodes(id)             ON DELETE CASCADE,
    FOREIGN KEY (hub_id)              REFERENCES hubs(id)              ON DELETE CASCADE,
    FOREIGN KEY (load_zone_id)        REFERENCES load_zones(id)        ON DELETE CASCADE,
    FOREIGN KEY (balancing_authority_id) REFERENCES balancing_authorities(id) ON DELETE CASCADE,
    INDEX idx_prices_time (interval_start_utc),
    INDEX idx_prices_node (node_id),
    INDEX idx_prices_hub (hub_id),
    INDEX idx_prices_zone (load_zone_id),
    INDEX idx_prices_ba (balancing_authority_id)
) ENGINE=InnoDB;

CREATE TABLE price_spreads (
    id                          BIGINT      AUTO_INCREMENT PRIMARY KEY,
    interval_start_utc          DATETIME    NOT NULL,
    interval_end_utc            DATETIME    NOT NULL,
    hub_from_id                 INT         DEFAULT NULL,
    hub_to_id                   INT         DEFAULT NULL,
    zone_from_id                INT         DEFAULT NULL,
    zone_to_id                  INT         DEFAULT NULL,
    node_from_id                INT         DEFAULT NULL,
    node_to_id                  INT         DEFAULT NULL,
    iso_region_id               INT         DEFAULT NULL,
    spread_usd_per_mwh          DECIMAL(12,4) NOT NULL,
    spread_type                 ENUM('hub_to_hub','zone_to_zone','node_to_node',
                                     'hub_to_zone','internal') NOT NULL,
    created_at                  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hub_from_id)   REFERENCES hubs(id)  ON DELETE CASCADE,
    FOREIGN KEY (hub_to_id)     REFERENCES hubs(id)  ON DELETE CASCADE,
    FOREIGN KEY (zone_from_id)  REFERENCES load_zones(id) ON DELETE CASCADE,
    FOREIGN KEY (zone_to_id)    REFERENCES load_zones(id) ON DELETE CASCADE,
    FOREIGN KEY (node_from_id)  REFERENCES nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (node_to_id)    REFERENCES nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (iso_region_id) REFERENCES iso_regions(id) ON DELETE CASCADE,
    INDEX idx_spreads_time (interval_start_utc),
    INDEX idx_spreads_iso (iso_region_id)
) ENGINE=InnoDB;

CREATE TABLE outages (
    id                      BIGINT      AUTO_INCREMENT PRIMARY KEY,
    generator_id            INT         NOT NULL,
    plant_id                INT         DEFAULT NULL,
    balancing_authority_id  INT         DEFAULT NULL,
    outage_start_utc        DATETIME    NOT NULL,
    outage_end_utc          DATETIME    DEFAULT NULL,
    outage_type             ENUM('planned','forced','maintenance','other') NOT NULL,
    capacity_affected_mw    DECIMAL(12,4) DEFAULT NULL,
    reason                  TEXT        DEFAULT NULL,
    created_at              TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (generator_id)           REFERENCES generators(id)           ON DELETE CASCADE,
    FOREIGN KEY (plant_id)               REFERENCES plants(id)               ON DELETE SET NULL,
    FOREIGN KEY (balancing_authority_id)  REFERENCES balancing_authorities(id) ON DELETE SET NULL,
    INDEX idx_outages_time (outage_start_utc, outage_end_utc),
    INDEX idx_outages_ba (balancing_authority_id),
    INDEX idx_outages_type (outage_type)
) ENGINE=InnoDB;

CREATE TABLE weather_conditions (
    id                      BIGINT      AUTO_INCREMENT PRIMARY KEY,
    balancing_authority_id  INT         DEFAULT NULL,
    station_id              VARCHAR(20) DEFAULT NULL,
    interval_start_utc      DATETIME    NOT NULL,
    interval_end_utc        DATETIME    NOT NULL,
    temperature_c           DECIMAL(6,2) DEFAULT NULL,
    dew_point_c             DECIMAL(6,2) DEFAULT NULL,
    humidity_pct            DECIMAL(5,2) DEFAULT NULL,
    wind_speed_ms           DECIMAL(6,2) DEFAULT NULL,
    wind_gust_ms            DECIMAL(6,2) DEFAULT NULL,
    precipitation_mm        DECIMAL(8,2) DEFAULT NULL,
    pressure_hpa            DECIMAL(8,2) DEFAULT NULL,
    cloud_cover_pct         DECIMAL(5,2) DEFAULT NULL,
    is_extreme              BOOLEAN     NOT NULL DEFAULT FALSE,
    extreme_type            VARCHAR(40) DEFAULT NULL,
    created_at              TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (balancing_authority_id) REFERENCES balancing_authorities(id) ON DELETE SET NULL,
    INDEX idx_weather_time (interval_start_utc),
    INDEX idx_weather_ba (balancing_authority_id),
    INDEX idx_weather_extreme (is_extreme)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------------
-- 5. Derived features table (populated by feature-engineering pipeline)
-- ---------------------------------------------------------------------------

CREATE TABLE derived_features (
    id                          BIGINT      AUTO_INCREMENT PRIMARY KEY,
    balancing_authority_id      INT         NOT NULL,
    interval_start_utc          DATETIME    NOT NULL,
    interval_end_utc            DATETIME    NOT NULL,
    load_mw                     DECIMAL(12,4) DEFAULT NULL,
    load_percentile             DECIMAL(5,4)  DEFAULT NULL,
    renewable_share             DECIMAL(5,4)  DEFAULT NULL,
    thermal_share               DECIMAL(5,4)  DEFAULT NULL,
    total_generation_mw         DECIMAL(14,4) DEFAULT NULL,
    reserve_margin_proxy        DECIMAL(6,4)  DEFAULT NULL,
    congestion_spread_max       DECIMAL(12,4) DEFAULT NULL,
    congestion_spread_avg       DECIMAL(12,4) DEFAULT NULL,
    avg_lmp_usd_per_mwh         DECIMAL(12,4) DEFAULT NULL,
    total_outage_mw             DECIMAL(14,4) DEFAULT NULL,
    forced_outage_mw            DECIMAL(14,4) DEFAULT NULL,
    temperature_c               DECIMAL(6,2)  DEFAULT NULL,
    is_extreme_weather          BOOLEAN       DEFAULT FALSE,
    renewable_share_bin         VARCHAR(20)   DEFAULT NULL,
    load_percentile_bin         VARCHAR(20)   DEFAULT NULL,
    created_at                  TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (balancing_authority_id) REFERENCES balancing_authorities(id) ON DELETE CASCADE,
    UNIQUE KEY uq_features (balancing_authority_id, interval_start_utc),
    INDEX idx_features_ba_time (balancing_authority_id, interval_start_utc),
    INDEX idx_features_extreme (is_extreme_weather)
) ENGINE=InnoDB;
