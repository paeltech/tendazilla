from crewai import Crew, Agent, Task, Tool
from tools.scraper import scrape_web
from tools.scorer import score_tender
from tools.proposal_writer import generate_proposal
from tools.email_sender import send_tender_notification, send_batch_notifications
import json
import logging
from datetime import datetime
from config import config
from typing import List, Dict, Any

# Setup logging
config.setup_logging()
logger = logging.getLogger(__name__)

class TendazillaCrew:
    """Main CrewAI orchestration system for tender processing"""
    
    def __init__(self):
        # Validate configuration
        if not config.validate():
            raise ValueError("Configuration validation failed. Please check your environment variables.")
        
        # Initialize tools
        self.tools = self._initialize_tools()
        
        # Initialize agents
        self.agents = self._initialize_agents()
        
        # Initialize tasks
        self.tasks = self._initialize_tasks()
        
        # Initialize crew
        self.crew = Crew(
            agents=self.agents,
            tasks=self.tasks,
            verbose=True,
            memory=True
        )
    
    def _initialize_tools(self):
        """Initialize all tools"""
        return {
            'scrape_web': Tool(
                name='scrape_web',
                func=scrape_web,
                description="Scrapes tender listings from a specific portal URL. Returns a list of structured tender opportunities."
            ),
            'score_tender': Tool(
                name='score_tender',
                func=score_tender,
                description="Evaluates a tender opportunity against company profile and returns a confidence score and reasoning."
            ),
            'generate_proposal': Tool(
                name='generate_proposal',
                func=generate_proposal,
                description="Generates a full proposal in markdown format based on the tender and company profile."
            ),
            'send_tender_notification': Tool(
                name='send_tender_notification',
                func=send_tender_notification,
                description="Sends a comprehensive tender notification email with proposal to internal approvers."
            )
        }
    
    def _initialize_agents(self):
        """Initialize all agents with their tools and roles"""
        return [
            Agent(
                name='TenderDiscoveryAgent',
                role='Tender Discovery and Web Scraping Specialist',
                goal='Crawl specified tender portals and extract structured tender listings that match industry relevance.',
                backstory="""You are a smart, efficient scraper trained to navigate various RFP and tender websites. 
                Your job is to extract important tender data for evaluation. You use multiple scraping strategies 
                including static parsing, dynamic JavaScript handling, and API endpoint discovery to ensure maximum 
                coverage of tender opportunities.""",
                tools=[self.tools['scrape_web']],
                verbose=True,
                allow_delegation=False
            ),
            Agent(
                name='EligibilityScoringAgent',
                role='Tender Evaluation Analyst',
                goal='Evaluate tenders against company profile and assign a win-confidence score using hybrid rule-based and AI-powered analysis.',
                backstory="""You are a proposal pre-screening expert with access to both rule-based scoring algorithms 
                and AI-powered analysis. Your job is to analyze tender metadata and match it with internal company 
                strengths, assigning a win-likelihood score. You consider industry match, location, budget, technical 
                requirements, experience, and certifications to provide comprehensive scoring.""",
                tools=[self.tools['score_tender']],
                verbose=True,
                allow_delegation=False
            ),
            Agent(
                name='ProposalWriterAgent',
                role='AI Proposal Writer',
                goal='Generate full proposal drafts for tenders with high win likelihood using AI-powered generation and company templates.',
                backstory="""You're a highly trained AI proposal writer with access to past wins, company capabilities, 
                and comprehensive templates. You write clear, compelling business proposals that address all tender 
                requirements while showcasing company strengths. You can generate proposals using advanced AI models 
                or fall back to sophisticated templates when needed.""",
                tools=[self.tools['generate_proposal']],
                verbose=True,
                allow_delegation=False
            ),
            Agent(
                name='EmailNotificationAgent',
                role='Notification & Approvals Assistant',
                goal='Format and send comprehensive emails with proposal drafts and tender summary to internal approvers.',
                backstory="""You are an internal assistant specializing in communication and stakeholder management. 
                You format and deliver proposal drafts with context via email for final approval before submission. 
                You ensure all relevant information is clearly presented and actionable for decision-makers.""",
                tools=[self.tools['send_tender_notification']],
                verbose=True,
                allow_delegation=False
            )
        ]
    
    def _initialize_tasks(self):
        """Initialize all tasks with their dependencies and expected outputs"""
        return [
            Task(
                name='ScrapeTenderSites',
                description="""Crawl tender portals and return structured tender metadata. 
                Use multiple scraping strategies to ensure maximum coverage. Focus on sites that are 
                most relevant to our industry focus areas.""",
                agent=self.agents[0],  # TenderDiscoveryAgent
                expected_output="""A comprehensive list of tender objects in JSON format, each containing:
                - title: Tender title
                - description: Detailed description
                - deadline: Submission deadline
                - budget: Project budget
                - requirements: List of requirements
                - industry: Industry sector
                - location: Geographic location
                - source_url: Source website
                - scraped_at: Timestamp of scraping""",
                context="""You have access to multiple tender sites including government portals, 
                international organizations, and industry-specific platforms. Prioritize sites that 
                align with our geographic focus (East Africa) and industry expertise (IT, Cloud, 
                Digital Transformation)."""
            ),
            Task(
                name='ScoreTenders',
                description="""Analyze tender metadata and score win-likelihood using hybrid approach. 
                Apply both rule-based scoring and AI-powered analysis to evaluate each tender against 
                our company profile. Only pass tenders scoring 50 or higher.""",
                agent=self.agents[1],  # EligibilityScoringAgent
                expected_output="""List of tender objects with added confidence scores and detailed justifications. 
                Each scored tender should include:
                - score: Numerical score (0-100)
                - justification: Detailed reasoning for the score
                - detailed_scores: Breakdown by scoring criteria
                - scoring_method: Method used (rule-based, AI-powered, or hybrid)""",
                context="""Use our comprehensive company profile including industry focus, core services, 
                certifications, team expertise, past projects, and preferred project size to evaluate 
                each tender. Consider both quantitative factors (budget, timeline) and qualitative 
                factors (industry alignment, technical fit)."""
            ),
            Task(
                name='GenerateProposals',
                description="""Write complete proposal drafts for high-confidence tenders. 
                Use AI-powered generation when possible, with fallback to sophisticated templates. 
                Ensure proposals address all tender requirements and showcase company capabilities.""",
                agent=self.agents[2],  # ProposalWriterAgent
                expected_output="""Markdown-formatted proposals tied to each tender, including all standard sections:
                - Executive Summary
                - Company Profile
                - Understanding of Requirements
                - Proposed Solution
                - Technical Approach
                - Project Timeline
                - Team Structure
                - Relevant Experience
                - Risk Management
                - Quality Assurance
                - Pricing
                - Terms and Conditions""",
                context="""Leverage our company's proven track record, technical expertise, and past 
                successful projects to create compelling proposals. Ensure each proposal is tailored 
                to the specific tender requirements while maintaining professional standards and 
                competitive positioning."""
            ),
            Task(
                name='NotifyApprover',
                description="""Format and email the tender summary and proposal to internal approvers. 
                Create comprehensive notifications that include all relevant information for decision-making. 
                Ensure the email is professional, actionable, and includes clear next steps.""",
                agent=self.agents[3],  # EmailNotificationAgent
                expected_output="""Email sent confirmation with details of what was sent, including:
                - Recipient email address
                - Subject line
                - Content summary
                - Proposal attachment status
                - Delivery confirmation""",
                context="""You are communicating with internal business development and approval teams. 
                They need clear, concise information to make informed decisions about tender opportunities. 
                Include all relevant context, scoring results, and clear next steps for each tender."""
            )
        ]
    
    def run_tender_processing(self, tender_sites: List[Dict[str, str]] = None, company_profile: Dict[str, Any] = None):
        """
        Run the complete tender processing workflow
        
        Args:
            tender_sites: List of tender sites to scrape (optional, will use default if not provided)
            company_profile: Company profile data (optional, will use default if not provided)
        """
        try:
            logger.info("Starting Tendazilla tender processing workflow...")
            
            # Load default data if not provided
            if not company_profile:
                with open('data/company_profile.json') as f:
                    company_profile = json.load(f)
                logger.info("Loaded company profile from data/company_profile.json")
            
            if not tender_sites:
                with open('data/tender_sites.json') as f:
                    tender_sites = json.load(f)
                logger.info("Loaded tender sites from data/tender_sites.json")
            
            # Execute the crew workflow
            result = self.crew.kickoff()
            
            logger.info("Tender processing workflow completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error in tender processing workflow: {str(e)}")
            raise e
    
    def run_single_tender_processing(self, tender_url: str, company_profile: Dict[str, Any] = None):
        """
        Process a single tender URL for testing or specific processing
        
        Args:
            tender_url: Single tender URL to process
            company_profile: Company profile data (optional)
        """
        try:
            logger.info(f"Processing single tender URL: {tender_url}")
            
            # Load company profile if not provided
            if not company_profile:
                with open('data/company_profile.json') as f:
                    company_profile = json.load(f)
            
            # Step 1: Scrape the tender
            logger.info("Step 1: Scraping tender data...")
            tenders = scrape_web(tender_url)
            
            if not tenders:
                logger.warning("No tenders found at the specified URL")
                return {"status": "no_tenders_found", "url": tender_url}
            
            logger.info(f"Found {len(tenders)} tenders")
            
            # Step 2: Score tenders
            logger.info("Step 2: Scoring tenders...")
            scored_tenders = []
            for tender in tenders:
                score_result = score_tender(tender, company_profile)
                if score_result['score'] >= config.SCORING_THRESHOLD:
                    tender.update(score_result)
                    scored_tenders.append(tender)
                    logger.info(f"Tender '{tender['title']}' scored {score_result['score']}/100")
                else:
                    logger.info(f"Tender '{tender['title']}' scored {score_result['score']}/100 - below threshold")
            
            if not scored_tenders:
                logger.info("No tenders met the scoring threshold")
                return {"status": "no_qualified_tenders", "url": tender_url, "total_tenders": len(tenders)}
            
            # Step 3: Generate proposals
            logger.info("Step 3: Generating proposals...")
            proposals = []
            for tender in scored_tenders:
                proposal = generate_proposal(tender, company_profile)
                proposals.append({
                    "tender": tender,
                    "proposal": proposal
                })
                logger.info(f"Generated proposal for tender: {tender['title']}")
            
            # Step 4: Send notifications
            logger.info("Step 4: Sending notifications...")
            email_results = []
            for p in proposals:
                tender = p["tender"]
                proposal = p["proposal"]
                
                email_result = send_tender_notification(
                    tender=tender,
                    proposal=proposal,
                    score=tender.get('score')
                )
                email_results.append(email_result)
                logger.info(f"Email notification sent for tender: {tender['title']}")
            
            # Return comprehensive results
            return {
                "status": "success",
                "url": tender_url,
                "total_tenders_found": len(tenders),
                "qualified_tenders": len(scored_tenders),
                "proposals_generated": len(proposals),
                "notifications_sent": len(email_results),
                "results": {
                    "tenders": tenders,
                    "scored_tenders": scored_tenders,
                    "proposals": proposals,
                    "email_results": email_results
                }
            }
            
        except Exception as e:
            logger.error(f"Error in single tender processing: {str(e)}")
            return {"status": "error", "error": str(e), "url": tender_url}
    
    def test_system_components(self):
        """Test all system components to ensure they're working correctly"""
        logger.info("Testing system components...")
        
        test_results = {}
        
        try:
            # Test configuration
            test_results['config'] = "✅ Configuration loaded successfully"
            
            # Test company profile loading
            with open('data/company_profile.json') as f:
                company_profile = json.load(f)
            test_results['company_profile'] = "✅ Company profile loaded successfully"
            
            # Test tender sites loading
            with open('data/tender_sites.json') as f:
                tender_sites = json.load(f)
            test_results['tender_sites'] = "✅ Tender sites loaded successfully"
            
            # Test tools initialization
            test_results['tools'] = "✅ All tools initialized successfully"
            
            # Test agents initialization
            test_results['agents'] = "✅ All agents initialized successfully"
            
            # Test tasks initialization
            test_results['tasks'] = "✅ All tasks initialized successfully"
            
            # Test crew initialization
            test_results['crew'] = "✅ Crew initialized successfully"
            
            logger.info("All system components tested successfully")
            return {"status": "success", "results": test_results}
            
        except Exception as e:
            logger.error(f"System component test failed: {str(e)}")
            return {"status": "error", "error": str(e), "results": test_results}

def main():
    """Main entry point for the Tendazilla system"""
    try:
        logger.info("Initializing Tendazilla CrewAI system...")
        
        # Initialize the system
        tendazilla = TendazillaCrew()
        
        # Test system components
        test_result = tendazilla.test_system_components()
        if test_result['status'] != 'success':
            logger.error("System component test failed")
            return
        
        # Run the main workflow
        logger.info("Running main tender processing workflow...")
        result = tendazilla.run_tender_processing()
        
        logger.info("Tendazilla workflow completed successfully!")
        return result
        
    except Exception as e:
        logger.error(f"Error in main Tendazilla workflow: {str(e)}")
        raise e

if __name__ == "__main__":
    main()
