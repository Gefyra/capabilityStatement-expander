#!/usr/bin/env python3
"""
Test script for the FHIR CapabilityStatement Expander
"""

import os
import sys
import tempfile
import shutil
import subprocess
from pathlib import Path

def run_test():
    """Runs a test of the CapabilityStatement Expander"""
    
    # Determine script directory
    script_dir = Path(__file__).parent
    expander_script = script_dir / "capability_statement_expander.py"
    examples_dir = script_dir / "examples"
    
    print("🧪 Testing FHIR CapabilityStatement Expander")
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
            # Führe den Expander aus
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
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                return False
            
            print("✅ Script executed successfully")
            print("📋 Output:")
            print(result.stdout)
            
            # Check output files
            expected_files = [
                "CapabilityStatement-example-base-capability-expanded.json"
            ]
            
            missing_files = []
            for expected_file in expected_files:
                file_path = output_dir / expected_file
                if not file_path.exists():
                    missing_files.append(expected_file)
                else:
                    print(f"✅ File created: {expected_file}")
            
            if missing_files:
                print(f"❌ Missing files: {missing_files}")
                return False
            
            # Show all created files
            all_files = list(output_dir.rglob("*.json"))
            print(f"\n📁 All created files ({len(all_files)}):")
            for file in sorted(all_files):
                relative_path = file.relative_to(output_dir)
                file_size = file.stat().st_size
                print(f"  📄 {relative_path} ({file_size} bytes)")
            
            return True
            
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False

def main():
    """Main function"""
    print("=" * 60)
    print("FHIR CapabilityStatement Expander - Test")
    print("=" * 60)
    
    success = run_test()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Test completed successfully")
        sys.exit(0)
    else:
        print("❌ Test failed")
        sys.exit(1)

if __name__ == "__main__":
    main()