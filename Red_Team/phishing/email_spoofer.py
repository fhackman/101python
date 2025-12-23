#!/usr/bin/env python3
"""
Red Team Tools - Email Spoofer Template Generator
For educational and authorized security testing only
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import *


class EmailSpoofer:
    """Email header spoofing template generator"""
    
    # Email templates
    TEMPLATES = {
        "password_reset": {
            "subject": "Password Reset Required - Action Needed",
            "body": """
Dear {target_name},

We've detected unusual activity on your account. For your security, 
please reset your password immediately by clicking the link below:

{link}

This link will expire in 24 hours.

If you did not request this reset, please contact our support team immediately.

Best regards,
{company_name} Security Team
"""
        },
        "document_share": {
            "subject": "{sender_name} shared a document with you",
            "body": """
Hi {target_name},

{sender_name} has shared a document with you: "{document_name}"

Click here to view: {link}

This document requires your login to access.

Best,
{company_name} Document System
"""
        },
        "invoice": {
            "subject": "Invoice #{invoice_number} - Payment Required",
            "body": """
Dear {target_name},

Please find attached your invoice #{invoice_number} for the amount of {amount}.

Payment is due within 30 days. Click the link below to view and pay:
{link}

If you have any questions, please don't hesitate to contact us.

Regards,
{company_name} Billing Department
"""
        },
        "it_support": {
            "subject": "IT: Your mailbox is almost full",
            "body": """
Dear {target_name},

Your mailbox has reached 95% capacity. To avoid losing incoming emails, 
please click the link below to increase your storage quota:

{link}

This is an automated message from IT Support.

IT Department
{company_name}
"""
        },
        "ceo_urgent": {
            "subject": "Urgent - Need your help",
            "body": """
{target_name},

I'm in a meeting and need you to handle something urgently. 
Can you process a wire transfer for me? 

Please let me know when you're available.

{sender_name}
CEO, {company_name}

Sent from my iPhone
"""
        }
    }
    
    def __init__(self):
        self.smtp_server = None
        self.smtp_port = 25
        self.use_tls = False
    
    def generate_email(self, template_name: str, variables: dict) -> dict:
        """Generate email from template"""
        if template_name not in self.TEMPLATES:
            error(f"Template '{template_name}' not found")
            return {}
        
        template = self.TEMPLATES[template_name]
        
        subject = template["subject"]
        body = template["body"]
        
        # Replace variables
        for key, value in variables.items():
            subject = subject.replace(f"{{{key}}}", str(value))
            body = body.replace(f"{{{key}}}", str(value))
        
        return {
            "subject": subject,
            "body": body
        }
    
    def generate_raw_email(self, from_addr: str, from_name: str, 
                          to_addr: str, to_name: str,
                          subject: str, body: str, 
                          reply_to: str = None,
                          html: bool = False) -> str:
        """Generate raw email with spoofed headers"""
        if html:
            msg = MIMEMultipart('alternative')
            msg.attach(MIMEText(body, 'plain'))
            msg.attach(MIMEText(body, 'html'))
        else:
            msg = MIMEText(body)
        
        msg['Subject'] = subject
        msg['From'] = f'{from_name} <{from_addr}>'
        msg['To'] = f'{to_name} <{to_addr}>'
        
        if reply_to:
            msg['Reply-To'] = reply_to
        
        # Add headers that may bypass filters
        msg['X-Mailer'] = 'Microsoft Outlook 16.0'
        msg['X-Originating-IP'] = '10.0.0.1'
        
        return msg.as_string()
    
    def create_phishing_email(self, template: str, 
                             spoofed_from: str, spoofed_name: str,
                             target_email: str, target_name: str,
                             phishing_link: str, company: str,
                             **extra_vars) -> str:
        """Create a complete phishing email"""
        
        variables = {
            "target_name": target_name,
            "sender_name": spoofed_name,
            "company_name": company,
            "link": phishing_link,
            **extra_vars
        }
        
        email_content = self.generate_email(template, variables)
        
        if not email_content:
            return ""
        
        raw_email = self.generate_raw_email(
            from_addr=spoofed_from,
            from_name=spoofed_name,
            to_addr=target_email,
            to_name=target_name,
            subject=email_content["subject"],
            body=email_content["body"]
        )
        
        return raw_email
    
    def analyze_email_headers(self, raw_email: str) -> dict:
        """Analyze email headers for security indicators"""
        analysis = {
            "spf": "Not found",
            "dkim": "Not found",
            "dmarc": "Not found",
            "received_hops": 0,
            "suspicious_headers": []
        }
        
        lines = raw_email.split('\n')
        
        for line in lines:
            line_lower = line.lower()
            
            if line_lower.startswith('received:'):
                analysis["received_hops"] += 1
            
            if 'spf=' in line_lower:
                if 'pass' in line_lower:
                    analysis["spf"] = "Pass"
                elif 'fail' in line_lower:
                    analysis["spf"] = "Fail"
                elif 'softfail' in line_lower:
                    analysis["spf"] = "Softfail"
            
            if 'dkim=' in line_lower:
                if 'pass' in line_lower:
                    analysis["dkim"] = "Pass"
                elif 'fail' in line_lower:
                    analysis["dkim"] = "Fail"
            
            if 'dmarc=' in line_lower:
                if 'pass' in line_lower:
                    analysis["dmarc"] = "Pass"
                elif 'fail' in line_lower:
                    analysis["dmarc"] = "Fail"
        
        return analysis
    
    def list_templates(self):
        """List available templates"""
        print(f"\n{C}Available Email Templates:{RESET}")
        for name, template in self.TEMPLATES.items():
            print(f"\n  {Y}[{name}]{RESET}")
            print(f"    Subject: {template['subject'][:50]}...")
    
    def save_email(self, raw_email: str, filename: str):
        """Save email to .eml file"""
        with open(filename, 'w') as f:
            f.write(raw_email)
        success(f"Email saved to {filename}")


def interactive_mode():
    """Interactive mode for email spoofing"""
    print_banner("EMAIL SPOOFER", color="red")
    warning("For authorized security testing only!")
    warning("Use only in authorized phishing simulations!")
    
    spoofer = EmailSpoofer()
    
    options = [
        "Generate Phishing Email",
        "List Available Templates",
        "Create Custom Email",
        "Analyze Email Headers"
    ]
    
    choice = menu_selector(options, "Select Option")
    
    if choice == 0:
        return
    
    elif choice == 1:
        spoofer.list_templates()
        print()
        
        template = prompt("Select template name")
        
        if template not in spoofer.TEMPLATES:
            error("Invalid template")
            return
        
        print(f"\n{Y}Enter email details:{RESET}")
        spoofed_from = prompt("Spoofed from email (e.g., support@company.com)")
        spoofed_name = prompt("Spoofed from name (e.g., IT Support)")
        target_email = prompt("Target email")
        target_name = prompt("Target name")
        phishing_link = prompt("Phishing link")
        company = prompt("Company name")
        
        # Extra variables based on template
        extra = {}
        if template == "document_share":
            extra["document_name"] = prompt("Document name")
        elif template == "invoice":
            extra["invoice_number"] = prompt("Invoice number")
            extra["amount"] = prompt("Amount")
        
        raw_email = spoofer.create_phishing_email(
            template, spoofed_from, spoofed_name,
            target_email, target_name, phishing_link, company,
            **extra
        )
        
        print(f"\n{C}{'═' * 60}{RESET}")
        print(f"{BRIGHT}GENERATED EMAIL{RESET}")
        print(f"{C}{'═' * 60}{RESET}")
        print(raw_email)
        
        if confirm("Save to .eml file?"):
            filename = prompt("Filename") or "phishing_email.eml"
            spoofer.save_email(raw_email, filename)
    
    elif choice == 2:
        spoofer.list_templates()
    
    elif choice == 3:
        print(f"\n{Y}Enter email details:{RESET}")
        from_email = prompt("From email")
        from_name = prompt("From name")
        to_email = prompt("To email")
        to_name = prompt("To name")
        subject = prompt("Subject")
        print("Enter body (end with empty line):")
        body_lines = []
        while True:
            line = input()
            if not line:
                break
            body_lines.append(line)
        body = '\n'.join(body_lines)
        
        raw_email = spoofer.generate_raw_email(
            from_email, from_name, to_email, to_name, subject, body
        )
        
        print(f"\n{G}Generated Email:{RESET}")
        print(raw_email)
    
    elif choice == 4:
        print("Paste email headers (end with empty line):")
        headers = []
        while True:
            line = input()
            if not line:
                break
            headers.append(line)
        
        raw = '\n'.join(headers)
        analysis = spoofer.analyze_email_headers(raw)
        
        print(f"\n{C}Header Analysis:{RESET}")
        print(f"  SPF: {analysis['spf']}")
        print(f"  DKIM: {analysis['dkim']}")
        print(f"  DMARC: {analysis['dmarc']}")
        print(f"  Received Hops: {analysis['received_hops']}")


if __name__ == "__main__":
    interactive_mode()
