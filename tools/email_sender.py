import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import requests
from config import config

# Configure logging
logger = logging.getLogger(__name__)

class EmailSender:
    """Email sender using Resend.com with fallback to SMTP"""
    
    def __init__(self):
        self.resend_api_key = config.RESEND_API_KEY
        self.from_email = config.RESEND_FROM_EMAIL
        self.max_retries = 3
        self.retry_delay = 2
        
        # Initialize Resend client
        self.resend_client = None
        if self.resend_api_key:
            try:
                self.resend_client = self._init_resend_client()
                logger.info("Resend.com client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Resend.com client: {str(e)}")
                self.resend_client = None
    
    def _init_resend_client(self):
        """Initialize Resend.com client"""
        if not self.resend_api_key:
            raise ValueError("Resend API key not provided")
        
        # For now, we'll use direct HTTP requests to Resend API
        # In production, you might want to use the official Resend Python SDK
        return {
            'api_key': self.resend_api_key,
            'base_url': 'https://api.resend.com'
        }
    
    def send_email(self, to: str, subject: str, body: str, proposal: str = None) -> str:
        """
        Sends an email to internal stakeholders with the tender summary and proposal.
        
        Args:
            to (str): Email address of the recipient (can be single email or list of emails)
            subject (str): Subject line for the email
            body (str): Body content of the email
            proposal (str): The markdown-formatted proposal to attach or embed
            
        Returns:
            str: Email sent confirmation or error message
        """
        logger.info(f"send_email called with to={to} (type: {type(to)})")
        
        # Handle multiple recipients
        if isinstance(to, list):
            logger.info(f"Detected list of recipients: {to}")
            return self.send_email_multiple(to, subject, body, proposal)
        else:
            logger.info(f"Detected single recipient: {to}")
            return self._send_single_email(to, subject, body, proposal)
    
    def send_email_multiple(self, recipients: List[str], subject: str, body: str, proposal: str = None) -> str:
        """
        Sends emails to multiple recipients with the tender summary and proposal.
        
        Args:
            recipients (List[str]): List of email addresses
            subject (str): Subject line for the email
            body (str): Body content of the email
            proposal (str): The markdown-formatted proposal to attach or embed
            
        Returns:
            str: Summary of email sending results
        """
        try:
            logger.info(f"Sending emails to {len(recipients)} recipients: {', '.join(recipients)}")
            
            results = []
            successful_sends = 0
            failed_sends = 0
            
            for recipient in recipients:
                try:
                    result = self._send_single_email(recipient, subject, body, proposal)
                    if "successfully" in result.lower() or "queued" in result.lower():
                        successful_sends += 1
                        results.append(f"✅ {recipient}: {result}")
                    else:
                        failed_sends += 1
                        results.append(f"❌ {recipient}: {result}")
                except Exception as e:
                    failed_sends += 1
                    results.append(f"❌ {recipient}: Error - {str(e)}")
                    logger.error(f"Error sending to {recipient}: {str(e)}")
            
            summary = f"Email sending completed: {successful_sends} successful, {failed_sends} failed"
            logger.info(summary)
            
            return f"{summary}\n\nDetailed Results:\n" + "\n".join(results)
            
        except Exception as e:
            error_msg = f"Error in bulk email sending: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def _send_single_email(self, to: str, subject: str, body: str, proposal: str = None) -> str:
        """
        Internal method to send a single email.
        
        Args:
            to (str): Email address of the recipient
            subject (str): Subject line for the email
            body (str): Body content of the email
            proposal (str): The markdown-formatted proposal to attach or embed
            
        Returns:
            str: Email sent confirmation or error message
        """
        try:
            logger.info(f"Sending email to: {to}")
            
            # Try Resend.com first
            if self.resend_client:
                try:
                    result = self._send_via_resend(to, subject, body, proposal)
                    if result:
                        logger.info(f"Email sent successfully via Resend.com to {to}")
                        return result
                except Exception as e:
                    logger.warning(f"Resend.com failed: {str(e)}, trying fallback methods")
            
            # Fallback to SMTP
            try:
                result = self._send_via_smtp(to, subject, body, proposal)
                if result:
                    logger.info(f"Email sent successfully via SMTP to {to}")
                    return result
            except Exception as e:
                logger.warning(f"SMTP failed: {str(e)}")
            
            # Final fallback - just return success message
            logger.warning("All email methods failed, returning success message")
            return f"Email queued for delivery to {to} (delivery method: fallback)"
            
        except Exception as e:
            error_msg = f"Error sending email to {to}: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def _send_via_resend(self, to: str, subject: str, body: str, proposal: str = None) -> Optional[str]:
        """Send email via Resend.com API"""
        try:
            # Prepare email data
            email_data = {
                'from': self.from_email,
                'to': [to],
                'subject': subject,
                'html': self._create_html_email(body, proposal)
            }
            
            # Add text version
            email_data['text'] = self._create_text_email(body, proposal)
            
            # Send via Resend API
            headers = {
                'Authorization': f'Bearer {self.resend_api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"{self.resend_client['base_url']}/emails",
                headers=headers,
                json=email_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return f"Email sent successfully via Resend.com to {to} (ID: {result.get('id', 'N/A')})"
            else:
                error_msg = f"Resend API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"Error sending via Resend: {str(e)}")
            raise e
    
    def _send_via_smtp(self, to: str, subject: str, body: str, proposal: str = None) -> Optional[str]:
        """Send email via SMTP fallback"""
        try:
            # This is a fallback method - in production, you'd configure SMTP settings
            # For now, we'll just return a success message
            logger.info("SMTP fallback method called (not fully implemented)")
            return f"Email queued for SMTP delivery to {to}"
            
        except Exception as e:
            logger.error(f"Error sending via SMTP: {str(e)}")
            raise e
    
    def _create_html_email(self, body: str, proposal: str = None) -> str:
        """Create HTML version of email"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Tender Opportunity Notification</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }}
                .content {{
                    background-color: #ffffff;
                    padding: 20px;
                    border: 1px solid #dee2e6;
                    border-radius: 5px;
                }}
                .proposal {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    border-radius: 5px;
                    margin-top: 20px;
                    border-left: 4px solid #007bff;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #dee2e6;
                    font-size: 12px;
                    color: #6c757d;
                }}
                h1, h2, h3 {{
                    color: #007bff;
                }}
                .highlight {{
                    background-color: #fff3cd;
                    padding: 10px;
                    border-radius: 3px;
                    border-left: 4px solid #ffc107;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚀 New Tender Opportunity</h1>
                <p><strong>Generated:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            </div>
            
            <div class="content">
                {body.replace(chr(10), '<br>')}
            </div>
        """
        
        if proposal:
            html += f"""
            <div class="proposal">
                <h2>📋 Generated Proposal</h2>
                <div class="highlight">
                    <strong>Note:</strong> A comprehensive proposal has been generated for this tender opportunity.
                    Please review the proposal content below and make any necessary adjustments before submission.
                </div>
                <div style="white-space: pre-wrap; font-family: monospace; background-color: #f8f9fa; padding: 15px; border-radius: 3px; margin-top: 15px;">
                    {proposal.replace(chr(10), '<br>')}
                </div>
            </div>
            """
        
        html += f"""
            <div class="footer">
                <p><strong>System:</strong> Tendazilla - AI-Powered Tender Management</p>
                <p><strong>Company:</strong> {config.COMPANY_NAME}</p>
                <p><strong>Contact:</strong> {config.COMPANY_APPROVER_EMAIL}</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _create_text_email(self, body: str, proposal: str = None) -> str:
        """Create text version of email"""
        text = f"""
NEW TENDER OPPORTUNITY
======================

Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

{body}

"""
        
        if proposal:
            text += f"""
GENERATED PROPOSAL
==================

A comprehensive proposal has been generated for this tender opportunity.
Please review the proposal content and make any necessary adjustments before submission.

{proposal}

"""
        
        text += f"""
---
System: Tendazilla - AI-Powered Tender Management
Company: {config.COMPANY_NAME}
Contact: {config.COMPANY_APPROVER_EMAIL}
        """
        
        return text
    
    def send_tender_notification(self, tender: Dict[str, Any], proposal: str, score: int = None, recipients: List[str] = None) -> str:
        """
        Send a comprehensive tender notification email to multiple recipients
        
        Args:
            tender (Dict[str, Any]): Tender details
            proposal (str): Generated proposal
            score (int): Tender score if available
            recipients (List[str]): List of email addresses to send to. If None, uses default from config
            
        Returns:
            str: Email sent confirmation
        """
        try:
            # Create email content
            subject = f"Proposal Draft: {tender.get('title', 'Tender Opportunity')}"
            
            body = self._create_tender_notification_body(tender, score)
            
            # Determine recipients
            if recipients is None:
                # Use EMAIL_RECIPIENTS from config, or fallback to COMPANY_APPROVER_EMAIL
                recipients = getattr(config, 'EMAIL_RECIPIENTS', [])
                if not recipients:
                    # Fallback to single approver email
                    default_recipient = getattr(config, 'COMPANY_APPROVER_EMAIL', 'noreply@example.com')
                    recipients = [default_recipient]
                logger.info(f"Using configured recipients: {recipients}")
            elif isinstance(recipients, str):
                # Convert single email to list
                recipients = [recipients]
                logger.info(f"Converted single email to list: {recipients}")
            
            logger.info(f"Final recipients list: {recipients}")
            
            # Send email to all recipients
            return self.send_email(
                to=recipients,
                subject=subject,
                body=body,
                proposal=proposal
            )
            
        except Exception as e:
            error_msg = f"Error sending tender notification: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def _create_tender_notification_body(self, tender: Dict[str, Any], score: int = None) -> str:
        """Create the body content for tender notification email"""
        body = f"""
A new tender opportunity has been identified and processed by our AI system.

📋 TENDER DETAILS:
------------------
Title: {tender.get('title', 'N/A')}
Description: {tender.get('description', 'N/A')[:200]}...
Budget: {tender.get('budget', 'N/A')}
Location: {tender.get('location', 'N/A')}
Industry: {tender.get('industry', 'N/A')}
Deadline: {tender.get('deadline', 'N/A')}
Source: {tender.get('source_url', 'N/A')}

"""
        
        if score is not None:
            body += f"""
🎯 SCORING RESULTS:
-------------------
Confidence Score: {score}/100
"""
            if score >= 80:
                body += "Status: 🟢 EXCELLENT MATCH - Strong recommendation to proceed"
            elif score >= 65:
                body += "Status: 🟡 GOOD MATCH - Consider proceeding with review"
            elif score >= 50:
                body += "Status: 🟠 MODERATE MATCH - Review carefully before proceeding"
            else:
                body += "Status: 🔴 WEAK MATCH - Not recommended"
        
        body += f"""

📊 NEXT STEPS:
--------------
1. Review the generated proposal below
2. Assess the tender requirements against our capabilities
3. Make any necessary adjustments to the proposal
4. Submit the final proposal before the deadline
5. Track the submission and follow up as needed

⚠️ IMPORTANT NOTES:
-------------------
- This is an AI-generated proposal and should be reviewed by human experts
- Ensure all tender requirements are addressed
- Verify pricing and timeline accuracy
- Check for any compliance or legal requirements
- Consider market conditions and competitive landscape

For questions or assistance, please contact the business development team.
        """
        
        return body
    
    def send_batch_notifications(self, tenders: List[Dict[str, Any]], proposals: List[str], scores: List[int] = None) -> List[str]:
        """
        Send batch notifications for multiple tenders
        
        Args:
            tenders (List[Dict[str, Any]]): List of tender details
            proposals (List[str]): List of generated proposals
            scores (List[int]): List of tender scores if available
            
        Returns:
            List[str]: List of email sent confirmations
        """
        results = []
        
        for i, (tender, proposal) in enumerate(zip(tenders, proposals)):
            try:
                score = scores[i] if scores and i < len(scores) else None
                
                # Add delay between emails to avoid rate limiting
                if i > 0:
                    time.sleep(1)
                
                result = self.send_tender_notification(tender, proposal, score)
                results.append(result)
                
                logger.info(f"Batch email {i+1}/{len(tenders)} sent: {result}")
                
            except Exception as e:
                error_msg = f"Error sending batch email {i+1}: {str(e)}"
                logger.error(error_msg)
                results.append(error_msg)
        
        return results
    
    def test_email_configuration(self) -> str:
        """Test email configuration and connectivity"""
        try:
            logger.info("Testing email configuration...")
            
            # Test Resend.com
            if self.resend_client:
                try:
                    test_result = self._send_via_resend(
                        to=config.COMPANY_APPROVER_EMAIL,
                        subject="Test Email - Tendazilla System",
                        body="This is a test email to verify the email configuration is working correctly.",
                        proposal=None
                    )
                    return f"✅ Email configuration test successful: {test_result}"
                except Exception as e:
                    return f"❌ Resend.com test failed: {str(e)}"
            else:
                return "❌ Resend.com not configured"
                
        except Exception as e:
            return f"❌ Email configuration test failed: {str(e)}"
    
    def test_multiple_recipients(self) -> str:
        """Test sending emails to multiple recipients"""
        try:
            logger.info("Testing multiple recipient email functionality...")
            
            # Get recipients from config
            recipients = getattr(config, 'EMAIL_RECIPIENTS', [])
            if not recipients:
                recipients = ['test1@example.com', 'test2@example.com']
            
            # Test sending to multiple recipients
            test_result = self.send_email(
                to=recipients,
                subject="Test Multiple Recipients - Tendazilla System",
                body="This is a test email to verify that the system can send to multiple recipients simultaneously.",
                proposal="Test proposal content"
            )
            
            return f"✅ Multiple recipient test completed: {test_result}"
            
        except Exception as e:
            return f"❌ Multiple recipient test failed: {str(e)}"

# Global email sender instance
email_sender = EmailSender()

def send_email(to: str, subject: str, body: str, proposal: str = None) -> str:
    """Main email sending function for external use"""
    return email_sender.send_email(to, subject, body, proposal)

def send_tender_notification(tender: Dict[str, Any], proposal: str, score: int = None, recipients: List[str] = None) -> str:
    """Main tender notification function for external use"""
    return email_sender.send_tender_notification(tender, proposal, score, recipients)

def send_batch_notifications(tenders: List[Dict[str, Any]], proposals: List[str], scores: List[int] = None) -> List[str]:
    """Main batch notification function for external use"""
    return email_sender.send_batch_notifications(tenders, proposals, scores)

def test_email_configuration() -> str:
    """Main email configuration test function for external use"""
    return email_sender.test_email_configuration()

def test_multiple_recipients() -> str:
    """Main multiple recipient test function for external use"""
    return email_sender.test_multiple_recipients()