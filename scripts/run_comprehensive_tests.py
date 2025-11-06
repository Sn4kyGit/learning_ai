#!/usr/bin/env python3
"""
Comprehensive test runner for the Local Business Intelligence Bot.

This script runs all test suites including unit, integration, e2e, 
performance, and deployment tests with proper reporting.
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path
from typing import Dict, List, Any
import argparse


class TestRunner:
    """Comprehensive test runner with reporting and metrics."""
    
    def __init__(self, verbose: bool = False, coverage: bool = True):
        self.verbose = verbose
        self.coverage = coverage
        self.results = {}
        self.start_time = time.time()
        
        # Test suite configurations
        self.test_suites = {
            "unit": {
                "path": "backend/tests/unit/",
                "description": "Unit tests for individual components",
                "timeout": 300,  # 5 minutes
                "required": True
            },
            "integration": {
                "path": "backend/tests/integration/",
                "description": "Integration tests for service interactions",
                "timeout": 600,  # 10 minutes
                "required": True
            },
            "e2e": {
                "path": "backend/tests/e2e/",
                "description": "End-to-end workflow tests",
                "timeout": 900,  # 15 minutes
                "required": True
            },
            "performance": {
                "path": "backend/tests/performance/",
                "description": "Performance and load tests",
                "timeout": 1200,  # 20 minutes
                "required": False
            },
            "deployment": {
                "path": "backend/tests/integration/test_deployment_monitoring.py",
                "description": "Deployment and monitoring tests",
                "timeout": 300,  # 5 minutes
                "required": True
            },
            "frontend_unit": {
                "path": "frontend/src/test/",
                "description": "Frontend unit and component tests",
                "timeout": 300,  # 5 minutes
                "required": True,
                "command": "npm"
            },
            "frontend_e2e": {
                "path": "frontend/src/test/e2e/",
                "description": "Frontend end-to-end tests",
                "timeout": 600,  # 10 minutes
                "required": False,
                "command": "npm"
            }
        }

    def print_header(self):
        """Print test runner header."""
        print("=" * 80)
        print("🧪 Local Business Intelligence Bot - Comprehensive Test Suite")
        print("=" * 80)
        print(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Coverage enabled: {self.coverage}")
        print(f"Verbose mode: {self.verbose}")
        print()

    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met."""
        print("🔍 Checking prerequisites...")
        
        prerequisites = []
        
        # Check Python environment
        try:
            result = subprocess.run([sys.executable, "--version"], 
                                  capture_output=True, text=True)
            python_version = result.stdout.strip()
            prerequisites.append(f"✅ Python: {python_version}")
        except Exception as e:
            prerequisites.append(f"❌ Python: {e}")
            return False
        
        # Check pytest
        try:
            result = subprocess.run([sys.executable, "-m", "pytest", "--version"], 
                                  capture_output=True, text=True)
            pytest_version = result.stdout.strip().split('\n')[0]
            prerequisites.append(f"✅ Pytest: {pytest_version}")
        except Exception as e:
            prerequisites.append(f"❌ Pytest: {e}")
            return False
        
        # Check Node.js for frontend tests
        try:
            result = subprocess.run(["node", "--version"], 
                                  capture_output=True, text=True)
            node_version = result.stdout.strip()
            prerequisites.append(f"✅ Node.js: {node_version}")
        except Exception as e:
            prerequisites.append(f"⚠️  Node.js: {e} (frontend tests will be skipped)")
        
        # Check npm
        try:
            result = subprocess.run(["npm", "--version"], 
                                  capture_output=True, text=True)
            npm_version = result.stdout.strip()
            prerequisites.append(f"✅ npm: {npm_version}")
        except Exception as e:
            prerequisites.append(f"⚠️  npm: {e} (frontend tests will be skipped)")
        
        # Check database
        if os.getenv("DATABASE_URL"):
            prerequisites.append("✅ Database URL configured")
        else:
            prerequisites.append("⚠️  Database URL not configured (using test database)")
        
        # Check Redis
        if os.getenv("REDIS_URL"):
            prerequisites.append("✅ Redis URL configured")
        else:
            prerequisites.append("⚠️  Redis URL not configured (using mock)")
        
        for prereq in prerequisites:
            print(f"  {prereq}")
        
        print()
        return True

    def run_backend_tests(self, suite_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run backend test suite."""
        print(f"🧪 Running {suite_name} tests...")
        print(f"   {config['description']}")
        
        # Build pytest command
        cmd = [sys.executable, "-m", "pytest"]
        
        if self.coverage and suite_name in ["unit", "integration"]:
            cmd.extend([
                "--cov=backend",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov",
                "--cov-append"
            ])
        
        if self.verbose:
            cmd.append("-v")
        else:
            cmd.append("-q")
        
        # Add test path
        cmd.append(config["path"])
        
        # Add markers for specific test types
        if suite_name == "performance":
            cmd.extend(["-m", "not slow"])  # Skip slow tests by default
        
        # Add timeout
        cmd.extend(["--timeout", str(config["timeout"])])
        
        # Add JSON report
        report_file = f"test-results-{suite_name}.json"
        cmd.extend(["--json-report", f"--json-report-file={report_file}"])
        
        start_time = time.time()
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=config["timeout"])
            duration = time.time() - start_time
            
            # Parse results
            test_result = {
                "suite": suite_name,
                "success": result.returncode == 0,
                "duration": duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
            # Try to parse JSON report
            try:
                if os.path.exists(report_file):
                    with open(report_file, 'r') as f:
                        json_report = json.load(f)
                        test_result.update({
                            "tests_collected": json_report.get("summary", {}).get("collected", 0),
                            "tests_passed": json_report.get("summary", {}).get("passed", 0),
                            "tests_failed": json_report.get("summary", {}).get("failed", 0),
                            "tests_skipped": json_report.get("summary", {}).get("skipped", 0)
                        })
            except Exception as e:
                if self.verbose:
                    print(f"   ⚠️  Could not parse JSON report: {e}")
            
            # Print results
            if test_result["success"]:
                print(f"   ✅ Passed in {duration:.2f}s")
                if "tests_passed" in test_result:
                    print(f"      {test_result['tests_passed']} passed, "
                          f"{test_result['tests_failed']} failed, "
                          f"{test_result['tests_skipped']} skipped")
            else:
                print(f"   ❌ Failed in {duration:.2f}s")
                if self.verbose and result.stderr:
                    print(f"      Error: {result.stderr}")
            
            return test_result
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"   ⏰ Timeout after {duration:.2f}s")
            return {
                "suite": suite_name,
                "success": False,
                "duration": duration,
                "error": "Timeout",
                "timeout": True
            }
        except Exception as e:
            duration = time.time() - start_time
            print(f"   💥 Exception: {e}")
            return {
                "suite": suite_name,
                "success": False,
                "duration": duration,
                "error": str(e),
                "exception": True
            }

    def run_frontend_tests(self, suite_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run frontend test suite."""
        print(f"🧪 Running {suite_name} tests...")
        print(f"   {config['description']}")
        
        # Check if we're in frontend directory or need to change
        original_cwd = os.getcwd()
        frontend_dir = Path("frontend")
        
        if not frontend_dir.exists():
            print(f"   ⚠️  Frontend directory not found, skipping")
            return {
                "suite": suite_name,
                "success": False,
                "skipped": True,
                "reason": "Frontend directory not found"
            }
        
        try:
            os.chdir(frontend_dir)
            
            # Install dependencies if needed
            if not Path("node_modules").exists():
                print("   📦 Installing frontend dependencies...")
                install_result = subprocess.run(["npm", "install"], 
                                              capture_output=True, text=True)
                if install_result.returncode != 0:
                    print(f"   ❌ Failed to install dependencies")
                    return {
                        "suite": suite_name,
                        "success": False,
                        "error": "Failed to install dependencies"
                    }
            
            # Build test command
            if suite_name == "frontend_unit":
                cmd = ["npm", "run", "test"]
                if not self.verbose:
                    cmd.append("--silent")
            elif suite_name == "frontend_e2e":
                cmd = ["npm", "run", "test:e2e"]
            else:
                cmd = ["npm", "test"]
            
            start_time = time.time()
            
            result = subprocess.run(cmd, capture_output=True, text=True, 
                                  timeout=config["timeout"])
            duration = time.time() - start_time
            
            test_result = {
                "suite": suite_name,
                "success": result.returncode == 0,
                "duration": duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
            # Print results
            if test_result["success"]:
                print(f"   ✅ Passed in {duration:.2f}s")
            else:
                print(f"   ❌ Failed in {duration:.2f}s")
                if self.verbose and result.stderr:
                    print(f"      Error: {result.stderr}")
            
            return test_result
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"   ⏰ Timeout after {duration:.2f}s")
            return {
                "suite": suite_name,
                "success": False,
                "duration": duration,
                "timeout": True
            }
        except Exception as e:
            duration = time.time() - start_time
            print(f"   💥 Exception: {e}")
            return {
                "suite": suite_name,
                "success": False,
                "duration": duration,
                "error": str(e)
            }
        finally:
            os.chdir(original_cwd)

    def run_all_tests(self, suites: List[str] = None) -> Dict[str, Any]:
        """Run all test suites."""
        if suites is None:
            suites = list(self.test_suites.keys())
        
        print(f"🚀 Running {len(suites)} test suites...\n")
        
        for suite_name in suites:
            if suite_name not in self.test_suites:
                print(f"⚠️  Unknown test suite: {suite_name}")
                continue
            
            config = self.test_suites[suite_name]
            
            # Skip non-required tests if they fail prerequisites
            if not config.get("required", True):
                if suite_name.startswith("frontend") and not self.check_frontend_available():
                    print(f"⏭️  Skipping {suite_name} (frontend not available)")
                    continue
            
            # Run the appropriate test runner
            if config.get("command") == "npm":
                result = self.run_frontend_tests(suite_name, config)
            else:
                result = self.run_backend_tests(suite_name, config)
            
            self.results[suite_name] = result
            print()
        
        return self.results

    def check_frontend_available(self) -> bool:
        """Check if frontend testing is available."""
        try:
            subprocess.run(["node", "--version"], capture_output=True, check=True)
            subprocess.run(["npm", "--version"], capture_output=True, check=True)
            return Path("frontend").exists()
        except:
            return False

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        total_duration = time.time() - self.start_time
        
        # Calculate summary statistics
        total_suites = len(self.results)
        passed_suites = len([r for r in self.results.values() if r.get("success", False)])
        failed_suites = total_suites - passed_suites
        
        total_tests = sum(r.get("tests_collected", 0) for r in self.results.values())
        passed_tests = sum(r.get("tests_passed", 0) for r in self.results.values())
        failed_tests = sum(r.get("tests_failed", 0) for r in self.results.values())
        skipped_tests = sum(r.get("tests_skipped", 0) for r in self.results.values())
        
        report = {
            "summary": {
                "total_duration": total_duration,
                "total_suites": total_suites,
                "passed_suites": passed_suites,
                "failed_suites": failed_suites,
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "skipped_tests": skipped_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            "suites": self.results,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "environment": {
                "python_version": sys.version,
                "platform": sys.platform,
                "coverage_enabled": self.coverage
            }
        }
        
        return report

    def print_summary(self, report: Dict[str, Any]):
        """Print test summary."""
        print("=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        summary = report["summary"]
        
        print(f"Total Duration: {summary['total_duration']:.2f}s")
        print(f"Test Suites: {summary['passed_suites']}/{summary['total_suites']} passed")
        print(f"Individual Tests: {summary['passed_tests']}/{summary['total_tests']} passed")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print()
        
        # Suite breakdown
        print("📋 Suite Results:")
        for suite_name, result in self.results.items():
            status = "✅" if result.get("success", False) else "❌"
            duration = result.get("duration", 0)
            
            if result.get("skipped"):
                status = "⏭️ "
                reason = result.get("reason", "Unknown")
                print(f"  {status} {suite_name:20} - Skipped ({reason})")
            elif result.get("timeout"):
                print(f"  {status} {suite_name:20} - Timeout ({duration:.1f}s)")
            elif result.get("exception"):
                error = result.get("error", "Unknown error")
                print(f"  {status} {suite_name:20} - Exception ({error})")
            else:
                tests_info = ""
                if "tests_passed" in result:
                    tests_info = f" ({result['tests_passed']} passed)"
                print(f"  {status} {suite_name:20} - {duration:.1f}s{tests_info}")
        
        print()
        
        # Overall result
        if summary["failed_suites"] == 0:
            print("🎉 ALL TESTS PASSED!")
        else:
            print(f"💥 {summary['failed_suites']} TEST SUITE(S) FAILED")
        
        print("=" * 80)

    def save_report(self, report: Dict[str, Any], filename: str = "test-report.json"):
        """Save test report to file."""
        try:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"📄 Test report saved to {filename}")
        except Exception as e:
            print(f"⚠️  Failed to save report: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Comprehensive test runner")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose output")
    parser.add_argument("--no-coverage", action="store_true", 
                       help="Disable coverage reporting")
    parser.add_argument("--suites", nargs="+", 
                       help="Specific test suites to run")
    parser.add_argument("--report", default="test-report.json",
                       help="Report output file")
    parser.add_argument("--performance", action="store_true",
                       help="Include performance tests")
    
    args = parser.parse_args()
    
    # Initialize test runner
    runner = TestRunner(
        verbose=args.verbose,
        coverage=not args.no_coverage
    )
    
    # Print header
    runner.print_header()
    
    # Check prerequisites
    if not runner.check_prerequisites():
        print("❌ Prerequisites not met. Exiting.")
        sys.exit(1)
    
    # Determine which suites to run
    suites_to_run = args.suites
    if suites_to_run is None:
        suites_to_run = ["unit", "integration", "e2e", "deployment", "frontend_unit"]
        if args.performance:
            suites_to_run.append("performance")
    
    # Run tests
    try:
        results = runner.run_all_tests(suites_to_run)
        
        # Generate and display report
        report = runner.generate_report()
        runner.print_summary(report)
        
        # Save report
        runner.save_report(report, args.report)
        
        # Exit with appropriate code
        failed_suites = len([r for r in results.values() if not r.get("success", False)])
        sys.exit(0 if failed_suites == 0 else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Test run interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()