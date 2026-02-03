# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.7.6] - 2026-02-03

### Fixed
- **Profile Extraction**: Fixed extraction of `type[].profile` references from StructureDefinitions
  - Added `extract_type_profiles_from_structuredefinitions()` method to recursively extract profile URLs from element type definitions
  - Profiles like `ISiKSnomedCTCoding`, `ISiKLoincCoding`, `ISiKICD10GMCoding` are now correctly included
  - This resolves IG Publisher warnings about missing Coding profiles in slice definitions
- **GitHub Actions Debug Logging**: Fixed verbose flag not being applied when `ACTIONS_STEP_DEBUG=true` is set
  - The `--verbose` flag is now correctly passed when GitHub Actions debug mode is active
  - Previously, the verbose input parameter was checked but the computed `VERBOSE_FLAG` variable was not used

### Technical Details
- Profile references in StructureDefinition element types (e.g., `{"code": "Coding", "profile": ["url"]}`) are now extracted during iterative reference resolution
- The extraction follows the same pattern as binding ValueSet extraction but specifically targets `type[].profile` arrays

## [0.7.5] - 2026-02-03

### Fixed
- **Reduced log spam**: Circular reference warnings are now logged only once per unique reference
- **FHIR Core resource handling**: Added intelligent filtering for FHIR core resources (StructureDefinition/Patient, Observation, etc.)
  - Circular references to FHIR core resources now logged at DEBUG level instead of WARNING
  - Missing parent profiles from FHIR core are now logged at DEBUG level (expected behavior)
  - Base definitions pointing to FHIR core resources no longer generate warnings
- **Better statistics**: `copy_referenced_resources()` now reports:
  - Number of files copied
  - Number of FHIR core resources skipped (not in input directory)
  - Number of resources not found
- **Performance**: FHIR core resources are now skipped during copy operations (prevents unnecessary warnings)

### Added
- `FHIR_CORE_PATTERNS` constant to identify FHIR core base resources
- `circular_refs_reported` set to track and deduplicate circular reference warnings
- Enhanced logging in `copy_referenced_resources()` with separate counters for different skip reasons

## [0.7.0] - 2026-02-03

### Added
- Enum classes for better type safety: `Expectation`, `ReferenceKeys`, `ResourceTypes`
- Deterministic resource iteration with sorted() for reproducible builds
- Constants for all magic strings to improve maintainability

### Changed
- **MAJOR REFACTORING**: Replaced all magic strings with typed constants
- Resource iteration is now deterministic (sorted) to ensure identical results across environments
- Improved code structure and readability throughout
- All FHIR resource type checks now use `ResourceTypes` constants
- All reference keys now use `ReferenceKeys` constants
- Expectation values now use `Expectation` enum

### Fixed
- Non-deterministic behavior between CI and local builds caused by unsorted Set iteration
- Code duplication in resource lookup (consolidated into single method)
- Indentation error in find_capability_statement method

## [0.6.2] - 2026-02-03

### Added
- Smart example detection via meta.profile references
- Enhanced documentation with detailed feature descriptions
- Complete GitHub Action integration

### Changed
- Improved resource collection algorithm
- Enhanced logging and error handling

### Fixed
- Various bug fixes and stability improvements

## How to Release

To create a new release:

1. Update the version in this CHANGELOG.md
2. Commit your changes
3. Create and push a new tag:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
4. The GitHub Action will automatically create the release

## Version Format

- Use semantic versioning: `vMAJOR.MINOR.PATCH`
- Examples: `v1.0.0`, `v1.2.3`, `v2.0.0`
- Major version tags (e.g., `v1`, `v2`) are automatically updated