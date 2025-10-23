"""
OSV Vulnerability Data Collector
Downloads and filters recent vulnerabilities from OSV bulk data exports
"""

import requests
import json
import zipfile
import io
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OSVDataCollector:
    """Collects vulnerability data from OSV.dev bulk exports"""
    
    # Base URL for OSV bulk data
    BASE_URL = "https://osv-vulnerabilities.storage.googleapis.com"
    
    # Target ecosystems (most commonly used in enterprises)
    ECOSYSTEMS = ["npm", "PyPI", "Maven", "Go", "Debian"]
    
    # Date range (last 3 years for relevance)
    DAYS_BACK = 3 * 365
    
    def __init__(self, output_dir: str = "osv_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.session = requests.Session()
        
    def download_ecosystem_data(self, ecosystem: str) -> List[Dict]:
        """Download all vulnerabilities for an ecosystem from bulk export"""
        url = f"{self.BASE_URL}/{ecosystem}/all.zip"
        
        logger.info(f"Downloading {ecosystem} vulnerabilities from {url}")
        logger.info("This may take a few minutes depending on ecosystem size...")
        
        try:
            response = self.session.get(url, timeout=300)
            response.raise_for_status()
            
            # Extract zip file in memory
            vulnerabilities = []
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                json_files = [f for f in zip_file.namelist() if f.endswith('.json')]
                logger.info(f"Found {len(json_files)} vulnerability records in {ecosystem}")
                
                for json_file in json_files:
                    try:
                        with zip_file.open(json_file) as f:
                            vuln_data = json.load(f)
                            vulnerabilities.append(vuln_data)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse {json_file}: {e}")
                        continue
            
            logger.info(f"Successfully loaded {len(vulnerabilities)} vulnerabilities from {ecosystem}")
            return vulnerabilities
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading {ecosystem} data: {e}")
            return []
        except zipfile.BadZipFile as e:
            logger.error(f"Invalid zip file for {ecosystem}: {e}")
            return []
    
    def is_recent_vulnerability(self, vuln_data: Dict) -> bool:
        """Check if vulnerability was published within target date range"""
        if "published" not in vuln_data:
            return False
            
        try:
            published_date = datetime.fromisoformat(
                vuln_data["published"].replace("Z", "+00:00")
            )
            cutoff_date = datetime.now().replace(tzinfo=published_date.tzinfo) - timedelta(days=self.DAYS_BACK)
            return published_date >= cutoff_date
        except (ValueError, TypeError):
            return False
    
    def extract_affected_info(self, vuln_data: Dict) -> List[Dict]:
        """Extract comprehensive affected package information"""
        affected_info = []
        
        if "affected" not in vuln_data:
            return affected_info
        
        for affected_item in vuln_data["affected"]:
            affected_detail = {}
            
            # Package information
            if "package" in affected_item:
                pkg = affected_item["package"]
                affected_detail["package"] = {
                    "name": pkg.get("name", ""),
                    "ecosystem": pkg.get("ecosystem", ""),
                    "purl": pkg.get("purl", "")
                }
            
            # Version ranges
            if "ranges" in affected_item:
                affected_detail["ranges"] = []
                for range_item in affected_item["ranges"]:
                    range_info = {
                        "type": range_item.get("type", ""),
                        "events": range_item.get("events", [])
                    }
                    if "repo" in range_item:
                        range_info["repo"] = range_item["repo"]
                    affected_detail["ranges"].append(range_info)
            
            # Specific versions affected
            if "versions" in affected_item:
                affected_detail["versions"] = affected_item["versions"]
            
            # Database-specific info
            if "database_specific" in affected_item:
                affected_detail["database_specific"] = affected_item["database_specific"]
            
            # Ecosystem-specific info
            if "ecosystem_specific" in affected_item:
                affected_detail["ecosystem_specific"] = affected_item["ecosystem_specific"]
            
            affected_info.append(affected_detail)
        
        return affected_info
    
    def extract_references(self, vuln_data: Dict) -> List[Dict]:
        """Extract all reference information"""
        references = []
        
        if "references" not in vuln_data:
            return references
        
        for ref in vuln_data["references"]:
            ref_info = {
                "type": ref.get("type", "WEB"),
                "url": ref.get("url", "")
            }
            references.append(ref_info)
        
        return references
    
    def format_for_rag(self, vuln_data: Dict, ecosystem: str) -> Dict:
        """Format vulnerability data for RAG system with complete information"""
        
        # Extract affected packages for content
        affected_info = self.extract_affected_info(vuln_data)
        affected_package_names = []
        for affected in affected_info:
            if "package" in affected and "name" in affected["package"]:
                affected_package_names.append(affected["package"]["name"])
        
        # Build semantic content for embedding (no IDs, no severity scores)
        content_parts = []
        
        # Summary
        if vuln_data.get("summary"):
            content_parts.append(f"Summary: {vuln_data['summary']}")
        
        # Detailed description
        if vuln_data.get("details"):
            content_parts.append(f"Details: {vuln_data['details']}")
        
        # Affected packages (helps with package-specific semantic queries)
        if affected_package_names:
            content_parts.append(f"Affects: {', '.join(affected_package_names)}")
        
        # Build comprehensive metadata
        metadata = {
            # Core identifiers
            "id": vuln_data.get("id", ""),
            "aliases": vuln_data.get("aliases", []),
            
            # Schema version
            "schema_version": vuln_data.get("schema_version", ""),
            
            # Timestamps
            "published": vuln_data.get("published", ""),
            "modified": vuln_data.get("modified", ""),
            "withdrawn": vuln_data.get("withdrawn", ""),
            
            # Ecosystem
            "ecosystem": ecosystem,
            
            # Severity information (stored as-is, not used for filtering)
            "severity": vuln_data.get("severity", []),
            
            # Affected packages with full details
            "affected": affected_info,
            
            # References
            "references": self.extract_references(vuln_data),
            
            # Credits
            "credits": vuln_data.get("credits", []),
            
            # Database-specific information
            "database_specific": vuln_data.get("database_specific", {}),
            
            # Related vulnerabilities
            "related": vuln_data.get("related", []),
        }
        
        return {
            "content": "\n\n".join(content_parts),
            "metadata": metadata
        }
    
    def filter_and_format_vulnerabilities(
        self, 
        vulnerabilities: List[Dict], 
        ecosystem: str,
        max_vulns: int = 5000
    ) -> List[Dict]:
        """Filter vulnerabilities by recency, then format for RAG"""
        
        logger.info(f"Filtering {ecosystem} vulnerabilities...")
        logger.info(f"Criteria: Published within last {self.DAYS_BACK} days (~3 years)")
        
        filtered_vulns = []
        
        for vuln_data in vulnerabilities:
            if len(filtered_vulns) >= max_vulns:
                logger.info(f"Reached target of {max_vulns} vulnerabilities for {ecosystem}")
                break
            
            # Check withdrawn status
            if vuln_data.get("withdrawn"):
                continue
            
            # Filter by recency only
            is_recent = self.is_recent_vulnerability(vuln_data)
            
            if is_recent:
                formatted_vuln = self.format_for_rag(vuln_data, ecosystem)
                filtered_vulns.append(formatted_vuln)
        
        logger.info(f"Filtered to {len(filtered_vulns)} recent vulnerabilities")
        return filtered_vulns
    
    def save_data(self, data: List[Dict], ecosystem: str):
        """Save collected data to JSON file"""
        output_file = self.output_dir / f"{ecosystem}_vulnerabilities.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(data)} vulnerabilities to {output_file}")
    
    def generate_summary(self, all_data: Dict[str, List[Dict]]):
        """Generate a summary of collected data"""
        summary = {
            "collection_date": datetime.now().isoformat(),
            "total_vulnerabilities": sum(len(vulns) for vulns in all_data.values()),
            "ecosystems": {},
            "parameters": {
                "date_range_days": self.DAYS_BACK,
                "target_ecosystems": self.ECOSYSTEMS
            }
        }
        
        for ecosystem, vulns in all_data.items():
            summary["ecosystems"][ecosystem] = len(vulns)
        
        summary_file = self.output_dir / "collection_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Summary saved to {summary_file}")
        return summary
    
    def collect_all(self):
        """Main collection function"""
        logger.info("="*70)
        logger.info("OSV VULNERABILITY DATA COLLECTION")
        logger.info("="*70)
        logger.info(f"Target ecosystems: {', '.join(self.ECOSYSTEMS)}")
        logger.info(f"Date range: Last {self.DAYS_BACK} days (~3 years)")
        logger.info("="*70)
        
        all_data = {}
        
        for ecosystem in self.ECOSYSTEMS:
            logger.info(f"\n{'='*70}")
            logger.info(f"Processing: {ecosystem}")
            logger.info(f"{'='*70}")
            
            # Download all vulnerabilities for ecosystem
            raw_vulns = self.download_ecosystem_data(ecosystem)
            
            if not raw_vulns:
                logger.warning(f"No data retrieved for {ecosystem}, skipping...")
                all_data[ecosystem] = []
                self.save_data([], ecosystem)
                continue
            
            # Filter and format
            filtered_vulns = self.filter_and_format_vulnerabilities(raw_vulns, ecosystem)
            all_data[ecosystem] = filtered_vulns
            
            # Save to file
            self.save_data(filtered_vulns, ecosystem)
        
        # Generate summary
        summary = self.generate_summary(all_data)
        
        logger.info("\n" + "="*70)
        logger.info("COLLECTION COMPLETE!")
        logger.info("="*70)
        logger.info(f"Total vulnerabilities collected: {summary['total_vulnerabilities']}")
        for eco, count in summary['ecosystems'].items():
            logger.info(f"  {eco}: {count}")
        logger.info("="*70)


if __name__ == "__main__":
    collector = OSVDataCollector(output_dir="osv_data")
    collector.collect_all()