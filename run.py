# run.py
#!/usr/bin/env python3
import sys
import os
from core import AuditLogger


def main():
    AuditLogger.tool_start("AUTO")

    # Auto-detect mode:
    # - If no args & Windows & interactive → GUI
    # - Else → CLI
    if (
        len(sys.argv) == 1
        and sys.stdin.isatty()
        and os.name == "nt"
        and "NO_GUI" not in os.environ
    ):
        try:
            from gui import WifiToolGUI
            import tkinter as tk
            root = tk.Tk()
            app = WifiToolGUI(root)
            root.mainloop()
        except ImportError as e:
            print(f"GUI dependencies missing: {e}", file=sys.stderr)
            print("Falling back to CLI...", file=sys.stderr)
            from cli import run_cli
            sys.exit(run_cli())
    else:
        from cli import run_cli
        sys.exit(run_cli())


if __name__ == "__main__":
    main()