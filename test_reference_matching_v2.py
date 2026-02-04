#!/usr/bin/env python3
"""
Updated unit tests for find_resource_by_reference() with FHIR Reference support
Tests 2 matching strategies:
1. Exact canonical URL matching (for StructureDefinitions, ValueSets, etc.)
2. FHIR Reference matching with MANDATORY ResourceType validation
   - Relative: Patient/patient-123 (ResourceType + ID)
   - Absolute: http://base/Patient/patient-123 (ResourceType + ID)
   - Simple IDs WITHOUT ResourceType are NOT allowed
"""

import sys
import tempfile
from pathlib import Path
import json
import unittest

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

class TestReferenceMatching(unittest.TestCase):
    """Test suite for reference matching strategies"""
    
    def setUp(self):
        """Set up test environment before each test"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.output_dir = Path(tempfile.mkdtemp())
        
        # Create test resources
        test_resources = [
            # Canonical URL resources (profiles, valuesets, etc.)
            create_test_resource("PatientProfile", "StructureDefinition", 
                               "http://example.org/fhir/StructureDefinition/PatientProfile"),
            create_test_resource("Bundle", "StructureDefinition",
                               "http://hl7.org/fhir/StructureDefinition/Bundle"),
            create_test_resource("ISiKBerichtBundle", "StructureDefinition",
                               "https://gematik.de/fhir/isik/StructureDefinition/ISiKBerichtBundle"),
            
            # Resource instances (patients, observations, etc.)
            create_test_resource("patient-123", "Patient"),
            create_test_resource("obs-456", "Observation"),
            create_test_resource("encounter-789", "Encounter"),
            
            # Versioned resources
            create_test_resource("PatientProfileV1", "StructureDefinition",
                               "http://example.org/fhir/StructureDefinition/PatientProfileV1", "1.0.0"),
            create_test_resource("PatientProfileV2", "StructureDefinition",
                               "http://example.org/fhir/StructureDefinition/PatientProfileV2", "2.0.0"),
        ]
        
        # Write resources to files
        for resource in test_resources:
            filename = f"{resource['resourceType']}-{resource['id']}.json"
            with open(self.temp_dir / filename, 'w') as f:
                json.dump(resource, f, indent=2)
        
        # Create expander
        self.expander = CapabilityStatementExpander(
            str(self.temp_dir), 
            str(self.output_dir), 
            "dummy", 
            verbose=True,  # Enable verbose for debugging
            clean_output=False
        )
        self.expander.load_all_resources()
    
    def test_strategy_1_exact_canonical_url(self):
        """Test Strategy 1: Exact canonical URL matching"""
        result = self.expander.find_resource_by_reference(
            "http://hl7.org/fhir/StructureDefinition/Bundle"
        )
        self.assertIsNotNone(result)
        self.assertEqual(result['resource']['id'], "Bundle")
    
    def test_strategy_1_false_positive_prevention(self):
        """Test that 'Bundle' URL does not match 'ISiKBerichtBundle'"""
        result = self.expander.find_resource_by_reference(
            "http://hl7.org/fhir/StructureDefinition/Bundle"
        )
        self.assertIsNotNone(result)
        self.assertEqual(result['resource']['id'], "Bundle")
        self.assertNotEqual(result['resource']['id'], "ISiKBerichtBundle")
    
    def test_strategy_1_scheme_exact_matching(self):
        """Test that http:// and https:// must match exactly"""
        # Resource has http://, search with https:// should NOT match
        result = self.expander.find_resource_by_reference(
            "https://example.org/fhir/StructureDefinition/PatientProfile"
        )
        self.assertIsNone(result)
        
        # Exact match should work
        result = self.expander.find_resource_by_reference(
            "http://example.org/fhir/StructureDefinition/PatientProfile"
        )
        self.assertIsNotNone(result)
    
    def test_strategy_1_version_validation(self):
        """Test version suffix validation with fallback for multiple versions"""
        # Correct version
        result = self.expander.find_resource_by_reference(
            "http://example.org/fhir/StructureDefinition/PatientProfileV1|1.0.0"
        )
        self.assertIsNotNone(result)
        
        # Wrong version - should not find it (no fallback resource with that version)
        result = self.expander.find_resource_by_reference(
            "http://example.org/fhir/StructureDefinition/PatientProfileV1|2.0.0"
        )
        self.assertIsNone(result)
    
    def test_strategy_2_requires_resourcetype(self):
        """Test Strategy 2: Simple IDs without ResourceType are NOT allowed"""
        # Simple ID without ResourceType should FAIL
        result = self.expander.find_resource_by_reference("patient-123")
        self.assertIsNone(result, "Simple IDs without ResourceType should NOT be found")
        
        # But with ResourceType it should work
        result = self.expander.find_resource_by_reference("Patient/patient-123")
        self.assertIsNotNone(result)
        self.assertEqual(result['resource']['id'], "patient-123")
        self.assertEqual(result['resource']['resourceType'], "Patient")
    
    def test_strategy_3_fhir_reference_relative(self):
        """Test Strategy 3: FHIR relative reference (ResourceType/ID)"""
        result = self.expander.find_resource_by_reference("Patient/patient-123")
        self.assertIsNotNone(result)
        self.assertEqual(result['resource']['id'], "patient-123")
        self.assertEqual(result['resource']['resourceType'], "Patient")
    
    def test_strategy_3_fhir_reference_absolute(self):
        """Test Strategy 3: FHIR absolute reference (http://base/ResourceType/ID)"""
        result = self.expander.find_resource_by_reference(
            "http://example.org/fhir/Patient/patient-123"
        )
        self.assertIsNotNone(result)
        self.assertEqual(result['resource']['id'], "patient-123")
        self.assertEqual(result['resource']['resourceType'], "Patient")
    
    def test_strategy_3_resourcetype_mismatch(self):
        """Test that ResourceType must match in FHIR references"""
        # Search for Patient/patient-123 (should work)
        result = self.expander.find_resource_by_reference("Patient/patient-123")
        self.assertIsNotNone(result)
        
        # Search for Observation/patient-123 (should NOT work - wrong type)
        result = self.expander.find_resource_by_reference("Observation/patient-123")
        self.assertIsNone(result)
    
    def test_not_found(self):
        """Test that non-existent resources return None"""
        result = self.expander.find_resource_by_reference(
            "http://example.org/nonexistent"
        )
        self.assertIsNone(result)
        
        result = self.expander.find_resource_by_reference("Patient/nonexistent")
        self.assertIsNone(result)

def run_tests():
    """Run all tests and print results"""
    print("=" * 80)
    print("FHIR Reference Matching Tests - 2 Strategies (Simplified)")
    print("=" * 80)
    
    # Run unittest
    suite = unittest.TestLoader().loadTestsFromTestCase(TestReferenceMatching)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 80)
    if result.wasSuccessful():
        print(f"✅ All {result.testsRun} tests PASSED")
        return 0
    else:
        print(f"❌ {len(result.failures)} tests FAILED, {len(result.errors)} errors")
        return 1

if __name__ == "__main__":
    exit(run_tests())
