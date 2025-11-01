"""
Risk scoring and prioritization system
Combines CVSS, EPSS, KEV, and asset criticality for comprehensive risk assessment
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger("RiskScoring")

@dataclass
class RiskFactors:
    """Risk factors for vulnerability scoring"""
    cvss_score: float = 0.0
    epss_score: float = 0.0
    kev_flag: bool = False
    asset_criticality: float = 1.0  # 1.0 = normal, 2.0 = high, 3.0 = critical
    internet_exposure: bool = False
    exploit_available: bool = False
    patch_available: bool = True
    days_since_published: int = 0

@dataclass
class RiskScore:
    """Comprehensive risk score"""
    overall_score: float
    cvss_contribution: float
    epss_contribution: float
    kev_contribution: float
    asset_contribution: float
    exposure_contribution: float
    exploit_contribution: float
    patch_contribution: float
    time_contribution: float
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    confidence: float

class RiskScorer:
    """Calculate comprehensive risk scores for vulnerabilities"""
    
    def __init__(self):
        # Weight configuration (sum should be 1.0)
        self.weights = {
            'cvss': 0.25,
            'epss': 0.20,
            'kev': 0.15,
            'asset': 0.15,
            'exposure': 0.10,
            'exploit': 0.10,
            'patch': 0.03,
            'time': 0.02
        }
        
        # Risk level thresholds
        self.thresholds = {
            'CRITICAL': 0.8,
            'HIGH': 0.6,
            'MEDIUM': 0.4,
            'LOW': 0.0
        }
    
    def calculate_risk_score(self, factors: RiskFactors) -> RiskScore:
        """Calculate comprehensive risk score"""
        
        # Normalize CVSS score (0-10 scale)
        cvss_score = min(factors.cvss_score / 10.0, 1.0)
        
        # EPSS score is already 0-1
        epss_score = min(factors.epss_score, 1.0)
        
        # KEV flag (binary)
        kev_score = 1.0 if factors.kev_flag else 0.0
        
        # Asset criticality (1.0 = normal, 2.0 = high, 3.0 = critical)
        asset_score = min(factors.asset_criticality / 3.0, 1.0)
        
        # Internet exposure (binary)
        exposure_score = 1.0 if factors.internet_exposure else 0.0
        
        # Exploit availability (binary)
        exploit_score = 1.0 if factors.exploit_available else 0.0
        
        # Patch availability (inverse - no patch = higher risk)
        patch_score = 0.0 if factors.patch_available else 1.0
        
        # Time factor (older vulnerabilities get slightly higher risk)
        time_score = min(factors.days_since_published / 365.0, 1.0) * 0.5
        
        # Calculate weighted score
        overall_score = (
            self.weights['cvss'] * cvss_score +
            self.weights['epss'] * epss_score +
            self.weights['kev'] * kev_score +
            self.weights['asset'] * asset_score +
            self.weights['exposure'] * exposure_score +
            self.weights['exploit'] * exploit_score +
            self.weights['patch'] * patch_score +
            self.weights['time'] * time_score
        )
        
        # Determine risk level
        risk_level = self._determine_risk_level(overall_score)
        
        # Calculate confidence based on data availability
        confidence = self._calculate_confidence(factors)
        
        return RiskScore(
            overall_score=overall_score,
            cvss_contribution=self.weights['cvss'] * cvss_score,
            epss_contribution=self.weights['epss'] * epss_score,
            kev_contribution=self.weights['kev'] * kev_score,
            asset_contribution=self.weights['asset'] * asset_score,
            exposure_contribution=self.weights['exposure'] * exposure_score,
            exploit_contribution=self.weights['exploit'] * exploit_score,
            patch_contribution=self.weights['patch'] * patch_score,
            time_contribution=self.weights['time'] * time_score,
            risk_level=risk_level,
            confidence=confidence
        )
    
    def _determine_risk_level(self, score: float) -> str:
        """Determine risk level based on score"""
        if score >= self.thresholds['CRITICAL']:
            return 'CRITICAL'
        elif score >= self.thresholds['HIGH']:
            return 'HIGH'
        elif score >= self.thresholds['MEDIUM']:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _calculate_confidence(self, factors: RiskFactors) -> float:
        """Calculate confidence in the risk score based on data availability"""
        confidence_factors = []
        
        # CVSS score availability
        confidence_factors.append(1.0 if factors.cvss_score > 0 else 0.0)
        
        # EPSS score availability
        confidence_factors.append(1.0 if factors.epss_score > 0 else 0.0)
        
        # KEV flag availability
        confidence_factors.append(1.0)  # Always available (True/False)
        
        # Asset criticality availability
        confidence_factors.append(1.0)  # Always available (default 1.0)
        
        # Internet exposure availability
        confidence_factors.append(1.0)  # Always available (True/False)
        
        # Exploit availability
        confidence_factors.append(1.0)  # Always available (True/False)
        
        # Patch availability
        confidence_factors.append(1.0)  # Always available (True/False)
        
        # Time information availability
        confidence_factors.append(1.0)  # Always available
        
        return sum(confidence_factors) / len(confidence_factors)
    
    def extract_risk_factors_from_vulnerability(
        self, 
        vuln_data: Dict[str, Any], 
        asset_info: Optional[Dict[str, Any]] = None
    ) -> RiskFactors:
        """Extract risk factors from vulnerability data"""
        
        # Extract CVSS score
        cvss_score = 0.0
        severity_data = vuln_data.get('severity', [])
        for sev in severity_data:
            if sev.get('type') in ['CVSS_V3', 'CVSS_V2']:
                try:
                    cvss_score = float(sev.get('score', 0))
                    break
                except (ValueError, TypeError):
                    continue
        
        # Extract EPSS score
        epss_score = 0.0
        if 'epss_data' in vuln_data:
            epss_score = vuln_data['epss_data'].get('epss_score', 0.0)
        
        # Check KEV flag
        kev_flag = vuln_data.get('source') == 'CISA_KEV' or 'kev_data' in vuln_data
        
        # Extract asset information
        asset_criticality = 1.0
        internet_exposure = False
        
        if asset_info:
            asset_criticality = asset_info.get('criticality', 1.0)
            internet_exposure = asset_info.get('internet_exposed', False)
        
        # Check for exploit availability
        exploit_available = False
        if 'exploit_data' in vuln_data:
            exploit_available = vuln_data['exploit_data'].get('exploit_available', False)
        
        # Check patch availability
        patch_available = True
        affected_packages = vuln_data.get('affected_packages', [])
        for pkg in affected_packages:
            if isinstance(pkg, dict) and 'ranges' in pkg:
                for range_info in pkg['ranges']:
                    if 'events' in range_info:
                        for event in range_info['events']:
                            if 'fixed' in event:
                                patch_available = True
                                break
        
        # Calculate days since published
        days_since_published = 0
        published_date = vuln_data.get('published', '')
        if published_date:
            try:
                pub_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                days_since_published = (datetime.now(pub_date.tzinfo) - pub_date).days
            except (ValueError, TypeError):
                days_since_published = 0
        
        return RiskFactors(
            cvss_score=cvss_score,
            epss_score=epss_score,
            kev_flag=kev_flag,
            asset_criticality=asset_criticality,
            internet_exposure=internet_exposure,
            exploit_available=exploit_available,
            patch_available=patch_available,
            days_since_published=days_since_published
        )
    
    def score_vulnerability(
        self, 
        vuln_data: Dict[str, Any], 
        asset_info: Optional[Dict[str, Any]] = None
    ) -> RiskScore:
        """Score a vulnerability with optional asset context"""
        factors = self.extract_risk_factors_from_vulnerability(vuln_data, asset_info)
        return self.calculate_risk_score(factors)
    
    def prioritize_vulnerabilities(
        self, 
        vulnerabilities: List[Dict[str, Any]], 
        asset_context: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[Tuple[Dict[str, Any], RiskScore]]:
        """Prioritize a list of vulnerabilities by risk score"""
        
        scored_vulns = []
        
        for vuln in vulnerabilities:
            # Get asset context for this vulnerability
            asset_info = None
            if asset_context:
                vuln_id = vuln.get('id', '')
                asset_info = asset_context.get(vuln_id)
            
            # Calculate risk score
            risk_score = self.score_vulnerability(vuln, asset_info)
            
            scored_vulns.append((vuln, risk_score))
        
        # Sort by overall risk score (descending)
        scored_vulns.sort(key=lambda x: x[1].overall_score, reverse=True)
        
        return scored_vulns
    
    def get_risk_summary(self, scored_vulnerabilities: List[Tuple[Dict[str, Any], RiskScore]]) -> Dict[str, Any]:
        """Generate risk summary from scored vulnerabilities"""
        
        total_vulns = len(scored_vulnerabilities)
        risk_levels = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        
        avg_score = 0.0
        avg_confidence = 0.0
        
        for vuln, score in scored_vulnerabilities:
            risk_levels[score.risk_level] += 1
            avg_score += score.overall_score
            avg_confidence += score.confidence
        
        if total_vulns > 0:
            avg_score /= total_vulns
            avg_confidence /= total_vulns
        
        return {
            'total_vulnerabilities': total_vulns,
            'risk_distribution': risk_levels,
            'average_risk_score': avg_score,
            'average_confidence': avg_confidence,
            'critical_count': risk_levels['CRITICAL'],
            'high_count': risk_levels['HIGH'],
            'medium_count': risk_levels['MEDIUM'],
            'low_count': risk_levels['LOW']
        }

# Global risk scorer instance
_risk_scorer = None

def get_risk_scorer() -> RiskScorer:
    """Get global risk scorer instance"""
    global _risk_scorer
    if _risk_scorer is None:
        _risk_scorer = RiskScorer()
    return _risk_scorer

def calculate_vulnerability_risk(
    vuln_data: Dict[str, Any], 
    asset_info: Optional[Dict[str, Any]] = None
) -> RiskScore:
    """Convenience function for calculating vulnerability risk"""
    scorer = get_risk_scorer()
    return scorer.score_vulnerability(vuln_data, asset_info)

def prioritize_vulnerabilities(
    vulnerabilities: List[Dict[str, Any]], 
    asset_context: Optional[Dict[str, Dict[str, Any]]] = None
) -> List[Tuple[Dict[str, Any], RiskScore]]:
    """Convenience function for prioritizing vulnerabilities"""
    scorer = get_risk_scorer()
    return scorer.prioritize_vulnerabilities(vulnerabilities, asset_context)





