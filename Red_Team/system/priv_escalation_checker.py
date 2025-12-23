#!/usr/bin/env python3
"""
Red Team Tools - Privilege Escalation Checker
For educational and authorized security testing only
"""

import os
import sys
import subprocess
import platform
import re
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import *


class PrivEscChecker:
    """Windows/Linux privilege escalation checker"""
    
    def __init__(self):
        self.is_windows = os.name == 'nt'
        self.findings = []
        self.system_info = {}
    
    def get_system_info(self) -> dict:
        """Gather system information"""
        info = {
            "os": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "architecture": platform.machine(),
            "hostname": platform.node(),
            "username": os.getenv('USERNAME') or os.getenv('USER', 'unknown'),
            "is_admin": False
        }
        
        # Check if admin/root
        if self.is_windows:
            try:
                import ctypes
                info["is_admin"] = ctypes.windll.shell32.IsUserAnAdmin() != 0
            except:
                pass
        else:
            info["is_admin"] = os.geteuid() == 0
        
        self.system_info = info
        return info
    
    def _run_cmd(self, cmd: str, shell: bool = True) -> str:
        """Run command and return output"""
        try:
            result = subprocess.run(
                cmd, shell=shell, capture_output=True, 
                text=True, timeout=30
            )
            return result.stdout + result.stderr
        except:
            return ""
    
    def check_windows_services(self) -> list:
        """Check for vulnerable Windows services"""
        findings = []
        
        if not self.is_windows:
            return findings
        
        info("Checking Windows services for misconfigurations...")
        
        # Check for unquoted service paths
        output = self._run_cmd('wmic service get name,displayname,pathname,startmode | findstr /i "auto"')
        
        for line in output.split('\n'):
            if line.strip() and 'C:\\' in line:
                # Check for unquoted paths with spaces
                match = re.search(r'C:\\[^"]+\s+\w+', line)
                if match:
                    path = match.group()
                    if ' ' in path and not path.startswith('"'):
                        findings.append({
                            'type': 'Unquoted Service Path',
                            'severity': 'HIGH',
                            'details': f"Service path: {path}",
                            'recommendation': 'Quote the service path'
                        })
        
        # Check service permissions
        try:
            output = self._run_cmd('sc query state=all')
            services = re.findall(r'SERVICE_NAME: (\S+)', output)
            
            for svc in services[:20]:  # Limit to 20
                sd_output = self._run_cmd(f'sc sdshow {svc}')
                if 'AU' in sd_output or 'BU' in sd_output:  # Authenticated Users or Built-in Users
                    if 'DC' in sd_output or 'WD' in sd_output:  # Change or Write DAC
                        findings.append({
                            'type': 'Weak Service Permissions',
                            'severity': 'HIGH',
                            'details': f"Service '{svc}' may have weak permissions",
                            'recommendation': 'Review and restrict service permissions'
                        })
        except:
            pass
        
        return findings
    
    def check_windows_scheduled_tasks(self) -> list:
        """Check for vulnerable scheduled tasks"""
        findings = []
        
        if not self.is_windows:
            return findings
        
        info("Checking scheduled tasks...")
        
        output = self._run_cmd('schtasks /query /fo CSV /v')
        
        for line in output.split('\n'):
            if '.exe' in line.lower() or '.bat' in line.lower() or '.ps1' in line.lower():
                # Check for writable paths
                match = re.search(r'[A-Z]:\\[^,]+\.(exe|bat|ps1|cmd)', line, re.IGNORECASE)
                if match:
                    task_path = match.group()
                    if os.path.exists(task_path):
                        if os.access(task_path, os.W_OK):
                            findings.append({
                                'type': 'Writable Scheduled Task Binary',
                                'severity': 'CRITICAL',
                                'details': f"Writable task binary: {task_path}",
                                'recommendation': 'Restrict write permissions'
                            })
        
        return findings
    
    def check_windows_registry(self) -> list:
        """Check registry for privilege escalation vectors"""
        findings = []
        
        if not self.is_windows:
            return findings
        
        info("Checking registry autorun locations...")
        
        # Check AlwaysInstallElevated
        output = self._run_cmd('reg query HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Installer /v AlwaysInstallElevated')
        if 'AlwaysInstallElevated' in output and '0x1' in output:
            findings.append({
                'type': 'AlwaysInstallElevated Enabled',
                'severity': 'CRITICAL',
                'details': 'AlwaysInstallElevated is enabled in HKLM',
                'recommendation': 'Disable AlwaysInstallElevated policy'
            })
        
        output = self._run_cmd('reg query HKCU\\SOFTWARE\\Policies\\Microsoft\\Windows\\Installer /v AlwaysInstallElevated')
        if 'AlwaysInstallElevated' in output and '0x1' in output:
            findings.append({
                'type': 'AlwaysInstallElevated Enabled',
                'severity': 'CRITICAL',
                'details': 'AlwaysInstallElevated is enabled in HKCU',
                'recommendation': 'Disable AlwaysInstallElevated policy'
            })
        
        # Check autorun locations
        autorun_keys = [
            r'HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run',
            r'HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run',
            r'HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce',
        ]
        
        for key in autorun_keys:
            output = self._run_cmd(f'reg query "{key}"')
            for line in output.split('\n'):
                if '.exe' in line.lower():
                    match = re.search(r'[A-Z]:\\[^\s]+\.exe', line, re.IGNORECASE)
                    if match:
                        exe_path = match.group()
                        if os.path.exists(exe_path) and os.access(exe_path, os.W_OK):
                            findings.append({
                                'type': 'Writable Autorun Binary',
                                'severity': 'HIGH',
                                'details': f"Writable autorun: {exe_path}",
                                'recommendation': 'Restrict write permissions'
                            })
        
        return findings
    
    def check_linux_suid(self) -> list:
        """Check for SUID/SGID binaries (Linux)"""
        findings = []
        
        if self.is_windows:
            return findings
        
        info("Checking SUID/SGID binaries...")
        
        # Known exploitable SUID binaries
        dangerous_suids = [
            'nmap', 'vim', 'vi', 'nano', 'less', 'more', 'man',
            'awk', 'find', 'python', 'python3', 'perl', 'ruby',
            'bash', 'sh', 'dash', 'zsh', 'ksh', 'csh',
            'cp', 'mv', 'tar', 'zip', 'gzip', 'dd',
            'wget', 'curl', 'nc', 'ncat', 'socat',
            'docker', 'lxc', 'systemctl', 'env'
        ]
        
        output = self._run_cmd('find / -perm -4000 -type f 2>/dev/null')
        
        for line in output.split('\n'):
            if line.strip():
                binary = os.path.basename(line.strip())
                if binary in dangerous_suids:
                    findings.append({
                        'type': 'Dangerous SUID Binary',
                        'severity': 'HIGH',
                        'details': f"SUID binary: {line.strip()}",
                        'recommendation': f'Check GTFOBins for {binary} exploitation'
                    })
        
        return findings
    
    def check_linux_sudo(self) -> list:
        """Check sudo configuration"""
        findings = []
        
        if self.is_windows:
            return findings
        
        info("Checking sudo configuration...")
        
        output = self._run_cmd('sudo -l 2>/dev/null')
        
        if 'NOPASSWD' in output:
            findings.append({
                'type': 'NOPASSWD sudo',
                'severity': 'MEDIUM',
                'details': 'User can run some commands with NOPASSWD',
                'recommendation': 'Review sudo configuration'
            })
        
        # Check for dangerous sudo permissions
        dangerous_sudo = ['ALL', 'vim', 'vi', 'nano', 'less', 'more', 'man',
                         'awk', 'find', 'python', 'perl', 'ruby', 'bash', 'sh',
                         'tar', 'zip', 'wget', 'curl', 'nc', 'ncat']
        
        for cmd in dangerous_sudo:
            if cmd in output:
                findings.append({
                    'type': 'Dangerous sudo Permission',
                    'severity': 'HIGH',
                    'details': f"User may sudo: {cmd}",
                    'recommendation': 'Consider restricting sudo permissions'
                })
        
        return findings
    
    def check_writable_paths(self) -> list:
        """Check for writable paths in PATH"""
        findings = []
        
        info("Checking PATH directories...")
        
        path_dirs = os.environ.get('PATH', '').split(os.pathsep)
        
        for directory in path_dirs:
            if os.path.exists(directory):
                if os.access(directory, os.W_OK):
                    findings.append({
                        'type': 'Writable PATH Directory',
                        'severity': 'MEDIUM',
                        'details': f"Writable PATH: {directory}",
                        'recommendation': 'Remove write permissions from PATH directories'
                    })
        
        return findings
    
    def check_credentials(self) -> list:
        """Check for stored credentials"""
        findings = []
        
        info("Checking for stored credentials...")
        
        if self.is_windows:
            # Check cmdkey stored credentials
            output = self._run_cmd('cmdkey /list')
            if 'Target:' in output:
                findings.append({
                    'type': 'Stored Windows Credentials',
                    'severity': 'MEDIUM',
                    'details': 'Found stored Windows credentials via cmdkey',
                    'recommendation': 'Review stored credentials with "cmdkey /list"'
                })
            
            # Check for saved WiFi passwords
            output = self._run_cmd('netsh wlan show profiles')
            if 'All User Profile' in output:
                profiles = re.findall(r'All User Profile\s*:\s*(.+)', output)
                if profiles:
                    findings.append({
                        'type': 'Saved WiFi Profiles',
                        'severity': 'LOW',
                        'details': f"Found {len(profiles)} saved WiFi profiles",
                        'recommendation': 'WiFi passwords can be extracted with netsh'
                    })
        else:
            # Check common credential locations
            cred_files = [
                '/etc/shadow', '.bash_history', '.mysql_history',
                '.psql_history', '.ssh/id_rsa', '.gnupg/secring.gpg'
            ]
            
            home = os.path.expanduser('~')
            for cf in cred_files:
                path = os.path.join(home, cf) if cf.startswith('.') else cf
                if os.path.exists(path) and os.access(path, os.R_OK):
                    findings.append({
                        'type': 'Readable Credential File',
                        'severity': 'MEDIUM',
                        'details': f"Readable: {path}",
                        'recommendation': 'Review file permissions'
                    })
        
        return findings
    
    def run_all_checks(self) -> list:
        """Run all privilege escalation checks"""
        self.get_system_info()
        
        print(f"\n{C}{'═' * 60}{RESET}")
        print(f"{BRIGHT}PRIVILEGE ESCALATION CHECK{RESET}")
        print(f"{C}{'═' * 60}{RESET}")
        
        print(f"\n{Y}System Information:{RESET}")
        print(f"  OS: {self.system_info['os']} {self.system_info['release']}")
        print(f"  Hostname: {self.system_info['hostname']}")
        print(f"  User: {self.system_info['username']}")
        print(f"  Admin/Root: {self.system_info['is_admin']}")
        print()
        
        all_findings = []
        
        if self.is_windows:
            all_findings.extend(self.check_windows_services())
            all_findings.extend(self.check_windows_scheduled_tasks())
            all_findings.extend(self.check_windows_registry())
        else:
            all_findings.extend(self.check_linux_suid())
            all_findings.extend(self.check_linux_sudo())
        
        all_findings.extend(self.check_writable_paths())
        all_findings.extend(self.check_credentials())
        
        self.findings = all_findings
        return all_findings
    
    def print_results(self):
        """Print check results"""
        print(f"\n{C}{'═' * 60}{RESET}")
        print(f"{BRIGHT}FINDINGS{RESET}")
        print(f"{C}{'═' * 60}{RESET}")
        
        if not self.findings:
            success("No obvious privilege escalation vectors found")
            return
        
        # Group by severity
        critical = [f for f in self.findings if f['severity'] == 'CRITICAL']
        high = [f for f in self.findings if f['severity'] == 'HIGH']
        medium = [f for f in self.findings if f['severity'] == 'MEDIUM']
        low = [f for f in self.findings if f['severity'] == 'LOW']
        
        if critical:
            print(f"\n{R}CRITICAL ({len(critical)}):{RESET}")
            for f in critical:
                print(f"  {R}[!]{RESET} {f['type']}")
                print(f"      {f['details']}")
        
        if high:
            print(f"\n{Y}HIGH ({len(high)}):{RESET}")
            for f in high:
                print(f"  {Y}[!]{RESET} {f['type']}")
                print(f"      {f['details']}")
        
        if medium:
            print(f"\n{B}MEDIUM ({len(medium)}):{RESET}")
            for f in medium:
                print(f"  {B}[*]{RESET} {f['type']}")
                print(f"      {f['details']}")
        
        if low:
            print(f"\n{W}LOW ({len(low)}):{RESET}")
            for f in low:
                print(f"  {W}[-]{RESET} {f['type']}")
        
        print(f"\n{Y}Total findings: {len(self.findings)}{RESET}")


def interactive_mode():
    """Interactive mode for privilege escalation checking"""
    print_banner("PRIV ESC CHECK", color="red")
    warning("For authorized security testing only!")
    
    checker = PrivEscChecker()
    
    options = [
        "Run All Checks",
        "Check Services/SUID Only",
        "Check Credentials Only",
        "Check PATH Only"
    ]
    
    choice = menu_selector(options, "Select Option")
    
    if choice == 0:
        return
    
    checker.get_system_info()
    
    if choice == 1:
        checker.run_all_checks()
    elif choice == 2:
        if checker.is_windows:
            checker.findings.extend(checker.check_windows_services())
        else:
            checker.findings.extend(checker.check_linux_suid())
    elif choice == 3:
        checker.findings.extend(checker.check_credentials())
    elif choice == 4:
        checker.findings.extend(checker.check_writable_paths())
    
    checker.print_results()


if __name__ == "__main__":
    interactive_mode()
