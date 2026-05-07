#!/usr/bin/env python3
"""
Interactive Script Menu System for Ride Optimizer
Single-screen menu with all options visible at once.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class Color:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class ScriptMenu:
    """Interactive menu system for running project scripts."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.scripts_dir = self.project_root / "scripts"
        
        # Define script categories and their scripts
        # Format: (script_name, description, script_type)
        self.categories: Dict[str, List[Tuple[str, str, str]]] = {
            "Testing & Validation": [
                ("run_tests.sh all", "Run all tests", "shell"),
                ("run_tests.sh unit", "Run unit tests only", "shell"),
                ("run_tests.sh integration", "Run integration tests only", "shell"),
                ("run_tests.sh coverage", "Run tests with coverage report", "shell"),
                ("run_tests.sh quick", "Run quick tests (exclude slow)", "shell"),
                ("test_imports.py", "Verify all imports work", "python"),
                ("verify_dependencies.py", "Check dependencies installed", "python"),
                ("test_trainerroad_integration.py", "Test TrainerRoad integration", "python"),
            ],
            "GitHub Integration": [
                ("sync_todos_to_issues.sh", "Sync TODOs to GitHub issues", "shell"),
                ("update-issue-priorities.sh", "Update issue priorities", "shell"),
            ],
            "Data Management": [
                ("set_rate_limit_block.py", "Set rate limit block", "python"),
                ("migrate_cache_to_json_storage.py", "Migrate cache to JSON storage", "python"),
                ("migrate_to_json.py", "Migrate data to JSON", "python"),
            ],
            "Application": [
                ("run_with_weasyprint.sh", "Run app with WeasyPrint PDF", "shell"),
            ],
        }
        
        # Build flat list of all scripts with their categories
        self.script_list = []
        for category, scripts in self.categories.items():
            for script, description, script_type in scripts:
                self.script_list.append((category, script, description, script_type))
    
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('clear' if os.name != 'nt' else 'cls')
    
    def print_menu(self):
        """Print the complete menu with all options."""
        self.clear_screen()
        
        # Header
        print(f"\n{Color.BOLD}{Color.CYAN}{'=' * 70}{Color.END}")
        print(f"{Color.BOLD}{Color.CYAN}🚴 RIDE OPTIMIZER - SCRIPT MENU{Color.END}")
        print(f"{Color.BOLD}{Color.CYAN}{'=' * 70}{Color.END}\n")
        
        # Print all categories and scripts
        choice_num = 1
        current_category = None
        
        for category, script, description, script_type in self.script_list:
            # Print category header when it changes
            if category != current_category:
                if current_category is not None:
                    print()  # Blank line between categories
                print(f"{Color.BOLD}{Color.YELLOW}=== {category} ==={Color.END}")
                current_category = category
            
            # Print script option
            type_icon = "🐍" if script_type == "python" else "🐚"
            print(f"  {Color.GREEN}{choice_num:2d}.{Color.END} {type_icon} {description}")
            choice_num += 1
        
        # Footer with quit option
        print(f"\n{Color.BOLD}{Color.YELLOW}{'=' * 70}{Color.END}")
        print(f"  {Color.RED} 0.{Color.END} 🚪 Exit")
        print(f"  {Color.RED} q.{Color.END} 🚪 Quit")
        print(f"{Color.BOLD}{Color.YELLOW}{'=' * 70}{Color.END}\n")
    
    def run_script(self, script: str, script_type: str, description: str) -> bool:
        """Run a script and return success status."""
        print(f"\n{Color.BOLD}{Color.BLUE}{'=' * 70}{Color.END}")
        print(f"{Color.BOLD}Running: {description}{Color.END}")
        print(f"{Color.CYAN}Command: {script}{Color.END}")
        print(f"{Color.BOLD}{Color.BLUE}{'=' * 70}{Color.END}\n")
        
        try:
            if script_type == "python":
                # Run Python script
                if script == "main.py":
                    cmd = [sys.executable, str(self.project_root / script)]
                else:
                    cmd = [sys.executable, str(self.scripts_dir / script)]
            else:
                # Run shell script
                script_path = self.scripts_dir / script
                if not script_path.exists():
                    print(f"{Color.RED}❌ Script not found: {script_path}{Color.END}")
                    return False
                
                # Make executable if not already
                os.chmod(script_path, 0o755)
                cmd = [str(script_path)]
            
            # Run the command
            result = subprocess.run(cmd, cwd=str(self.project_root))
            
            print(f"\n{Color.BOLD}{Color.BLUE}{'=' * 70}{Color.END}")
            if result.returncode == 0:
                print(f"{Color.GREEN}✅ Script completed successfully{Color.END}")
            else:
                print(f"{Color.RED}❌ Script exited with code {result.returncode}{Color.END}")
            print(f"{Color.BOLD}{Color.BLUE}{'=' * 70}{Color.END}\n")
            
            return result.returncode == 0
            
        except KeyboardInterrupt:
            print(f"\n\n{Color.YELLOW}⚠️  Script interrupted by user{Color.END}")
            return False
        except Exception as e:
            print(f"\n{Color.RED}❌ Error running script: {e}{Color.END}")
            return False
    
    def get_user_choice(self) -> Optional[int]:
        """Get and validate user input."""
        try:
            choice = input(f"{Color.BOLD}Enter choice (0 to quit): {Color.END}").strip().lower()
            
            # Handle quit commands
            if choice in ('0', 'q', 'quit', 'exit'):
                return 0
            
            if not choice.isdigit():
                print(f"{Color.RED}❌ Please enter a number or 'q' to quit{Color.END}")
                return None
            
            choice_num = int(choice)
            if choice_num < 0 or choice_num > len(self.script_list):
                print(f"{Color.RED}❌ Invalid choice. Please enter 1-{len(self.script_list)} or 0 to quit{Color.END}")
                return None
            
            return choice_num
            
        except KeyboardInterrupt:
            print(f"\n{Color.YELLOW}Exiting...{Color.END}")
            return 0
    
    def wait_for_continue(self):
        """Wait for user to press enter."""
        try:
            input(f"\n{Color.BOLD}Press Enter to continue...{Color.END}")
        except KeyboardInterrupt:
            print(f"\n{Color.YELLOW}Returning to menu...{Color.END}")
    
    def run(self):
        """Run the interactive menu system."""
        while True:
            self.print_menu()
            
            choice = self.get_user_choice()
            
            if choice is None:
                self.wait_for_continue()
                continue
            
            if choice == 0:
                print(f"\n{Color.GREEN}👋 Goodbye!{Color.END}\n")
                break
            
            # Run selected script
            category, script, description, script_type = self.script_list[choice - 1]
            self.clear_screen()
            self.run_script(script, script_type, description)
            self.wait_for_continue()


def main():
    """Main entry point."""
    menu = ScriptMenu()
    menu.run()


if __name__ == "__main__":
    main()

# Made with Bob
