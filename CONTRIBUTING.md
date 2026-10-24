# Contributing to PadungGo

Contributions are welcome: clearer instructions, accessibility improvements, tests, bug fixes, and well-sourced transport corrections.

## Code and documentation

1. Read the [overview](README.md), [setup](docs/REPOSITORY_SETUP.md), and relevant [technical guide](docs/README.md).
2. Describe the problem or proposed change in an issue or pull request. Include reproducible steps for bugs, without personal location history or credentials.
3. Keep changes focused. Explain the resulting behavior and any limitations; distinguish actual results from proposed work.
4. Run checks relevant to the change. Backend changes normally need pytest and a migration check; frontend changes need Vitest and a production build. Record the commands and results in the pull request.
5. Update documentation and the changelog when public behavior changes. Check local Markdown links and examples.

Automated checks run on pull requests and pushes to main. They use SQLite for backend tests; passing them does not verify production PostGIS behavior, live transport service, or provider availability. Discuss significant architecture or data changes before implementation to avoid incompatible work.

## Transport and map data

Follow the [source register](docs/DATA_SOURCES.md) and [verification guide](docs/DATA_VERIFICATION.md). Include source URL or identifier, date, exact scope, reuse permission, and conflicting evidence. A route name or sighting alone is not enough to supply a navigable path.

Do not label historic, inferred, or synthetic records as current verified service. Do not upload third-party feeds, photographs, maps, or personal observations containing identifying information without appropriate rights and consent. The repository's MIT license does not establish those rights.

Imported records start as documented, not verified. Review both directions, boarding and alighting permissions, transfer access, distance provenance, fares, and current operation separately. Route codes are not unique database identifiers.

## Safety and respectful collaboration

Never commit secrets, real credentials, or personal trip histories. See [security notes](docs/SECURITY.md) for handling a sensitive report. Keep discussion respectful, explain evidence, and welcome corrections. Do not post a person's private details in issues or evidence records.

Original code and documentation contributions fall under the existing [MIT License](LICENSE). Record licenses and notices separately for any third-party material; do not assume that a code license covers embedded datasets.
