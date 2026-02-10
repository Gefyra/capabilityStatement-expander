# FHIR CapabilityStatement Expander Action 🚀

A **GitHub### Advanced Configuration

```yaml
- name: Expand FHIR CapabilityStatement  
  id: expand
  uses: Gefyra/capabilityStatement-expander@v0  # or @v0.0.2 for specific version
  with:
    input_directory: './implementation-guide/input'
    output_directory: './build/expanded'
    capability_statement_url: 'https://example.org/fhir/CapabilityStatement/MyCapability'
    verbose: 'true'  # Enable detailed logging for debugging
    python_version: '3.10'
    
- name: Show Results
  run: |
    echo "Expanded files: ${{ steps.expand.outputs.expanded_files_count }}"
    echo "CapabilityStatement: ${{ steps.expand.outputs.expanded_capability_statement }}"
```

### 🔍 Verbose Logging

Enable detailed logging to troubleshoot expansion issues:

```yaml
- name: Debug Expansion Process
  uses: Gefyra/capabilityStatement-expander@v0
  with:
    input_directory: './resources'
    output_directory: './output'
    capability_statement_url: 'https://example.org/fhir/CapabilityStatement/MyCS'
    verbose: 'true'  # Shows detailed processing steps
```

**With `verbose: 'true'` you get:**
- 📋 Detailed file processing information
- 🔍 Step-by-step import resolution
- 📊 Resource collection statistics  
- 🧩 Profile and example discovery details
- ⚠️ Warning messages for missing resources

### 🤖 Auto-Enable Verbose with GitHub Debug Mode

**Bonus Feature:** Verbose logging is automatically enabled when you activate GitHub Actions debug logging!

```yaml
# No need to set verbose: 'true' when using GitHub debug mode
- name: Expand CapabilityStatement (with auto-verbose)
  uses: Gefyra/capabilityStatement-expander@v0
  with:
    input_directory: './resources'
    output_directory: './output'
    capability_statement_url: 'https://example.org/fhir/CapabilityStatement/MyCS'
    # verbose automatically enabled when ACTIONS_STEP_DEBUG=true
```

**To activate both debug modes:**
1. 🔧 **Repository Settings** → Actions → General → "Enable debug logging"
2. 🚀 **Run workflow** → Both GitHub Actions debug + FHIR verbose logging active automatically!ursively expands FHIR CapabilityStatements by resolving all `imports` and collecting all referenced resources. Perfect for FHIR Implementation Guide development and distribution.

[![GitHub Release](https://img.shields.io/github/v/release/Gefyra/capabilityStatement-expander)](https://github.com/Gefyra/capabilityStatement-expander/releases)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![FHIR R4](https://img.shields.io/badge/FHIR-R4-green.svg)](https://hl7.org/fhir/R4/)

## ✨ Features

- 🔄 **Recursive Import Resolution**: Automatically resolves all `imports` and `instantiates` references
- 🏷️ **Canonical URL Support**: Uses FHIR-compliant canonical URLs for resource identification  
- 🧩 **Complete Resource Extraction**: Automatically collects:
  - ✅ StructureDefinitions (profiles)
  - ✅ ValueSets and CodeSystems (including from StructureDefinition bindings)
  - ✅ SearchParameters and OperationDefinitions
  - ✅ Examples and other referenced resources
- 📋 **Smart Example Detection**: Finds examples via `meta.profile` references to collected profiles
- 🧹 **Import Cleanup**: Removes `imports`/`_imports` from the final expanded CapabilityStatement
- ⚡ **GitHub Action Ready**: Directly usable as a reusable action
- 🔍 **Iterative Analysis**: Multi-layered analysis for nested dependencies
- 📊 **Detailed Logging**: Complete traceability of the expansion process

## 🚀 Usage as GitHub Action

### Simple Usage (Single CapabilityStatement)

```yaml
name: Expand FHIR CapabilityStatement

on:
  workflow_dispatch:
    inputs:
      capability_statement_url:
        description: 'Canonical URL of the CapabilityStatement'
        required: true

jobs:
  expand:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Expand CapabilityStatement
      uses: Gefyra/capabilityStatement-expander@v0  # or @v0.0.2 for specific version
      with:
        input_directory: './fhir-resources'
        output_directory: './expanded-resources'  
        capability_statement_url: ${{ github.event.inputs.capability_statement_url }}
        
    - name: Upload Results
      uses: actions/upload-artifact@v4
      with:
        name: expanded-fhir-resources
        path: './expanded-resources'
```

### Expanding Multiple CapabilityStatements

```yaml
name: Expand Multiple FHIR CapabilityStatements

on:
  push:
    branches: [ main ]

jobs:
  expand:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Expand Multiple CapabilityStatements
      uses: Gefyra/capabilityStatement-expander@v0
      with:
        input_directory: './fhir-resources'
        output_directory: './expanded-resources'
        # Use toJSON() to convert YAML list to JSON array
        capability_statement_url: ${{ toJSON(fromJSON('[
          "https://example.org/fhir/CapabilityStatement/ServerCapability",
          "https://example.org/fhir/CapabilityStatement/ClientCapability"
        ]')) }}
        
    - name: Upload Results
      uses: actions/upload-artifact@v4
      with:
        name: expanded-fhir-resources
        path: './expanded-resources'
```

### Using Matrix Strategy for Multiple CapabilityStatements

```yaml
name: Expand CapabilityStatements with Matrix

on:
  push:
    branches: [ main ]

jobs:
  expand:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        capability_statement_urls:
          - https://gematik.de/fhir/isik/CapabilityStatement/ISiKCapabilityStatementBasis
          - https://gematik.de/fhir/isik/CapabilityStatement/ISiKCapabilityStatementSubscription
    steps:
    - uses: actions/checkout@v4
    
    - name: Expand CapabilityStatement
      uses: Gefyra/capabilityStatement-expander@v0
      with:
        input_directory: './Resources/fsh-generated/resources'
        output_directory: './publisher-input/resources'
        # Convert YAML list to JSON array
        capability_statement_url: ${{ toJSON(matrix.capability_statement_urls) }}
```

### Advanced Configuration

```yaml
- name: Expand FHIR CapabilityStatement  
  id: expand
  uses: Gefyra/capabilityStatement-expander@v0  # or @v0.0.2 for specific version
  with:
    input_directory: './implementation-guide/input'
    output_directory: './build/expanded'
    capability_statement_url: 'https://example.org/fhir/CapabilityStatement/MyCapability'
    verbose: 'true'
    python_version: '3.11'
    
- name: Show Results
  run: |
    echo "Expanded files: ${{ steps.expand.outputs.expanded_files_count }}"
    echo "CapabilityStatement: ${{ steps.expand.outputs.expanded_capability_statement }}"
```

### 🏷️ Version Tags

This action supports semantic versioning with automatic major version tags:

```yaml
# Latest within major version (recommended for most use cases)
uses: Gefyra/capabilityStatement-expander@v0

# Specific version (recommended for production)
uses: Gefyra/capabilityStatement-expander@v0.0.2

# Latest release (not recommended)
uses: Gefyra/capabilityStatement-expander@main
```

**📋 Version Strategy:**
- `@v0` - Always points to the latest `v0.x.x` release (automatic updates)
- `@v0.0.2` - Fixed to specific version (no automatic updates)
- `@main` - Development branch (may be unstable)

## 📥 Action Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------||
| `input_directory` | Directory with FHIR JSON files | ✅ | `./input` |
| `output_directory` | Target directory for expanded resources | ✅ | `./output` |
| `capability_statement_url` | Canonical URL(s) of the CapabilityStatement(s) to expand.<br>Can be:<br>• Single URL: `"https://example.org/CS"`<br>• JSON array: `["url1", "url2"]`<br>• YAML list (use `toJSON()`): `${{ toJSON(matrix.urls) }}` | ✅ | - |
| `verbose` | Enable verbose logging | ❌ | `false` |
| `no_clean` | Do not clean output directory before expansion (by default, directory is cleaned) | ❌ | `false` |
| `expectation_filter` | Filter imports by minimum expectation level.<br>`SHALL` = only SHALL<br>`SHOULD` = SHALL + SHOULD<br>`MAY` = SHALL + SHOULD + MAY<br>Default: import all expectations<br>**Note:** `SHOULD-NOT` is never imported | ❌ | - |
| `python_version` | Python version for execution | ❌ | `3.11` |

## 📤 Action Outputs

| Output | Description |
|---------|------------|
| `expanded_files_count` | Number of created files |
| `output_directory` | Path to output directory |
| `expanded_capability_statement` | Filename of the expanded CapabilityStatement |
## 💻 Local Execution (for Development)

You can also run the script locally:

```bash
python capability_statement_expander.py <input_dir> <output_dir> <capability_statement_url>
```

**Parameters:**
- `input_dir`: Directory with JSON files (CapabilityStatements, profiles, etc.)
- `output_dir`: Target directory for expanded resources
- `capability_statement_url`: Canonical URL(s) of the CapabilityStatement(s) to expand
  - Single URL: `"https://example.org/CS"`
  - JSON array: `'["url1", "url2"]'` (note the quotes!)

**Options:**
- `--verbose` or `-v`: Enables detailed logging
- `--no-clean`: Do not clean output directory before expansion (by default, the output directory is cleaned to avoid stale files)
- `--expectation-filter {SHALL|SHOULD|MAY}`: Filter imports by minimum expectation level. `SHALL` imports only SHALL, `SHOULD` imports SHALL+SHOULD, `MAY` imports SHALL+SHOULD+MAY. Default: import all expectations. **Note:** `SHOULD-NOT` is never imported regardless of filter.

### Local Examples

**Single CapabilityStatement:**
```bash
python capability_statement_expander.py ./fhir-resources ./output "http://example.org/CapabilityStatement/MyCapabilityStatement" --verbose
```

**Multiple CapabilityStatements:**
```bash
python capability_statement_expander.py ./fhir-resources ./output '["http://example.org/CapabilityStatement/CS1", "http://example.org/CapabilityStatement/CS2"]' --verbose
```

## 🧪 Tests

The project includes automated tests:

```bash
# Run tests
python test_expander.py

# For ISiK tests (if ISiK resources are available)  
python capability_statement_expander.py ./isik_resources ./output_isik "https://gematik.de/fhir/isik/CapabilityStatement/ISiKCapabilityStatementSubscriptionServerAkteur"
```

## 📁 Directory Structure

### Input Directory
```
input/
├── CapabilityStatement-MyCS.json
├── CapabilityStatement-ImportedCS.json
├── profiles/
│   ├── Patient-Profile.json
│   └── Observation-Profile.json
├── examples/
│   ├── Patient-Example.json
│   └── Observation-Example.json
└── terminology/
    ├── ValueSet-Codes.json
    └── CodeSystem-MySystem.json
```

### Output Directory (after expansion)
```
output/
├── CapabilityStatement-example-base-capability-expanded.json  # ✨ Expanded CapabilityStatement  
├── StructureDefinition-PatientProfile.json                    # 🏗️ Patient profile
├── StructureDefinition-ObservationProfile.json                # 🏗️ Observation profile  
├── ValueSet-PatientStatus.json                                # 📋 Patient status values
├── SearchParameter-Patient-identifier.json                    # 🔍 Patient identifier search
├── CapabilityStatement-example-base-capability.json           # 📄 Original CapabilityStatement
├── CapabilityStatement-imported-capability.json               # 📥 Imported CapabilityStatement
├── Patient-example-1.json                                     # 👤 Example detected via meta.profile
└── Observation-example-1.json                                 # 📊 Example detected via meta.profile
```

**📝 Note:** The expanded CapabilityStatement has:
- **File name**: Original ID + `-expanded` suffix (e.g., `CapabilityStatement-MyCS-expanded.json`)
- **Resource ID**: Original ID + `-expanded` suffix (e.g., `"id": "MyCS-expanded"`)
- **Canonical URL**: Original URL + `-expanded` suffix (e.g., `"url": "https://example.org/CS-expanded"`)
- **Name & Title**: Original + `Expanded` suffix (e.g., `"name": "MyCSExpanded"`)
- **No imports**: All `imports` and `_imports` fields are removed after expansion

## 🔧 How It Works

The expander performs the following steps:

1. **Initial Analysis**: Loads the base CapabilityStatement and analyzes its structure
2. **Import Resolution**: Recursively resolves all `imports` and `instantiates` references
   - Supports multi-level imports (CS1 → CS2 → CS3, CS4)
   - Respects expectation filters (SHALL/SHOULD/MAY)
3. **Profile Collection**: Extracts all StructureDefinition references from `supportedProfile` fields
4. **Binding Analysis**: Analyzes StructureDefinitions for ValueSet and CodeSystem bindings
5. **Dependency Resolution**: Follows references in SearchParameters and OperationDefinitions
6. **Example Detection**: Searches for Examples via `meta.profile` references to collected profiles
7. **Iterative Processing**: Repeats analysis until no new resources are found
8. **Final Assembly**: Creates expanded CapabilityStatement with modified metadata:
   - Canonical URL: `{original-url}-expanded` (e.g., `https://example.org/CS-expanded`)
   - Resource ID: `{original-id}-expanded`
   - Name/Title: `{original}Expanded` / `{original} (Expanded)`
   - Removes all `imports` and `_imports` fields
9. **Resource Copy**: Copies all referenced resources (profiles, ValueSets, examples, etc.)

### 🎯 Smart Example Detection

The expander includes intelligent example detection that:
- Scans all resources in the directory structure
- Identifies resources with `meta.profile` references
- Matches these references against collected `supportedProfile` URLs
- Automatically includes matching examples in the expanded output

For example, if your CapabilityStatement references:
```json
"supportedProfile": [
  "http://example.org/StructureDefinition/PatientProfile"
]
```

And you have an example like:
```json
{
  "resourceType": "Patient",
  "meta": {
    "profile": ["http://example.org/StructureDefinition/PatientProfile"]
  },
  // ... rest of example
}
```

The example will be automatically detected and included in the expanded package.

## 🔧 FHIR CapabilityStatement Import Mechanism

The script supports the following import mechanisms from the FHIR standard:

### `imports`
```json
{
  "resourceType": "CapabilityStatement",
  "imports": [
    "http://example.org/CapabilityStatement/BaseCapability",
    "CapabilityStatement/AnotherCapability"
  ]
}
```

### `instantiates`
```json
{
  "resourceType": "CapabilityStatement", 
  "instantiates": [
    "http://hl7.org/fhir/CapabilityStatement/base"
  ]
}
```

## 🎯 Use Cases

- **🏥 Implementation Guide Development**: Automatically collect all dependencies
- **📦 FHIR Package Creation**: Complete resource collections for distribution
- **✅ Validation**: Verify completeness of CapabilityStatements
- **🔄 CI/CD**: Automated processing in GitHub Actions workflows

## 🧑‍💻 Development

```bash
# Clone repository
git clone https://github.com/patrickwerner/CapabilityStatementExpander.git
cd CapabilityStatementExpander

# Run tests
python test_expander.py

# Test local development
python capability_statement_expander.py ./examples ./output_test "http://example.org/CapabilityStatement/example-base-capability" --verbose
```

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🤝 Contributing

Contributions are welcome! Please create an issue or submit a pull request.

---

**Created for the FHIR Community** 🏥✨

