# Contributing to PadungGo

Thank you for helping improve commuter guidance in Metro Cebu. Contributions are welcome even while the application is still in planning.

## Before contributing

1. Check open issues and this repository's roadmap.
2. For major design changes, open an issue first.
3. For route/stopping point/fare changes, provide **evidence**, not only an assertion.
4. Do **not** upload private location histories, API keys, secrets, or third-party datasets without permission.

## Suggested workflow

1. Fork this repository.
2. Create a descriptive branch such as `docs/clarify-fare-sources` or `fix/return-routing`.
3. Make one focused change and update documentation and tests where appropriate.
4. Submit a pull request that explains the problem, what changed, and how it was verified.
5. Be respectful when discussing corrections.

## Route-data submissions

A usable proposed route record should identify the route code, operator (if known), vehicle category, direction and variant, stop order, source(s), evidence date, operating status, and dataset license/permission. A submitted route remains **Candidate** until reviewed; only **Verified** routes can be used for trusted recommendations.

See [Route Verification](docs/DATA_VERIFICATION.md).

## Development standards (once code is added)

- Python: modular Django REST services, typed/validated API inputs, pytest coverage of route and fare calculations.
- TypeScript: strong types, accessible React components, tests of major user journeys.
- Favor clarity and correctness over additional frameworks or large-scale redesign.
- Never display made-up journey alternatives or unsupported time estimates as facts.

## Licensing

By contributing original code or text, you agree it can be distributed under the repository's MIT License. Data from other publishers must be licensed or permissioned separately.

## Product scope for contributors

Support same-city, same-barangay and intercity journeys throughout Cebu City, Mandaue City and Lapu-Lapu City. The MVP uses a verified subset; 01K, 23D, 20A and 03Q are initial research only. Expand the dataset without hardcoding codes in routing. Verify each directional pattern independently and disclose unknown fare/time fields. Canonical stored statuses are `candidate`, `documented`, `verified` and `needs_review`.
