# Core Responsibility: Process Supervisor & Lifecycle Manager

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Alpha Sovereign Organism - Launcher Module
==========================================
File: alpha_launcher.py
Version: 1.0.0 (Ignition Edition)
Responsibility: Pillar 2 - Lifecycle (System Supervisor & Process Orchestrator)
Author: Chief System Architect (AI)

Description:
The 'Awakening Gateway'. This module is responsible for:
1. Validating the environment and configuration integrity.
2. Launching the Rust Engine (The Muscle).
3. Launching the Python Brain (The Cognitive Core).
4. Launching the Flutter UI (The Dashboard).
5. Monitoring heartbeats and handling graceful shutdowns.
"""

import os
import sys
import time
import signal
import subprocess
import logging
import threading
from pathlib import Path
from typing import List, Optional, Dict

# --- Configuration & Styling ---
ROOT_DIR = Path(r"F:\win10\alpha")
LOG_FORMAT = '%(asctime)s | LAUNCHER | %(levelname)s | %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("AlphaIgnition")

# ANSI Colors for Terminal Output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

class Launcher:
    """
    The Supervisor Class.
    Manages the lifecycle of the entire Sovereign Organism.
    """

    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.running = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Catch Ctrl+C and termination signals to ensure clean shutdown."""
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def _log_status(self, component: str, status: str, level="INFO"):
        msg = f"[{component}] -> {status}"
        if level == "INFO":
            print(f"{Colors.OKGREEN}{msg}{Colors.ENDC}")
            logger.info(msg)
        elif level == "ERROR":
            print(f"{Colors.FAIL}{msg}{Colors.ENDC}")
            logger.error(msg)
        elif level == "WARN":
            print(f"{Colors.WARNING}{msg}{Colors.ENDC}")
            logger.warning(msg)

    def verify_integrity(self) -> bool:
        """
        Pre-flight checklist. Checks if critical paths and compilers exist.
        """
        print(f"{Colors.HEADER}--- Alpha Pre-flight Checklist ---{Colors.ENDC}")
        
        checks = [
            ("Brain Core", ROOT_DIR / "brain/brain_router.py"),
            ("Engine Config", ROOT_DIR / "engine/Cargo.toml"),
            ("UI Entry", ROOT_DIR / "ui/lib/main.dart"),
            ("Genetic Config", ROOT_DIR / "alpha_genesis.py"),
        ]

        all_passed = True
        for name, path in checks:
            if path.exists():
                self._log_status("CHECK", f"{name}: DETECTED", "INFO")
            else:
                self._log_status("CHECK", f"{name}: MISSING at {path}", "ERROR")
                all_passed = False
        
        # Check for Rust/Cargo
        try:
            subprocess.run(["cargo", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._log_status("TOOLCHAIN", "Rust/Cargo: ONLINE", "INFO")
        except FileNotFoundError:
            self._log_status("TOOLCHAIN", "Rust/Cargo: NOT FOUND (Engine cannot start)", "ERROR")
            all_passed = False

        return all_passed

    def _start_process(self, name: str, command: List[str], cwd: Path) -> Optional[subprocess.Popen]:
        """
        Generic process starter with error handling.
        """
        try:
            self._log_status("IGNITION", f"Starting {name}...", "WARN")
            proc = subprocess.Popen(
                command,
                cwd=str(cwd),
                shell=True if os.name == 'nt' else False, # Windows specific
                # We do not capture stdout/stderr here to let them flow to the main console
                # In production, these should be piped to separate log files.
            )
            self.processes[name] = proc
            return proc
        except Exception as e:
            self._log_status("FAIL", f"Could not start {name}: {e}", "ERROR")
            return None

    def ignite_engine(self):
        """Starts the Rust Execution Engine."""
        # Using 'cargo run' for dev. In prod, this should point to target/release/alpha_engine.exe
        cmd = ["cargo", "run", "--quiet"] 
        self._start_process("ENGINE", cmd, cwd=ROOT_DIR / "engine")

    def ignite_brain(self):
        """Starts the Python Cognitive Core."""
        python_exec = sys.executable
        # Assuming brain_router.py is the entry point
        cmd = [python_exec, "brain/brain_router.py"]
        self._start_process("BRAIN", cmd, cwd=ROOT_DIR)

    def ignite_ui(self):
        """Starts the Flutter Dashboard."""
        # Runs flutter as a windows desktop app
        cmd = ["flutter", "run", "-d", "windows"]
        self._start_process("UI", cmd, cwd=ROOT_DIR / "ui")

    def ignite_shield(self):
        """Starts background security services (mock implementation for now)."""
        # Could be a Docker container or a separate watcher script
        pass 

    def monitor(self):
        """
        The Heartbeat Loop. Monitors child processes.
        If a critical component dies, it triggers a system-wide shutdown.
        """
        self.running = True
        print(f"\n{Colors.BOLD}=== ALPHA SOVEREIGN ORGANISM IS ALIVE ==={Colors.ENDC}\n")
        
        while self.running:
            critical_failure = False
            
            for name, proc in self.processes.items():
                ret_code = proc.poll()
                if ret_code is not None:
                    self._log_status("MONITOR", f"{name} DIED unexpectedly with code {ret_code}", "ERROR")
                    critical_failure = True
            
            if critical_failure:
                self._log_status("SYSTEM", "CRITICAL FAILURE DETECTED. INITIATING EMERGENCY SHUTDOWN.", "ERROR")
                self.shutdown(None, None)
                break
            
            time.sleep(2) # Pulse check every 2 seconds

    def shutdown(self, signum, frame):
        """
        Graceful Shutdown Protocol.
        """
        if not self.running: return
        self.running = False
        
        print(f"\n{Colors.WARNING}--- INITIATING SHUTDOWN PROTOCOL ---{Colors.ENDC}")
        
        for name, proc in self.processes.items():
            if proc.poll() is None: # If still running
                self._log_status("SHUTDOWN", f"Terminating {name}...", "WARN")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._log_status("SHUTDOWN", f"Force killing {name}...", "ERROR")
                    proc.kill()
        
        print(f"{Colors.HEADER}=== SYSTEM OFFLINE ==={Colors.ENDC}")
        sys.exit(0)

def main():
    launcher = Launcher()
    
    # Step 1: Verification
    if not launcher.verify_integrity():
        print(f"{Colors.FAIL}Integrity Check Failed. Aborting Launch.{Colors.ENDC}")
        sys.exit(1)

    # Step 2: Ignition Sequence
    # Order matters: Engine first (Data layer), then Brain (Logic), then UI (View)
    
    launcher.ignite_engine()
    time.sleep(2) # Give Engine a moment to bind ports (ZeroMQ)
    
    launcher.ignite_brain()
    time.sleep(1) # Give Brain a moment to connect to Engine
    
    launcher.ignite_ui()
    
    # Step 3: Monitor
    try:
        launcher.monitor()
    except KeyboardInterrupt:
        launcher.shutdown(None, None)

if __name__ == "__main__":
    main()