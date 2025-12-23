#!/usr/bin/env python3
"""
Red Team Tools - Process Monitor
For educational and authorized security testing only
"""

import psutil
import time
import threading
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import *


class ProcessMonitor:
    """Process monitoring and analysis tool"""
    
    # Suspicious process names
    SUSPICIOUS_PROCESSES = [
        # Security tools
        "wireshark", "procmon", "procexp", "tcpview", "autoruns",
        "processhacker", "x64dbg", "x32dbg", "ollydbg", "ida",
        "ghidra", "radare2", "immunity", "windbg", "apimonitor",
        
        # Antivirus/EDR
        "mbam", "malwarebytes", "avp", "avast", "avg", "norton",
        "mcafee", "defender", "carbonblack", "crowdstrike", "sentinel",
        "cylance", "sophos", "eset", "kaspersky", "bitdefender",
        
        # Forensics
        "ftk", "encase", "autopsy", "volatility", "rekall",
        
        # Sandbox indicators
        "vboxservice", "vboxtray", "vmtoolsd", "vmwaretray",
        "sandboxie", "cuckoomon", "python.exe",  # in sandbox
        
        # Remote access
        "teamviewer", "anydesk", "logmein", "gotomeeting",
    ]
    
    def __init__(self):
        self.monitoring = False
        self.baseline_processes = set()
        self.new_processes = []
        self.lock = threading.Lock()
    
    def get_all_processes(self) -> list:
        """Get all running processes"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 
                                        'memory_percent', 'status', 'create_time']):
            try:
                pinfo = proc.info
                pinfo['exe'] = proc.exe() if proc.pid != 0 else ''
                pinfo['cmdline'] = ' '.join(proc.cmdline()) if proc.pid != 0 else ''
                processes.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return processes
    
    def get_process_tree(self, pid: int = None) -> dict:
        """Get process tree starting from PID or all root processes"""
        def get_children(parent_pid):
            children = []
            try:
                parent = psutil.Process(parent_pid)
                for child in parent.children(recursive=False):
                    child_info = {
                        'pid': child.pid,
                        'name': child.name(),
                        'children': get_children(child.pid)
                    }
                    children.append(child_info)
            except:
                pass
            return children
        
        if pid:
            try:
                proc = psutil.Process(pid)
                return {
                    'pid': proc.pid,
                    'name': proc.name(),
                    'children': get_children(pid)
                }
            except:
                return {}
        
        # Get all root processes
        all_pids = set(p.pid for p in psutil.process_iter())
        children_pids = set()
        
        for proc in psutil.process_iter():
            try:
                for child in proc.children():
                    children_pids.add(child.pid)
            except:
                pass
        
        root_pids = all_pids - children_pids
        trees = []
        for pid in list(root_pids)[:10]:  # Limit to first 10 roots
            try:
                proc = psutil.Process(pid)
                trees.append({
                    'pid': pid,
                    'name': proc.name(),
                    'children': get_children(pid)
                })
            except:
                pass
        
        return trees
    
    def check_suspicious(self) -> list:
        """Check for suspicious processes"""
        suspicious = []
        
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
            try:
                name = proc.info['name'].lower()
                
                for susp in self.SUSPICIOUS_PROCESSES:
                    if susp in name:
                        suspicious.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'match': susp
                        })
                        break
            except:
                pass
        
        return suspicious
    
    def check_hidden_processes(self) -> list:
        """Check for potentially hidden processes (basic check)"""
        hidden = []
        
        # Compare WMI and psutil (Windows only)
        if os.name == 'nt':
            try:
                import subprocess
                # Get processes via WMIC
                output = subprocess.check_output(
                    ['wmic', 'process', 'get', 'processid'],
                    stderr=subprocess.DEVNULL
                ).decode()
                
                wmic_pids = set()
                for line in output.split('\n'):
                    line = line.strip()
                    if line.isdigit():
                        wmic_pids.add(int(line))
                
                # Get processes via psutil
                psutil_pids = set(p.pid for p in psutil.process_iter())
                
                # Find differences
                hidden_pids = wmic_pids - psutil_pids
                
                for pid in hidden_pids:
                    hidden.append({'pid': pid, 'reason': 'Not visible to psutil'})
            except:
                pass
        
        return hidden
    
    def monitor_new_processes(self, duration: int = 60, callback=None):
        """Monitor for new process creation"""
        self.monitoring = True
        self.baseline_processes = set(p.pid for p in psutil.process_iter())
        self.new_processes = []
        
        start_time = time.time()
        
        info(f"Monitoring for new processes for {duration} seconds...")
        info("Press Ctrl+C to stop")
        print()
        
        try:
            while self.monitoring and (time.time() - start_time) < duration:
                current = set(p.pid for p in psutil.process_iter())
                new_pids = current - self.baseline_processes
                
                for pid in new_pids:
                    try:
                        proc = psutil.Process(pid)
                        proc_info = {
                            'pid': pid,
                            'name': proc.name(),
                            'exe': proc.exe(),
                            'cmdline': ' '.join(proc.cmdline()),
                            'time': datetime.now().strftime("%H:%M:%S")
                        }
                        
                        with self.lock:
                            self.new_processes.append(proc_info)
                            self.baseline_processes.add(pid)
                        
                        # Print immediately
                        print(f"{G}[{proc_info['time']}]{RESET} New: {proc_info['name']} (PID: {pid})")
                        
                        if callback:
                            callback(proc_info)
                    except:
                        pass
                
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        
        self.monitoring = False
        return self.new_processes
    
    def get_network_connections(self, pid: int = None) -> list:
        """Get network connections for process or all"""
        connections = []
        
        try:
            if pid:
                proc = psutil.Process(pid)
                conns = proc.connections()
            else:
                conns = psutil.net_connections()
            
            for conn in conns:
                conn_info = {
                    'pid': conn.pid if hasattr(conn, 'pid') else pid,
                    'local': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "",
                    'remote': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "",
                    'status': conn.status,
                    'type': 'TCP' if conn.type == 1 else 'UDP'
                }
                connections.append(conn_info)
        except:
            pass
        
        return connections
    
    def print_processes(self, processes: list, limit: int = 20):
        """Print process list"""
        print(f"\n{C}{'═' * 80}{RESET}")
        print(f"{BRIGHT}RUNNING PROCESSES{RESET}")
        print(f"{C}{'═' * 80}{RESET}")
        
        # Sort by memory usage
        sorted_procs = sorted(processes, key=lambda x: x.get('memory_percent', 0), reverse=True)
        
        rows = []
        for proc in sorted_procs[:limit]:
            rows.append([
                str(proc.get('pid', '')),
                proc.get('name', '')[:20],
                proc.get('username', '-')[:15] if proc.get('username') else '-',
                f"{proc.get('cpu_percent', 0):.1f}%",
                f"{proc.get('memory_percent', 0):.1f}%",
                proc.get('status', '')
            ])
        
        print_table(["PID", "NAME", "USER", "CPU", "MEM", "STATUS"], rows, color="green")
        
        if len(processes) > limit:
            print(f"\n{Y}Showing {limit} of {len(processes)} processes{RESET}")


def interactive_mode():
    """Interactive mode for process monitoring"""
    print_banner("PROC MONITOR", color="red")
    
    monitor = ProcessMonitor()
    
    options = [
        "List All Processes",
        "Check Suspicious Processes",
        "Monitor New Process Creation",
        "View Process Details",
        "View Network Connections",
        "Process Tree"
    ]
    
    choice = menu_selector(options, "Select Option")
    
    if choice == 0:
        return
    
    elif choice == 1:
        processes = monitor.get_all_processes()
        monitor.print_processes(processes)
    
    elif choice == 2:
        suspicious = monitor.check_suspicious()
        
        if suspicious:
            warning(f"Found {len(suspicious)} suspicious processes:")
            for s in suspicious:
                print(f"  {R}[!]{RESET} {s['name']} (PID: {s['pid']}) - matches: {s['match']}")
        else:
            success("No known suspicious processes found")
    
    elif choice == 3:
        duration = int(prompt("Monitor duration (seconds)") or "60")
        new_procs = monitor.monitor_new_processes(duration)
        
        print(f"\n{G}Detected {len(new_procs)} new processes{RESET}")
    
    elif choice == 4:
        pid = int(prompt("Enter PID"))
        try:
            proc = psutil.Process(pid)
            print(f"\n{C}Process Details:{RESET}")
            print(f"  Name: {proc.name()}")
            print(f"  PID: {proc.pid}")
            print(f"  PPID: {proc.ppid()}")
            print(f"  Status: {proc.status()}")
            print(f"  User: {proc.username()}")
            print(f"  Exe: {proc.exe()}")
            print(f"  CWD: {proc.cwd()}")
            print(f"  Cmdline: {' '.join(proc.cmdline())}")
            print(f"  CPU: {proc.cpu_percent()}%")
            print(f"  Memory: {proc.memory_percent():.2f}%")
            print(f"  Threads: {proc.num_threads()}")
            print(f"  Created: {datetime.fromtimestamp(proc.create_time())}")
        except Exception as e:
            error(f"Failed to get process info: {e}")
    
    elif choice == 5:
        pid_input = prompt("Enter PID (or 'all')")
        
        if pid_input.lower() == 'all':
            connections = monitor.get_network_connections()
        else:
            connections = monitor.get_network_connections(int(pid_input))
        
        if connections:
            rows = []
            for conn in connections[:30]:
                rows.append([
                    str(conn['pid']),
                    conn['type'],
                    conn['local'],
                    conn['remote'],
                    conn['status']
                ])
            print_table(["PID", "TYPE", "LOCAL", "REMOTE", "STATUS"], rows)
        else:
            warning("No connections found")
    
    elif choice == 6:
        pid_input = prompt("Enter PID (or 'all' for roots)")
        
        def print_tree(node, indent=0):
            print(f"{'  ' * indent}{node['name']} (PID: {node['pid']})")
            for child in node.get('children', []):
                print_tree(child, indent + 1)
        
        if pid_input.lower() == 'all':
            trees = monitor.get_process_tree()
            for tree in trees:
                print_tree(tree)
                print()
        else:
            tree = monitor.get_process_tree(int(pid_input))
            if tree:
                print_tree(tree)
            else:
                error("Process not found")


if __name__ == "__main__":
    interactive_mode()
