#!/usr/bin/env python3
"""
Unit tests for find_resource_by_reference() edge cases
Tests the reference matching logic to ensure correct behavior for:
- Canonical URL exact matching
- Simple ID matching via last segment
- Prevention of false positives (Bundle vs ISiKBerichtBundle)
- Scheme-agnostic matching (http vs https)
"""

import sys
import tempfile
from pathlib import Path
import json

# Import the expander
sys.path.insert(0, str(Path(__file__).parent))
from capability_statement_expander import CapabilityStatementExpander

def create_test_resource(resource_id: str, resource_type: str, url: str = None, version: str = None) -> dict:
    """Helper to create a minimal FHIR resource"""
    resource = {
        "resourceType": resource_type,
        "id": resource_id
    }
    if url:
        resource["url"] = url
    if version:
        resource["version"] = version
    return resource

def setup_test_environment():
    """Creates a temporary test environment with various test resources"""
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    
    # Create test resources with different ID/URL patterns
    test_resources = [
        # Simple ID-based resources (no URL)
        create_test_resource("Patient", "Patient"),
        create_test_resource("Observation", "Observation"),
        
        # Resources with canonical URLs
        create_test_resource("PatientProfile", "StructureDefinition", 
                           "http://example.org/fhir/StructureDefinition/PatientProfile"),
        create_test_resource("Bundle", "StructureDefinition",
                           "http://hl7.org/fhir/StructureDefinition/Bundle"),
        
        # Edge case: URL ending with "Bundle" but different resource
        create_test_resource("ISiKBerichtBundle", "StructureDefinition",
                           "https://gematik.de/fhir/isik/StructureDefinition/ISiKBerichtBundle"),
        
        # Resources with versions
        create_test_resource("PatientProfileV1", "StructureDefinition",
                           "http://example.org/fhir/StructureDefinition/PatientProfileV1",
                           "1.0.0"),
        create_test_resource("PatientProfileV2", "StructureDefinition",
                           "http://example.org/fhir/StructureDefinition/PatientProfileV2",
                           "2.0.0"),
        
        # Resource with ID containing another resource name
        create_test_resource("ISiKPatient", "StructureDefinition",
                           "https://gematik.de/fhir/isik/StructureDefinition/ISiKPatient"),
    ]
    
    # Write resources to files
    for resource in test_resources:
        resource_id = resource['id']
        resource_type = resource['resourceType']
        filename = f"{resource_type}-{resource_id}.json"
        filepath = temp_path / filename
        
        with open(filepath, 'w') as f:
            json.dump(resource, f, indent=2)
    
    return temp_path

def test_exact_canonical_url_match():
    """Test that canonical URLs must match exactly"""
    print("\n🧪 Test: Exact Canonical URL Match")
    
    temp_dir = setup_test_environment()
    output_dir = tempfile.mkdtemp()
    
    expander = CapabilityStatementExpander(
        str(temp_dir), 
        output_dir, 
        "dummy", 
        verbose=False, 
        clean_output=False
    )
    expander.load_all_resources()
    
    # Test exact match
    result = expander.find_resource_by_reference("http://hl7.org/fhir/StructureDefinition/Bundle")
    assert result is not None, "Should find exact canonical URL"
    assert result['resource']['id'] == "Bundle", f"Found wrong resource: {result['resource']['id']}"
    print("  ✅ Exact canonical URL match works")
    
    # Test that it does NOT match similar URLs
    result = expander.find_resource_by_reference("http://hl7.org/fhir/StructureDefinition/ISiKBerichtBundle")
    assert result is None, "Should NOT find ISiKBerichtBundle when searching for Bundle"
    print("  ✅ Does not match different canonical URLs")
    
    return True

def test_false_positive_prevention():
    """Test that 'Bundle' does not match 'ISiKBerichtBundle'"""
    print("\n🧪 Test: False Positive Prevention (Bundle vs ISiKBerichtBundle)")
    
    temp_dir = setup_test_environment()
    output_dir = tempfile.mkdtemp()
    
    expander = CapabilityStatementExpander(
        str(temp_dir), 
        output_dir, 
        "dummy", 
        verbose=False, 
        clean_output=False
    )
    expander.load_all_resources()
    
    # Search for FHIR core Bundle
    result = expander.find_resource_by_reference("http://hl7.org/fhir/StructureDefinition/Bundle")
    assert result is not None, "Should find FHIR core Bundle"
    assert result['resource']['id'] == "Bundle", f"Should find 'Bundle', got '{result['resource']['id']}'"
    assert "ISiKBerichtBundle" not in result['resource']['id'], "Should NOT match ISiKBerichtBundle"
    print("  ✅ Correctly finds 'Bundle' without matching 'ISiKBerichtBundle'")
    
    # Search for ISiKBerichtBundle explicitly
    result = expander.find_resource_by_reference("https://gematik.de/fhir/isik/StructureDefinition/ISiKBerichtBundle")
    assert result is not None, "Should find ISiKBerichtBundle"
    assert result['resource']['id'] == "ISiKBerichtBundle", f"Should find 'ISiKBerichtBundle', got '{result['resource']['id']}'"
    print("  ✅ Correctly finds 'ISiKBerichtBundle' when explicitly requested")
    
    return True

def test_simple_id_matching():
    """Test that simple IDs (e.g., 'Patient') match via last segment"""
    print("\n🧪 Test: Simple ID Matching (last segment)")
    
    temp_dir = setup_test_environment()
    output_dir = tempfile.mkdtemp()
    
    expander = CapabilityStatementExpander(
        str(temp_dir), 
        output_dir, 
        "dummy", 
        verbose=False, 
        clean_output=False
    )
    expander.load_all_resources()
    
    # Test simple ID match
    result = expander.find_resource_by_reference("Patient")
    assert result is not None, "Should find Patient by simple ID"
    assert result['resource']['id'] == "Patient", f"Found wrong resource: {result['resource']['id']}"
    print("  ✅ Simple ID 'Patient' matches")
    
    # Test that it does NOT match ISiKPatient when searching for Patient
    result = expander.find_resource_by_reference("Patient")
    assert result is not None, "Should find some Patient resource"
    # The ID should be exactly "Patient", not "ISiKPatient"
    assert result['resource']['id'] == "Patient", f"Should match 'Patient', not 'ISiKPatient'. Got: {result['resource']['id']}"
    print("  ✅ Simple ID 'Patient' does not match 'ISiKPatient'")
    
    return True

def test_scheme_exact_matching():
    """Test that http:// and https:// are treated as DIFFERENT (no scheme-agnostic matching)"""
    print("\n🧪 Test: Scheme Exact Matching (http:// != https://)")
    
    temp_dir = setup_test_environment()
    output_dir = tempfile.mkdtemp()
    
    expander = CapabilityStatementExpander(
        str(temp_dir), 
        output_dir, 
        "dummy", 
        verbose=False, 
        clean_output=False
    )
    expander.load_all_resources()
    
    # Resource is stored with http://
    # Try to find it with https:// (should NOT work)
    result = expander.find_resource_by_reference("https://example.org/fhir/StructureDefinition/PatientProfile")
    assert result is None, "Should NOT find resource with different scheme (https:// when resource has http://)"
    print("  ✅ Different schemes do not match (https:// != http://)")
    
    # Exact match should work
    result = expander.find_resource_by_reference("http://example.org/fhir/StructureDefinition/PatientProfile")
    assert result is not None, "Should find resource with exact scheme match"
    print("  ✅ Exact scheme match works (http:// == http://)")
    
    return True

def test_version_suffix_matching():
    """Test that version suffixes (|1.0.0) are validated against resource.version"""
    print("\n🧪 Test: Version Suffix Matching and Validation")
    
    temp_dir = setup_test_environment()
    output_dir = tempfile.mkdtemp()
    
    expander = CapabilityStatementExpander(
        str(temp_dir), 
        output_dir, 
        "dummy", 
        verbose=False, 
        clean_output=False
    )
    expander.load_all_resources()
    
    # Test correct version match
    result = expander.find_resource_by_reference("http://example.org/fhir/StructureDefinition/PatientProfileV1|1.0.0")
    assert result is not None, "Should find resource with correct version"
    assert result['resource']['version'] == "1.0.0", "Should have correct version"
    print("  ✅ Correct version match works")
    
    # Test version mismatch (should return None and log error)
    result = expander.find_resource_by_reference("http://example.org/fhir/StructureDefinition/PatientProfileV1|2.0.0")
    assert result is None, "Should NOT find resource with wrong version (should log error)"
    print("  ✅ Version mismatch returns None (error logged)")
    
    # Test resource without version suffix still works
    result = expander.find_resource_by_reference("http://example.org/fhir/StructureDefinition/PatientProfileV1")
    assert result is not None, "Should find resource without version suffix"
    print("  ✅ Resource lookup without version suffix works")
    
    return True

def test_no_substring_matching_for_urls():
    """Test that canonical URLs do NOT use substring matching"""
    print("\n🧪 Test: No Substring Matching for Canonical URLs")
    
    temp_dir = setup_test_environment()
    output_dir = tempfile.mkdtemp()
    
    expander = CapabilityStatementExpander(
        str(temp_dir), 
        output_dir, 
        "dummy", 
        verbose=False, 
        clean_output=False
    )
    expander.load_all_resources()
    
    # Try to find a resource with a partial URL (should NOT work)
    result = expander.find_resource_by_reference("fhir/StructureDefinition/Patient")
    # This should NOT match via substring, only via ID fallback if ID="Patient" exists
    # Since we have a Patient resource with ID="Patient", it might match via ID fallback
    # But it should NOT match PatientProfile or ISiKPatient
    if result is not None:
        # If it found something, it should be via ID fallback, not substring match
        assert result['resource']['id'] == "Patient", f"Partial URL should only match via ID fallback. Got: {result['resource']['id']}"
        print("  ✅ Partial URL matched via ID fallback only (expected)")
    else:
        print("  ✅ Partial URL did not match (also acceptable)")
    
    return True

def test_last_segment_exact_match():
    """Test that last segment matching is exact, not endswith"""
    print("\n🧪 Test: Last Segment Exact Match (not endswith)")
    
    temp_dir = setup_test_environment()
    output_dir = tempfile.mkdtemp()
    
    expander = CapabilityStatementExpander(
        str(temp_dir), 
        output_dir, 
        "dummy", 
        verbose=False, 
        clean_output=False
    )
    expander.load_all_resources()
    
    # Search by simple ID "Bundle"
    result = expander.find_resource_by_reference("Bundle")
    assert result is not None, "Should find Bundle resource"
    
    # Verify it found the EXACT "Bundle", not "ISiKBerichtBundle"
    assert result['resource']['id'] == "Bundle", f"Should match 'Bundle' exactly, got '{result['resource']['id']}'"
    print("  ✅ Last segment 'Bundle' matches exactly, not 'ISiKBerichtBundle'")
    
    return True

def run_all_tests():
    """Run all test cases"""
    print("=" * 70)
    print("FHIR CapabilityStatement Expander - Reference Matching Tests")
    print("=" * 70)
    
    tests = [
        ("Exact Canonical URL Match", test_exact_canonical_url_match),
        ("False Positive Prevention", test_false_positive_prevention),
        ("Simple ID Matching", test_simple_id_matching),
        ("Scheme Exact Matching", test_scheme_exact_matching),
        ("Version Suffix Matching", test_version_suffix_matching),
        ("No Substring Matching for URLs", test_no_substring_matching_for_urls),
        ("Last Segment Exact Match", test_last_segment_exact_match),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"  ❌ {test_name} FAILED")
        except AssertionError as e:
            failed += 1
            print(f"  ❌ {test_name} FAILED: {e}")
        except Exception as e:
            failed += 1
            print(f"  ❌ {test_name} ERROR: {e}")
    
    print("\n" + "=" * 70)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    if failed == 0:
        print("✅ All tests passed!")
        return 0
    else:
        print(f"❌ {failed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())
