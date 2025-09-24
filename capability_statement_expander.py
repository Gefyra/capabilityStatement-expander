#!/usr/bin/env python3
"""
FHIR CapabilityStatement Expander

Dieses Script expandiert ein FHIR CapabilityStatement durch rekursive Auflösung aller Imports
und kopiert alle referenzierten Profile, Examples und Terminologieressourcen.
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
        self.all_resources: Dict[str, Dict] = {}
        self.resources_by_url: Dict[str, Dict] = {}  # Index für canonical URLs
        
    def load_all_resources(self):
        """Lädt alle JSON-Ressourcen aus dem Input-Verzeichnis"""
        logger.info(f"Lade Ressourcen aus {self.input_dir}")
        
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
                    
                    # Index auch nach canonical URL, falls vorhanden
                    canonical_url = resource.get('url')
                    if canonical_url:
                        self.resources_by_url[canonical_url] = self.all_resources[resource_id]
                    
                    logger.debug(f"Geladen: {resource['resourceType']}/{resource_id}" + 
                               (f" ({canonical_url})" if canonical_url else ""))
                    
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Konnte {json_file} nicht als FHIR-Ressource laden: {e}")
                
        logger.info(f"Insgesamt {len(self.all_resources)} Ressourcen geladen")
    
    def find_capability_statement(self) -> Dict:
        """Findet das angegebene CapabilityStatement anhand der canonical URL"""
        logger.info(f"Suche CapabilityStatement mit URL: {self.capability_statement_url}")
        
        # Zuerst nach canonical URL suchen
        if self.capability_statement_url in self.resources_by_url:
            resource_info = self.resources_by_url[self.capability_statement_url]
            cs = resource_info['resource']
            
            if cs.get('resourceType') != 'CapabilityStatement':
                raise ValueError(f"Ressource mit URL {self.capability_statement_url} ist kein CapabilityStatement")
                
            logger.info(f"CapabilityStatement gefunden: {cs.get('id')} ({self.capability_statement_url})")
            return cs
        
        # Fallback: Suche nach ID falls keine URL angegeben
        # (für Rückwärtskompatibilität)
        if self.capability_statement_url in self.all_resources:
            resource_info = self.all_resources[self.capability_statement_url]
            cs = resource_info['resource']
            
            if cs.get('resourceType') != 'CapabilityStatement':
                raise ValueError(f"Ressource mit ID {self.capability_statement_url} ist kein CapabilityStatement")
                
            logger.info(f"CapabilityStatement gefunden per ID: {cs.get('id')}")
            return cs
            
        # Versuche auch partielle URL-Matches
        for url, resource_info in self.resources_by_url.items():
            if self.capability_statement_url in url or url.endswith(self.capability_statement_url):
                cs = resource_info['resource']
                if cs.get('resourceType') == 'CapabilityStatement':
                    logger.info(f"CapabilityStatement gefunden per URL-Match: {cs.get('id')} ({url})")
                    return cs
        
        raise FileNotFoundError(f"CapabilityStatement nicht gefunden: {self.capability_statement_url}")    
    
    def extract_imports(self, resource: Dict) -> List[str]:
        """Extrahiert alle Import-Referenzen aus einer Ressource"""
        imports = []
        
        # Suche nach imports in verschiedenen Kontexten
        if 'imports' in resource:
            if isinstance(resource['imports'], list):
                imports.extend(resource['imports'])
            else:
                imports.append(resource['imports'])
        
        # Suche nach instantiates (erweiterte CapabilityStatements)
        if 'instantiates' in resource:
            if isinstance(resource['instantiates'], list):
                imports.extend(resource['instantiates'])
            else:
                imports.append(resource['instantiates'])
        
        return imports
    
    def resolve_reference(self, reference: str) -> str:
        """Löst eine Referenz in eine Ressourcen-ID oder URL auf"""
        # Gib die vollständige Referenz zurück für URL-basierte Suche
        return reference.strip()
    
    def expand_capability_statement(self, cs: Dict, visited: Set[str] = None) -> Dict:
        """Expandiert ein CapabilityStatement rekursiv durch Auflösung aller Imports"""
        if visited is None:
            visited = set()
            
        cs_id = cs.get('id', 'unknown')
        if cs_id in visited:
            logger.warning(f"Zirkuläre Referenz erkannt für CapabilityStatement: {cs_id}")
            return cs
            
        visited.add(cs_id)
        logger.info(f"Expandiere CapabilityStatement: {cs_id}")
        
        # Erstelle eine Kopie für die Expansion
        expanded_cs = copy.deepcopy(cs)
        
        # Extrahiere Imports
        imports = self.extract_imports(cs)
        
        for import_ref in imports:
            import_id = self.resolve_reference(import_ref)
            
            if import_id in self.processed_imports:
                continue
                
            self.processed_imports.add(import_id)
            
            # Suche das importierte CapabilityStatement
            imported_resource_info = None
            
            # Zuerst nach canonical URL suchen
            if import_id in self.resources_by_url:
                imported_resource_info = self.resources_by_url[import_id]
            # Fallback nach ID
            elif import_id in self.all_resources:
                imported_resource_info = self.all_resources[import_id]
            # Versuche URL-Fragmente zu matchen
            else:
                for url, resource_info in self.resources_by_url.items():
                    if import_id in url or url.endswith(import_id.split('/')[-1]):
                        imported_resource_info = resource_info
                        break
                        
                # Fallback: Suche auch in IDs nach dem letzten URL-Segment
                if not imported_resource_info:
                    fragment = import_id.split('/')[-1]
                    if fragment in self.all_resources:
                        imported_resource_info = self.all_resources[fragment]
            
            if imported_resource_info:
                imported_resource = imported_resource_info['resource']
                
                if imported_resource.get('resourceType') == 'CapabilityStatement':
                    # Rekursiv expandieren
                    imported_expanded = self.expand_capability_statement(imported_resource, visited.copy())
                    
                    # Merge die Inhalte
                    self.merge_capability_statements(expanded_cs, imported_expanded)
                    
                    logger.info(f"Import aufgelöst: {import_id}")
                else:
                    logger.warning(f"Import ist kein CapabilityStatement: {import_id}")
            else:
                logger.warning(f"Import nicht gefunden: {import_id}")
        
        # Sammle alle referenzierten Ressourcen
        self.collect_referenced_resources(expanded_cs)
        
        # Entferne imports und _imports nach der Expansion
        self.clean_expanded_capability_statement(expanded_cs)
        
        return expanded_cs
    
    def clean_expanded_capability_statement(self, cs: Dict):
        """Entfernt imports und _imports aus dem expandierten CapabilityStatement"""
        # Entferne imports da sie bereits aufgelöst wurden
        if 'imports' in cs:
            del cs['imports']
        
        # Entferne _imports da sie bereits aufgelöst wurden
        if '_imports' in cs:
            del cs['_imports']
        
        logger.debug("imports und _imports aus expandiertem CapabilityStatement entfernt")
    
    def merge_capability_statements(self, target: Dict, source: Dict):
        """Merged zwei CapabilityStatements zusammen"""
        
        # Merge rest resources
        if 'rest' in source:
            if 'rest' not in target:
                target['rest'] = []
            
            for source_rest in source['rest']:
                # Finde oder erstelle matching rest entry
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
                            # Deduplizierung basierend auf type
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
                # Komplexeres Messaging-Merge könnte hier implementiert werden
                pass
    
    def merge_supported_profiles(self, target_resource: Dict, source_resource: Dict):
        """Merged supportedProfile Arrays zwischen zwei Ressourcen"""
        if 'supportedProfile' in source_resource:
            if 'supportedProfile' not in target_resource:
                target_resource['supportedProfile'] = []
            
            for profile in source_resource['supportedProfile']:
                if profile not in target_resource['supportedProfile']:
                    target_resource['supportedProfile'].append(profile)
    
    def collect_referenced_resources(self, cs: Dict):
        """Sammelt alle in einem CapabilityStatement referenzierten Ressourcen"""
        
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
                            # Binding mit valueSet
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
                    
                    # Nested Ressourcen durchsuchen
                    else:
                        extract_references(value, f"{path}.{key}")
                        
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    extract_references(item, f"{path}[{i}]")
        
        extract_references(cs)
        logger.info(f"Referenzierte Ressourcen gesammelt: {len(self.referenced_resources)}")
        logger.debug(f"Referenzen: {sorted(list(self.referenced_resources))}")
        
        # Extrahiere CodeSystems aus referenzierten ValueSets
        self.extract_codesystems_from_valuesets()
        
        # Extrahiere Bindings aus StructureDefinitions
        self.extract_bindings_from_structuredefinitions()
    
    def extract_bindings_from_structuredefinitions(self):
        """Extrahiert ValueSet/CodeSystem-Referenzen aus StructureDefinition-Bindings"""
        for resource_ref in list(self.referenced_resources):
            resource_info = self.find_resource_by_reference(resource_ref)
            if resource_info and resource_info['resource'].get('resourceType') == 'StructureDefinition':
                self.extract_bindings_from_structuredefinition(resource_info['resource'])
    
    def extract_bindings_from_structuredefinition(self, structdef: Dict):
        """Extrahiert ValueSet-Referenzen aus den Bindings einer StructureDefinition"""
        def extract_bindings_recursive(obj: Any, path: str = ""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == 'binding' and isinstance(value, dict):
                        # Binding gefunden - extrahiere ValueSet
                        if 'valueSet' in value and isinstance(value['valueSet'], str):
                            valueset_ref = self.resolve_reference(value['valueSet'])
                            self.referenced_resources.add(valueset_ref)
                            logger.debug(f"ValueSet aus StructureDefinition-Binding extrahiert: {valueset_ref}")
                    else:
                        extract_bindings_recursive(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    extract_bindings_recursive(item, f"{path}[{i}]")
        
        extract_bindings_recursive(structdef)
    
    def extract_codesystems_from_valuesets(self):
        """Extrahiert CodeSystem-Referenzen iterativ aus bereits referenzierten ValueSets und SearchParameters"""
        max_iterations = 10  # Verhindere unendliche Schleifen
        iteration = 0
        
        while iteration < max_iterations:
            initial_count = len(self.referenced_resources)
            resources_to_analyze = []
            
            # Sammle alle ValueSet-, SearchParameter- und StructureDefinition-Referenzen
            for resource_ref in list(self.referenced_resources):
                resource_info = self.find_resource_by_reference(resource_ref)
                if resource_info:
                    resource_type = resource_info['resource'].get('resourceType')
                    if resource_type in ['ValueSet', 'SearchParameter', 'StructureDefinition']:
                        resources_to_analyze.append(resource_info['resource'])
            
            # Analysiere Ressourcen nach weiteren Referenzen
            for resource in resources_to_analyze:
                if resource.get('resourceType') == 'ValueSet':
                    self.extract_codesystems_from_valueset(resource)
                elif resource.get('resourceType') == 'SearchParameter':
                    self.extract_references_from_searchparameter(resource)
                elif resource.get('resourceType') == 'StructureDefinition':
                    self.extract_bindings_from_structuredefinition(resource)
            
            new_count = len(self.referenced_resources)
            if new_count > initial_count:
                logger.info(f"Iteration {iteration + 1}: {new_count - initial_count} zusätzliche Ressourcen extrahiert")
                iteration += 1
            else:
                # Keine neuen Referenzen gefunden, beende die Iteration
                break
        
        if iteration >= max_iterations:
            logger.warning(f"Maximale Iterationsanzahl ({max_iterations}) erreicht bei Referenz-Extraktion")
    
    def extract_references_from_searchparameter(self, searchparam: Dict):
        """Extrahiert Referenzen aus einem SearchParameter"""
        def extract_refs_recursive(obj: Any):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == 'valueSet' and isinstance(value, str):
                        self.referenced_resources.add(self.resolve_reference(value))
                        logger.debug(f"ValueSet aus SearchParameter extrahiert: {value}")
                    elif key == 'system' and isinstance(value, str):
                        self.referenced_resources.add(self.resolve_reference(value))
                        logger.debug(f"CodeSystem aus SearchParameter extrahiert: {value}")
                    else:
                        extract_refs_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_refs_recursive(item)
        
        extract_refs_recursive(searchparam)
    
    def extract_codesystems_from_valueset(self, valueset: Dict):
        """Extrahiert CodeSystem-Referenzen aus einem einzelnen ValueSet"""
        def extract_systems_recursive(obj: Any):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == 'system' and isinstance(value, str):
                        # CodeSystem-URL gefunden
                        self.referenced_resources.add(self.resolve_reference(value))
                        logger.debug(f"CodeSystem aus ValueSet extrahiert: {value}")
                    elif key == 'valueSet' and isinstance(value, str):
                        # Referenz auf andere ValueSets (für compose.include)
                        self.referenced_resources.add(self.resolve_reference(value))
                    else:
                        extract_systems_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_systems_recursive(item)
        
        extract_systems_recursive(valueset)
    
    def find_resource_by_reference(self, resource_ref: str) -> Dict:
        """Findet eine Ressource anhand einer Referenz (URL oder ID)"""
        # Suche nach canonical URL
        if resource_ref in self.resources_by_url:
            return self.resources_by_url[resource_ref]
        
        # Fallback nach ID
        if resource_ref in self.all_resources:
            return self.all_resources[resource_ref]
        
        # Versuche URL-Fragmente
        for url, resource_info in self.resources_by_url.items():
            if resource_ref in url or url.endswith(resource_ref.split('/')[-1]):
                return resource_info
                
        # Fallback: letztes URL-Segment als ID
        fragment = resource_ref.split('/')[-1]
        if fragment in self.all_resources:
            return self.all_resources[fragment]
            
        return None
    
    def copy_referenced_resources(self):
        """Kopiert alle referenzierten Ressourcen in den Output-Ordner"""
        logger.info(f"Kopiere {len(self.referenced_resources)} referenzierte Ressourcen")
        
        # Erstelle Output-Verzeichnis
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        copied_count = 0
        for resource_ref in self.referenced_resources:
            resource_info = None
            
            # Suche nach canonical URL
            if resource_ref in self.resources_by_url:
                resource_info = self.resources_by_url[resource_ref]
            # Fallback nach ID
            elif resource_ref in self.all_resources:
                resource_info = self.all_resources[resource_ref]
            # Versuche URL-Fragmente
            else:
                for url, info in self.resources_by_url.items():
                    if resource_ref in url or url.endswith(resource_ref.split('/')[-1]):
                        resource_info = info
                        break
                        
                # Fallback: letztes URL-Segment als ID
                if not resource_info:
                    fragment = resource_ref.split('/')[-1]
                    if fragment in self.all_resources:
                        resource_info = self.all_resources[fragment]
            
            if resource_info:
                source_path = resource_info['file_path']
                relative_path = resource_info['relative_path']
                target_path = self.output_dir / relative_path
                
                # Erstelle Zielverzeichnis
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Kopiere Datei
                shutil.copy2(source_path, target_path)
                copied_count += 1
                
                logger.debug(f"Kopiert: {relative_path}")
            else:
                logger.warning(f"Referenzierte Ressource nicht gefunden: {resource_ref}")
        
        logger.info(f"{copied_count} Dateien kopiert")
    
    def save_expanded_capability_statement(self, expanded_cs: Dict):
        """Speichert das expandierte CapabilityStatement"""
        original_id = expanded_cs.get('id', 'unknown')
        expanded_id = f"{original_id}-expanded"
        
        # Update ID und Metadaten
        expanded_cs['id'] = expanded_id
        if 'name' in expanded_cs:
            expanded_cs['name'] = f"{expanded_cs['name']}Expanded"
        if 'title' in expanded_cs:
            expanded_cs['title'] = f"{expanded_cs['title']} (Expanded)"
        
        # Entferne imports (da sie jetzt aufgelöst sind)
        if 'imports' in expanded_cs:
            del expanded_cs['imports']
        if 'instantiates' in expanded_cs:
            del expanded_cs['instantiates']
        
        # Speichere die expandierte Version
        output_file = self.output_dir / f"CapabilityStatement-{expanded_id}.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(expanded_cs, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Expandiertes CapabilityStatement gespeichert: {output_file}")
    
    def run(self):
        """Hauptausführung des Expanders"""
        try:
            logger.info("Starte CapabilityStatement Expansion")
            
            # Lade alle Ressourcen
            self.load_all_resources()
            
            # Finde das Basis-CapabilityStatement
            base_cs = self.find_capability_statement()
            
            # Expandiere das CapabilityStatement
            expanded_cs = self.expand_capability_statement(base_cs)
            
            # Speichere das expandierte CapabilityStatement
            self.save_expanded_capability_statement(expanded_cs)
            
            # Kopiere alle referenzierten Ressourcen
            self.copy_referenced_resources()
            
            logger.info("CapabilityStatement Expansion erfolgreich abgeschlossen")
            
        except Exception as e:
            logger.error(f"Fehler während der Expansion: {e}")
            raise

def main():
    parser = argparse.ArgumentParser(description='FHIR CapabilityStatement Expander')
    parser.add_argument('input_dir', help='Eingabeordner mit JSON-Dateien')
    parser.add_argument('output_dir', help='Ausgabeordner für expandierte Ressourcen')
    parser.add_argument('capability_statement_url', help='Canonical URL des zu expandierenden CapabilityStatements')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validiere Input-Verzeichnis
    if not os.path.isdir(args.input_dir):
        logger.error(f"Input-Verzeichnis existiert nicht: {args.input_dir}")
        sys.exit(1)
    
    # Erstelle Expander und führe aus
    expander = CapabilityStatementExpander(
        args.input_dir,
        args.output_dir, 
        args.capability_statement_url
    )
    
    try:
        expander.run()
        logger.info("Expansion erfolgreich abgeschlossen")
    except Exception as e:
        logger.error(f"Expansion fehlgeschlagen: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()