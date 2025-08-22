import json
import re
from typing import Dict, Any, List, Tuple
from datetime import datetime
import logging
import openai
from config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HybridTenderScorer:
    """Hybrid tender scoring system combining rule-based and AI-powered analysis"""
    
    def __init__(self):
        self.openai_client = None
        if config.SCORING_AI_ENABLED and config.OPENAI_API_KEY:
            try:
                openai.api_key = config.OPENAI_API_KEY
                self.openai_client = openai
                logger.info("OpenAI client initialized for AI-powered scoring")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {str(e)}")
                self.openai_client = None
        
        # Scoring weights for rule-based scoring
        self.scoring_weights = {
            'industry_match': 0.20,
            'location_match': 0.15,
            'budget_match': 0.20,
            'technical_match': 0.20,
            'experience_match': 0.15,
            'certification_match': 0.10
        }
    
    def score_tender(self, tender: Dict[str, Any], company_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates a tender opportunity against company profile using hybrid approach.
        Returns a confidence score and reasoning.
        
        Args:
            tender (Dict[str, Any]): A JSON object containing tender metadata
            company_profile (Dict[str, Any]): JSON object describing company strengths, past experience, and certifications
            
        Returns:
            Dict[str, Any]: Scoring result with score and justification
        """
        try:
            logger.info(f"Scoring tender: {tender.get('title', 'Unknown')}")
            
            # Rule-based scoring
            rule_based_result = self._rule_based_scoring(tender, company_profile)
            
            # AI-powered scoring (if available)
            ai_result = None
            if self.openai_client and config.SCORING_AI_ENABLED:
                try:
                    ai_result = self._ai_powered_scoring(tender, company_profile)
                except Exception as e:
                    logger.warning(f"AI scoring failed: {str(e)}")
            
            # Combine results
            final_result = self._combine_scoring_results(rule_based_result, ai_result)
            
            logger.info(f"Tender scored: {final_result['score']}/100 - {final_result['justification'][:100]}...")
            return final_result
            
        except Exception as e:
            logger.error(f"Error scoring tender: {str(e)}")
            return {
                "score": 0,
                "justification": f"Error during scoring: {str(e)}",
                "detailed_scores": {},
                "scored_at": datetime.now().isoformat(),
                "scoring_method": "error"
            }
    
    def _rule_based_scoring(self, tender: Dict[str, Any], company_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Perform rule-based scoring"""
        try:
            # Initialize scoring components
            scores = {}
            justifications = []
            
            # 1. Industry Match (0-20 points)
            industry_score, industry_justification = self._score_industry_match(tender, company_profile)
            scores['industry_match'] = industry_score
            justifications.append(industry_justification)
            
            # 2. Location Match (0-15 points)
            location_score, location_justification = self._score_location_match(tender, company_profile)
            scores['location_match'] = location_score
            justifications.append(location_justification)
            
            # 3. Budget Match (0-20 points)
            budget_score, budget_justification = self._score_budget_match(tender, company_profile)
            scores['budget_match'] = budget_score
            justifications.append(budget_justification)
            
            # 4. Technical Requirements Match (0-20 points)
            technical_score, technical_justification = self._score_technical_match(tender, company_profile)
            scores['technical_match'] = technical_score
            justifications.append(technical_justification)
            
            # 5. Experience Match (0-15 points)
            experience_score, experience_justification = self._score_experience_match(tender, company_profile)
            scores['experience_match'] = experience_score
            justifications.append(experience_justification)
            
            # 6. Certification Match (0-10 points)
            certification_score, certification_justification = self._score_certification_match(tender, company_profile)
            scores['certification_match'] = certification_score
            justifications.append(certification_justification)
            
            # Calculate weighted total score
            total_score = sum(scores[key] * self.scoring_weights[key] for key in scores)
            total_score = int(total_score)
            
            # Generate overall justification
            overall_justification = self._generate_overall_justification(scores, justifications, total_score)
            
            return {
                "score": total_score,
                "justification": overall_justification,
                "detailed_scores": scores,
                "scored_at": datetime.now().isoformat(),
                "scoring_method": "rule_based"
            }
            
        except Exception as e:
            logger.error(f"Error in rule-based scoring: {str(e)}")
            return {
                "score": 0,
                "justification": f"Rule-based scoring error: {str(e)}",
                "detailed_scores": {},
                "scored_at": datetime.now().isoformat(),
                "scoring_method": "rule_based_error"
            }
    
    def _ai_powered_scoring(self, tender: Dict[str, Any], company_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Perform AI-powered scoring using OpenAI"""
        try:
            # Prepare prompt for AI analysis
            prompt = self._create_ai_scoring_prompt(tender, company_profile)
            
            # Call OpenAI API
            response = self.openai_client.ChatCompletion.create(
                model=config.SCORING_AI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert tender evaluation analyst. Analyze the tender opportunity against the company profile and provide a score from 0-100 with detailed reasoning."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            # Parse AI response
            ai_response = response.choices[0].message.content
            
            # Extract score and reasoning
            score, reasoning = self._parse_ai_response(ai_response)
            
            return {
                "score": score,
                "justification": reasoning,
                "detailed_scores": {"ai_analysis": score},
                "scored_at": datetime.now().isoformat(),
                "scoring_method": "ai_powered"
            }
            
        except Exception as e:
            logger.error(f"Error in AI-powered scoring: {str(e)}")
            return None
    
    def _create_ai_scoring_prompt(self, tender: Dict[str, Any], company_profile: Dict[str, Any]) -> str:
        """Create prompt for AI scoring"""
        prompt = f"""
        Please evaluate this tender opportunity against the company profile and provide a score from 0-100.

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
        Preferred Budget Range: ${company_profile.get('preferred_project_size', {}).get('min_budget', 'N/A')} - ${company_profile.get('preferred_project_size', {}).get('max_budget', 'N/A')}

        Please provide:
        1. A score from 0-100
        2. Detailed reasoning for the score
        3. Key strengths and weaknesses
        4. Recommendations for improvement

        Format your response as:
        Score: [number]
        Reasoning: [detailed explanation]
        """
        return prompt
    
    def _parse_ai_response(self, ai_response: str) -> Tuple[int, str]:
        """Parse AI response to extract score and reasoning"""
        try:
            # Try to extract score
            score_match = re.search(r'Score:\s*(\d+)', ai_response, re.I)
            score = int(score_match.group(1)) if score_match else 50
            
            # Extract reasoning
            reasoning_match = re.search(r'Reasoning:\s*(.+)', ai_response, re.I | re.DOTALL)
            reasoning = reasoning_match.group(1).strip() if reasoning_match else ai_response
            
            return score, reasoning
            
        except Exception as e:
            logger.warning(f"Failed to parse AI response: {str(e)}")
            return 50, ai_response
    
    def _combine_scoring_results(self, rule_result: Dict[str, Any], ai_result: Dict[str, Any] = None) -> Dict[str, Any]:
        """Combine rule-based and AI scoring results"""
        if not ai_result:
            return rule_result
        
        try:
            # Calculate combined score (70% rule-based, 30% AI)
            combined_score = int(rule_result['score'] * 0.7 + ai_result['score'] * 0.3)
            
            # Combine justifications
            combined_justification = f"Rule-based score: {rule_result['score']}/100. AI analysis: {ai_result['score']}/100. "
            combined_justification += f"Combined score: {combined_score}/100. "
            combined_justification += f"Rule-based reasoning: {rule_result['justification']} "
            combined_justification += f"AI insights: {ai_result['justification']}"
            
            # Combine detailed scores
            combined_scores = rule_result['detailed_scores'].copy()
            combined_scores.update(ai_result['detailed_scores'])
            
            return {
                "score": combined_score,
                "justification": combined_justification,
                "detailed_scores": combined_scores,
                "scored_at": datetime.now().isoformat(),
                "scoring_method": "hybrid",
                "rule_based_score": rule_result['score'],
                "ai_score": ai_result['score']
            }
            
        except Exception as e:
            logger.error(f"Error combining scoring results: {str(e)}")
            return rule_result
    
    def _score_industry_match(self, tender: Dict[str, Any], company_profile: Dict[str, Any]) -> Tuple[int, str]:
        """Score industry alignment (0-20 points)"""
        tender_industry = tender.get('industry', '').lower()
        company_industries = [ind.lower() for ind in company_profile.get('industry_focus', [])]
        
        if not tender_industry:
            return 10, "Industry not specified in tender - assigned neutral score"
        
        # Check for exact matches
        for company_ind in company_industries:
            if company_ind in tender_industry or tender_industry in company_ind:
                return 20, f"Perfect industry match: {tender_industry} aligns with {company_ind}"
        
        # Check for partial matches
        for company_ind in company_industries:
            if any(word in tender_industry for word in company_ind.split()) or \
               any(word in company_ind for word in tender_industry.split()):
                return 15, f"Strong industry alignment: {tender_industry} relates to {company_ind}"
        
        # Check for technology-related matches
        if any(tech in tender_industry.lower() for tech in ['it', 'technology', 'software', 'digital', 'cloud']):
            return 12, f"Technology sector match: {tender_industry} aligns with IT focus"
        
        return 5, f"Limited industry alignment: {tender_industry} vs company focus areas"
    
    def _score_location_match(self, tender: Dict[str, Any], company_profile: Dict[str, Any]) -> Tuple[int, str]:
        """Score geographical location match (0-15 points)"""
        tender_location = tender.get('location', '').lower()
        company_locations = [loc.lower() for loc in company_profile.get('geographical_focus', [])]
        company_headquarters = company_profile.get('headquarters', '').lower()
        other_locations = [loc.lower() for loc in company_profile.get('other_locations', [])]
        
        if not tender_location:
            return 7, "Location not specified - assigned neutral score"
        
        # Check for exact location matches
        if tender_location in company_locations or tender_location in company_headquarters:
            return 15, f"Perfect location match: {tender_location} is in company's focus area"
        
        # Check for country/region matches
        for company_loc in company_locations + [company_headquarters] + other_locations:
            if any(word in tender_location for word in company_loc.split()) or \
               any(word in company_loc for word in tender_location.split()):
                return 12, f"Strong location match: {tender_location} aligns with {company_loc}"
        
        # Check for Africa-wide focus
        if 'africa' in tender_location and any('africa' in loc for loc in company_locations):
            return 10, f"Regional match: {tender_location} aligns with Africa focus"
        
        return 3, f"Limited location alignment: {tender_location} vs company focus areas"
    
    def _score_budget_match(self, tender: Dict[str, Any], company_profile: Dict[str, Any]) -> Tuple[int, str]:
        """Score budget alignment (0-20 points)"""
        tender_budget = tender.get('budget', '')
        preferred_range = company_profile.get('preferred_project_size', {})
        min_budget = preferred_range.get('min_budget', 20000)
        max_budget = preferred_range.get('max_budget', 500000)
        
        if not tender_budget:
            return 10, "Budget not specified - assigned neutral score"
        
        # Extract numeric value from budget string
        budget_match = re.search(r'[\d,]+(?:\.\d{2})?', tender_budget)
        if not budget_match:
            return 10, f"Budget format unclear: {tender_budget} - assigned neutral score"
        
        try:
            budget_value = float(budget_match.group().replace(',', ''))
            
            # Check if budget is in preferred range
            if min_budget <= budget_value <= max_budget:
                return 20, f"Perfect budget match: ${budget_value:,.0f} within preferred range (${min_budget:,.0f}-${max_budget:,.0f})"
            
            # Check if budget is close to preferred range
            if budget_value < min_budget * 0.5:
                return 5, f"Budget too small: ${budget_value:,.0f} below minimum threshold"
            elif budget_value < min_budget:
                return 12, f"Budget below preferred range: ${budget_value:,.0f} vs minimum ${min_budget:,.0f}"
            elif budget_value > max_budget * 2:
                return 8, f"Budget too large: ${budget_value:,.0f} exceeds maximum threshold"
            elif budget_value > max_budget:
                return 15, f"Budget above preferred range: ${budget_value:,.0f} vs maximum ${max_budget:,.0f}"
            
        except ValueError:
            return 10, f"Budget parsing error: {tender_budget} - assigned neutral score"
        
        return 10, f"Budget analysis incomplete: {tender_budget}"
    
    def _score_technical_match(self, tender: Dict[str, Any], company_profile: Dict[str, Any]) -> Tuple[int, str]:
        """Score technical requirements match (0-20 points)"""
        tender_requirements = tender.get('requirements', [])
        company_technologies = company_profile.get('relevant_technologies', [])
        company_services = company_profile.get('core_services', [])
        
        if not tender_requirements:
            return 10, "No specific technical requirements listed - assigned neutral score"
        
        matches = 0
        total_requirements = len(tender_requirements)
        
        for requirement in tender_requirements:
            req_lower = requirement.lower()
            
            # Check technology matches
            for tech in company_technologies:
                if tech.lower() in req_lower or req_lower in tech.lower():
                    matches += 1
                    break
            
            # Check service matches
            for service in company_services:
                if any(word in req_lower for word in service.lower().split()):
                    matches += 1
                    break
            
            # Check certification matches
            if any(cert.lower() in req_lower for cert in ['aws', 'azure', 'iso', 'pmi']):
                matches += 1
        
        if total_requirements == 0:
            return 10, "No requirements to match"
        
        match_percentage = matches / total_requirements
        score = int(match_percentage * 20)
        
        if score >= 18:
            justification = f"Excellent technical match: {matches}/{total_requirements} requirements aligned"
        elif score >= 15:
            justification = f"Strong technical match: {matches}/{total_requirements} requirements aligned"
        elif score >= 10:
            justification = f"Moderate technical match: {matches}/{total_requirements} requirements aligned"
        else:
            justification = f"Limited technical match: {matches}/{total_requirements} requirements aligned"
        
        return score, justification
    
    def _score_experience_match(self, tender: Dict[str, Any], company_profile: Dict[str, Any]) -> Tuple[int, str]:
        """Score past experience relevance (0-15 points)"""
        tender_description = tender.get('description', '').lower()
        tender_title = tender.get('title', '').lower()
        past_projects = company_profile.get('past_projects', [])
        
        if not past_projects:
            return 7, "No past projects available for comparison"
        
        # Look for project similarities
        relevant_projects = 0
        total_projects = len(past_projects)
        
        for project in past_projects:
            project_name = project.get('name', '').lower()
            project_desc = project.get('description', '').lower()
            
            # Check for keyword matches
            tender_text = f"{tender_title} {tender_description}"
            
            # Look for technology matches
            if any(tech.lower() in tender_text for tech in ['cloud', 'migration', 'security', 'devops']):
                if any(tech.lower() in f"{project_name} {project_desc}" for tech in ['cloud', 'migration', 'security', 'devops']):
                    relevant_projects += 1
                    continue
            
            # Look for service matches
            if any(service.lower() in tender_text for service in ['migration', 'audit', 'automation', 'development']):
                if any(service.lower() in f"{project_name} {project_desc}" for service in ['migration', 'audit', 'automation', 'development']):
                    relevant_projects += 1
                    continue
        
        if total_projects == 0:
            return 7, "No projects to compare"
        
        relevance_percentage = relevant_projects / total_projects
        score = int(relevance_percentage * 15)
        
        if score >= 12:
            justification = f"Strong experience match: {relevant_projects}/{total_projects} relevant past projects"
        elif score >= 8:
            justification = f"Moderate experience match: {relevant_projects}/{total_projects} relevant past projects"
        else:
            justification = f"Limited experience match: {relevant_projects}/{total_projects} relevant past projects"
        
        return score, justification
    
    def _score_certification_match(self, tender: Dict[str, Any], company_profile: Dict[str, Any]) -> Tuple[int, str]:
        """Score certification requirements match (0-10 points)"""
        tender_requirements = tender.get('requirements', [])
        company_certifications = company_profile.get('certifications', [])
        
        if not tender_requirements:
            return 5, "No specific certification requirements listed"
        
        if not company_certifications:
            return 3, "Company has no certifications listed"
        
        matches = 0
        total_requirements = len(tender_requirements)
        
        for requirement in tender_requirements:
            req_lower = requirement.lower()
            
            for cert in company_certifications:
                cert_lower = cert.lower()
                
                # Check for exact matches
                if cert_lower in req_lower or req_lower in cert_lower:
                    matches += 1
                    break
                
                # Check for partial matches (e.g., "AWS" in "AWS Certified")
                if any(word in req_lower for word in cert_lower.split()):
                    matches += 1
                    break
        
        if total_requirements == 0:
            return 5, "No requirements to match"
        
        match_percentage = matches / total_requirements
        score = int(match_percentage * 10)
        
        if score >= 8:
            justification = f"Strong certification match: {matches}/{total_requirements} requirements met"
        elif score >= 5:
            justification = f"Moderate certification match: {matches}/{total_requirements} requirements met"
        else:
            justification = f"Limited certification match: {matches}/{total_requirements} requirements met"
        
        return score, justification
    
    def _generate_overall_justification(self, scores: Dict[str, int], justifications: List[str], total_score: int) -> str:
        """Generate overall justification based on component scores"""
        # Find strengths and weaknesses
        strengths = [k for k, v in scores.items() if v >= 15]
        weaknesses = [k for k, v in scores.items() if v <= 5]
        
        if total_score >= 80:
            overall = "Excellent match - Strong alignment across all criteria"
        elif total_score >= 65:
            overall = "Strong match - Good alignment with minor areas for improvement"
        elif total_score >= 50:
            overall = "Moderate match - Some alignment but several areas need attention"
        else:
            overall = "Weak match - Limited alignment with company capabilities"
        
        # Build detailed justification
        justification_parts = [overall]
        
        if strengths:
            strength_text = ", ".join([k.replace('_', ' ').title() for k in strengths])
            justification_parts.append(f"Strengths: {strength_text}")
        
        if weaknesses:
            weakness_text = ", ".join([k.replace('_', ' ').title() for k in weaknesses])
            justification_parts.append(f"Areas for improvement: {weakness_text}")
        
        # Add key justifications
        key_justifications = [j for j in justifications if any(word in j.lower() for word in ['perfect', 'strong', 'excellent'])]
        if key_justifications:
            justification_parts.append(f"Key highlights: {'; '.join(key_justifications[:2])}")
        
        return ". ".join(justification_parts)

# Global scorer instance
scorer = HybridTenderScorer()

def score_tender(tender: Dict[str, Any], company_profile: Dict[str, Any]) -> Dict[str, Any]:
    """Main scoring function for external use"""
    return scorer.score_tender(tender, company_profile)
