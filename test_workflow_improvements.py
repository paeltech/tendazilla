#!/usr/bin/env python3
"""Test script to verify workflow improvements"""

from run_chain import TendazillaCrew
import json

def test_workflow_improvements():
    """Test the improved workflow"""
    
    print("Testing Workflow Improvements")
    print("=" * 60)
    
    try:
        # Initialize the system
        print("1. Initializing Tendazilla system...")
        tendazilla = TendazillaCrew()
        print("   ✅ System initialized successfully")
        
        # Test the new workflow method
        print("\n2. Testing real scraping workflow...")
        result = tendazilla.test_workflow_with_real_scraping()
        
        print(f"   Status: {result.get('status', 'Unknown')}")
        print(f"   Sites tested: {result.get('total_sites_tested', 0)}")
        print(f"   Total tenders found: {result.get('total_tenders_found', 0)}")
        print(f"   Qualified tenders: {result.get('qualified_tenders', 0)}")
        
        if result.get('status') == 'success' and result.get('sample_tenders'):
            print("\n3. Sample tenders found:")
            for i, tender in enumerate(result['sample_tenders']):
                print(f"   Tender {i+1}:")
                print(f"     Title: {tender.get('title', 'No title')[:100]}...")
                print(f"     Industry: {tender.get('industry', 'Unknown')}")
                print(f"     Location: {tender.get('location', 'Unknown')}")
                print(f"     Source: {tender.get('source_url', 'Unknown')}")
                print()
        
        # Test the main workflow
        print("\n4. Testing main CrewAI workflow...")
        print("   This will test the full agent pipeline...")
        
        # Run with real scraping (not sample data)
        main_result = tendazilla.run_tender_processing(use_sample_data=False)
        
        if main_result:
            print("   ✅ Main workflow completed")
            print(f"   Result type: {type(main_result)}")
            if isinstance(main_result, str):
                print(f"   Result preview: {main_result[:200]}...")
            else:
                print(f"   Result keys: {list(main_result.keys()) if hasattr(main_result, 'keys') else 'Not a dict'}")
        else:
            print("   ⚠️  Main workflow returned no result")
        
        print("\n" + "=" * 60)
        print("Testing completed!")
        
        return result
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_workflow_improvements()
