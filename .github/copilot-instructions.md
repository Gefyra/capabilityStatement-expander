# FHIR CapabilityStatement Expander - AI Coding Assistant Guide

## Project Overview
This is a **FHIR R4 CapabilityStatement expansion tool** that recursively resolves `imports`/`instantiates` references and collects all related FHIR resources (profiles, ValueSets, CodeSystems, SearchParameters, Examples). It's packaged as both a **Python CLI tool** and a **GitHub Action**.

**Core Purpose**: Given a CapabilityStatement URL, produce a complete, self-contained package of all referenced FHIR resources for Implementation Guide development, validation, or distribution.

## Architecture

### Single-File Design
- **All logic in [`capability_statement_expander.py`](../capability_statement_expander.py)** (~1131 lines)
- **Current Version**: 0.7.5 (see `__version__` constant)
- Pure Python 3.11+ with **zero external dependencies** (uses only stdlib: `json`, `pathlib`, `shutil`, `argparse`, `logging`)
- Test file: [`test_expander.py`](../test_expander.py) (subprocess-based integration test)
- GitHub Action wrapper: [`action.yml`](../action.yml) (delegates to Python script)

### Key Classes & Constants
```python
class Expectation(Enum):      # Import priority: SHALL > SHOULD > MAY > SHOULD-NOT (never imported)
class ReferenceKeys:          # FHIR reference field names (supportedProfile, valueSet, binding, etc.)
class ResourceTypes:          # FHIR resource types (CapabilityStatement, StructureDefinition, etc.)
class CapabilityStatementExpander:  # Main engine with 20+ methods

# FHIR Core Detection (v0.7.5+)
FHIR_CORE_PATTERNS = [
    'http://hl7.org/fhir/StructureDefinition/',
    'http://terminology.hl7.org/',
    'http://hl7.org/fhir/SearchParameter/'
]
```

### Core Data Structures
- `self.all_resources: Dict[str, Dict]` - Indexed by resource ID: `{id → {resource, file_path, relative_path}}`
- `self.resources_by_url: Dict[str, Dict]` - Indexed by canonical URL for FHIR-compliant lookups
- `self.referenced_resources: Set[str]` - Accumulates all URLs/IDs to copy (grows during iterations)
- `self.processed_imports: Set[str]` - Prevents circular import processing
- `self.expectation_filter: str` - Filters imports by SHALL/SHOULD/MAY hierarchy (see `should_import_expectation()`)
- `self.circular_refs_reported: Set[str]` - **(v0.7.5)** Tracks reported circular references to prevent duplicate warnings

## Critical Workflows

### Expansion Algorithm (8-Step Process)
1. **Load all resources** (`load_all_resources()`) - Scans `input_dir/**/*.json`, builds dual index (ID + URL)
2. **Find base CapabilityStatement(s)** (`find_capability_statements()`) - Lookup by canonical URL
3. **Recursive import resolution** (`expand_capability_statement()`) - Follows `imports`/`instantiates` chains
4. **Profile collection** (`collect_referenced_resources()`) - Extracts from `supportedProfile`, `searchParam.definition`, etc.
5. **Binding analysis** (`extract_bindings_from_structuredefinitions()`) - ValueSets from StructureDefinition element bindings
6. **Iterative dependency resolution** (`iterative_reference_extraction()`) - Multi-pass for nested ValueSet→CodeSystem references
7. **Example detection** (`collect_examples_by_meta_profile()`) - Matches `meta.profile` to collected profiles
8. **Output generation** - Copy all resources flat (no subdirs), save expanded CapabilityStatement with `-expanded.json` suffix

### Import Expectation Filtering
- **Default**: Import ALL expectations (except `SHOULD-NOT`)
- **`--expectation-filter SHALL`**: Only process imports with SHALL expectation
- **`--expectation-filter SHOULD`**: Process SHALL + SHOULD
- **`--expectation-filter MAY`**: Process SHALL + SHOULD + MAY
- Implementation: `should_import_expectation()` checks against `expectation_hierarchy` dict

### Reference Resolution Chain
1. **Canonical URL lookup** (`resources_by_url`) - Primary for conformance resources
2. **FHIR Reference with ResourceType validation** - For resource instances
   - Validates BOTH ResourceType and ID
   - Supports relative (`Patient/patient-123`) and absolute (`http://base/fhir/Patient/patient-123`) format
   - **Simple IDs without ResourceType are NOT allowed** (FHIR-compliant)
3. Method: `find_resource_by_reference()` - Used everywhere for resource lookups

**CRITICAL: ResourceType Validation**
- **ALL** reference matching (except canonical URLs) validates ResourceType
- Simple IDs like `"patient-123"` will FAIL
- Must use FHIR Reference format: `"Patient/patient-123"`
- Prevents false matches across resource types

## FHIR-Specific Patterns

### Import Mechanisms
```json
{
  "imports": ["http://example.org/CapabilityStatement/BaseCS"],
  "_imports": [{  // Optional expectation extensions
    "extension": [{
      "url": "http://hl7.org/fhir/StructureDefinition/capabilitystatement-expectation",
      "valueCode": "SHALL"  // or SHOULD, MAY, SHOULD-NOT
    }]
  }]
}
```
**Code**: `extract_imports()` parses both `imports` array and `_imports` extensions

### Recursive Reference Extraction
Search paths (see `collect_referenced_resources()`):
- `supportedProfile`, `profile`, `targetProfile` → StructureDefinitions
- `binding.valueSet` → ValueSets
- `searchParam[].definition` → SearchParameters
- `extension[].url` → StructureDefinitions (extensions)
- `operation[].definition` → OperationDefinitions
- ValueSet `compose.include[].system` → CodeSystems (nested in `extract_codesystems_from_valueset()`)

### Parent Profile Hierarchy
- `extract_parent_profile_recursive()` follows `baseDefinition` chains up to FHIR base resources
- Circular reference protection via `visited` set
- Warnings logged for missing parents (likely from FHIR core/dependencies, not included)

### Smart Example Detection
```python
# Finds examples where meta.profile matches collected supportedProfile URLs
for resource in all_resources:
    if resource.get('meta', {}).get('profile'):
        for profile_url in resource['meta']['profile']:
            if profile_url in referenced_resources:
                # Include this example!
```

## Development Commands

### Local Testing
```bash
# Single CapabilityStatement
python capability_statement_expander.py ./examples ./output \
  "http://example.org/CapabilityStatement/example-base-capability" --verbose

# Multiple CapabilityStatements (JSON array - note quotes!)
python capability_statement_expander.py ./resources ./output \
  '["http://example.org/CS1", "http://example.org/CS2"]' --verbose

# With expectation filter (only SHALL imports)
python capability_statement_expander.py ./input ./output \
  "https://gematik.de/fhir/isik/CapabilityStatement/ISiKCapabilityStatementBasis" \
  --expectation-filter SHALL --verbose
```

### Integration Test
```bash
python test_expander.py  # Uses examples/ directory, checks output file creation
```

### GitHub Action Development
Test locally by running Python script directly (action.yml just wraps CLI args). Check composite action steps in `action.yml` for shell script output formatting.

## Project Conventions

### File Naming
- **Input**: Any `*.json` files in `input_dir/**/*` (recursive scan)
- **Output**: Flat structure (no subdirectories), expanded CapabilityStatement gets `-expanded.json` suffix
- **Example**: `CapabilityStatement-example-base-capability.json` → `CapabilityStatement-expanded-example-base-capability.json`

### Logging Strategy
- **INFO**: Expansion progress, resource counts, import resolution
- **DEBUG** (`--verbose`): Per-resource processing, reference extraction details
- **WARNING**: Missing resources, circular references, parent profile issues
- Special markers: `🔍` (analyzing), `✅` (found), `📦` (analyzing bindings), `⚠️` (warnings)

### Error Handling
- **Missing CapabilityStatement**: `FileNotFoundError` with URL
- **Invalid JSON**: `json.JSONDecodeError` logged as warning, file skipped
- **Circular imports**: Detected via `visited` set, logged as warning, processing continues

## Common Pitfall: URL vs ID Lookups
**Problem**: CapabilityStatement specifies canonical URL but resource file has different ID
```json
// CapabilityStatement-MyCS.json
{"id": "MyCS", "url": "http://example.org/CapabilityStatement/MyCapabilityStatement"}
```
**Solution**: Always use canonical URLs for conformance resources (StructureDefinition, ValueSet, etc.) and FHIR References for instances (Patient, Observation, etc.).

**FHIR Reference Requirements**:
- **Conformance resources** (StructureDefinition, ValueSet, CodeSystem, etc.): **MUST use canonical URLs**
  - ✅ `"http://example.org/fhir/StructureDefinition/PatientProfile"`
  - ❌ `"PatientProfile"` (will FAIL - no simple ID matching)
  
- **Resource instances** (Patient, Observation, etc.): **MUST use ResourceType/ID format**
  - ✅ `"Patient/patient-123"` (relative FHIR reference)
  - ✅ `"http://base/fhir/Patient/patient-123"` (absolute FHIR reference)
  - ❌ `"patient-123"` (will FAIL - requires ResourceType)

The expander prioritizes canonical URL lookups for conformance resources and validates ResourceType for all instance references.

## Debugging Workflow
1. **Enable verbose logging**: `--verbose` or `verbose: 'true'` in GitHub Action
2. **Check resource loading**: Look for "Total X resources loaded" - all input files indexed?
3. **Verify canonical URLs**: Search logs for "CapabilityStatement found: ..." - correct URL used?
4. **Trace import chain**: Logs show "Import with SHALL/SHOULD/MAY expectation: ..." for each processed import
5. **Check reference extraction**: "Referenced resources collected: X" after each CapabilityStatement expansion
6. **Missing resources**: Warning "Referenced resource not found: ..." indicates broken reference

## Extending Functionality

### Adding New Reference Types
1. Update `ReferenceKeys` class constants
2. Add extraction logic to `collect_referenced_resources()` → `extract_references()` nested function
3. Add test case in `examples/` with new reference type

### Supporting New FHIR Versions
- Currently FHIR R4-focused (check `fhirVersion` field)
- Core logic is version-agnostic (works with any JSON structure)
- May need updates to reference paths for R5/R6 breaking changes

### GitHub Action Outputs
See `action.yml` composite action section - outputs are generated via shell script that:
1. Counts files: `find "$OUTPUT_DIR" -type f -name "*.json" | wc -l`
2. Finds expanded CS: `find "$OUTPUT_DIR" -name "*-expanded-*.json"`
3. Sets GitHub Action outputs: `echo "files_count=$COUNT" >> $GITHUB_OUTPUT`

## Testing Strategy

### Integration Testing (Automated)
**Test Script**: [`test_expander.py`](../test_expander.py) runs full expansion via subprocess
- Uses `examples/` directory with simple CapabilityStatements
- Validates output files exist and have correct structure
- Returns 0 on success, 1 on failure

**Running Tests (zsh/bash)**:
```bash
# Basic test with example data
python3 test_expander.py

# Expected output:
# ============================================================
# FHIR CapabilityStatement Expander - Test
# ============================================================
# 🧪 Testing FHIR CapabilityStatement Expander
# ✅ Script executed successfully
# ✅ File created: CapabilityStatement-example-base-capability-expanded.json
# 📁 All created files (10):
#   📄 CapabilityStatement-example-base-capability-expanded.json (2363 bytes)
#   ... (9 more files)
# ✅ Test completed successfully
```

### Real-World Validation (ISiK Profiles)
**Dataset**: German ISiK profiles in `resources/` directory (~300 FHIR resources)
- CapabilityStatements with complex import chains
- Multiple SHALL/SHOULD/MAY expectations
- Real-world FHIR core base profile references

**Test Commands**:
```bash
# Test with ISiK Basis Server Actor (validates log improvements)
python3 capability_statement_expander.py \
  ./resources \
  /tmp/isik-test-output \
  "https://gematik.de/fhir/isik/CapabilityStatement/ISiKCapabilityStatementBasisServerAkteur" \
  --verbose

# Test with expectation filter (SHALL only)
python3 capability_statement_expander.py \
  ./resources \
  /tmp/isik-test-output \
  "https://gematik.de/fhir/isik/CapabilityStatement/ISiKCapabilityStatementBasisServerAkteur" \
  --expectation-filter SHALL \
  --verbose
```

**Expected Log Improvements (v0.7.5+)**:
- ✅ **No duplicate circular reference warnings**: Each circular ref logged only once at DEBUG level
- ✅ **FHIR core parent profiles**: Changed from WARNING to DEBUG for expected base resources
- ✅ **Base definition warnings**: Filtered for FHIR core resources (Patient, Observation, etc.)
- ✅ **Copy statistics**: Clear counts for copied/skipped_fhir_core/not_found resources

**Before v0.7.5** (verbose log excerpt):
```
WARNING - Circular reference detected: http://hl7.org/fhir/StructureDefinition/Patient
WARNING - Circular reference detected: http://hl7.org/fhir/StructureDefinition/Patient
WARNING - Circular reference detected: http://hl7.org/fhir/StructureDefinition/Patient
WARNING - Parent profile not found: http://hl7.org/fhir/StructureDefinition/Encounter
WARNING - Parent profile not found: http://hl7.org/fhir/StructureDefinition/Organization
WARNING - Base definition is not a StructureDefinition: http://hl7.org/fhir/StructureDefinition/Observation
WARNING - Referenced resource not found: http://hl7.org/fhir/SearchParameter/Observation-combo-code
```

**After v0.7.5** (verbose log excerpt):
```
DEBUG - Circular reference detected: http://hl7.org/fhir/StructureDefinition/Patient (FHIR core base resource)
DEBUG - Parent is FHIR core resource (not in input): http://hl7.org/fhir/StructureDefinition/Encounter
INFO - 150 files copied, 45 FHIR core resources skipped, 0 not found
```

### Manual Testing (Development)
**Quick Validation**: Use `examples/` directory for rapid iteration
```bash
# Test basic expansion with examples
python3 capability_statement_expander.py \
  ./examples \
  ./output \
  "http://example.org/CapabilityStatement/example-base-capability" \
  --verbose

# Expected: 10 files (1 expanded, 2 CapabilityStatements, 7 resources)
```

### Terminal-Specific Notes (macOS/zsh)
**Issue**: Python scripts may appear to "hang" in VS Code terminal when using complex pipes
**Solution**: 
- Use simple redirections: `> file.txt 2>&1` instead of pipes with `tee`
- Add unbuffered output: `python3 -u script.py`
- Check background processes: Use `get_terminal_output` tool if launched as background
- For large output: Redirect to file first, then read file: `python3 script.py > /tmp/out.txt 2>&1 && cat /tmp/out.txt`
