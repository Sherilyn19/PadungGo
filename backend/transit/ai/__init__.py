"""Optional AI explanation of one planner result.

The deterministic planner decides everything about a trip. This package only
asks an open-weight model to restate the planner's facts in plain English, and
it refuses any answer that does not pass `output_checks`.
"""
