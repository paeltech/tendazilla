import json
import re
from typing import Dict, Any, List
from datetime import datetime
import logging
import os
from pathlib import Path
import openai
from config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIProposalWriter:
    """AI-powered proposal generation system"""
    
    def __init__(self):
        self.openai_client = None
        if config.PROPOSAL_AI_ENABLED and config.OPENAI_API_KEY:
            try:
                openai.api_key = config.OPENAI_API_KEY
                self.openai_client = openai
                logger.info("OpenAI client initialized for AI-powered proposal generation")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {str(e)}")
                self.openai_client = None
    
    def generate_proposal(self, tender: Dict[str, Any], company_profile: Dict[str, Any]) -> str:
        """
        Generates a full proposal in markdown format based on the tender and company profile.
        
        Args:
            tender (Dict[str, Any]): Tender opportunity details
            company_profile (Dict[str, Any]): Company details including past experience and offerings
            
        Returns:
            str: Markdown-formatted proposal
        """
        try:
            logger.info(f"Generating proposal for tender: {tender.get('title', 'Unknown')}")
            
            # Try AI-powered generation first if available
            if self.openai_client and config.PROPOSAL_AI_ENABLED:
                try:
                    ai_proposal = self._generate_ai_proposal(tender, company_profile)
                    if ai_proposal:
                        logger.info("AI-powered proposal generated successfully")
                        return ai_proposal
                except Exception as e:
                    logger.warning(f"AI proposal generation failed: {str(e)}, falling back to template-based generation")
            
            # Fall back to template-based generation
            logger.info("Using template-based proposal generation")
            return self._generate_template_proposal(tender, company_profile)
            
        except Exception as e:
            logger.error(f"Error generating proposal: {str(e)}")
            return f"# Error Generating Proposal\n\nAn error occurred while generating the proposal: {str(e)}"
    
    def _generate_ai_proposal(self, tender: Dict[str, Any], company_profile: Dict[str, Any]) -> str:
        """Generate proposal using OpenAI"""
        try:
            # Create comprehensive prompt for AI
            prompt = self._create_ai_proposal_prompt(tender, company_profile)
            
            # Call OpenAI API
            response = self.openai_client.ChatCompletion.create(
                model=config.PROPOSAL_AI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert proposal writer specializing in technology tenders. Write a comprehensive, professional proposal in markdown format that addresses all tender requirements and showcases company capabilities."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=config.PROPOSAL_MAX_TOKENS,
                temperature=0.7
            )
            
            # Extract and clean the proposal
            ai_proposal = response.choices[0].message.content
            
            # Ensure it starts with a title
            if not ai_proposal.startswith('#'):
                ai_proposal = f"# Proposal: {tender.get('title', 'Tender Opportunity')}\n\n{ai_proposal}"
            
            # Add metadata
            ai_proposal = self._add_proposal_metadata(ai_proposal, tender, company_profile)
            
            return ai_proposal
            
        except Exception as e:
            logger.error(f"Error in AI proposal generation: {str(e)}")
            return None
    
    def _create_ai_proposal_prompt(self, tender: Dict[str, Any], company_profile: Dict[str, Any]) -> str:
        """Create comprehensive prompt for AI proposal generation"""
        prompt = f"""
        Write a comprehensive, professional proposal for this tender opportunity. The proposal should be in markdown format and include all standard sections.

        TENDER DETAILS:
        Title: {tender.get('title', 'N/A')}
        Description: {tender.get('description', 'N/A')}
        Budget: {tender.get('budget', 'N/A')}
        Location: {tender.get('location', 'N/A')}
        Industry: {tender.get('industry', 'N/A')}
        Requirements: {', '.join(tender.get('requirements', []))}
        Deadline: {tender.get('deadline', 'N/A')}

        COMPANY PROFILE:
        Company: {company_profile.get('company_name', 'N/A')}
        Industry Focus: {', '.join(company_profile.get('industry_focus', []))}
        Core Services: {', '.join(company_profile.get('core_services', []))}
        Certifications: {', '.join(company_profile.get('certifications', []))}
        Technologies: {', '.join(company_profile.get('relevant_technologies', []))}
        Experience: {company_profile.get('years_in_operation', 'N/A')} years
        Past Projects: {len(company_profile.get('past_projects', []))} relevant projects
        Team Size: {sum(company_profile.get('team_expertise', {}).values())} professionals
        Preferred Budget Range: ${company_profile.get('preferred_project_size', {}).get('min_budget', 'N/A')} - ${company_profile.get('preferred_project_size', {}).get('max_budget', 'N/A')}

        PROPOSAL REQUIREMENTS:
        1. Use markdown formatting throughout
        2. Include all standard sections: Executive Summary, Company Profile, Understanding of Requirements, Proposed Solution, Technical Approach, Project Timeline, Team Structure, Relevant Experience, Risk Management, Quality Assurance, Pricing, Terms and Conditions
        3. Make it specific to the tender requirements
        4. Highlight company strengths and relevant experience
        5. Include realistic project timeline and team structure
        6. Provide competitive but realistic pricing
        7. Address all tender requirements explicitly
        8. Use professional, persuasive language
        9. Include specific examples from past projects where relevant
        10. Ensure the proposal demonstrates clear understanding of the tender requirements

        The proposal should be comprehensive, professional, and tailored to win this specific tender opportunity.
        """
        return prompt
    
    def _generate_template_proposal(self, tender: Dict[str, Any], company_profile: Dict[str, Any]) -> str:
        """Generate proposal using template-based approach"""
        try:
            # Generate proposal sections
            proposal_sections = []
            
            # 1. Executive Summary
            executive_summary = self._generate_executive_summary(tender, company_profile)
            proposal_sections.append(("## Executive Summary", executive_summary))
            
            # 2. Company Profile
            company_overview = self._generate_company_overview(company_profile)
            proposal_sections.append(("## Company Profile", company_overview))
            
            # 3. Understanding of Requirements
            requirements_analysis = self._generate_requirements_analysis(tender)
            proposal_sections.append(("## Understanding of Requirements", requirements_analysis))
            
            # 4. Proposed Solution
            proposed_solution = self._generate_proposed_solution(tender, company_profile)
            proposal_sections.append(("## Proposed Solution", proposed_solution))
            
            # 5. Technical Approach
            technical_approach = self._generate_technical_approach(tender, company_profile)
            proposal_sections.append(("## Technical Approach", technical_approach))
            
            # 6. Project Timeline
            project_timeline = self._generate_project_timeline(tender, company_profile)
            proposal_sections.append(("## Project Timeline", project_timeline))
            
            # 7. Team Structure
            team_structure = self._generate_team_structure(company_profile)
            proposal_sections.append(("## Team Structure", team_structure))
            
            # 8. Relevant Experience
            relevant_experience = self._generate_relevant_experience(tender, company_profile)
            proposal_sections.append(("## Relevant Experience", relevant_experience))
            
            # 9. Risk Management
            risk_management = self._generate_risk_management()
            proposal_sections.append(("## Risk Management", risk_management))
            
            # 10. Quality Assurance
            quality_assurance = self._generate_quality_assurance()
            proposal_sections.append(("## Quality Assurance", quality_assurance))
            
            # 11. Pricing
            pricing = self._generate_pricing(tender, company_profile)
            proposal_sections.append(("## Pricing", pricing))
            
            # 12. Terms and Conditions
            terms_conditions = self._generate_terms_conditions()
            proposal_sections.append(("## Terms and Conditions", terms_conditions))
            
            # Combine all sections
            proposal = f"# Proposal: {tender.get('title', 'Tender Opportunity')}\n\n"
            proposal += f"**Tender Reference:** {tender.get('source_url', 'N/A')}\n"
            proposal += f"**Submission Date:** {datetime.now().strftime('%B %d, %Y')}\n\n"
            
            for section_title, section_content in proposal_sections:
                proposal += f"{section_title}\n{section_content}\n\n"
            
            # Add footer
            proposal += f"---\n\n"
            proposal += f"*This proposal was generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}*\n"
            proposal += f"*For questions or clarifications, please contact {company_profile.get('company_email', 'our team')}*\n"
            
            # Add metadata
            proposal = self._add_proposal_metadata(proposal, tender, company_profile)
            
            logger.info(f"Template-based proposal generated successfully for {tender.get('title', 'Unknown')}")
            return proposal
            
        except Exception as e:
            logger.error(f"Error in template proposal generation: {str(e)}")
            return f"# Error Generating Proposal\n\nAn error occurred while generating the proposal: {str(e)}"
    
    def _add_proposal_metadata(self, proposal: str, tender: Dict[str, Any], company_profile: Dict[str, Any]) -> str:
        """Add metadata and generation info to proposal"""
        metadata = f"\n\n---\n\n"
        metadata += f"**Proposal Metadata:**\n"
        metadata += f"- Generated: {datetime.now().isoformat()}\n"
        metadata += f"- Tender ID: {tender.get('source_url', 'N/A')}\n"
        metadata += f"- Company: {company_profile.get('company_name', 'N/A')}\n"
        metadata += f"- Generation Method: {'AI-Powered' if self.openai_client and config.PROPOSAL_AI_ENABLED else 'Template-Based'}\n"
        metadata += f"- AI Model: {config.PROPOSAL_AI_MODEL if self.openai_client else 'N/A'}\n"
        
        return proposal + metadata
    
    def _generate_executive_summary(self, tender: Dict[str, Any], company_profile: Dict[str, Any]) -> str:
        """Generate executive summary section"""
        company_name = company_profile.get('company_name', 'Our Company')
        
        summary = f"{company_name} is pleased to submit this comprehensive proposal for the "
        summary += f"**{tender.get('title', 'tender opportunity')}**. "
        
        if tender.get('budget'):
            summary += f"This project represents a {tender.get('budget')} investment in "
        else:
            summary += f"This project represents a significant investment in "
        
        summary += f"{tender.get('industry', 'technology infrastructure')} that aligns perfectly with our "
        summary += f"core competencies in {', '.join(company_profile.get('core_services', ['technology solutions'])[:3])}. "
        
        summary += f"\n\nWith {company_profile.get('years_in_operation', 7)} years of experience and "
        summary += f"a proven track record of delivering similar projects, we are confident in our ability "
        summary += f"to exceed expectations and deliver exceptional value. "
        
        summary += f"Our approach combines technical expertise, industry best practices, and "
        summary += f"a deep understanding of the challenges and opportunities in this sector."
        
        return summary
    
    def _generate_company_overview(self, company_profile: Dict[str, Any]) -> str:
        """Generate company profile section"""
        company_name = company_profile.get('company_name', 'Our Company')
        headquarters = company_profile.get('headquarters', 'our headquarters')
        years = company_profile.get('years_in_operation', 7)
        
        overview = f"{company_name} is a leading technology solutions provider headquartered in {headquarters}. "
        overview += f"With {years} years of operation, we have established ourselves as a trusted partner "
        overview += f"for organizations seeking innovative, reliable, and scalable technology solutions.\n\n"
        
        # Core Services
        core_services = company_profile.get('core_services', [])
        if core_services:
            overview += "**Our Core Services Include:**\n"
            for service in core_services:
                overview += f"- {service}\n"
            overview += "\n"
        
        # Certifications
        certifications = company_profile.get('certifications', [])
        if certifications:
            overview += "**Certifications & Partnerships:**\n"
            for cert in certifications:
                overview += f"- {cert}\n"
            overview += "\n"
        
        # Team Expertise
        team_expertise = company_profile.get('team_expertise', {})
        if team_expertise:
            overview += "**Our Team:**\n"
            total_team = sum(team_expertise.values())
            overview += f"- Total team members: {total_team}\n"
            for role, count in team_expertise.items():
                overview += f"- {role.replace('_', ' ').title()}: {count}\n"
            overview += "\n"
        
        # Notable Clients
        notable_clients = company_profile.get('notable_clients', [])
        if notable_clients:
            overview += "**Notable Clients:**\n"
            for client in notable_clients[:5]:  # Limit to top 5
                overview += f"- {client}\n"
        
        return overview
    
    def _generate_requirements_analysis(self, tender: Dict[str, Any]) -> str:
        """Generate requirements analysis section"""
        analysis = "Based on our thorough review of the tender documentation, we have identified "
        analysis += "the following key requirements and objectives:\n\n"
        
        # Extract requirements from tender
        requirements = tender.get('requirements', [])
        if requirements:
            analysis += "**Key Requirements:**\n"
            for req in requirements:
                analysis += f"- {req}\n"
            analysis += "\n"
        
        # Analyze description for implicit requirements
        description = tender.get('description', '')
        if description:
            analysis += "**Project Objectives:**\n"
            analysis += f"Based on the project description, the primary objectives include:\n"
            analysis += f"- {description[:200]}...\n\n"
        
        # Budget analysis
        budget = tender.get('budget', '')
        if budget:
            analysis += f"**Budget Considerations:**\n"
            analysis += f"The project budget of {budget} indicates the scope and complexity "
            analysis += f"of this engagement, requiring careful resource allocation and "
            analysis += f"efficient project management to ensure optimal value delivery.\n\n"
        
        # Timeline analysis
        deadline = tender.get('deadline', '')
        if deadline:
            analysis += f"**Timeline Requirements:**\n"
            analysis += f"With a deadline of {deadline}, we understand the urgency "
            analysis += f"and will ensure our proposed solution can be delivered within "
            analysis += f"the required timeframe while maintaining quality standards."
        
        return analysis
    
    def _generate_proposed_solution(self, tender: Dict[str, Any], company_profile: Dict[str, Any]) -> str:
        """Generate proposed solution section"""
        solution = "Our proposed solution is designed to address all identified requirements "
        solution += "while leveraging our proven expertise and best practices. "
        solution += "We will deliver a comprehensive, scalable, and future-ready solution "
        solution += "that exceeds expectations.\n\n"
        
        # Core approach
        solution += "**Our Approach:**\n"
        solution += "1. **Discovery & Analysis:** Comprehensive requirements gathering and stakeholder engagement\n"
        solution += "2. **Design & Architecture:** Robust, scalable solution design with security by design\n"
        solution += "3. **Development & Implementation:** Agile development with continuous integration and testing\n"
        solution += "4. **Testing & Quality Assurance:** Rigorous testing protocols and quality gates\n"
        solution += "5. **Deployment & Training:** Smooth deployment with comprehensive user training\n"
        solution += "6. **Support & Maintenance:** Ongoing support and continuous improvement\n\n"
        
        # Technology stack
        relevant_technologies = company_profile.get('relevant_technologies', [])
        if relevant_technologies:
            solution += "**Proposed Technology Stack:**\n"
            for tech in relevant_technologies[:8]:  # Limit to top 8
                solution += f"- {tech}\n"
            solution += "\n"
        
        # Key benefits
        solution += "**Key Benefits of Our Solution:**\n"
        solution += "- **Scalability:** Built to grow with your business needs\n"
        solution += "- **Security:** Enterprise-grade security and compliance\n"
        solution += "- **Reliability:** Proven technologies and robust architecture\n"
        solution += "- **Cost-Effectiveness:** Optimized resource utilization and long-term value\n"
        solution += "- **Innovation:** Latest technologies and industry best practices"
        
        return solution
    
    def _generate_technical_approach(self, tender: Dict[str, Any], company_profile: Dict[str, Any]) -> str:
        """Generate technical approach section"""
        approach = "Our technical approach is founded on industry best practices, "
        approach += "proven methodologies, and our extensive experience in similar projects. "
        approach += "We will employ a systematic, phased approach to ensure successful delivery.\n\n"
        
        # Methodology
        approach += "**Development Methodology:**\n"
        approach += "We will utilize an **Agile-Scrum** methodology with 2-week sprint cycles, "
        approach += "daily stand-ups, and regular stakeholder demos. This approach ensures:\n"
        approach += "- Continuous stakeholder engagement and feedback\n"
        approach += "- Early identification and resolution of issues\n"
        approach += "- Flexible adaptation to changing requirements\n"
        approach += "- Regular delivery of working software\n\n"
        
        # Technical phases
        approach += "**Technical Implementation Phases:**\n"
        approach += "1. **Phase 1: Foundation & Infrastructure** (Weeks 1-4)\n"
        approach += "   - Environment setup and configuration\n"
        approach += "   - Core infrastructure deployment\n"
        approach += "   - Security framework implementation\n\n"
        
        approach += "2. **Phase 2: Core Development** (Weeks 5-12)\n"
        approach += "   - Feature development and integration\n"
        approach += "   - API development and testing\n"
        approach += "   - User interface development\n\n"
        
        approach += "3. **Phase 3: Integration & Testing** (Weeks 13-16)\n"
        approach += "   - System integration\n"
        approach += "   - Comprehensive testing\n"
        approach += "   - Performance optimization\n\n"
        
        approach += "4. **Phase 4: Deployment & Training** (Weeks 17-20)\n"
        approach += "   - Production deployment\n"
        approach += "   - User training and documentation\n"
        approach += "   - Go-live support\n\n"
        
        # Quality assurance
        approach += "**Quality Assurance:**\n"
        approach += "- Automated testing with CI/CD pipelines\n"
        approach += "- Code review and pair programming\n"
        approach += "- Security testing and vulnerability assessment\n"
        approach += "- Performance testing and optimization\n"
        approach += "- User acceptance testing and feedback integration"
        
        return approach
    
    def _generate_project_timeline(self, tender: Dict[str, Any], company_profile: Dict[str, Any]) -> str:
        """Generate project timeline section"""
        timeline = "Our proposed project timeline is designed to deliver maximum value "
        timeline += "while ensuring quality and meeting all requirements. "
        timeline += "We will maintain flexibility to accommodate any adjustments needed.\n\n"
        
        # Overall timeline
        timeline += "**Project Duration:** 20 weeks (5 months)\n\n"
        
        # Detailed timeline
        timeline += "**Detailed Timeline:**\n\n"
        
        timeline += "**Month 1: Foundation**\n"
        timeline += "- Week 1-2: Project kickoff and requirements finalization\n"
        timeline += "- Week 3-4: Infrastructure setup and environment configuration\n\n"
        
        timeline += "**Month 2-3: Development**\n"
        timeline += "- Week 5-8: Core feature development (Sprint 1-2)\n"
        timeline += "- Week 9-12: Advanced features and integration (Sprint 3-4)\n\n"
        
        timeline += "**Month 4: Testing & Integration**\n"
        timeline += "- Week 13-14: System integration and testing\n"
        timeline += "- Week 15-16: Performance optimization and final testing\n\n"
        
        timeline += "**Month 5: Deployment**\n"
        timeline += "- Week 17-18: Production deployment and configuration\n"
        timeline += "- Week 19-20: User training, documentation, and go-live support\n\n"
        
        # Milestones
        timeline += "**Key Milestones:**\n"
        timeline += "- **Week 4:** Infrastructure and foundation complete\n"
        timeline += "- **Week 8:** Core features demonstration\n"
        timeline += "- **Week 12:** Full system demonstration\n"
        timeline += "- **Week 16:** Testing complete and system ready\n"
        timeline += "- **Week 20:** Project completion and handover\n\n"
        
        # Risk mitigation
        timeline += "**Timeline Risk Mitigation:**\n"
        timeline += "- Buffer time built into each phase\n"
        timeline += "- Parallel development tracks where possible\n"
        timeline += "- Regular progress monitoring and adjustment\n"
        timeline += "- Contingency plans for critical path items"
        
        return timeline
    
    def _generate_team_structure(self, company_profile: Dict[str, Any]) -> str:
        """Generate team structure section"""
        team = "Our project team is carefully selected based on the specific requirements "
        team += "and complexity of this engagement. Each team member brings relevant expertise "
        team += "and proven track record in similar projects.\n\n"
        
        # Project team composition
        team += "**Project Team Composition:**\n\n"
        
        team += "**Project Manager (1)**\n"
        team += "- Overall project coordination and stakeholder management\n"
        team += "- Risk management and issue resolution\n"
        team += "- Progress reporting and quality assurance\n\n"
        
        team += "**Technical Lead (1)**\n"
        team += "- Technical architecture and design decisions\n"
        team += "- Code review and quality standards\n"
        team += "- Technical problem resolution\n\n"
        
        team += "**Senior Developers (3-4)**\n"
        team += "- Core feature development and implementation\n"
        team += "- API development and integration\n"
        team += "- Unit testing and code quality\n\n"
        
        team += "**DevOps Engineer (1)**\n"
        team += "- Infrastructure and deployment automation\n"
        team += "- CI/CD pipeline management\n"
        team += "- Environment configuration and monitoring\n\n"
        
        team += "**QA Engineer (1-2)**\n"
        team += "- Test planning and execution\n"
        team += "- Automated testing implementation\n"
        team += "- Quality assurance and validation\n\n"
        
        team += "**UI/UX Designer (1)**\n"
        team += "- User interface design and user experience\n"
        team += "- Design system and component library\n"
        team += "- User feedback integration\n\n"
        
        # Team expertise
        team_expertise = company_profile.get('team_expertise', {})
        if team_expertise:
            team += "**Team Expertise Summary:**\n"
            for role, count in team_expertise.items():
                team += f"- {role.replace('_', ' ').title()}: {count} professionals\n"
        
        return team
    
    def _generate_relevant_experience(self, tender: Dict[str, Any], company_profile: Dict[str, Any]) -> str:
        """Generate relevant experience section"""
        experience = "Our company has successfully delivered numerous projects similar to "
        experience += f"the **{tender.get('title', 'current opportunity')}**. "
        experience += "Below are highlights of our most relevant experience that demonstrate "
        experience += "our capability to deliver this project successfully.\n\n"
        
        # Past projects
        past_projects = company_profile.get('past_projects', [])
        if past_projects:
            experience += "**Relevant Past Projects:**\n\n"
            
            for i, project in enumerate(past_projects[:3], 1):  # Top 3 projects
                experience += f"**Project {i}: {project.get('name', 'Project Name')}**\n"
                experience += f"- **Client:** {project.get('client', 'Confidential')}\n"
                experience += f"- **Description:** {project.get('description', 'Project description')}\n"
                experience += f"- **Budget:** {project.get('budget', 'Budget not specified')}\n"
                experience += f"- **Duration:** {project.get('duration', 'Duration not specified')}\n"
                experience += f"- **Outcome:** {project.get('outcome', 'Successful delivery')}\n\n"
        
        # Success metrics
        tender_history = company_profile.get('tender_response_history', {})
        if tender_history:
            experience += "**Success Metrics:**\n"
            experience += f"- Total tender responses: {tender_history.get('total_responses', 0)}\n"
            experience += f"- Successful wins: {tender_history.get('wins', 0)}\n"
            experience += f"- Win rate: {tender_history.get('win_rate', 'N/A')}\n\n"
        
        # Client testimonials
        experience += "**Client Satisfaction:**\n"
        experience += "Our clients consistently rate our services highly for:\n"
        experience += "- Technical expertise and innovation\n"
        experience += "- Project delivery on time and within budget\n"
        experience += "- Quality of deliverables and support\n"
        experience += "- Long-term partnership and value creation"
        
        return experience
    
    def _generate_risk_management(self) -> str:
        """Generate risk management section"""
        risk = "We have identified potential risks and developed comprehensive mitigation strategies "
        risk += "to ensure project success. Our proactive approach to risk management "
        risk += "minimizes potential disruptions and ensures smooth project delivery.\n\n"
        
        risk += "**Identified Risks and Mitigation Strategies:**\n\n"
        
        risk += "**Technical Risks:**\n"
        risk += "- **Risk:** Technology compatibility issues\n"
        risk += "- **Mitigation:** Comprehensive technical assessment and proof-of-concept development\n\n"
        
        risk += "**Timeline Risks:**\n"
        risk += "- **Risk:** Scope creep and timeline delays\n"
        risk += "- **Mitigation:** Agile methodology with regular stakeholder reviews and change control\n\n"
        
        risk += "**Resource Risks:**\n"
        risk += "- **Risk:** Key team member unavailability\n"
        risk += "- **Mitigation:** Cross-training and backup resource allocation\n\n"
        
        risk += "**Quality Risks:**\n"
        risk += "- **Risk:** Quality standards not met\n"
        risk += "- **Mitigation:** Continuous testing, code reviews, and quality gates\n\n"
        
        risk += "**Communication Risks:**\n"
        risk += "- **Risk:** Miscommunication and stakeholder misalignment\n"
        risk += "- **Mitigation:** Regular status meetings, clear documentation, and stakeholder engagement"
        
        return risk
    
    def _generate_quality_assurance(self) -> str:
        """Generate quality assurance section"""
        quality = "Quality is embedded in every aspect of our project delivery process. "
        quality += "We maintain rigorous quality standards through systematic processes, "
        quality += "continuous monitoring, and regular validation.\n\n"
        
        quality += "**Quality Assurance Framework:**\n\n"
        
        quality += "**Development Standards:**\n"
        quality += "- Coding standards and best practices\n"
        quality += "- Code review and pair programming\n"
        quality += "- Automated testing and continuous integration\n"
        quality += "- Documentation standards and maintenance\n\n"
        
        quality += "**Testing Strategy:**\n"
        quality += "- Unit testing with minimum 90% code coverage\n"
        quality += "- Integration testing for all system components\n"
        quality += "- Performance testing and load testing\n"
        quality += "- Security testing and vulnerability assessment\n"
        quality += "- User acceptance testing and feedback integration\n\n"
        
        quality += "**Quality Gates:**\n"
        quality += "- Requirements validation and sign-off\n"
        quality += "- Design review and architecture approval\n"
        quality += "- Code quality and security review\n"
        quality += "- Testing completion and validation\n"
        quality += "- Final delivery and acceptance\n\n"
        
        quality += "**Continuous Improvement:**\n"
        quality += "- Regular process reviews and optimization\n"
        quality += "- Lessons learned documentation and application\n"
        quality += "- Stakeholder feedback integration\n"
        quality += "- Industry best practice adoption"
        
        return quality
    
    def _generate_pricing(self, tender: Dict[str, Any], company_profile: Dict[str, Any]) -> str:
        """Generate pricing section"""
        pricing = "Our pricing structure is designed to provide exceptional value while "
        pricing += "ensuring project success and long-term partnership. "
        pricing += "We offer transparent, competitive pricing with no hidden costs.\n\n"
        
        # Budget analysis
        tender_budget = tender.get('budget', '')
        if tender_budget:
            pricing += f"**Project Budget:** {tender_budget}\n\n"
        
        # Pricing structure
        pricing += "**Pricing Structure:**\n"
        pricing += "We propose a **fixed-price model** with milestone-based payments "
        pricing += "to provide budget certainty and align payments with project progress.\n\n"
        
        # Payment schedule
        pricing += "**Payment Schedule:**\n"
        pricing += "- **30%** upon project initiation and infrastructure setup\n"
        pricing += "- **30%** upon completion of core development phase\n"
        pricing += "- **25%** upon successful testing and integration\n"
        pricing += "- **15%** upon final delivery and acceptance\n\n"
        
        # Value proposition
        pricing += "**Value Proposition:**\n"
        pricing += "- **Cost Efficiency:** Optimized resource utilization and streamlined processes\n"
        pricing += "- **Risk Mitigation:** Fixed pricing with no cost overruns\n"
        pricing += "- **Quality Assurance:** Built-in quality processes and testing\n"
        pricing += "- **Long-term Value:** Scalable solution with minimal maintenance costs\n"
        pricing += "- **Expertise:** Access to specialized skills and industry experience\n\n"
        
        # Additional services
        pricing += "**Additional Services (Optional):**\n"
        pricing += "- Extended support and maintenance\n"
        pricing += "- Additional training and documentation\n"
        pricing += "- Performance optimization and scaling\n"
        pricing += "- Security audits and compliance support"
        
        return pricing
    
    def _generate_terms_conditions(self) -> str:
        """Generate terms and conditions section"""
        terms = "This proposal is valid for 30 days from the date of submission. "
        terms += "All terms and conditions are subject to mutual agreement and final contract negotiation.\n\n"
        
        terms += "**Key Terms and Conditions:**\n\n"
        
        terms += "**Project Delivery:**\n"
        terms += "- Project completion within agreed timeline\n"
        terms += "- Quality standards as specified in project requirements\n"
        terms += "- Regular progress reporting and stakeholder communication\n\n"
        
        terms += "**Intellectual Property:**\n"
        terms += "- Client retains ownership of business logic and requirements\n"
        terms += "- Company retains rights to reusable components and frameworks\n"
        terms += "- Mutual agreement on custom developments\n\n"
        
        terms += "**Confidentiality:**\n"
        terms += "- Strict confidentiality of all project information\n"
        terms += "- Non-disclosure agreements as required\n"
        terms += "- Secure handling of sensitive data\n\n"
        
        terms += "**Support and Warranty:**\n"
        terms += "- 90-day warranty period post-delivery\n"
        terms += "- Bug fixes and critical issue resolution\n"
        terms += "- Optional extended support agreements\n\n"
        
        terms += "**Change Management:**\n"
        terms += "- Formal change request process\n"
        terms += "- Impact assessment and approval workflow\n"
        terms += "- Transparent pricing for scope changes"
        
        return terms

# Global proposal writer instance
proposal_writer = AIProposalWriter()

def generate_proposal(tender: Dict[str, Any], company_profile: Dict[str, Any]) -> str:
    """Main proposal generation function for external use"""
    return proposal_writer.generate_proposal(tender, company_profile)