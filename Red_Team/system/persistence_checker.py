#!/usr/bin/env python3
"""
Red Team Tools - Persistence Checker
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


class PersistenceChecker:
    """Check for persistence mechanisms on Windows/Linux"""
    
    def __init__(self):
        self.is_windows = os.name == 'nt'
        self.findings = []
    
    def _run_cmd(self, cmd: str) -> str:
        """Run command and return output"""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, 
                text=True, timeout=30
            )
            return result.stdout + result.stderr
        except:
            return ""
    
    def check_windows_autoruns(self) -> list:
        """Check Windows autorun locations"""
        findings = []
        
        if not self.is_windows:
            return findings
        
        info("Checking Windows autorun locations...")
        
        # Registry Run keys
        run_keys = [
            r'HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run',
            r'HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce',
            r'HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run',
            r'HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce',
            r'HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run',
            r'HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer\Run',
        ]
        
        for key in run_keys:
            output = self._run_cmd(f'reg query "{key}" 2>nul')
            if output.strip():
                entries = []
                for line in output.split('\n'):
                    if 'REG_' in line:
                        parts = line.split('REG_')
                        if len(parts) >= 2:
                            name = parts[0].strip()
                            value = parts[1].split(None, 1)[-1] if parts[1].split(None, 1) else ''
                            entries.append({'name': name, 'value': value})
                
                if entries:
                    findings.append({
                        'type': 'Registry Autorun',
                        'location': key,
                        'entries': entries
                    })
        
        return findings
    
    def check_windows_services(self) -> list:
        """Check Windows services for persistence"""
        findings = []
        
        if not self.is_windows:
            return findings
        
        info("Checking Windows services...")
        
        output = self._run_cmd('sc query state=all type=own')
        
        # Check for recently created services (non-Microsoft)
        service_blocks = output.split('SERVICE_NAME:')
        
        for block in service_blocks[1:]:  # Skip first empty
            lines = block.strip().split('\n')
            if lines:
                svc_name = lines[0].strip()
                
                # Get service details
                qc_output = self._run_cmd(f'sc qc "{svc_name}" 2>nul')
                
                # Check for non-standard paths
                if 'BINARY_PATH_NAME' in qc_output:
                    match = re.search(r'BINARY_PATH_NAME\s*:\s*(.+)', qc_output)
                    if match:
                        path = match.group(1).strip()
                        
                        # Check if not in standard Windows directories
                        standard_paths = ['C:\\Windows', 'C:\\Program Files']
                        is_standard = any(path.lower().startswith(sp.lower()) for sp in standard_paths)
                        
                        if not is_standard and path:
                            findings.append({
                                'type': 'Non-Standard Service',
                                'service': svc_name,
                                'path': path
                            })
        
        return findings
    
    def check_windows_scheduled_tasks(self) -> list:
        """Check Windows scheduled tasks"""
        findings = []
        
        if not self.is_windows:
            return findings
        
        info("Checking Windows scheduled tasks...")
        
        output = self._run_cmd('schtasks /query /fo LIST /v')
        
        # Parse tasks
        current_task = {}
        for line in output.split('\n'):
            if ':' in line:
                key, _, value = line.partition(':')
                key = key.strip()
                value = value.strip()
                
                if key == 'TaskName' and current_task:
                    # Check previous task
                    if current_task.get('TaskName') and current_task.get('Task To Run'):
                        task_path = current_task.get('Task To Run', '')
                        # Filter out system tasks
                        if 'Microsoft' not in current_task.get('TaskName', '') and task_path:
                            findings.append({
                                'type': 'Scheduled Task',
                                'name': current_task.get('TaskName'),
                                'action': task_path[:100],
                                'status': current_task.get('Status', 'Unknown')
                            })
                    current_task = {}
                
                current_task[key] = value
        
        return findings
    
    def check_windows_wmi(self) -> list:
        """Check WMI event subscriptions"""
        findings = []
        
        if not self.is_windows:
            return findings
        
        info("Checking WMI event subscriptions...")
        
        # Check for WMI event filters
        output = self._run_cmd('powershell -Command "Get-WmiObject -Namespace root\\subscription -Class __EventFilter 2>$null | Select-Object Name, Query | Format-List"')
        
        if 'Name' in output:
            findings.append({
                'type': 'WMI Event Subscription',
                'details': 'WMI event filters found - may indicate persistence'
            })
        
        return findings
    
    def check_windows_startup_folders(self) -> list:
        """Check startup folders"""
        findings = []
        
        if not self.is_windows:
            return findings
        
        info("Checking startup folders...")
        
        startup_folders = [
            os.path.expanduser(r'~\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup'),
            r'C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp'
        ]
        
        for folder in startup_folders:
            if os.path.exists(folder):
                for item in os.listdir(folder):
                    item_path = os.path.join(folder, item)
                    findings.append({
                        'type': 'Startup Folder Item',
                        'location': folder,
                        'item': item,
                        'path': item_path
                    })
        
        return findings
    
    def check_linux_cron(self) -> list:
        """Check Linux cron jobs"""
        findings = []
        
        if self.is_windows:
            return findings
        
        info("Checking cron jobs...")
        
        cron_locations = [
            '/etc/crontab',
            '/etc/cron.d',
            '/var/spool/cron/crontabs',
            '/var/spool/cron',
        ]
        
        # User crontab
        output = self._run_cmd('crontab -l 2>/dev/null')
        if output.strip() and 'no crontab' not in output.lower():
            findings.append({
                'type': 'User Crontab',
                'entries': output.strip().split('\n')
            })
        
        # Check cron directories
        for loc in cron_locations:
            if os.path.exists(loc):
                if os.path.isfile(loc):
                    with open(loc, 'r') as f:
                        content = f.read()
                        if content.strip():
                            findings.append({
                                'type': 'Cron File',
                                'location': loc,
                                'entries': [l for l in content.split('\n') if l.strip() and not l.startswith('#')]
                            })
                elif os.path.isdir(loc):
                    for item in os.listdir(loc):
                        findings.append({
                            'type': 'Cron Directory Entry',
                            'location': loc,
                            'item': item
                        })
        
        return findings
    
    def check_linux_init(self) -> list:
        """Check Linux init scripts and systemd services"""
        findings = []
        
        if self.is_windows:
            return findings
        
        info("Checking init scripts and systemd services...")
        
        # Systemd services
        output = self._run_cmd('systemctl list-unit-files --type=service 2>/dev/null | grep enabled')
        
        for line in output.split('\n'):
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    svc_name = parts[0]
                    
                    # Check if custom service
                    if not svc_name.startswith(('systemd-', 'dbus', 'ssh', 'cron', 'network')):
                        findings.append({
                            'type': 'Enabled Systemd Service',
                            'service': svc_name
                        })
        
        # Check rc.local
        rc_local = '/etc/rc.local'
        if os.path.exists(rc_local):
            with open(rc_local, 'r') as f:
                content = f.read()
                commands = [l for l in content.split('\n') if l.strip() and not l.startswith('#') and l.strip() != 'exit 0']
                if commands:
                    findings.append({
                        'type': 'rc.local Commands',
                        'commands': commands
                    })
        
        return findings
    
    def check_linux_profile(self) -> list:
        """Check shell profile files"""
        findings = []
        
        if self.is_windows:
            return findings
        
        info("Checking shell profile files...")
        
        profile_files = [
            '.bashrc', '.bash_profile', '.profile', '.zshrc',
            '/etc/profile', '/etc/bash.bashrc', '/etc/profile.d'
        ]
        
        home = os.path.expanduser('~')
        
        for pf in profile_files:
            path = os.path.join(home, pf) if pf.startswith('.') else pf
            
            if os.path.exists(path):
                if os.path.isfile(path):
                    try:
                        mtime = os.stat(path).st_mtime
                        import time
                        age_days = (time.time() - mtime) / 86400
                        
                        if age_days < 7:  # Modified in last week
                            findings.append({
                                'type': 'Recently Modified Profile',
                                'file': path,
                                'modified_days_ago': round(age_days, 1)
                            })
                    except:
                        pass
        
        return findings
    
    def check_linux_ssh(self) -> list:
        """Check SSH persistence mechanisms"""
        findings = []
        
        if self.is_windows:
            return findings
        
        info("Checking SSH configuration...")
        
        ssh_dir = os.path.expanduser('~/.ssh')
        
        if os.path.exists(ssh_dir):
            # Check authorized_keys
            auth_keys = os.path.join(ssh_dir, 'authorized_keys')
            if os.path.exists(auth_keys):
                with open(auth_keys, 'r') as f:
                    keys = [l.strip() for l in f if l.strip() and not l.startswith('#')]
                    findings.append({
                        'type': 'SSH Authorized Keys',
                        'count': len(keys),
                        'file': auth_keys
                    })
        
        return findings
    
    def run_all_checks(self) -> list:
        """Run all persistence checks"""
        print(f"\n{C}{'═' * 60}{RESET}")
        print(f"{BRIGHT}PERSISTENCE CHECK{RESET}")
        print(f"{C}{'═' * 60}{RESET}")
        print()
        
        all_findings = []
        
        if self.is_windows:
            all_findings.extend(self.check_windows_autoruns())
            all_findings.extend(self.check_windows_services())
            all_findings.extend(self.check_windows_scheduled_tasks())
            all_findings.extend(self.check_windows_wmi())
            all_findings.extend(self.check_windows_startup_folders())
        else:
            all_findings.extend(self.check_linux_cron())
            all_findings.extend(self.check_linux_init())
            all_findings.extend(self.check_linux_profile())
            all_findings.extend(self.check_linux_ssh())
        
        self.findings = all_findings
        return all_findings
    
    def print_results(self):
        """Print check results"""
        print(f"\n{C}{'═' * 60}{RESET}")
        print(f"{BRIGHT}PERSISTENCE MECHANISMS FOUND{RESET}")
        print(f"{C}{'═' * 60}{RESET}")
        
        if not self.findings:
            success("No notable persistence mechanisms found")
            return
        
        # Group by type
        by_type = {}
        for f in self.findings:
            ftype = f['type']
            if ftype not in by_type:
                by_type[ftype] = []
            by_type[ftype].append(f)
        
        for ftype, items in by_type.items():
            print(f"\n{Y}[{ftype}] ({len(items)}){RESET}")
            
            for item in items[:10]:  # Limit display
                if 'location' in item:
                    print(f"  Location: {item['location']}")
                if 'service' in item:
                    print(f"  Service: {item['service']}")
                if 'path' in item:
                    print(f"  Path: {item['path']}")
                if 'name' in item:
                    print(f"  Name: {item['name']}")
                if 'entries' in item and isinstance(item['entries'], list):
                    for entry in item['entries'][:3]:
                        if isinstance(entry, dict):
                            print(f"    - {entry.get('name', 'N/A')}: {entry.get('value', 'N/A')[:50]}")
                        else:
                            print(f"    - {entry[:60]}")
                print()
        
        print(f"\n{Y}Total findings: {len(self.findings)}{RESET}")


def interactive_mode():
    """Interactive mode for persistence checking"""
    print_banner("PERSISTENCE CHECK", color="red")
    warning("For authorized security testing only!")
    
    checker = PersistenceChecker()
    checker.run_all_checks()
    checker.print_results()


if __name__ == "__main__":
    interactive_mode()
