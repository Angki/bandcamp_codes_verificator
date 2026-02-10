#!/usr/bin/env python3
"""
Bandcamp Code Verificator - CLI Interface
Command-line tool for verifying Bandcamp download codes.
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
    from rich.table import Table
    from rich import print as rprint
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: 'rich' library not installed. Install it for better CLI experience: pip install rich")

from app.verificator import BandcampVerificator
from app.utils import (
    read_codes_from_file,
    write_results_to_csv,
    write_results_to_json,
    sanitize_codes,
)
from app.config import Config
from app.logger import logger


class CLI:
    """Command-line interface for Bandcamp Code Verificator."""
    
    def __init__(self):
        """Initialize CLI."""
        self.console = Console() if RICH_AVAILABLE else None
        self.stop_requested = False
    
    def print(self, message: str, style: Optional[str] = None):
        """Print message with optional styling.
        
        Args:
            message: Message to print
            style: Rich style (if available)
        """
        if RICH_AVAILABLE and style:
            self.console.print(message, style=style)
        else:
            print(message)
    
    def verify_command(self, args):
        """Execute verify command.
        
        Args:
            args: Parsed command-line arguments
        """
        # Read codes
        try:
            if args.input:
                self.print(f"Reading codes from: {args.input}", "cyan")
                codes = read_codes_from_file(args.input)
            elif args.codes:
                codes = sanitize_codes(args.codes)
            else:
                self.print("Error: Either --input or --codes is required", "red bold")
                sys.exit(1)
            
            if not codes:
                self.print("Error: No codes found", "red bold")
                sys.exit(1)
            
            if len(codes) > Config.MAX_CODES:
                self.print(f"Error: Too many codes ({len(codes)}). Maximum is {Config.MAX_CODES}", "red bold")
                sys.exit(1)
            
            self.print(f"Found {len(codes)} code(s) to verify", "green")
        
        except FileNotFoundError as e:
            self.print(f"Error: {e}", "red bold")
            sys.exit(1)
        except Exception as e:
            self.print(f"Error reading codes: {e}", "red bold")
            sys.exit(1)
        
        # Get credentials
        crumb = args.crumb
        client_id = args.client_id
        session = args.session
        
        # Interactive prompts if not provided
        if not crumb:
            crumb = input("Enter crumb: ").strip()
        if not client_id:
            client_id = input("Enter client_id: ").strip()
        if not session:
            session = input("Enter session: ").strip()
        
        if not all([crumb, client_id, session]):
            self.print("Error: All credentials (crumb, client_id, session) are required", "red bold")
            sys.exit(1)
        
        # Dry run check
        if args.dry_run:
            self.print("\n[DRY RUN] Would verify the following codes:", "yellow bold")
            for idx, code in enumerate(codes[:10], 1):  # Show first 10
                self.print(f"  {idx}. {code}", "yellow")
            if len(codes) > 10:
                self.print(f"  ... and {len(codes) - 10} more", "yellow")
            self.print(f"\nOutput would be saved to: {args.output}", "yellow")
            return
        
        # Initialize verificator
        try:
            verificator = BandcampVerificator(
                crumb=crumb,
                client_id=client_id,
                session=session,
            )
        except ValueError as e:
            self.print(f"Error: {e}", "red bold")
            sys.exit(1)
        
        # Verify codes with progress
        results = []
        
        if RICH_AVAILABLE:
            # Rich progress bar
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=self.console,
            ) as progress:
                task = progress.add_task("Verifying codes...", total=len(codes))
                
                def progress_callback(current, total, result):
                    progress.update(task, completed=current)
                    if args.verbose:
                        status = "✓" if result["success"] else "✗"
                        self.console.print(
                            f"{status} [{current}/{total}] {result['code'][:30]} - "
                            f"HTTP {result['status']} ({result['elapsed_ms']:.0f}ms)"
                        )
                
                results = verificator.verify_batch(
                    codes,
                    progress_callback=progress_callback,
                )
        else:
            # Simple progress
            def progress_callback(current, total, result):
                if args.verbose or current % 10 == 0:  # Show every 10th
                    status = "OK" if result["success"] else "FAIL"
                    print(f"[{current}/{total}] {result['code'][:30]} - {status}")
            
            results = verificator.verify_batch(
                codes,
                progress_callback=progress_callback,
            )
        
        verificator.close()
        
        # Display summary
        self.print("\n" + "=" * 60, "cyan")
        self.print("VERIFICATION SUMMARY", "cyan bold")
        self.print("=" * 60, "cyan")
        
        success_count = sum(1 for r in results if r["success"])
        fail_count = len(results) - success_count
        
        self.print(f"Total codes: {len(results)}", "white")
        self.print(f"Successful: {success_count}", "green")
        self.print(f"Failed: {fail_count}", "red")
        
        # Save results
        if args.output:
            try:
                if args.format == "csv":
                    write_results_to_csv(results, args.output)
                    self.print(f"\nResults saved to: {args.output}", "green bold")
                elif args.format == "json":
                    write_results_to_json(results, args.output)
                    self.print(f"\nResults saved to: {args.output}", "green bold")
            except Exception as e:
                self.print(f"Error saving results: {e}", "red bold")
        
        # Display sample results if verbose
        if args.verbose and RICH_AVAILABLE:
            self.print("\nSample Results:", "cyan bold")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Code", style="cyan", width=30)
            table.add_column("Status", justify="center", width=10)
            table.add_column("Success", justify="center", width=10)
            table.add_column("Time", justify="right", width=12)
            
            for result in results[:10]:  # Show first 10
                status_color = "green" if result["success"] else "red"
                table.add_row(
                    result["code"][:28] + "..." if len(result["code"]) > 30 else result["code"],
                    f"[{status_color}]{result['status']}[/{status_color}]",
                    "✓" if result["success"] else "✗",
                    f"{result['elapsed_ms']:.0f}ms",
                )
            
            self.console.print(table)
            if len(results) > 10:
                self.print(f"... and {len(results) - 10} more results", "dim")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Bandcamp Code Verificator - Verify Bandcamp download codes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify codes from file
  python cli.py verify --input codes.txt --output results.csv
  
  # With credentials provided
  python cli.py verify --input codes.txt --crumb "..." --client-id "..." --session "..." --output results.csv
  
  # JSON output format
  python cli.py verify --input codes.txt --output results.json --format json
  
  # Verbose mode
  python cli.py verify --input codes.txt --output results.csv --verbose
  
  # Dry run (test without actually verifying)
  python cli.py verify --input codes.txt --output results.csv --dry-run
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify Bandcamp codes")
    
    # Input options
    input_group = verify_parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--input", "-i",
        help="Path to text file containing codes (one per line)"
    )
    input_group.add_argument(
        "--codes", "-c",
        help="Codes as string (separated by newlines)"
    )
    
    # Credentials
    verify_parser.add_argument(
        "--crumb",
        help="API crumb (will prompt if not provided)"
    )
    verify_parser.add_argument(
        "--client-id",
        help="Client ID cookie (will prompt if not provided)"
    )
    verify_parser.add_argument(
        "--session",
        help="Session cookie (will prompt if not provided)"
    )
    
    # Output options
    verify_parser.add_argument(
        "--output", "-o",
        help="Output file path (default: results.csv)",
        default="results.csv"
    )
    verify_parser.add_argument(
        "--format", "-f",
        choices=["csv", "json"],
        default="csv",
        help="Output format (default: csv)"
    )
    
    # Other options
    verify_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    verify_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run (don't actually verify)"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    cli = CLI()
    
    if args.command == "verify":
        cli.verify_command(args)


if __name__ == "__main__":
    main()
