# Build and Reproducibility Standard

This file owns shared build requirements; the actual procedure remains in [BUILDING](../BUILDING.md). Shared identity rules are in [the core standard](LOCALIZATION_STANDARD.md); test gates are in [acceptance](ACCEPTANCE.md).

The project [BUILDING](../BUILDING.md) owns actual game/platform/region/disc/build identities, supported input manifest, locales/adapters, dependency lock, working directory, fonts/hashes/licenses, entry points, output names and reproducibility comparator. Keep those values verified and distinguish historic commands from current ones.
List external tools by exact version, source, digest and configuration. Include font rasterizer/encoder versions and settings when they affect output.
Store local paths in an ignored config file with a checked-in example; accept quoted Unicode paths and paths with spaces.
Document operating-system/architecture requirements and manual operations with exact inputs and outputs.

## Build sequence

1. Validate dependencies and supported input manifest, then create an isolated working copy.
2. Extract resources deterministically; record extraction source and stable identifiers.
3. Merge and validate translations using [the data contract](DATA_CONTRACT.md).
4. Generate fonts/assets using [the asset specification](ASSET_LOCALIZATION.md).
5. Rebuild resources and apply version-specific executable changes; update dependent metadata.
6. Read the result back and compare intended/unintended changes.
7. Assemble only allowlisted release files, notices and install instructions.
8. Produce content hashes and a build manifest; test the actual package through G4.

Validate translations before writing runtime resources. Stop on fatal errors; never let stale output masquerade as a successful build.
Use one obvious documented entry point where practical. A specific CLI is a project decision; do not copy a hypothetical command into player instructions as an implemented feature.

## Reproducibility

Keep ordering, locale, normalization, timestamps, random seeds, compression and font settings deterministic where practical.
Pin dependencies; identify every manual or external input.
Before each supported release, build in a fresh directory using only documented inputs. Build twice when claiming deterministic output.
Declare byte-identical, normalized-structural or scenario-tested functional equivalence and provide the actual comparison.
If timestamps differ, isolate and explain those bytes instead of ignoring all binary differences.

## Build and release records

Record source revision/tree hash, input manifest, locale/config digest, dependency versions, exact command, exit code, validation report and output hashes.
Separate tool tests runnable on synthetic fixtures from private-input integration tests.
CI may run synthetic tests publicly; do not upload game inputs or restricted artifacts as CI logs/artifacts.
Never report private-input or runtime checks as passed when CI only ran fixtures.
Test the extracted release package, not only the developer's build directory.
Installation behavior belongs in [the installation specification](INSTALLATION_STANDARD.md).

## Troubleshooting record

For each recurring failure, link its case in [pitfalls](PITFALLS.md), the failed command, actionable diagnostic and verified repair.
Keep diagnostics specific: expected versus actual identity, missing dependency, encoding failure, failing resource/ID or output mismatch.
