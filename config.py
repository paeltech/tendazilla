import os
from typing import Optional
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for Tendazilla system"""
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY', '')
    OPENAI_MODEL: str = os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')
    
    # Email Configuration (Resend.com)
    RESEND_API_KEY: str = os.getenv('RESEND_API_KEY', '')
    RESEND_FROM_EMAIL: str = os.getenv('RESEND_FROM_EMAIL', 'noreply@example.com')
    
    # Company Configuration
    COMPANY_APPROVER_EMAIL: str = os.getenv('COMPANY_APPROVER_EMAIL', 'approver@example.com')
    COMPANY_NAME: str = os.getenv('COMPANY_NAME', 'ADB Technology')
    
    # Email Recipients Configuration
    EMAIL_RECIPIENTS: list = [email.strip() for email in os.getenv('EMAIL_RECIPIENTS', 'pmandele9@gmail.com,proposals@company.com,management@company.com').split(',') if email.strip()]
    EMAIL_RECIPIENTS_CC: list = [email.strip() for email in os.getenv('EMAIL_RECIPIENTS_CC', '').split(',') if email.strip()] if os.getenv('EMAIL_RECIPIENTS_CC') else []
    EMAIL_RECIPIENTS_BCC: list = [email.strip() for email in os.getenv('EMAIL_RECIPIENTS_BCC', '').split(',') if email.strip()] if os.getenv('EMAIL_RECIPIENTS_BCC') else []
    
    # Scraping Configuration
    SCRAPING_TIMEOUT: int = int(os.getenv('SCRAPING_TIMEOUT', '30'))
    SCRAPING_MAX_RETRIES: int = int(os.getenv('SCRAPING_MAX_RETRIES', '3'))
    SCRAPING_DELAY_BETWEEN_REQUESTS: float = float(os.getenv('SCRAPING_DELAY_BETWEEN_REQUESTS', '2'))
    
    # Scoring Configuration
    SCORING_THRESHOLD: int = int(os.getenv('SCORING_THRESHOLD', '50'))
    SCORING_AI_ENABLED: bool = os.getenv('SCORING_AI_ENABLED', 'true').lower() == 'true'
    SCORING_AI_MODEL: str = os.getenv('SCORING_AI_MODEL', 'gpt-3.5-turbo')
    
    # Proposal Configuration
    PROPOSAL_AI_ENABLED: bool = os.getenv('PROPOSAL_AI_ENABLED', 'true').lower() == 'true'
    PROPOSAL_AI_MODEL: str = os.getenv('PROPOSAL_AI_MODEL', 'gpt-4-turbo-preview')
    PROPOSAL_MAX_TOKENS: int = int(os.getenv('PROPOSAL_MAX_TOKENS', '4000'))
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', 'tendazilla.log')
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = int(os.getenv('RATE_LIMIT_REQUESTS_PER_MINUTE', '60'))
    RATE_LIMIT_DELAY_SECONDS: float = float(os.getenv('RATE_LIMIT_DELAY_SECONDS', '1'))
    
    # Testing Configuration
    USE_SAMPLE_DATA: bool = os.getenv('USE_SAMPLE_DATA', 'false').lower() == 'true'
    TEST_MODE: bool = os.getenv('TEST_MODE', 'false').lower() == 'true'
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        required_vars = [
            'OPENAI_API_KEY',
            'RESEND_API_KEY'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            return False
        
        return True
    
    @classmethod
    def setup_logging(cls):
        """Setup logging configuration"""
        log_level = getattr(logging, cls.LOG_LEVEL.upper(), logging.INFO)
        
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(cls.LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Configure logging
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(cls.LOG_FILE),
                logging.StreamHandler()
            ]
        )
        
        # Set specific logger levels
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('playwright').setLevel(logging.WARNING)

# Global config instance
config = Config()
