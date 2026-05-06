#!/usr/bin/env python3
"""
Interactive Script Menu System for Ride Optimizer
Provides easy access to all utility scripts organized by category.
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
        self.categories: Dict[str, List[Tuple[str, str, str]]] = {
            "Testing & Validation": [
                ("run_tests.sh all", "Run all tests", "shell"),
                ("run_tests.sh unit", "Run unit tests only", "shell"),
                ("run_tests.sh integration", "Run integration tests only", "shell"),
                ("run_tests.sh coverage", "Run tests with coverage report", "shell"),
                ("run_tests.sh quick", "Run quick tests (exclude slow)", "shell"),
                ("test_imports.py", "Verify all imports work", "python"),
                ("verify_dependencies.py", "Check dependencies installed", "python"),
            ],
            "Feature Testing": [
                ("test_geocoding.py", "Test geocoding functionality", "python"),
                ("test_long_ride_recommendations.py", "Test long ride analysis", "python"),
                ("test_long_rides_feature.py", "Test long rides feature", "python"),
                ("test_next_commute.py", "Test next commute feature", "python"),
                ("test_route_naming.py", "Test route naming", "python"),
                ("test_sport_type_fix.py", "Test sport type fix", "python"),
                ("test_uses_count.py", "Test uses count feature", "python"),
                ("test_analyze_no_hang.py", "Test analysis doesn't hang", "python"),
            ],
            "Debugging & Diagnostics": [
                ("debug_route_matching.py", "Debug route matching issues", "python"),
                ("debug_sport_type.py", "Debug sport type issues", "python"),
                ("diagnose_long_rides.py", "Diagnose long rides issues", "python"),
                ("check_old_school_routes.py", "Check Old School route grouping", "python"),
                ("profile_analysis.py", "Profile application performance", "python"),
            ],
            "Data & Analysis": [
                ("fetch_test_activities.py", "Fetch test activities from Strava", "python"),
                ("find_matched_routes.py", "Find and analyze matched routes", "python"),
                ("set_rate_limit_block.py", "Set rate limit block", "python"),
            ],
            "GitHub Integration": [
                ("create_issues.sh", "Create GitHub issues", "shell"),
                ("create_p2_issues.sh", "Create P2 issues", "shell"),
                ("sync_todos_to_issues.sh", "Sync TODOs to GitHub issues", "shell"),
            ],
            "Application": [
                ("run_with_weasyprint.sh", "Run app with WeasyPrint PDF", "shell"),
                ("main.py", "Run main application", "python"),
            ],
        }
    
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('clear' if os.name != 'nt' else 'cls')
    
    def print_header(self):
        """Print the menu header."""
        print(f"\n{Color.BOLD}{Color.CYAN}{'=' * 70}{Color.END}")
        print(f"{Color.BOLD}{Color.CYAN}🚴 Ride Optimizer - Script Menu System{Color.END}")
        print(f"{Color.BOLD}{Color.CYAN}{'=' * 70}{Color.END}\n")
    
    def print_category_menu(self):
        """Print the main category menu."""
        self.print_header()
        print(f"{Color.BOLD}Select a category:{Color.END}\n")
        
        categories = list(self.categories.keys())
        for idx, category in enumerate(categories, 1):
            icon = self._get_category_icon(category)
            print(f"  {Color.GREEN}{idx}.{Color.END} {icon} {category}")
        
        print(f"\n  {Color.YELLOW}0.{Color.END} 🚪 Exit")
        print()
    
    def print_script_menu(self, category: str):
        """Print scripts in a category."""
        self.clear_screen()
        self.print_header()
        
        icon = self._get_category_icon(category)
        print(f"{Color.BOLD}{icon} {category}{Color.END}\n")
        
        scripts = self.categories[category]
        for idx, (script, description, script_type) in enumerate(scripts, 1):
            type_icon = "🐍" if script_type == "python" else "🐚"
            print(f"  {Color.GREEN}{idx}.{Color.END} {type_icon} {description}")
            print(f"      {Color.CYAN}→ {script}{Color.END}")
        
        print(f"\n  {Color.YELLOW}0.{Color.END} ⬅️  Back to categories")
        print()
    
    def _get_category_icon(self, category: str) -> str:
        """Get icon for category."""
        icons = {
            "Testing & Validation": "🧪",
            "Feature Testing": "✨",
            "Debugging & Diagnostics": "🔍",
            "Data & Analysis": "📊",
            "GitHub Integration": "🐙",
            "Application": "🚀",
        }
        return icons.get(category, "📁")
    
    def run_script(self, script: str, script_type: str) -> bool:
        """Run a script and return success status."""
        print(f"\n{Color.BOLD}{Color.BLUE}{'=' * 70}{Color.END}")
        print(f"{Color.BOLD}Running: {script}{Color.END}")
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
    
    def get_user_choice(self, max_choice: int) -> Optional[int]:
        """Get and validate user input."""
        try:
            choice = input(f"{Color.BOLD}Enter your choice (0-{max_choice}): {Color.END}").strip()
            
            if not choice.isdigit():
                print(f"{Color.RED}❌ Please enter a number{Color.END}")
                return None
            
            choice_num = int(choice)
            if choice_num < 0 or choice_num > max_choice:
                print(f"{Color.RED}❌ Invalid choice. Please enter 0-{max_choice}{Color.END}")
                return None
            
            return choice_num
            
        except KeyboardInterrupt:
            print(f"\n{Color.YELLOW}Exiting...{Color.END}")
            sys.exit(0)
    
    def wait_for_continue(self):
        """Wait for user to press enter."""
        try:
            input(f"\n{Color.BOLD}Press Enter to continue...{Color.END}")
        except KeyboardInterrupt:
            print(f"\n{Color.YELLOW}Exiting...{Color.END}")
            sys.exit(0)
    
    def run(self):
        """Run the interactive menu system."""
        while True:
            self.clear_screen()
            self.print_category_menu()
            
            categories = list(self.categories.keys())
            choice = self.get_user_choice(len(categories))
            
            if choice is None:
                continue
            
            if choice == 0:
                print(f"\n{Color.GREEN}👋 Goodbye!{Color.END}\n")
                break
            
            # Show scripts in selected category
            category = categories[choice - 1]
            
            while True:
                self.print_script_menu(category)
                scripts = self.categories[category]
                
                script_choice = self.get_user_choice(len(scripts))
                
                if script_choice is None:
                    continue
                
                if script_choice == 0:
                    break
                
                # Run selected script
                script, description, script_type = scripts[script_choice - 1]
                self.clear_screen()
                self.run_script(script, script_type)
                self.wait_for_continue()


def main():
    """Main entry point."""
    menu = ScriptMenu()
    menu.run()


if __name__ == "__main__":
    main()

# Made with Bob
