# Data contributions

This directory contains guidance and empty candidate/verified placeholders, not a bundled transport feed. Production data is maintained separately in the application database.

- `candidate/`: space for permitted research leads and supporting notes.
- `verified/`: space for permitted reviewed records with source/evidence references.

Follow the [verification standard](../docs/DATA_VERIFICATION.md) and [source/rights register](../docs/DATA_SOURCES.md). Moving a file between these directories does not change database status or establish verification. Do not commit restricted feeds or personal information. The MIT code license does not cover third-party data automatically.

For an authorized feed, see [import instructions](../backend/README.md#import-a-transport-feed). Historic imports remain documented and need an explicit configuration setting to appear in planner results.
