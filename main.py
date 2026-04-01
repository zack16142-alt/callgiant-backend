#!/usr/bin/env python3
"""
CallGiant — Automated Calling System

Launch the GUI application.

Usage:
    python main.py

Build standalone .exe:
    pip install pyinstaller
    pyinstaller --onefile --noconsole --name CallGiant main.py

Dependencies (install once):
    pip install -r requirements.txt
"""

import sys
import os
import traceback


def main():
    # When frozen by PyInstaller, ensure the working directory is next
    # to the .exe so the SQLite database is found / created there.
    if getattr(sys, "frozen", False):
        os.chdir(os.path.dirname(sys.executable))

    import tkinter as tk
    from app import CallGiantApp

    root = tk.Tk()
    root.iconname("CallGiant")
    CallGiantApp(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # With --noconsole there's no terminal, so show a GUI error dialog
        error_text = traceback.format_exc()
        try:
            import tkinter as tk
            from tkinter import messagebox
            _root = tk.Tk()
            _root.withdraw()
            messagebox.showerror(
                "CallGiant — Startup Error",
                f"The application failed to start.\n\n{error_text}",
            )
            _root.destroy()
        except Exception:
            pass
        sys.exit(1)
