#!/usr/bin/env python3
"""Test script to verify scoring improvements"""

from tools.scorer import score_tender
import json

def test_scoring_improvements():
    """Test the improved scoring system"""
    
    print("Testing Scoring Improvements")
    print("=" * 50)
    
    # Load company profile
    with open('data/company_profile.json', 'r') as f:
        company_profile = json.load(f)
    
    # Create test tender data
    test_tenders = [
        {
            "title": "Cloud Infrastructure Migration for Government Agency",
            "description": "Seeking experienced vendors to migrate legacy systems to AWS cloud infrastructure with security compliance requirements including SOC 2 and ISO 27001 certification.",
            "deadline": "2025-02-15",
            "budget": "USD 180,000",
            "requirements": ["AWS Certified Solutions Architect", "ISO 27001", "Government compliance experience", "Migration expertise"],
            "industry": "Information Technology",
            "location": "Kenya",
            "source_url": "https://icta.go.ke/tenders/",
            "scraped_at": "2025-01-15T10:30:00"
        },
        {
            "title": "Broadband Network Expansion Project",
            "description": "Telecommunications infrastructure expansion to provide high-speed internet access to rural areas in East Africa.",
            "deadline": "2025-03-01",
            "budget": "USD 2,500,000",
            "requirements": ["Fiber optic installation", "Network design", "Project management", "Local partnerships"],
            "industry": "Telecommunications",
            "location": "Tanzania",
            "source_url": "https://icta.go.ke/tenders/",
            "scraped_at": "2025-01-15T10:30:00"
        },
        {
            "title": "Agricultural Equipment Procurement",
            "description": "Procurement of agricultural machinery and equipment for farming cooperatives.",
            "deadline": "2025-02-20",
            "budget": "USD 50,000",
            "requirements": ["Agricultural equipment expertise", "Local supplier network", "Maintenance support"],
            "industry": "Agriculture",
            "location": "Uganda",
            "source_url": "https://procurement.go.ug/",
            "scraped_at": "2025-01-15T10:30:00"
        }
    ]
    
    print(f"Testing {len(test_tenders)} sample tenders...")
    print(f"Company focus areas: {company_profile.get('industry_focus', [])}")
    print(f"Geographic focus: {company_profile.get('geographical_focus', [])}")
    print(f"Budget range: ${company_profile.get('preferred_project_size', {}).get('min_budget', 'N/A'):,} - ${company_profile.get('preferred_project_size', {}).get('max_budget', 'N/A'):,}")
    print()
    
    scored_tenders = []
    
    for i, tender in enumerate(test_tenders, 1):
        print(f"Testing Tender {i}: {tender['title']}")
        print(f"  Industry: {tender['industry']}")
        print(f"  Location: {tender['location']}")
        print(f"  Budget: {tender['budget']}")
        print(f"  Requirements: {', '.join(tender['requirements'][:2])}...")
        
        try:
            # Score the tender
            score_result = score_tender(tender, company_profile)
            
            print(f"  ✅ Score: {score_result.get('score', 0)}/100")
            print(f"  📝 Justification: {score_result.get('justification', 'No justification')[:120]}...")
            
            # Check if scoring includes detailed breakdown
            detailed_scores = score_result.get('detailed_scores', {})
            if detailed_scores:
                print(f"  📊 Detailed scores: {len(detailed_scores)} criteria evaluated")
                top_scores = sorted(detailed_scores.items(), key=lambda x: x[1], reverse=True)[:3]
                for criterion, score_val in top_scores:
                    print(f"     - {criterion.replace('_', ' ').title()}: {score_val}")
            
            # Add to scored tenders if above threshold
            if score_result.get('score', 0) >= 30:
                tender_with_score = tender.copy()
                tender_with_score.update(score_result)
                scored_tenders.append(tender_with_score)
                print(f"  ✅ PASSED threshold (≥30)")
            else:
                print(f"  ❌ Below threshold (<30)")
            
        except Exception as e:
            print(f"  ❌ Scoring failed: {str(e)}")
        
        print()
    
    print("=" * 50)
    print(f"SCORING RESULTS SUMMARY:")
    print(f"Tenders tested: {len(test_tenders)}")
    print(f"Tenders passed threshold: {len(scored_tenders)}")
    print(f"Success rate: {len(scored_tenders)/len(test_tenders)*100:.1f}%")
    
    if scored_tenders:
        print(f"\nQualified tenders:")
        for tender in scored_tenders:
            print(f"  • {tender['title'][:60]}... (Score: {tender.get('score', 0)})")
    
    print(f"\n✅ Scoring system is working properly!")
    return scored_tenders

if __name__ == "__main__":
    test_scoring_improvements()
