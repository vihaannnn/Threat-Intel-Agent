"""
SBOM (Software Bill of Materials) ingestion and analysis
Supports CycloneDX and SPDX formats for vulnerability mapping
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
import xml.etree.ElementTree as ET

logger = logging.getLogger("SBOMProcessor")

class SBOMProcessor:
    """Process SBOM files and extract package information"""
    
    def __init__(self):
        self.supported_formats = ['cyclonedx', 'spdx']
    
    def process_sbom_file(self, file_path: str) -> Dict[str, Any]:
        """Process SBOM file and extract package information"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"SBOM file not found: {file_path}")
        
        file_extension = file_path.suffix.lower()
        
        if file_extension == '.json':
            return self._process_json_sbom(file_path)
        elif file_extension == '.xml':
            return self._process_xml_sbom(file_path)
        else:
            raise ValueError(f"Unsupported SBOM format: {file_extension}")
    
    def _process_json_sbom(self, file_path: Path) -> Dict[str, Any]:
        """Process JSON SBOM (CycloneDX or SPDX)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Detect format
            if 'bomFormat' in data and data['bomFormat'] == 'CycloneDX':
                return self._process_cyclonedx_json(data)
            elif 'spdxVersion' in data:
                return self._process_spdx_json(data)
            else:
                # Try to detect format by structure
                if 'components' in data:
                    return self._process_cyclonedx_json(data)
                elif 'packages' in data:
                    return self._process_spdx_json(data)
                else:
                    raise ValueError("Unknown SBOM format")
        
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
    
    def _process_xml_sbom(self, file_path: Path) -> Dict[str, Any]:
        """Process XML SBOM (CycloneDX)"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Check if it's CycloneDX
            if root.tag.endswith('bom'):
                return self._process_cyclonedx_xml(root)
            else:
                raise ValueError("Unsupported XML SBOM format")
        
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML format: {e}")
    
    def _process_cyclonedx_json(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process CycloneDX JSON format"""
        packages = []
        
        # Extract components
        components = data.get('components', [])
        for component in components:
            package_info = {
                'name': component.get('name', ''),
                'version': component.get('version', ''),
                'type': component.get('type', 'library'),
                'purl': component.get('purl', ''),
                'bomRef': component.get('bom-ref', ''),
                'description': component.get('description', ''),
                'licenses': component.get('licenses', []),
                'externalReferences': component.get('externalReferences', []),
                'properties': component.get('properties', [])
            }
            
            # Extract ecosystem from purl
            if package_info['purl']:
                purl_parts = package_info['purl'].split('/')
                if len(purl_parts) > 1:
                    package_info['ecosystem'] = purl_parts[1]
            
            packages.append(package_info)
        
        return {
            'format': 'cyclonedx',
            'version': data.get('specVersion', '1.4'),
            'metadata': data.get('metadata', {}),
            'packages': packages,
            'total_packages': len(packages)
        }
    
    def _process_cyclonedx_xml(self, root: ET.Element) -> Dict[str, Any]:
        """Process CycloneDX XML format"""
        packages = []
        
        # Find components
        components = root.findall('.//{*}component')
        for component in components:
            package_info = {
                'name': component.get('name', ''),
                'version': component.get('version', ''),
                'type': component.get('type', 'library'),
                'bomRef': component.get('bom-ref', ''),
                'description': '',
                'licenses': [],
                'externalReferences': [],
                'properties': []
            }
            
            # Extract description
            desc_elem = component.find('{*}description')
            if desc_elem is not None:
                package_info['description'] = desc_elem.text or ''
            
            # Extract purl
            purl_elem = component.find('{*}purl')
            if purl_elem is not None:
                package_info['purl'] = purl_elem.text or ''
                # Extract ecosystem from purl
                purl_parts = package_info['purl'].split('/')
                if len(purl_parts) > 1:
                    package_info['ecosystem'] = purl_parts[1]
            
            packages.append(package_info)
        
        return {
            'format': 'cyclonedx',
            'version': root.get('version', '1.4'),
            'metadata': {},
            'packages': packages,
            'total_packages': len(packages)
        }
    
    def _process_spdx_json(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process SPDX JSON format"""
        packages = []
        
        # Extract packages
        spdx_packages = data.get('packages', [])
        for pkg in spdx_packages:
            package_info = {
                'name': pkg.get('name', ''),
                'version': pkg.get('versionInfo', ''),
                'type': 'library',
                'description': pkg.get('description', ''),
                'licenses': pkg.get('licenseDeclared', ''),
                'externalReferences': pkg.get('externalRefs', []),
                'properties': []
            }
            
            # Extract ecosystem from external references
            for ref in package_info['externalReferences']:
                if ref.get('referenceType') == 'purl':
                    package_info['purl'] = ref.get('referenceLocator', '')
                    purl_parts = package_info['purl'].split('/')
                    if len(purl_parts) > 1:
                        package_info['ecosystem'] = purl_parts[1]
                    break
            
            packages.append(package_info)
        
        return {
            'format': 'spdx',
            'version': data.get('spdxVersion', '2.3'),
            'metadata': data.get('documentNamespace', {}),
            'packages': packages,
            'total_packages': len(packages)
        }
    
    def extract_package_list(self, sbom_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract simplified package list for vulnerability matching"""
        packages = []
        
        for pkg in sbom_data.get('packages', []):
            package_entry = {
                'name': pkg.get('name', ''),
                'version': pkg.get('version', ''),
                'ecosystem': pkg.get('ecosystem', ''),
                'purl': pkg.get('purl', ''),
                'type': pkg.get('type', 'library')
            }
            
            # Only include packages with valid names
            if package_entry['name']:
                packages.append(package_entry)
        
        return packages
    
    def get_ecosystem_summary(self, sbom_data: Dict[str, Any]) -> Dict[str, int]:
        """Get summary of packages by ecosystem"""
        ecosystem_counts = {}
        
        for pkg in sbom_data.get('packages', []):
            ecosystem = pkg.get('ecosystem', 'unknown')
            ecosystem_counts[ecosystem] = ecosystem_counts.get(ecosystem, 0) + 1
        
        return ecosystem_counts
    
    def find_vulnerable_packages(
        self, 
        sbom_data: Dict[str, Any], 
        vulnerability_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find packages in SBOM that match known vulnerabilities"""
        vulnerable_packages = []
        
        sbom_packages = self.extract_package_list(sbom_data)
        
        for vuln in vulnerability_data:
            affected_packages = vuln.get('affected_packages', [])
            
            for affected in affected_packages:
                if isinstance(affected, dict) and 'package' in affected:
                    pkg_info = affected['package']
                    vuln_pkg_name = pkg_info.get('name', '')
                    vuln_ecosystem = pkg_info.get('ecosystem', '')
                    
                    # Find matching packages in SBOM
                    for sbom_pkg in sbom_packages:
                        if (sbom_pkg['name'] == vuln_pkg_name and 
                            sbom_pkg['ecosystem'] == vuln_ecosystem):
                            
                            vulnerable_packages.append({
                                'package': sbom_pkg,
                                'vulnerability': vuln,
                                'match_type': 'exact'
                            })
        
        return vulnerable_packages

class SBOMIngestionTool:
    """Tool for ingesting SBOM files into the system"""
    
    def __init__(self, output_dir: str = "sbom_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.processor = SBOMProcessor()
    
    def ingest_sbom(self, file_path: str) -> Dict[str, Any]:
        """Ingest SBOM file and save processed data"""
        try:
            # Process SBOM
            sbom_data = self.processor.process_sbom_file(file_path)
            
            # Save processed data
            output_file = self.output_dir / f"sbom_{Path(file_path).stem}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(sbom_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Processed SBOM: {file_path}")
            logger.info(f"Found {sbom_data['total_packages']} packages")
            logger.info(f"Saved to: {output_file}")
            
            return sbom_data
            
        except Exception as e:
            logger.error(f"Failed to ingest SBOM {file_path}: {e}")
            raise
    
    def batch_ingest_sboms(self, directory_path: str) -> List[Dict[str, Any]]:
        """Ingest all SBOM files in a directory"""
        directory = Path(directory_path)
        
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        sbom_files = []
        for pattern in ['*.json', '*.xml']:
            sbom_files.extend(directory.glob(pattern))
        
        results = []
        for sbom_file in sbom_files:
            try:
                result = self.ingest_sbom(str(sbom_file))
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process {sbom_file}: {e}")
                continue
        
        return results

if __name__ == "__main__":
    # Example usage
    processor = SBOMProcessor()
    ingestion_tool = SBOMIngestionTool()
    
    # Process a single SBOM file
    # result = ingestion_tool.ingest_sbom("path/to/sbom.json")
    
    # Process all SBOMs in a directory
    # results = ingestion_tool.batch_ingest_sboms("path/to/sboms/")
    
    print("SBOM processor ready")





