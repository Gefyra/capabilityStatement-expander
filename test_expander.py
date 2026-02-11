#!/usr/bin/env python3
"""
Comprehensive test suite for the FHIR CapabilityStatement Expander

Tests:
1. Basic expansion with examples directory
2. Expectation upgrade (SHALL > SHOULD > MAY > SHOULD-NOT)
3. Multi-level import chain expectation propagation
4. Reference matching strategies (canonical URLs, FHIR references, versioning)
"""

import os
import sys
import json
import tempfile
import shutil
import subprocess
import unittest
from pathlib import Path

# Import expander for direct testing
from capability_statement_expander import CapabilityStatementExpander

def test_basic_expansion():
    """Test basic expansion with examples directory"""
    print("\n" + "=" * 70)
    print("TEST 1: Basic Expansion")
    print("=" * 70)
    
    # Determine script directory
    script_dir = Path(__file__).parent
    expander_script = script_dir / "capability_statement_expander.py"
    examples_dir = script_dir / "examples"
    
    print(f"📁 Script directory: {script_dir}")
    print(f"📝 Expander script: {expander_script}")
    print(f"📂 Examples: {examples_dir}")
    
    # Check if files exist
    if not expander_script.exists():
        print(f"❌ Expander script not found: {expander_script}")
        return False
        
    if not examples_dir.exists():
        print(f"❌ Examples directory not found: {examples_dir}")
        return False
    
    # Create temporary output directory
    with tempfile.TemporaryDirectory() as temp_output:
        output_dir = Path(temp_output)
        
        print(f"📤 Output directory: {output_dir}")
        
        try:
            # Run the expander
            cmd = [
                sys.executable,
                str(expander_script),
                str(examples_dir),
                str(output_dir),
                "http://example.org/CapabilityStatement/example-base-capability",
                "--verbose"
            ]
            
            print(f"🚀 Executing: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Error executing script:")
                print(f"STDERR: {result.stderr}")
                return False
            
            print("✅ Script executed successfully")
            
            # Check output files
            expected_files = [
                "CapabilityStatement-example-base-capability-expanded.json"
            ]
            
            for expected_file in expected_files:
                file_path = output_dir / expected_file
                if not file_path.exists():
                    print(f"❌ Missing file: {expected_file}")
                    return False
                print(f"✅ File created: {expected_file}")
            
            # Show all created files
            all_files = list(output_dir.rglob("*.json"))
            print(f"\n📁 All created files ({len(all_files)}):")
            for file in sorted(all_files):
                relative_path = file.relative_to(output_dir)
                file_size = file.stat().st_size
                print(f"  📄 {relative_path} ({file_size} bytes)")
            
            print("\n✅ TEST 1 PASSED: Basic expansion works correctly")
            return True
            
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False

def test_expectation_upgrade():
    """Test that SHALL expectation upgrades MAY expectation"""
    print("\n" + "=" * 70)
    print("TEST 2: Expectation Upgrade (SHALL > MAY)")
    print("=" * 70)
    
    # Create test data with conflicting expectations
    test_cs_weak = {
        "resourceType": "CapabilityStatement",
        "id": "test-weak",
        "url": "http://test.example/CapabilityStatement/test-weak",
        "status": "active",
        "kind": "requirements",
        "fhirVersion": "4.0.1",
        "format": ["application/fhir+json"],
        "rest": [{
            "mode": "server",
            "resource": [{
                "type": "Patient",
                "supportedProfile": ["http://test.example/StructureDefinition/TestProfile"],
                "_supportedProfile": [{
                    "extension": [{
                        "url": "http://hl7.org/fhir/StructureDefinition/capabilitystatement-expectation",
                        "valueCode": "MAY"
                    }]
                }],
                "searchParam": [{
                    "name": "identifier",
                    "type": "token",
                    "extension": [{
                        "url": "http://hl7.org/fhir/StructureDefinition/capabilitystatement-expectation",
                        "valueCode": "MAY"
                    }]
                }]
            }]
        }]
    }
    
    test_cs_strong = {
        "resourceType": "CapabilityStatement",
        "id": "test-strong",
        "url": "http://test.example/CapabilityStatement/test-strong",
        "status": "active",
        "kind": "requirements",
        "fhirVersion": "4.0.1",
        "format": ["application/fhir+json"],
        "imports": ["http://test.example/CapabilityStatement/test-weak"],
        "rest": [{
            "mode": "server",
            "resource": [{
                "type": "Patient",
                "supportedProfile": ["http://test.example/StructureDefinition/TestProfile"],
                "_supportedProfile": [{
                    "extension": [{
                        "url": "http://hl7.org/fhir/StructureDefinition/capabilitystatement-expectation",
                        "valueCode": "SHALL"
                    }]
                }],
                "searchParam": [{
                    "name": "identifier",
                    "type": "token",
                    "extension": [{
                        "url": "http://hl7.org/fhir/StructureDefinition/capabilitystatement-expectation",
                        "valueCode": "SHALL"
                    }]
                }]
            }]
        }]
    }
    
    print("Setup:")
    print("  - Weak CS: Profile=MAY, SearchParam=MAY")
    print("  - Strong CS: Profile=SHALL, SearchParam=SHALL (imports Weak)")
    print("  - Expected: SHALL wins")
    
    # Create temp directories
    with tempfile.TemporaryDirectory() as input_dir, tempfile.TemporaryDirectory() as output_dir:
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        # Write test files
        with open(input_path / "CapabilityStatement-test-weak.json", 'w') as f:
            json.dump(test_cs_weak, f, indent=2)
        
        with open(input_path / "CapabilityStatement-test-strong.json", 'w') as f:
            json.dump(test_cs_strong, f, indent=2)
        
        # Run expander
        expander = CapabilityStatementExpander(
            str(input_path),
            str(output_path),
            ["http://test.example/CapabilityStatement/test-strong"],
            verbose=False,
            clean_output=True
        )
        
        expander.run()
        
        # Check result
        expanded_file = output_path / "CapabilityStatement-test-strong-expanded.json"
        
        if not expanded_file.exists():
            print("❌ Expanded file not found!")
            return False
        
        with open(expanded_file) as f:
            expanded = json.load(f)
        
        # Check supportedProfile expectation
        profile_ext = expanded['rest'][0]['resource'][0]['_supportedProfile'][0]
        profile_expectation = None
        for ext in profile_ext.get('extension', []):
            if 'capabilitystatement-expectation' in ext.get('url', ''):
                profile_expectation = ext.get('valueCode')
        
        # Check searchParam expectation
        search_param = expanded['rest'][0]['resource'][0]['searchParam'][0]
        search_expectation = None
        for ext in search_param.get('extension', []):
            if 'capabilitystatement-expectation' in ext.get('url', ''):
                search_expectation = ext.get('valueCode')
        
        print(f"\nResults:")
        print(f"  supportedProfile expectation: {profile_expectation}")
        print(f"  searchParam expectation: {search_expectation}")
        
        # Verify
        if profile_expectation != "SHALL":
            print(f"❌ Profile expectation is {profile_expectation}, expected SHALL")
            return False
        
        if search_expectation != "SHALL":
            print(f"❌ SearchParam expectation is {search_expectation}, expected SHALL")
            return False
        
        print("\n✅ TEST 2 PASSED: Expectation upgrade works correctly")
        return True

def test_multi_level_expectation():
    """Test that SHALL expectation propagates through multiple import levels"""
    print("\n" + "=" * 70)
    print("TEST 3: Multi-Level Expectation Propagation")
    print("=" * 70)
    
    # CS3: Defines identifier with SHALL (deepest level)
    test_cs3 = {
        "resourceType": "CapabilityStatement",
        "id": "test-level3",
        "url": "http://test.example/CapabilityStatement/test-level3",
        "status": "active",
        "kind": "requirements",
        "fhirVersion": "4.0.1",
        "format": ["application/fhir+json"],
        "rest": [{
            "mode": "server",
            "resource": [{
                "type": "Patient",
                "searchParam": [{
                    "name": "identifier",
                    "type": "token",
                    "extension": [{
                        "url": "http://hl7.org/fhir/StructureDefinition/capabilitystatement-expectation",
                        "valueCode": "SHALL"
                    }]
                }]
            }]
        }]
    }
    
    # CS2: Imports CS3 AND defines identifier with MAY (middle level)
    test_cs2 = {
        "resourceType": "CapabilityStatement",
        "id": "test-level2",
        "url": "http://test.example/CapabilityStatement/test-level2",
        "status": "active",
        "kind": "requirements",
        "fhirVersion": "4.0.1",
        "format": ["application/fhir+json"],
        "imports": ["http://test.example/CapabilityStatement/test-level3"],
        "rest": [{
            "mode": "server",
            "resource": [{
                "type": "Patient",
                "searchParam": [{
                    "name": "identifier",
                    "type": "token",
                    "extension": [{
                        "url": "http://hl7.org/fhir/StructureDefinition/capabilitystatement-expectation",
                        "valueCode": "MAY"
                    }]
                }]
            }]
        }]
    }
    
    # CS1: Imports CS2 only (top level)
    test_cs1 = {
        "resourceType": "CapabilityStatement",
        "id": "test-level1",
        "url": "http://test.example/CapabilityStatement/test-level1",
        "status": "active",
        "kind": "requirements",
        "fhirVersion": "4.0.1",
        "format": ["application/fhir+json"],
        "imports": ["http://test.example/CapabilityStatement/test-level2"],
        "rest": [{
            "mode": "server"
        }]
    }
    
    print("Import chain:")
    print("  CS1 (Base)")
    print("   └─ imports CS2 (identifier: MAY)")
    print("       └─ imports CS3 (identifier: SHALL)")
    print("  Expected: CS1.identifier = SHALL")
    
    # Create temp directories
    with tempfile.TemporaryDirectory() as input_dir, tempfile.TemporaryDirectory() as output_dir:
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        # Write test files
        (input_path / "CapabilityStatement-test-level3.json").write_text(json.dumps(test_cs3, indent=2))
        (input_path / "CapabilityStatement-test-level2.json").write_text(json.dumps(test_cs2, indent=2))
        (input_path / "CapabilityStatement-test-level1.json").write_text(json.dumps(test_cs1, indent=2))
        
        # Run expander
        expander = CapabilityStatementExpander(
            str(input_path),
            str(output_path),
            ["http://test.example/CapabilityStatement/test-level1"],
            verbose=False,
            clean_output=True
        )
        
        expander.run()
        
        # Check result
        expanded_file = output_path / "CapabilityStatement-test-level1-expanded.json"
        
        if not expanded_file.exists():
            print("❌ Expanded file not found!")
            return False
        
        with open(expanded_file) as f:
            expanded = json.load(f)
        
        # Check searchParam expectation
        resources = expanded['rest'][0].get('resource', [])
        if not resources:
            print("❌ No resources in expanded CS!")
            return False
        
        patient_resource = next((r for r in resources if r.get('type') == 'Patient'), None)
        if not patient_resource:
            print("❌ No Patient resource found!")
            return False
        
        search_params = patient_resource.get('searchParam', [])
        identifier_param = next((p for p in search_params if p.get('name') == 'identifier'), None)
        
        if not identifier_param:
            print("❌ identifier searchParam not found!")
            return False
        
        # Extract expectation
        expectation = None
        for ext in identifier_param.get('extension', []):
            if 'capabilitystatement-expectation' in ext.get('url', ''):
                expectation = ext.get('valueCode')
        
        print(f"\nResult: identifier expectation = {expectation}")
        
        # Verify
        if expectation != "SHALL":
            print(f"❌ Expected SHALL, got {expectation}")
            return False
        
        print("\n✅ TEST 3 PASSED: Multi-level expectation propagation works correctly")
        return True

def test_reference_matching():
    """Test reference matching strategies using examples/ directory resources"""
    print("\n" + "=" * 70)
    print("TEST 4: Reference Matching Strategies")
    print("=" * 70)
    
    script_dir = Path(__file__).parent
    examples_dir = script_dir / "examples"
    
    print(f"📂 Examples directory: {examples_dir}")
    
    # Create temp output directory
    with tempfile.TemporaryDirectory() as temp_output:
        output_dir = Path(temp_output)
        
        # Create expander with examples directory
        expander = CapabilityStatementExpander(
            str(examples_dir),
            str(output_dir),
            "dummy",
            verbose=False,
            clean_output=False
        )
        expander.load_all_resources()
        
        print(f"📊 Loaded {len(expander.all_resources)} resources from examples/")
        
        # Test 1: Exact canonical URL matching
        print("\n🔍 Test 4.1: Exact canonical URL matching")
        result = expander.find_resource_by_reference(
            "http://hl7.org/fhir/StructureDefinition/Bundle"
        )
        if result and result['resource']['id'] == "Bundle":
            print("  ✅ Found Bundle via canonical URL")
        else:
            print("  ❌ Failed to find Bundle")
            return False
        
        # Test 2: False positive prevention (Bundle vs ISiKBerichtBundle)
        print("\n🔍 Test 4.2: False positive prevention")
        result = expander.find_resource_by_reference(
            "http://hl7.org/fhir/StructureDefinition/Bundle"
        )
        if result and result['resource']['id'] == "Bundle" and result['resource']['id'] != "ISiKBerichtBundle":
            print("  ✅ Bundle URL does not match ISiKBerichtBundle")
        else:
            print("  ❌ False positive detected")
            return False
        
        # Test 3: Scheme exact matching (http vs https)
        print("\n🔍 Test 4.3: Scheme exact matching (http vs https)")
        result = expander.find_resource_by_reference(
            "https://example.org/fhir/StructureDefinition/PatientProfile"  # https
        )
        if result is None:
            print("  ✅ https:// does not match http:// resource")
        else:
            print("  ❌ Scheme should not match")
            return False
        
        result = expander.find_resource_by_reference(
            "http://example.org/fhir/StructureDefinition/PatientProfile"  # http
        )
        if result is not None:
            print("  ✅ Exact http:// scheme match works")
        else:
            print("  ❌ Exact scheme match failed")
            return False
        
        # Test 4: Version validation
        print("\n🔍 Test 4.4: Version validation")
        result = expander.find_resource_by_reference(
            "http://example.org/fhir/StructureDefinition/PatientProfileV1|1.0.0"
        )
        if result is not None:
            print("  ✅ Correct version found")
        else:
            print("  ❌ Version matching failed")
            return False
        
        result = expander.find_resource_by_reference(
            "http://example.org/fhir/StructureDefinition/PatientProfileV1|2.0.0"
        )
        if result is None:
            print("  ✅ Wrong version correctly rejected")
        else:
            print("  ❌ Wrong version should not match")
            return False
        
        # Test 5: Simple IDs without ResourceType are NOT allowed
        print("\n🔍 Test 4.5: Simple IDs require ResourceType")
        result = expander.find_resource_by_reference("patient-123")
        if result is None:
            print("  ✅ Simple ID without ResourceType rejected")
        else:
            print("  ❌ Simple ID should not be found")
            return False
        
        result = expander.find_resource_by_reference("Patient/patient-123")
        if result and result['resource']['id'] == "patient-123":
            print("  ✅ FHIR reference with ResourceType works")
        else:
            print("  ❌ FHIR reference failed")
            return False
        
        # Test 6: FHIR relative reference
        print("\n🔍 Test 4.6: FHIR relative reference (ResourceType/ID)")
        result = expander.find_resource_by_reference("Patient/patient-123")
        if result and result['resource']['resourceType'] == "Patient" and result['resource']['id'] == "patient-123":
            print("  ✅ Relative FHIR reference works")
        else:
            print("  ❌ Relative reference failed")
            return False
        
        # Test 7: FHIR absolute reference
        print("\n🔍 Test 4.7: FHIR absolute reference (http://base/ResourceType/ID)")
        result = expander.find_resource_by_reference(
            "http://example.org/fhir/Patient/patient-123"
        )
        if result and result['resource']['id'] == "patient-123":
            print("  ✅ Absolute FHIR reference works")
        else:
            print("  ❌ Absolute reference failed")
            return False
        
        # Test 8: ResourceType mismatch
        print("\n🔍 Test 4.8: ResourceType validation")
        result = expander.find_resource_by_reference("Patient/patient-123")
        if result is not None:
            print("  ✅ Patient/patient-123 found")
        else:
            print("  ❌ Should find Patient/patient-123")
            return False
        
        result = expander.find_resource_by_reference("Observation/patient-123")
        if result is None:
            print("  ✅ Observation/patient-123 correctly rejected (wrong type)")
        else:
            print("  ❌ ResourceType mismatch should fail")
            return False
        
        # Test 9: Non-existent resources
        print("\n🔍 Test 4.9: Non-existent resources")
        result = expander.find_resource_by_reference("http://example.org/nonexistent")
        if result is None:
            print("  ✅ Non-existent URL returns None")
        else:
            print("  ❌ Should not find non-existent resource")
            return False
        
        result = expander.find_resource_by_reference("Patient/nonexistent")
        if result is None:
            print("  ✅ Non-existent FHIR reference returns None")
        else:
            print("  ❌ Should not find non-existent resource")
            return False
        
        print("\n✅ TEST 4 PASSED: All reference matching strategies work correctly")
        return True

def main():
    """Main test runner"""
    print("=" * 70)
    print("FHIR CapabilityStatement Expander - Test Suite")
    print("=" * 70)
    
    # Run all tests
    tests = [
        ("Basic Expansion", test_basic_expansion),
        ("Expectation Upgrade", test_expectation_upgrade),
        ("Multi-Level Expectation", test_multi_level_expectation),
        ("Reference Matching", test_reference_matching)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print("=" * 70)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests completed successfully!")
        sys.exit(0)
    else:
        print(f"❌ {total - passed} test(s) failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()