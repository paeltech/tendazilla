# 🚀 Tendazilla - AI-Powered Tender Management System

Tendazilla is a sophisticated, AI-powered tender management system that automates the entire tender lifecycle from discovery to proposal generation and approval notification. Built with CrewAI, it orchestrates four specialized agents to deliver comprehensive tender processing capabilities.

## ✨ Features

### 🔍 **Intelligent Tender Discovery**
- **Multi-Strategy Scraping**: Combines BeautifulSoup, Playwright, and Selenium for maximum coverage
- **API Endpoint Discovery**: Automatically detects and uses available API endpoints
- **Rate Limiting & Retry Logic**: Respectful scraping with intelligent fallbacks
- **Sample Data Fallback**: Provides test data when scraping fails

### 🎯 **Hybrid Tender Scoring**
- **Rule-Based Scoring**: Comprehensive evaluation using industry, location, budget, and technical criteria
- **AI-Powered Analysis**: OpenAI integration for intelligent tender assessment
- **Combined Scoring**: 70% rule-based + 30% AI analysis for optimal results
- **Detailed Justifications**: Clear reasoning for each scoring decision

### 📝 **AI-Powered Proposal Generation**
- **OpenAI Integration**: Uses GPT-4 for intelligent proposal creation
- **Template Fallback**: Sophisticated templates when AI is unavailable
- **Comprehensive Sections**: All standard proposal components included
- **Company Profile Integration**: Leverages past experience and capabilities

### 📧 **Professional Email Notifications**
- **Resend.com Integration**: Professional email delivery service
- **HTML & Text Versions**: Beautiful, responsive email templates
- **Batch Processing**: Efficient handling of multiple tenders
- **SMTP Fallback**: Backup email delivery method

### 🛠 **Enterprise Features**
- **Environment Configuration**: Secure API key management
- **Comprehensive Logging**: Detailed system monitoring and debugging
- **Error Handling**: Robust error handling with graceful fallbacks
- **Testing Framework**: Built-in system component testing

## 🏗 Architecture

### **CrewAI Agent System**
```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│ TenderDiscovery     │    │ EligibilityScoring  │    │ ProposalWriter      │    │ EmailNotification   │
│ Agent               │    │ Agent               │    │ Agent               │    │ Agent               │
├─────────────────────┤    ├─────────────────────┤    ├─────────────────────┤    ├─────────────────────┤
│ • Web Scraping      │    │ • Rule-based        │    │ • AI Generation      │    │ • Email Templates   │
│ • Multiple          │    │   Scoring           │    │ • Template          │    │ • Resend.com        │
│   Strategies        │    │ • AI Analysis       │    │   Fallback          │    │ • SMTP Fallback     │
│ • API Discovery     │    │ • Hybrid Scoring    │    │ • Company Data      │    │ • Batch Processing  │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

### **Data Flow**
1. **Discovery** → Scrapes tender sites for opportunities
2. **Scoring** → Evaluates tenders against company profile
3. **Generation** → Creates comprehensive proposals
4. **Notification** → Sends approval emails to stakeholders

## 🚀 Quick Start

### **1. Environment Setup**
```bash
# Clone the repository
git clone <repository-url>
cd tendazilla

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### **2. Configuration**
```bash
# Copy environment template
cp env.example .env

# Edit .env with your API keys
nano .env
```

**Required Environment Variables:**
```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4-turbo-preview

# Email Configuration (Resend.com)
RESEND_API_KEY=your_resend_api_key_here
RESEND_FROM_EMAIL=noreply@yourdomain.com

# Company Configuration
COMPANY_APPROVER_EMAIL=approver@yourdomain.com
COMPANY_NAME=Your Company Name
```

### **3. Install Playwright Browsers**
```bash
playwright install
```

### **4. Run the System**
```bash
# Test system components
python run_chain.py

# Or run specific components
python -c "
from run_chain import TendazillaCrew
tendazilla = TendazillaCrew()
result = tendazilla.run_single_tender_processing('https://example-tender-site.com')
print(result)
"
```

## 📊 System Configuration

### **Scraping Configuration**
```env
SCRAPING_TIMEOUT=30
SCRAPING_MAX_RETRIES=3
SCRAPING_DELAY_BETWEEN_REQUESTS=2
RATE_LIMIT_REQUESTS_PER_MINUTE=60
```

### **Scoring Configuration**
```env
SCORING_THRESHOLD=50
SCORING_AI_ENABLED=true
SCORING_AI_MODEL=gpt-3.5-turbo
```

### **Proposal Configuration**
```env
PROPOSAL_AI_ENABLED=true
PROPOSAL_AI_MODEL=gpt-4-turbo-preview
PROPOSAL_MAX_TOKENS=4000
```

## 🎯 Usage Examples

### **Single Tender Processing**
```python
from run_chain import TendazillaCrew

# Initialize system
tendazilla = TendazillaCrew()

# Process single tender
result = tendazilla.run_single_tender_processing(
    tender_url="https://tenders.example.com/opportunity/123"
)

print(f"Status: {result['status']}")
print(f"Tenders found: {result['total_tenders_found']}")
print(f"Qualified tenders: {result['qualified_tenders']}")
print(f"Proposals generated: {result['proposals_generated']}")
```

### **Batch Processing**
```python
# Process multiple tender sites
tender_sites = [
    {"name": "Site 1", "url": "https://site1.com/tenders"},
    {"name": "Site 2", "url": "https://site2.com/opportunities"}
]

result = tendazilla.run_tender_processing(tender_sites=tender_sites)
```

### **Custom Company Profile**
```python
custom_profile = {
    "company_name": "Custom Tech Solutions",
    "industry_focus": ["Custom Software", "AI Solutions"],
    "core_services": ["Custom Development", "AI Integration"],
    "preferred_project_size": {"min_budget": 50000, "max_budget": 1000000}
}

result = tendazilla.run_tender_processing(company_profile=custom_profile)
```

## 🔧 Customization

### **Adding New Tender Sites**
Edit `data/tender_sites.json`:
```json
[
    {
        "name": "New Tender Portal",
        "url": "https://newportal.com/tenders"
    }
]
```

### **Modifying Scoring Criteria**
Edit `tools/scorer.py` to adjust scoring weights and criteria:
```python
self.scoring_weights = {
    'industry_match': 0.25,      # Increased from 0.20
    'location_match': 0.20,      # Increased from 0.15
    'budget_match': 0.20,        # Unchanged
    'technical_match': 0.20,     # Unchanged
    'experience_match': 0.10,    # Decreased from 0.15
    'certification_match': 0.05  # Decreased from 0.10
}
```

### **Custom Proposal Templates**
Modify `tools/proposal_writer.py` to add new sections or modify existing ones.

## 🧪 Testing

### **System Component Testing**
```python
from run_chain import TendazillaCrew

tendazilla = TendazillaCrew()
test_result = tendazilla.test_system_components()

if test_result['status'] == 'success':
    print("✅ All components working correctly")
else:
    print(f"❌ Test failed: {test_result['error']}")
```

### **Email Configuration Testing**
```python
from tools.email_sender import test_email_configuration

result = test_email_configuration()
print(result)
```

### **Individual Tool Testing**
```python
from tools.scraper import scrape_web
from tools.scorer import score_tender
from tools.proposal_writer import generate_proposal

# Test scraping
tenders = scrape_web("https://example.com")

# Test scoring
if tenders:
    score = score_tender(tenders[0], company_profile)
    print(f"Score: {score['score']}/100")

# Test proposal generation
proposal = generate_proposal(tenders[0], company_profile)
print(f"Proposal length: {len(proposal)} characters")
```

## 📈 Performance & Monitoring

### **Logging**
The system provides comprehensive logging at multiple levels:
- **INFO**: General workflow progress
- **WARNING**: Non-critical issues and fallbacks
- **ERROR**: Critical errors and failures
- **DEBUG**: Detailed debugging information

### **Metrics Tracking**
Monitor system performance through:
- Tender discovery success rates
- Scoring accuracy and consistency
- Proposal generation quality
- Email delivery success rates

### **Error Handling**
The system implements graceful degradation:
- Multiple scraping strategies with fallbacks
- AI and template-based proposal generation
- Multiple email delivery methods
- Comprehensive error logging and reporting

## 🔒 Security & Compliance

### **API Key Management**
- Environment variable-based configuration
- No hardcoded credentials
- Secure API key handling

### **Data Privacy**
- Local processing of sensitive data
- No external data transmission beyond API calls
- Configurable data retention policies

### **Rate Limiting**
- Respectful web scraping practices
- Configurable request delays
- Automatic retry with exponential backoff

## 🚀 Deployment

### **Local Development**
```bash
# Development mode with hot reload
python -m flask run --debug

# Or direct execution
python run_chain.py
```

### **Production Deployment**
```bash
# Install production dependencies
pip install -r requirements.txt --no-dev

# Set production environment variables
export PRODUCTION=true
export LOG_LEVEL=WARNING

# Run with production settings
python run_chain.py
```

### **Docker Deployment**
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN playwright install

CMD ["python", "run_chain.py"]
```

## 🤝 Contributing

### **Development Setup**
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Code formatting
black .
flake8 .
mypy .
```

### **Code Standards**
- Follow PEP 8 style guidelines
- Include comprehensive docstrings
- Write unit tests for new features
- Update documentation for changes

## 📚 Documentation

- **API Reference**: Detailed tool and function documentation
- **Configuration Guide**: Environment variables and settings
- **Troubleshooting**: Common issues and solutions
- **Examples**: Real-world usage scenarios

## 🆘 Support

### **Common Issues**
1. **API Key Errors**: Verify environment variables are set correctly
2. **Scraping Failures**: Check website accessibility and rate limiting
3. **Email Delivery Issues**: Verify Resend.com configuration
4. **Memory Issues**: Adjust token limits and batch sizes

### **Getting Help**
- Check the troubleshooting guide
- Review system logs for error details
- Test individual components
- Contact the development team

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **CrewAI**: For the powerful agent orchestration framework
- **OpenAI**: For advanced AI capabilities
- **Resend.com**: For reliable email delivery
- **Open Source Community**: For the excellent tools and libraries

---

**Tendazilla** - Transforming tender management with AI-powered automation 🚀
