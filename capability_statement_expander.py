#!/usr/bin/env python3
"""
FHIR CapabilityStatement Expander

This script expands a FHIR CapabilityStatement by recursively resolving all imports
and copying all referenced profiles, examples, and terminology resources.
"""

import json
import os
import shutil
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Set, Any
import logging
import copy

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CapabilityStatementExpander:
    def __init__(self, input_dir: str, output_dir: str, capability_statement_url: str):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.capability_statement_url = capability_statement_url
        self.processed_imports: Set[str] = set()
        self.referenced_resources: Set[str] = set()
        self.imported_capability_statements: Set[str] = set()  # Track imported CapabilityStatements
        self.all_resources: Dict[str, Dict] = {}
        self.resources_by_url: Dict[str, Dict] = {}  # Index for canonical URLs
        
        # Track processed files for reporting
        self.expanded_files: List[Dict] = []
        self.copied_files: List[Dict] = []
        
    def load_all_resources(self):
        """Loads all JSON resources from the input directory"""
        logger.info(f"Loading resources from {self.input_dir}")
        
        for json_file in self.input_dir.glob("**/*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    resource = json.load(f)
                    
                if isinstance(resource, dict) and 'resourceType' in resource:
                    resource_id = resource.get('id', json_file.stem)
                    self.all_resources[resource_id] = {
                        'resource': resource,
                        'file_path': json_file,
                        'relative_path': json_file.relative_to(self.input_dir)
                    }
                    
                    # Index also by canonical URL if available
                    canonical_url = resource.get('url')
                    if canonical_url:
                        self.resources_by_url[canonical_url] = self.all_resources[resource_id]
                    
                    logger.debug(f"Loaded: {resource['resourceType']}/{resource_id}" + 
                               (f" ({canonical_url})" if canonical_url else ""))
                    
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Could not load {json_file} as FHIR resource: {e}")
                
        logger.info(f"Total {len(self.all_resources)} resources loaded")
    
    def find_capability_statement(self) -> Dict:
        """Finds the specified CapabilityStatement by canonical URL"""
        logger.info(f"Searching for CapabilityStatement with URL: {self.capability_statement_url}")
        
        # First search by canonical URL
        if self.capability_statement_url in self.resources_by_url:
            resource_info = self.resources_by_url[self.capability_statement_url]
            cs = resource_info['resource']
            
            if cs.get('resourceType') != 'CapabilityStatement':
                raise ValueError(f"Resource with URL {self.capability_statement_url} is not a CapabilityStatement")
                
            logger.info(f"CapabilityStatement found: {cs.get('id')} ({self.capability_statement_url})")
            return cs
        
        # Fallback: Search by ID if no URL provided
        # (for backward compatibility)
        if self.capability_statement_url in self.all_resources:
            resource_info = self.all_resources[self.capability_statement_url]
            cs = resource_info['resource']
            
            if cs.get('resourceType') != 'CapabilityStatement':
                raise ValueError(f"Resource with ID {self.capability_statement_url} is not a CapabilityStatement")
                
            logger.info(f"CapabilityStatement found by ID: {cs.get('id')}")
            return cs
            
        # Try partial URL matches
        for url, resource_info in self.resources_by_url.items():
            if self.capability_statement_url in url or url.endswith(self.capability_statement_url):
                cs = resource_info['resource']
                if cs.get('resourceType') == 'CapabilityStatement':
                    logger.info(f"CapabilityStatement found by URL match: {cs.get('id')} ({url})")
                    return cs
        
        raise FileNotFoundError(f"CapabilityStatement not found: {self.capability_statement_url}")    
    
    def extract_imports(self, resource: Dict) -> List[str]:
        """Extracts all import references from a resource"""
        imports = []
        
        # Search for imports in various contexts
        if 'imports' in resource:
            if isinstance(resource['imports'], list):
                imports.extend(resource['imports'])
            else:
                imports.append(resource['imports'])
        
        # Search for instantiates (extended CapabilityStatements)
        if 'instantiates' in resource:
            if isinstance(resource['instantiates'], list):
                imports.extend(resource['instantiates'])
            else:
                imports.append(resource['instantiates'])
        
        return imports
    
    def resolve_reference(self, reference: str) -> str:
        """Resolves a reference to a resource ID or URL"""
        # Return the complete reference for URL-based search
        return reference.strip()
    
    def expand_capability_statement(self, cs: Dict, visited: Set[str] = None) -> Dict:
        """Expands a CapabilityStatement recursively by resolving all imports"""
        if visited is None:
            visited = set()
            
        cs_id = cs.get('id', 'unknown')
        if cs_id in visited:
            logger.warning(f"Circular reference detected for CapabilityStatement: {cs_id}")
            return cs
            
        visited.add(cs_id)
        logger.info(f"Expanding CapabilityStatement: {cs_id}")
        
        # Create a copy for expansion
        expanded_cs = copy.deepcopy(cs)
        
        # Extract imports
        imports = self.extract_imports(cs)
        
        for import_ref in imports:
            import_id = self.resolve_reference(import_ref)
            
            if import_id in self.processed_imports:
                continue
                
            self.processed_imports.add(import_id)
            
            # Search for the imported CapabilityStatement
            imported_resource_info = None
            
            # First search by canonical URL
            if import_id in self.resources_by_url:
                imported_resource_info = self.resources_by_url[import_id]
            # Fallback by ID
            elif import_id in self.all_resources:
                imported_resource_info = self.all_resources[import_id]
            # Try to match URL fragments
            else:
                for url, resource_info in self.resources_by_url.items():
                    if import_id in url or url.endswith(import_id.split('/')[-1]):
                        imported_resource_info = resource_info
                        break
                        
                # Fallback: Also search in IDs for the last URL segment
                if not imported_resource_info:
                    fragment = import_id.split('/')[-1]
                    if fragment in self.all_resources:
                        imported_resource_info = self.all_resources[fragment]
            
            if imported_resource_info:
                imported_resource = imported_resource_info['resource']
                
                if imported_resource.get('resourceType') == 'CapabilityStatement':
                    # Add the imported CapabilityStatement to imported_capability_statements set
                    canonical_url = imported_resource.get('url')
                    if canonical_url:
                        self.imported_capability_statements.add(canonical_url)
                    else:
                        # If no canonical URL, use the resource ID
                        resource_id = imported_resource.get('id')
                        if resource_id:
                            self.imported_capability_statements.add(resource_id)
                    
                    # Recursively expand
                    imported_expanded = self.expand_capability_statement(imported_resource, visited.copy())
                    
                    # Merge the contents
                    self.merge_capability_statements(expanded_cs, imported_expanded)
                    
                    logger.info(f"Import resolved: {import_id}")
                else:
                    logger.warning(f"Import is not a CapabilityStatement: {import_id}")
            else:
                logger.warning(f"Import not found: {import_id}")
        
        # Collect all referenced resources
        self.collect_referenced_resources(expanded_cs)
        
        # Remove imports and _imports after expansion
        self.clean_expanded_capability_statement(expanded_cs)
        
        return expanded_cs
    
    def clean_expanded_capability_statement(self, cs: Dict):
        """Removes imports and _imports from the expanded CapabilityStatement"""
        # Remove imports as they have already been resolved
        if 'imports' in cs:
            del cs['imports']
        
        # Remove _imports as they have already been resolved
        if '_imports' in cs:
            del cs['_imports']
        
        logger.debug("Removed imports and _imports from expanded CapabilityStatement")
    
    def merge_capability_statements(self, target: Dict, source: Dict):
        """Merges two CapabilityStatements together"""
        
        # Merge rest resources
        if 'rest' in source:
            if 'rest' not in target:
                target['rest'] = []
            
            for source_rest in source['rest']:
                # Find or create matching rest entry
                target_rest = None
                for tr in target['rest']:
                    if tr.get('mode') == source_rest.get('mode'):
                        target_rest = tr
                        break
                
                if target_rest is None:
                    target['rest'].append(copy.deepcopy(source_rest))
                else:
                    # Merge resources
                    if 'resource' in source_rest:
                        if 'resource' not in target_rest:
                            target_rest['resource'] = []
                        
                        for source_resource in source_rest['resource']:
                            # Deduplication based on type
                            existing = next((r for r in target_rest['resource'] 
                                           if r.get('type') == source_resource.get('type')), None)
                            
                            if existing is None:
                                target_rest['resource'].append(copy.deepcopy(source_resource))
                            else:
                                # Merge supportedProfile
                                self.merge_supported_profiles(existing, source_resource)
        
        # Merge messaging
        if 'messaging' in source:
            if 'messaging' not in target:
                target['messaging'] = source['messaging']
            else:
                # More complex messaging merge could be implemented here
                pass
    
    def merge_supported_profiles(self, target_resource: Dict, source_resource: Dict):
        """Merges supportedProfile arrays between two resources"""
        if 'supportedProfile' in source_resource:
            if 'supportedProfile' not in target_resource:
                target_resource['supportedProfile'] = []
            
            for profile in source_resource['supportedProfile']:
                if profile not in target_resource['supportedProfile']:
                    target_resource['supportedProfile'].append(profile)
    
    def collect_referenced_resources(self, cs: Dict):
        """Collects all resources referenced in a CapabilityStatement"""
        
        def extract_references(obj: Any, path: str = ""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    # Profile-Referenzen
                    if key in ['supportedProfile', 'profile', 'targetProfile']:
                        if isinstance(value, list):
                            for ref in value:
                                self.referenced_resources.add(self.resolve_reference(ref))
                        else:
                            self.referenced_resources.add(self.resolve_reference(value))
                    
                    # ValueSet-Referenzen
                    elif key in ['valueSet', 'binding']:
                        if isinstance(value, dict) and 'valueSet' in value:
                            # Binding with valueSet
                            self.referenced_resources.add(self.resolve_reference(value['valueSet']))
                        elif isinstance(value, str):
                            self.referenced_resources.add(self.resolve_reference(value))
                    
                    # CodeSystem-Referenzen (nur in spezifischen Kontexten)
                    elif key == 'system' and isinstance(value, str):
                        # Nur in bestimmten Kontexten CodeSystems sammeln
                        context_path = path.lower()
                        if any(ctx in context_path for ctx in ['binding', 'searchparam', 'valueset', 'extension']):
                            self.referenced_resources.add(self.resolve_reference(value))
                    
                    # SearchParameter-Referenzen
                    elif key == 'searchParam' and isinstance(value, list):
                        for param in value:
                            if isinstance(param, dict):
                                # SearchParameter Definition URL
                                if 'definition' in param:
                                    self.referenced_resources.add(self.resolve_reference(param['definition']))
                                # Binding in SearchParameter
                                if 'binding' in param and isinstance(param['binding'], dict):
                                    if 'valueSet' in param['binding']:
                                        self.referenced_resources.add(self.resolve_reference(param['binding']['valueSet']))
                    
                    # Interaction-spezifische Profile
                    elif key == 'interaction' and isinstance(value, list):
                        for interaction in value:
                            if isinstance(interaction, dict) and 'profile' in interaction:
                                self.referenced_resources.add(self.resolve_reference(interaction['profile']))
                    
                    # Extension-Referenzen
                    elif key in ['extension', 'modifierExtension'] and isinstance(value, list):
                        for ext in value:
                            if isinstance(ext, dict) and 'url' in ext:
                                self.referenced_resources.add(self.resolve_reference(ext['url']))
                    
                    # Operation-Definition Referenzen
                    elif key == 'operation' and isinstance(value, list):
                        for op in value:
                            if isinstance(op, dict) and 'definition' in op:
                                self.referenced_resources.add(self.resolve_reference(op['definition']))
                    
                    # Compartment-Referenzen
                    elif key == 'compartment' and isinstance(value, list):
                        for comp in value:
                            if isinstance(comp, str):
                                self.referenced_resources.add(self.resolve_reference(comp))
                    
                    # Search nested resources
                    else:
                        extract_references(value, f"{path}.{key}")
                        
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    extract_references(item, f"{path}[{i}]")
        
        extract_references(cs)
        logger.info(f"Referenced resources collected: {len(self.referenced_resources)}")
        logger.debug(f"Referenzen: {sorted(list(self.referenced_resources))}")
        
        # Extract CodeSystems from referenced ValueSets
        self.extract_codesystems_from_valuesets()
        
        # Extract bindings from StructureDefinitions
        self.extract_bindings_from_structuredefinitions()
        
        # Collect parent profiles from StructureDefinitions
        self.collect_parent_profiles()
        
        # Collect examples based on meta.profile
        self.collect_examples_by_meta_profile()
    
    def extract_bindings_from_structuredefinitions(self):
        """Extracts ValueSet/CodeSystem references from StructureDefinition bindings"""
        for resource_ref in list(self.referenced_resources):
            resource_info = self.find_resource_by_reference(resource_ref)
            if resource_info and resource_info['resource'].get('resourceType') == 'StructureDefinition':
                self.extract_bindings_from_structuredefinition(resource_info['resource'])
    
    def extract_bindings_from_structuredefinition(self, structdef: Dict):
        """Extracts ValueSet references from the bindings of a StructureDefinition"""
        def extract_bindings_recursive(obj: Any, path: str = ""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == 'binding' and isinstance(value, dict):
                        # Binding found - extract ValueSet
                        if 'valueSet' in value and isinstance(value['valueSet'], str):
                            valueset_ref = self.resolve_reference(value['valueSet'])
                            self.referenced_resources.add(valueset_ref)
                            logger.debug(f"ValueSet extracted from StructureDefinition binding: {valueset_ref}")
                    else:
                        extract_bindings_recursive(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    extract_bindings_recursive(item, f"{path}[{i}]")
        
        extract_bindings_recursive(structdef)
    
    def collect_parent_profiles(self):
        """Collects all parent profiles recursively from referenced StructureDefinitions"""
        logger.info("Collecting parent profiles from StructureDefinitions")
        
        # Get all currently referenced StructureDefinitions
        structuredefs_to_process = []
        for resource_ref in list(self.referenced_resources):
            resource_info = self.find_resource_by_reference(resource_ref)
            if resource_info and resource_info['resource'].get('resourceType') == 'StructureDefinition':
                structuredefs_to_process.append((resource_ref, resource_info['resource']))
        
        total_parents_found = 0
        
        # Process each StructureDefinition and collect its complete parent hierarchy
        for resource_ref, structdef in structuredefs_to_process:
            parents_found = self.extract_parent_profile_recursive(structdef, resource_ref)
            total_parents_found += parents_found
        
        if total_parents_found > 0:
            logger.info(f"Total parent profiles found: {total_parents_found}")
        
        logger.info("Parent profile collection completed")
    
    def extract_parent_profile_recursive(self, structdef: Dict, profile_ref: str, depth: int = 0, max_depth: int = 50, visited: Set[str] = None) -> int:
        """Recursively extracts all parent profiles (baseDefinition) from a StructureDefinition hierarchy
        
        Returns the number of parent profiles found in this hierarchy
        """
        if visited is None:
            visited = set()
        
        # Prevent infinite recursion
        if depth >= max_depth:
            logger.warning(f"Maximum recursion depth ({max_depth}) reached for profile: {profile_ref}")
            return 0
        
        base_definition = structdef.get('baseDefinition')
        
        if not base_definition:
            # No parent profile defined - end of hierarchy
            return 0
        
        # Check for circular references
        if base_definition in visited:
            logger.warning(f"Circular reference detected: {base_definition} in hierarchy of {profile_ref}")
            return 0
        
        visited.add(base_definition)
        
        # Check if the parent profile is already in our referenced resources
        if base_definition in self.referenced_resources:
            # Already collected, but we still need to check its parents
            parent_resource_info = self.find_resource_by_reference(base_definition)
            if parent_resource_info and parent_resource_info['resource'].get('resourceType') == 'StructureDefinition':
                # Continue with parent's parent
                return self.extract_parent_profile_recursive(parent_resource_info['resource'], base_definition, depth + 1, max_depth, visited)
            return 0
        
        # Try to find the parent profile in our resources
        parent_resource_info = self.find_resource_by_reference(base_definition)
        
        if parent_resource_info:
            # Parent profile found in our resources
            if parent_resource_info['resource'].get('resourceType') == 'StructureDefinition':
                self.referenced_resources.add(base_definition)
                logger.info(f"Parent profile added: {base_definition} (parent of {profile_ref})")
                
                # Recursively collect parent's parents
                parents_found = 1 + self.extract_parent_profile_recursive(
                    parent_resource_info['resource'], 
                    base_definition, 
                    depth + 1, 
                    max_depth, 
                    visited
                )
                return parents_found
            else:
                logger.warning(f"Base definition is not a StructureDefinition: {base_definition}")
                return 0
        else:
            # Parent profile not found - likely from FHIR core spec or dependency
            logger.warning(f"Parent profile not found (likely from FHIR core or dependency): {base_definition} (parent of {profile_ref})")
            return 0
    
    def collect_examples_by_meta_profile(self):
        """Collects Examples based on meta.profile references to already referenced profiles"""
        logger.info("Searching for examples based on meta.profile references")
        
        initial_count = len(self.referenced_resources)
        examples_found = 0
        
        # Create set of all already referenced profile URLs
        referenced_profiles = set()
        for resource_ref in self.referenced_resources:
            # Normalize the reference for comparisons
            referenced_profiles.add(resource_ref)
        
        # Search all resources for meta.profile
        for resource_id, resource_info in self.all_resources.items():
            resource = resource_info['resource']
            
            # Check if the resource has meta.profile
            if 'meta' in resource and 'profile' in resource.get('meta', {}):
                profiles = resource['meta']['profile']
                
                # Normalize to list
                if isinstance(profiles, str):
                    profiles = [profiles]
                elif not isinstance(profiles, list):
                    continue
                
                # Check if one of the profiles is already referenced
                for profile_url in profiles:
                    normalized_profile = self.resolve_reference(profile_url)
                    
                    if normalized_profile in referenced_profiles:
                        # This resource uses a referenced profile -> is an Example
                        resource_url = resource.get('url', resource_id)
                        
                        if resource_url not in self.referenced_resources:
                            self.referenced_resources.add(resource_url)
                            examples_found += 1
                            
                            logger.info(f"Example found via meta.profile: {resource.get('resourceType', 'Unknown')}/{resource_id} → Profile: {profile_url}")
                            break  # One match is enough to classify the resource as an example
        
        logger.info(f"Meta.profile analysis completed: {examples_found} examples found")
        
        final_count = len(self.referenced_resources)
        if final_count > initial_count:
            logger.info(f"Total {final_count - initial_count} additional resources added via meta.profile")
    
    def extract_codesystems_from_valuesets(self):
        """Extracts CodeSystem references iteratively from already referenced ValueSets and SearchParameters"""
        max_iterations = 10  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            initial_count = len(self.referenced_resources)
            resources_to_analyze = []
            
            # Collect all ValueSet, SearchParameter and StructureDefinition references
            for resource_ref in list(self.referenced_resources):
                resource_info = self.find_resource_by_reference(resource_ref)
                if resource_info:
                    resource_type = resource_info['resource'].get('resourceType')
                    if resource_type in ['ValueSet', 'SearchParameter', 'StructureDefinition']:
                        resources_to_analyze.append(resource_info['resource'])
            
            # Analyze resources for additional references
            for resource in resources_to_analyze:
                if resource.get('resourceType') == 'ValueSet':
                    self.extract_codesystems_from_valueset(resource)
                elif resource.get('resourceType') == 'SearchParameter':
                    self.extract_references_from_searchparameter(resource)
                elif resource.get('resourceType') == 'StructureDefinition':
                    self.extract_bindings_from_structuredefinition(resource)
            
            new_count = len(self.referenced_resources)
            if new_count > initial_count:
                logger.info(f"Iteration {iteration + 1}: {new_count - initial_count} additional resources extracted")
                iteration += 1
            else:
                # No new references found, end iteration
                break
        
        if iteration >= max_iterations:
            logger.warning(f"Maximum iteration count reached during reference extraction")
    
    def extract_references_from_searchparameter(self, searchparam: Dict):
        """Extracts references from a SearchParameter"""
        def extract_refs_recursive(obj: Any):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == 'valueSet' and isinstance(value, str):
                        self.referenced_resources.add(self.resolve_reference(value))
                        logger.debug(f"ValueSet extracted from SearchParameter: {value}")
                    elif key == 'system' and isinstance(value, str):
                        self.referenced_resources.add(self.resolve_reference(value))
                        logger.debug(f"CodeSystem extracted from SearchParameter: {value}")
                    else:
                        extract_refs_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_refs_recursive(item)
        
        extract_refs_recursive(searchparam)
    
    def extract_codesystems_from_valueset(self, valueset: Dict):
        """Extracts CodeSystem references from a single ValueSet"""
        def extract_systems_recursive(obj: Any):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == 'system' and isinstance(value, str):
                        # CodeSystem URL found
                        self.referenced_resources.add(self.resolve_reference(value))
                        logger.debug(f"CodeSystem extracted from ValueSet: {value}")
                    elif key == 'valueSet' and isinstance(value, str):
                        # Reference to other ValueSets (for compose.include)
                        self.referenced_resources.add(self.resolve_reference(value))
                    else:
                        extract_systems_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_systems_recursive(item)
        
        extract_systems_recursive(valueset)
    
    def find_resource_by_reference(self, resource_ref: str) -> Dict:
        """Finds a resource by reference (URL or ID)"""
        # Search by canonical URL
        if resource_ref in self.resources_by_url:
            return self.resources_by_url[resource_ref]
        
        # Fallback by ID
        if resource_ref in self.all_resources:
            return self.all_resources[resource_ref]
        
        # Try URL fragments
        for url, resource_info in self.resources_by_url.items():
            if resource_ref in url or url.endswith(resource_ref.split('/')[-1]):
                return resource_info

        # Fallback: last URL segment as ID
        fragment = resource_ref.split('/')[-1]
        if fragment in self.all_resources:
            return self.all_resources[fragment]
            
        return None
    
    def copy_referenced_resources(self):
        """Copies all referenced resources to the output directory"""
        logger.info(f"Kopiere {len(self.referenced_resources)} referenzierte Ressourcen")
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        copied_count = 0
        for resource_ref in self.referenced_resources:
            resource_info = None
            
            # Search by canonical URL
            if resource_ref in self.resources_by_url:
                resource_info = self.resources_by_url[resource_ref]
            # Fallback by ID
            elif resource_ref in self.all_resources:
                resource_info = self.all_resources[resource_ref]
            # Try URL fragments
            else:
                for url, info in self.resources_by_url.items():
                    if resource_ref in url or url.endswith(resource_ref.split('/')[-1]):
                        resource_info = info
                        break
                        
                # Fallback: last URL-Segment as ID
                if not resource_info:
                    fragment = resource_ref.split('/')[-1]
                    if fragment in self.all_resources:
                        resource_info = self.all_resources[fragment]
            
            if resource_info:
                source_path = resource_info['file_path']
                relative_path = resource_info['relative_path']
                
                # Copy all files flat into output directory (without subdirectories)
                filename = os.path.basename(source_path)
                target_path = self.output_dir / filename
                
                # Create target directory
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                shutil.copy2(source_path, target_path)
                copied_count += 1
                
                # Track copied file
                resource_type = resource_info['resource'].get('resourceType', 'Unknown')
                self.copied_files.append({
                    'filename': os.path.basename(target_path),
                    'relative_path': os.path.basename(target_path),  # Flache Struktur
                    'size': os.path.getsize(target_path),
                    'resource_type': resource_type
                })
                
                logger.debug(f"Copied: {filename}")
            else:
                logger.warning(f"Referenced resource not found: {resource_ref}")
        
        logger.info(f"{copied_count} files copied")
    
    def copy_imported_capability_statements(self):
        """Copies all imported CapabilityStatements to the output directory"""
        logger.info(f"Kopiere {len(self.imported_capability_statements)} importierte CapabilityStatements")
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        copied_count = 0
        for cs_ref in self.imported_capability_statements:
            resource_info = None
            
            # Search by canonical URL
            if cs_ref in self.resources_by_url:
                resource_info = self.resources_by_url[cs_ref]
            # Fallback by ID
            elif cs_ref in self.all_resources:
                resource_info = self.all_resources[cs_ref]
            # Try URL fragments
            else:
                for url, info in self.resources_by_url.items():
                    if cs_ref in url or url.endswith(cs_ref.split('/')[-1]):
                        resource_info = info
                        break
                        
                # Fallback: last URL-Segment as ID
                if not resource_info:
                    fragment = cs_ref.split('/')[-1]
                    if fragment in self.all_resources:
                        resource_info = self.all_resources[fragment]
            
            if resource_info:
                source_path = resource_info['file_path']
                
                # Copy all files flat into output directory (without subdirectories)
                filename = os.path.basename(source_path)
                target_path = self.output_dir / filename
                
                # Create target directory
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                shutil.copy2(source_path, target_path)
                copied_count += 1
                
                # Track copied file
                resource_type = resource_info['resource'].get('resourceType', 'Unknown')
                self.copied_files.append({
                    'filename': os.path.basename(target_path),
                    'relative_path': os.path.basename(target_path),  # Flache Struktur
                    'size': os.path.getsize(target_path),
                    'resource_type': resource_type
                })
                
                logger.info(f"Copied imported CapabilityStatement: {filename}")
            else:
                logger.warning(f"Imported CapabilityStatement not found: {cs_ref}")
        
        logger.info(f"{copied_count} imported CapabilityStatements copied")
    
    def copy_original_capability_statement(self, cs: Dict):
        """Copies the original CapabilityStatement to the output directory"""
        logger.info("Kopiere das ursprüngliche CapabilityStatement")
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Find the original CapabilityStatement file
        cs_url = cs.get('url')
        cs_id = cs.get('id')
        
        resource_info = None
        if cs_url and cs_url in self.resources_by_url:
            resource_info = self.resources_by_url[cs_url]
        elif cs_id and cs_id in self.all_resources:
            resource_info = self.all_resources[cs_id]
        
        if resource_info:
            source_path = resource_info['file_path']
            
            # Copy all files flat into output directory (without subdirectories)
            filename = os.path.basename(source_path)
            target_path = self.output_dir / filename
            
            # Create target directory
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(source_path, target_path)
            
            # Track copied file
            resource_type = resource_info['resource'].get('resourceType', 'Unknown')
            self.copied_files.append({
                'filename': os.path.basename(target_path),
                'relative_path': os.path.basename(target_path),  # Flache Struktur
                'size': os.path.getsize(target_path),
                'resource_type': resource_type
            })
            
            logger.info(f"Copied original CapabilityStatement: {filename}")
        else:
            logger.warning("Original CapabilityStatement file not found for copying")
    
    def print_summary_report(self):
        """Prints a structured report of all processed files"""
        
        # Separate CapabilityStatements from other copied files
        capability_statements = [f for f in self.copied_files if f['resource_type'] == 'CapabilityStatement']
        other_resources = [f for f in self.copied_files if f['resource_type'] != 'CapabilityStatement']
        
        print("\n" + "📄 Processed FHIR Resources:")
        print("=" * 32)
        
        print("🔧 Expanded Resources:")
        for file in self.expanded_files:
            print(f"📋 {file['filename']} (expanded)")
        
        if capability_statements:
            print("\n📋 CapabilityStatements:")
            for file in capability_statements:
                print(f"  📋 {file['filename']} [{file['resource_type']}]")
        
        print("\n📁 Copied Resources:")
        for file in other_resources:
            print(f"  📋 {file['filename']} [{file['resource_type']}]")
        
        print("\n" + "=" * 32)
        print("📊 Summary:")
        print(f"  🔧 Expanded: {len(self.expanded_files)} files")
        print(f"  📋 CapabilityStatements: {len(capability_statements)} files")
        print(f"  📁 Other Resources: {len(other_resources)} files")
        print(f"  📋 Total: {len(self.expanded_files) + len(self.copied_files)} files processed")
        
        # Also print the original JSON summary for compatibility
        print("\n" + "="*50)
        print("FHIR_PROCESSING_SUMMARY_START")
        print(json.dumps({
            'expanded_files': self.expanded_files,
            'copied_files': self.copied_files,
            'total_expanded': len(self.expanded_files),
            'total_copied': len(self.copied_files),
            'total_capability_statements': len(capability_statements),
            'total_other_resources': len(other_resources),
            'total_files': len(self.expanded_files) + len(self.copied_files)
        }, indent=2))
        print("FHIR_PROCESSING_SUMMARY_END")
        print("="*50)
    
    def save_expanded_capability_statement(self, expanded_cs: Dict):
        """Saves the expanded CapabilityStatement"""
        original_id = expanded_cs.get('id', 'unknown')
        expanded_id = f"{original_id}-expanded"
        
        # Update ID and metadata
        expanded_cs['id'] = expanded_id
        if 'name' in expanded_cs:
            expanded_cs['name'] = f"{expanded_cs['name']}Expanded"
        if 'title' in expanded_cs:
            expanded_cs['title'] = f"{expanded_cs['title']} (Expanded)"
        
        # Remove imports (as they are now resolved)
        if 'imports' in expanded_cs:
            del expanded_cs['imports']
        if 'instantiates' in expanded_cs:
            del expanded_cs['instantiates']
        
        # Save the expanded version
        output_file = self.output_dir / f"CapabilityStatement-{expanded_id}.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(expanded_cs, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Expanded CapabilityStatement saved: {output_file}")
        
        # Track expanded file
        self.expanded_files.append({
            'filename': os.path.basename(output_file),
            'relative_path': os.path.relpath(output_file, self.output_dir),
            'size': os.path.getsize(output_file),
            'resource_type': 'CapabilityStatement'
        })
    
    def run(self):
        """Main execution of the expander"""
        try:
            logger.info("Starting CapabilityStatement expansion")
            
            # Load all resources
            self.load_all_resources()
            
            # Find the base CapabilityStatement
            base_cs = self.find_capability_statement()
            
            # Copy the original CapabilityStatement
            self.copy_original_capability_statement(base_cs)
            
            # Expand the CapabilityStatement
            expanded_cs = self.expand_capability_statement(base_cs)
            
            # Save the expanded CapabilityStatement
            self.save_expanded_capability_statement(expanded_cs)
            
            # Copy all imported CapabilityStatements
            self.copy_imported_capability_statements()
            
            # Copy all referenced resources
            self.copy_referenced_resources()
            
            # Print structured report
            self.print_summary_report()
            
            logger.info("CapabilityStatement expansion completed successfully")
            
        except Exception as e:
            logger.error(f"Error during expansion: {e}")
            raise

def main():
    parser = argparse.ArgumentParser(description='FHIR CapabilityStatement Expander')
    parser.add_argument('input_dir', help='Input directory with JSON files')
    parser.add_argument('output_dir', help='Output directory for expanded resources')
    parser.add_argument('capability_statement_url', help='Canonical URL of the CapabilityStatement to expand')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate input directory
    if not os.path.isdir(args.input_dir):
        logger.error(f"Input directory does not exist: {args.input_dir}")
        sys.exit(1)
    
    # Create expander and execute
    expander = CapabilityStatementExpander(
        args.input_dir,
        args.output_dir, 
        args.capability_statement_url
    )
    
    try:
        expander.run()
        logger.info("Expansion completed successfully")
    except Exception as e:
        logger.error(f"Expansion failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()