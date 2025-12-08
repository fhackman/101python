# wifi_tool/cli.py
import sys
import argparse
import getpass
from pathlib import Path
from typing import List
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from core import WifiConnectionManager, AuditLogger, AUDIT_LOG_PATH


console = Console()


def cmd_init_vault(args):
    """Initialize encrypted vault"""
    from crypto import SecureVault
    vault = SecureVault()
    if vault.vault_path.exists() or vault.key_path.exists():
        console.print("[red]❌ Vault already exists. Delete 'output.txt.enc' and 'vault.key' to reset.[/]")
        return 1

    passphrase = Prompt.ask("Enter new vault passphrase", password=True)
    confirm = Prompt.ask("Confirm passphrase", password=True)
    if passphrase != confirm:
        console.print("[red]❌ Passphrases do not match.[/]")
        return 1

    if not passphrase:
        console.print("[yellow]⚠️ Empty passphrase not allowed.[/]")
        return 1

    if vault.initialize_vault(passphrase):
        console.print("[green]✅ Vault initialized successfully.[/]")
        console.print(f"   • Encrypted storage: {vault.vault_path}")
        console.print(f"   • Key (salt): {vault.key_path}")
        console.print("[dim]⚠️ Keep 'vault.key' secure. Without it, vault is unrecoverable.[/]")
        return 0
    else:
        console.print("[red]❌ Failed to initialize vault.[/]")
        return 1


def cmd_add_passwords(args):
    """Add passwords to vault (append)"""
    from crypto import SecureVault
    vault = SecureVault()
    if not vault.key_path.exists():
        console.print("[red]❌ Vault not initialized. Run 'init-vault' first.[/]")
        return 1

    passphrase = Prompt.ask("Enter vault passphrase", password=True)
    if not vault.unlock(passphrase):
        console.print("[red]❌ Incorrect passphrase.[/]")
        return 1

    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            console.print(f"[red]❌ File not found: {file_path}[/]")
            return 1
        try:
            passwords = file_path.read_text(encoding="utf-8").splitlines()
        except Exception as e:
            console.print(f"[red]❌ Failed to read file: {e}[/]")
            return 1
    else:
        console.print("[dim]Enter passwords (one per line). Press Ctrl+D (Linux/Mac) or Ctrl+Z+Enter (Windows) to finish:[/]")
        passwords = []
        try:
            while True:
                pwd = input("> ").strip()
                if pwd:
                    passwords.append(pwd)
        except EOFError:
            pass

    if not passwords:
        console.print("[yellow]⚠️ No passwords provided.[/]")
        return 0

    vault.add_passwords(passwords)
    console.print(f"[green]✅ Added {len(passwords)} password(s) to vault.[/]")
    return 0


def cmd_list_interfaces(args):
    mgr = WifiConnectionManager()
    interfaces = mgr.get_interface_names()
    if not interfaces:
        console.print("[red]❌ No Wi-Fi interfaces found.[/]")
        return 1
    table = Table(title="📡 Wi-Fi Interfaces")
    table.add_column("#", style="cyan", justify="right")
    table.add_column("Name")
    for i, name in enumerate(interfaces):
        table.add_column()
        table.add_row(str(i), name)
    console.print(table)
    return 0


def cmd_scan(args):
    mgr = WifiConnectionManager()
    idx = args.interface
    if idx < 0 or idx >= len(mgr.interfaces):
        console.print(f"[red]❌ Invalid interface index: {idx}[/]")
        return 1

    console.print(f"[blue]🔍 Scanning on [bold]{mgr.interfaces[idx].name()}[/]...[/]")
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        task = progress.add_task("Scanning...", total=None)
        ssids = mgr.scan_blocking(idx)
        progress.update(task, completed=True)

    if not ssids:
        console.print("[yellow]⚠️ No networks found.[/]")
        return 0

    table = Table(title=f"📶 Networks (Interface #{idx})")
    table.add_column("#", style="dim", justify="right")
    table.add_column("SSID", style="green")
    for i, ssid in enumerate(ssids):
        table.add_row(str(i), ssid)
    console.print(table)
    return 0


def cmd_connect(args):
    mgr = WifiConnectionManager()
    idx = args.interface
    ssid = args.ssid

    if idx < 0 or idx >= len(mgr.interfaces):
        console.print("[red]❌ Invalid interface index.[/]")
        return 1

    # Unlock vault if needed
    if not args.no_vault:
        if not mgr.vault.key_path.exists():
            console.print("[yellow]💡 Vault not initialized. Skipping password use.[/]")
        else:
            passphrase = Prompt.ask("Enter vault passphrase (or leave empty to skip)", password=True, default="")
            if passphrase:
                if mgr.unlock_vault(passphrase):
                    console.print("[green]✅ Vault unlocked.[/]")
                else:
                    console.print("[red]❌ Failed to unlock vault — passwords will not be used.[/]")
            else:
                console.print("[dim]🔒 Vault remains locked — using open-network only.[/]")

    AuditLogger.connection_attempt(
        ssid=ssid,
        interface=mgr.interfaces[idx].name(),
        method="BRUTEFORCE" if mgr.is_vault_unlocked() else "OPEN_ONLY"
    )

    console.print(f"[blue]🔗 Connecting to '[bold]{ssid}[/]'...[/]")
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        task = progress.add_task("Attempting connection...", total=None)
        success, password = mgr.connect(idx, ssid)
        pwd_len = len(password) if password else 0
        AuditLogger.connection_result(ssid, success, pwd_len)
        progress.update(task, completed=True)

    if success:
        msg = f"[green]✅ Connected to '[bold]{ssid}[/]'[/]"
        if pwd_len:
            msg += f"\n🔑 Password length: {pwd_len} chars (redacted)"
        console.print(msg)
        return 0
    else:
        console.print(f"[red]❌ Failed to connect to '[bold]{ssid}[/]'[/]")
        if not mgr.is_vault_unlocked():
            console.print("[dim]💡 Vault is locked — no passwords were tried.[/]")
        return 1


def cmd_audit(args):
    if not AUDIT_LOG_PATH.exists():
        console.print("[yellow]No audit log found.[/]")
        return 0

    lines = AUDIT_LOG_PATH.read_text(encoding="utf-8").strip().split("\n")
    if not lines or lines == [""]:
        console.print("[yellow]Audit log is empty.[/]")
        return 0

    table = Table(title="📜 Audit Log (Latest 15 Entries)", show_lines=True, highlight=True)
    table.add_column("Time (UTC)", style="dim", width=12)
    table.add_column("Event", style="cyan", width=15)
    table.add_column("Details")

    for line in lines[-15:]:
        try:
            entry = __import__("json").loads(line)
            ts = entry["timestamp"].split("T")[1].split(".")[0].split("+")[0]
            etype = entry["event_type"]
            details = entry["details"]

            if etype == "CONNECTION_RESULT":
                status = "✅ SUCCESS" if details["success"] else "❌ FAIL"
                detail_str = f"SSID: {details['ssid']}"
                if details.get("password_length"):
                    detail_str += f" | PwdLen: {details['password_length']}"
                table.add_row(ts, status, detail_str)
            elif etype == "VAULT_UNLOCK":
                status = "🔓 UNLOCKED" if details["success"] else "🔒 FAILED"
                table.add_row(ts, status, "")
            else:
                table.add_row(ts, etype, str(details))
        except Exception as e:
            table.add_row(ts, "PARSE_ERR", f"[red]{e}[/]")

    console.print(table)
    return 0


def run_cli():
    AuditLogger.tool_start("CLI")

    parser = argparse.ArgumentParser(
        prog="wifi-tool",
        description="🔐 Professional Wi-Fi Audit Tool — CLI & GUI",
        epilog="⚠️ Use only on authorized networks. All actions are logged immutably."
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Sub-commands")

    # init-vault
    parser_init = subparsers.add_parser("init-vault", help="Initialize encrypted password vault")
    
    # add-passwords
    parser_add = subparsers.add_parser("add-passwords", help="Add passwords to vault")
    parser_add.add_argument("--file", "-f", help="File with passwords (one per line)")

    # interfaces
    parser_if = subparsers.add_parser("interfaces", help="List Wi-Fi interfaces")

    # scan
    parser_scan = subparsers.add_parser("scan", help="Scan for networks")
    parser_scan.add_argument("--interface", "-i", type=int, default=0, help="Interface index")

    # connect
    parser_conn = subparsers.add_parser("connect", help="Connect to network")
    parser_conn.add_argument("--interface", "-i", type=int, default=0, help="Interface index")
    parser_conn.add_argument("--ssid", "-s", required=True, help="SSID to connect to")
    parser_conn.add_argument("--no-vault", action="store_true", help="Skip vault unlock prompt")

    # audit
    parser_audit = subparsers.add_parser("audit", help="View audit log")

    args = parser.parse_args()

    try:
        if args.command == "init-vault":
            return cmd_init_vault(args)
        elif args.command == "add-passwords":
            return cmd_add_passwords(args)
        elif args.command == "interfaces":
            return cmd_list_interfaces(args)
        elif args.command == "scan":
            return cmd_scan(args)
        elif args.command == "connect":
            return cmd_connect(args)
        elif args.command == "audit":
            return cmd_audit(args)
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Aborted by user.[/]")
        return 130
    except Exception as e:
        console.print(f"[red]💥 Critical error: {e}[/]")
        return 2


if __name__ == "__main__":
    sys.exit(run_cli())