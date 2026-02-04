# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.7.7] - 2026-02-04

### Fixed
- **CRITICAL BUG**: Fixed reference matching to use exact last-segment comparison instead of substring matching
  - Previous: `url.endswith("Bundle")` matched both "Bundle" AND "ISiKBerichtBundle"
  - Now: `url.split('/')[-1] == "Bundle"` only matches exactly "Bundle"
  - This prevents cross-IG resource pollution where documentation resources were incorrectly included

### Changed
- **Simplified and hardened reference matching to 2 strategies**:
  1. **Exact canonical URL** - for definitions (StructureDefinition, ValueSet, etc.)
  2. **FHIR Reference format with MANDATORY ResourceType validation**
     - Relative: `Patient/patient-123`
     - Absolute: `http://base/fhir/Patient/patient-123`
     - **Simple IDs WITHOUT ResourceType are NO LONGER allowed** (FHIR-compliant)

- **BREAKING CHANGE**: Removed simple ID matching without ResourceType
  - Previous: `"patient-123"` would match any resource with `id="patient-123"`
  - Now: Requires `"Patient/patient-123"` to ensure ResourceType validation
  - **Rationale**: FHIR References MUST include ResourceType to prevent false matches

- **Improved version handling**: Multiple resources with same URL but different versions
  - If requested version not found, continues search instead of immediate error
  - Enables support for versioned canonical URLs (e.g., multiple StructureDefinition versions)

- **ResourceType validation**: ALL ID-based matches now validate ResourceType
  - `"Patient/123"` only matches if `resourceType="Patient"` AND `id="123"`
  - Prevents false matches like `"Observation/patient-123"` matching a Patient resource
  - No exceptions - ResourceType validation is ALWAYS enforced

- **Removed**: Scheme-agnostic matching - http:// and https:// must match exactly

- **Added**: Comprehensive DEBUG logging for both strategies
  - Each strategy logs success or failure
  - ResourceType mismatches logged at DEBUG level
  - Version mismatches logged as DEBUG during search
  - Helpful error message: "Simple IDs require ResourceType, e.g., 'Patient/{id}'"

### Migration Guide
If your code uses simple IDs without ResourceType:

**Before (v0.7.6):**
```python
find_resource_by_reference("patient-123")  # ✅ Worked
```

**After (v0.7.7):**
```python
find_resource_by_reference("Patient/patient-123")  # ✅ Required
find_resource_by_reference("patient-123")  # ❌ Will fail
```

### Technical Details
- FHIR Reference matching validates both ResourceType and ID in ALL cases
- No fallback to simple ID matching - ResourceType is MANDATORY
- Version validation continues search for alternative versions before failing
- Conformance resources (StructureDefinition, ValueSet, etc.) MUST use canonical URLs

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