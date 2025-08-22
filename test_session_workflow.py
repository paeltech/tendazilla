#!/usr/bin/env python3
"""Test script to verify the improved workflow with session management"""

from run_chain import TendazillaCrew
import json
import os
from pathlib import Path

def test_session_workflow():
    """Test the improved workflow with session management"""
    
    print("Testing Improved Workflow with Session Management")
    print("=" * 60)
    
    try:
        # Initialize the system
        print("1. Initializing Tendazilla system...")
        tendazilla = TendazillaCrew()
        print("   ✅ System initialized successfully")
        
        # Test the improved workflow
        print("\n2. Running improved workflow with session management...")
        result = tendazilla.run_tender_processing(use_sample_data=False)
        
        if result and result.get('status') == 'success':
            print("   ✅ Workflow completed successfully!")
            
            # Display session information
            session_folder = result.get('session_folder')
            session_id = result.get('session_id')
            
            print(f"\n3. Session Information:")
            print(f"   Session ID: {session_id}")
            print(f"   Session Folder: {session_folder}")
            
            # Verify session folder exists
            if session_folder and os.path.exists(session_folder):
                print("   ✅ Session folder created successfully")
                
                # Check files in session folder
                session_path = Path(session_folder)
                print(f"\n4. Session Folder Contents:")
                
                # List all files
                for item in session_path.rglob('*'):
                    if item.is_file():
                        rel_path = item.relative_to(session_path)
                        size = item.stat().st_size
                        print(f"   📄 {rel_path} ({size} bytes)")
                
                # Check specific files
                scraped_file = session_path / "01_scraped_tenders.json"
                scored_file = session_path / "02_scored_tenders.json"
                proposals_folder = session_path / "proposals"
                
                if scraped_file.exists():
                    with open(scraped_file, 'r') as f:
                        scraped_data = json.load(f)
                    print(f"   ✅ Scraped tenders: {len(scraped_data)} tenders")
                
                if scored_file.exists():
                    with open(scored_file, 'r') as f:
                        scored_data = json.load(f)
                    print(f"   ✅ Scored tenders: {len(scored_data)} tenders")
                    
                    # Show scoring distribution
                    scores = [t.get('score', 0) for t in scored_data if isinstance(t, dict)]
                    if scores:
                        qualified = len([s for s in scores if s >= 30])
                        print(f"      - Qualified (≥30): {qualified}")
                        print(f"      - Average score: {sum(scores)/len(scores):.1f}")
                
                if proposals_folder.exists():
                    proposal_files = list(proposals_folder.glob("*.md"))
                    print(f"   ✅ Proposals: {len(proposal_files)} markdown files")
                
            else:
                print("   ❌ Session folder not found")
            
            # Display workflow summary
            print(f"\n5. Workflow Summary:")
            print(f"   - Tenders Scraped: {result.get('scraped_tenders_count', 0)}")
            print(f"   - Tenders Scored: {result.get('scored_tenders_count', 0)}")
            print(f"   - Qualified Tenders: {result.get('qualified_tenders_count', 0)}")
            print(f"   - Proposals Generated: {result.get('proposals_generated', 0)}")
            
        else:
            print("   ❌ Workflow failed")
            if result:
                print(f"   Error: {result.get('message', 'Unknown error')}")
                print(f"   Session folder: {result.get('session_folder', 'None')}")
    
    except Exception as e:
        print(f"   ❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_session_workflow()
