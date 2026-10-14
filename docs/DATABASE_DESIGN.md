# PadungGo Database Design

## Database

PostgreSQL with PostGIS support.

## Core Tables

## locations

Purpose: Stores supported places and landmarks.

Important fields: - id - name - latitude - longitude - location_type

## routes

Purpose: Stores transportation route definitions.

Fields: - id - route_name - vehicle_type - active_status

## route_stops

Purpose: Stores ordered stops.

Fields: - id - route_id - location_id - sequence_number - direction

## fare_rules

Purpose: Stores fare assumptions.

Fields: - id - route_id - amount - effective_date - source_id

## route_sources

Purpose: Stores evidence references.

Fields: - id - source_name - source_url - collected_date

## route_verification

Purpose: Preserves verification history.

Fields: - id - route_id - status - notes - verified_date

## Integrity Rules

-   Never overwrite verification history.
-   Unknown data is different from zero values.
-   Geographic columns should use spatial indexing where needed.
