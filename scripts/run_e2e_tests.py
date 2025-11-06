#!/usr/bin/env python3
"""
End-to-end test runner for Local Business Intelligence Bot.

This script runs comprehensive end-to-end tests including:
- Complete user workflows
- Performance optimization tests
- Database optimization tests
- Multi-language functionality
- Multi-tenant access control
- GDPR compliance

Usage:
    python scripts/run_e2e_tests.py [--performance] [--database] [--workflows] [--all]
"""

import asyncio
import argparse
import sys
import time
import subprocess
from pathlib import Path
from typing import List, Dict, Any
import json


class E2ETestRunner:
    """End-to-end test runner with comprehensive reporting."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_results = {}
        self.start_time = None
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
    def run_test_suite(self, test_module: str, description: str) -> Dict[str, Any]:
        """Run a specific test suite and capture results."""
        print(f"\n{'='*60}")
        print(f"Running {description}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        # Run pytest with specific module
        cmd = [
            "python", "-m", "pytest",
            f"backend/tests/e2e/{test_module}",
            "-v",
            "--tb=short",
            "--durations=10",
            "--json-report",
            "--json-report-file=test_results.json"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes timeout
            )
            
            execution_time = time.time() - start_time
            
            # Parse results
            success = result.returncode == 0
            
            # Try to load JSON report
            json_report = None
            try:
                with open(self.project_root / "test_results.json", "r") as f:
                    json_report = json.load(f)
            except FileNotFoundError:
                pass
            
            test_result = {
                "module": test_module,
                "description": description,
                "success": success,
                "execution_time": execution_time,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "json_report": json_report
            }
            
            if json_report:
                self.total_tests += json_report.get("summary", {}).get("total", 0)
                self.passed_tests += json_report.get("summary", {}).get("passed", 0)
                self.failed_tests += json_report.get("summary", {}).get("failed", 0)
            
            # Print summary
            if success:
                print(f"✅ {description} - PASSED ({execution_time:.2f}s)")
            else:
                print(f"❌ {description} - FAILED ({execution_time:.2f}s)")
                print(f"Error output: {result.stderr}")
            
            return test_result
            
        except subprocess.TimeoutExpired:
            print(f"⏰ {description} - TIMEOUT (30 minutes)")
            return {
                "module": test_module,
                "description": description,
                "success": False,
                "execution_time": 1800,
                "error": "Test suite timed out after 30 minutes"
            }
        except Exception as e:
            print(f"💥 {description} - ERROR: {str(e)}")
            return {
                "module": test_module,
                "description": description,
                "success": False,
                "execution_time": 0,
                "error": str(e)
            }
    
    def run_workflow_tests(self) -> List[Dict[str, Any]]:
        """Run complete user workflow tests."""
        return [
            self.run_test_suite(
                "test_complete_user_workflows.py::TestCompleteUserWorkflow::test_complete_restaurant_owner_workflow",
                "Complete Restaurant Owner Workflow"
            ),
            self.run_test_suite(
                "test_complete_user_workflows.py::TestCompleteUserWorkflow::test_multi_tenant_workflow",
                "Multi-Tenant Workflow"
            ),
            self.run_test_suite(
                "test_complete_user_workflows.py::TestCompleteUserWorkflow::test_multi_language_workflow",
                "Multi-Language Workflow"
            ),
            self.run_test_suite(
                "test_complete_user_workflows.py::TestCompleteUserWorkflow::test_alert_and_notification_workflow",
                "Alert and Notification Workflow"
            ),
            self.run_test_suite(
                "test_complete_user_workflows.py::TestCompleteUserWorkflow::test_gdpr_compliance_workflow",
                "GDPR Compliance Workflow"
            )
        ]
    
    def run_performance_tests(self) -> List[Dict[str, Any]]:
        """Run performance optimization tests."""
        return [
            self.run_test_suite(
                "test_performance_optimization.py::TestBatchProcessingPerformance::test_500_review_classification_performance",
                "500 Review Batch Processing Performance"
            ),
            self.run_test_suite(
                "test_performance_optimization.py::TestBatchProcessingPerformance::test_concurrent_user_performance",
                "Concurrent User Performance"
            ),
            self.run_test_suite(
                "test_performance_optimization.py::TestBatchProcessingPerformance::test_memory_usage_optimization",
                "Memory Usage Optimization"
            ),
            self.run_test_suite(
                "test_complete_user_workflows.py::TestPerformanceRequirements::test_api_response_time_requirements",
                "API Response Time Requirements"
            ),
            self.run_test_suite(
                "test_performance_optimization.py::TestScalabilityLimits::test_maximum_businesses_per_organization",
                "Scalability Limits Testing"
            )
        ]
    
    def run_database_tests(self) -> List[Dict[str, Any]]:
        """Run database optimization tests."""
        return [
            self.run_test_suite(
                "test_database_optimization.py::TestIndexEffectiveness",
                "Database Index Effectiveness"
            ),
            self.run_test_suite(
                "test_database_optimization.py::TestQueryOptimization",
                "Query Optimization"
            ),
            self.run_test_suite(
                "test_database_optimization.py::TestDatabasePerformanceUnderLoad",
                "Database Performance Under Load"
            ),
            self.run_test_suite(
                "test_database_optimization.py::TestQueryPlanAnalysis",
                "Query Plan Analysis"
            )
        ]
    
    def run_data_isolation_tests(self) -> List[Dict[str, Any]]:
        """Run multi-tenant data isolation tests."""
        return [
            self.run_test_suite(
                "test_complete_user_workflows.py::TestDataIsolation::test_organization_data_isolation",
                "Organization Data Isolation"
            ),
            self.run_test_suite(
                "test_complete_user_workflows.py::TestDataIsolation::test_user_business_access_isolation",
                "User Business Access Isolation"
            )
        ]
    
    def generate_performance_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        performance_metrics = {
            "total_execution_time": sum(r.get("execution_time", 0) for r in results),
            "average_test_time": sum(r.get("execution_time", 0) for r in results) / len(results) if results else 0,
            "success_rate": sum(1 for r in results if r.get("success", False)) / len(results) if results else 0,
            "failed_tests": [r for r in results if not r.get("success", False)],
            "performance_benchmarks": {}
        }
        
        # Extract specific performance metrics
        for result in results:
            if result.get("json_report"):
                # Extract performance data from test results
                test_data = result["json_report"]
                if "tests" in test_data:
                    for test in test_data["tests"]:
                        if "performance" in test.get("nodeid", "").lower():
                            performance_metrics["performance_benchmarks"][test["nodeid"]] = {
                                "duration": test.get("duration", 0),
                                "outcome": test.get("outcome", "unknown")
                            }
        
        return performance_metrics
    
    def print_final_report(self, all_results: List[Dict[str, Any]]):
        """Print comprehensive final report."""
        print(f"\n{'='*80}")
        print("END-TO-END TEST EXECUTION SUMMARY")
        print(f"{'='*80}")
        
        total_time = time.time() - self.start_time if self.start_time else 0
        
        print(f"Total Execution Time: {total_time:.2f} seconds")
        print(f"Total Test Suites: {len(all_results)}")
        print(f"Successful Suites: {sum(1 for r in all_results if r.get('success', False))}")
        print(f"Failed Suites: {sum(1 for r in all_results if not r.get('success', False))}")
        
        if self.total_tests > 0:
            print(f"Total Individual Tests: {self.total_tests}")
            print(f"Passed Tests: {self.passed_tests}")
            print(f"Failed Tests: {self.failed_tests}")
            print(f"Success Rate: {(self.passed_tests / self.total_tests * 100):.1f}%")
        
        # Performance summary
        performance_report = self.generate_performance_report(all_results)
        print(f"\nPerformance Summary:")
        print(f"Average Test Suite Time: {performance_report['average_test_time']:.2f}s")
        print(f"Suite Success Rate: {(performance_report['success_rate'] * 100):.1f}%")
        
        # Failed tests details
        failed_results = [r for r in all_results if not r.get("success", False)]
        if failed_results:
            print(f"\n{'='*40}")
            print("FAILED TEST SUITES:")
            print(f"{'='*40}")
            
            for result in failed_results:
                print(f"❌ {result['description']}")
                if "error" in result:
                    print(f"   Error: {result['error']}")
                elif result.get("stderr"):
                    print(f"   Error: {result['stderr'][:200]}...")
        
        # Performance benchmarks
        if performance_report["performance_benchmarks"]:
            print(f"\n{'='*40}")
            print("PERFORMANCE BENCHMARKS:")
            print(f"{'='*40}")
            
            for test_name, metrics in performance_report["performance_benchmarks"].items():
                status = "✅" if metrics["outcome"] == "passed" else "❌"
                print(f"{status} {test_name}: {metrics['duration']:.3f}s")
        
        # Requirements validation
        print(f"\n{'='*40}")
        print("REQUIREMENTS VALIDATION:")
        print(f"{'='*40}")
        
        requirements_status = {
            "500 Review Batch Processing (< 60s)": "✅ VALIDATED" if any("500_review" in r.get("description", "") and r.get("success", False) for r in all_results) else "❌ FAILED",
            "API Response Times (< 500ms)": "✅ VALIDATED" if any("response_time" in r.get("description", "").lower() and r.get("success", False) for r in all_results) else "❌ FAILED",
            "Multi-Language Support": "✅ VALIDATED" if any("multi_language" in r.get("description", "").lower() and r.get("success", False) for r in all_results) else "❌ FAILED",
            "Multi-Tenant Data Isolation": "✅ VALIDATED" if any("isolation" in r.get("description", "").lower() and r.get("success", False) for r in all_results) else "❌ FAILED",
            "Database Query Optimization": "✅ VALIDATED" if any("database" in r.get("description", "").lower() and r.get("success", False) for r in all_results) else "❌ FAILED"
        }
        
        for requirement, status in requirements_status.items():
            print(f"{requirement}: {status}")
        
        # Overall result
        overall_success = all(r.get("success", False) for r in all_results)
        print(f"\n{'='*80}")
        if overall_success:
            print("🎉 ALL END-TO-END TESTS PASSED! SYSTEM READY FOR PRODUCTION.")
        else:
            print("⚠️  SOME TESTS FAILED. REVIEW ISSUES BEFORE PRODUCTION DEPLOYMENT.")
        print(f"{'='*80}")
        
        return overall_success
    
    def run_all_tests(self, test_categories: List[str]) -> bool:
        """Run all specified test categories."""
        self.start_time = time.time()
        all_results = []
        
        print("Starting End-to-End Test Execution...")
        print(f"Test Categories: {', '.join(test_categories)}")
        
        if "workflows" in test_categories or "all" in test_categories:
            print("\n🔄 Running User Workflow Tests...")
            all_results.extend(self.run_workflow_tests())
        
        if "performance" in test_categories or "all" in test_categories:
            print("\n⚡ Running Performance Tests...")
            all_results.extend(self.run_performance_tests())
        
        if "database" in test_categories or "all" in test_categories:
            print("\n🗄️  Running Database Optimization Tests...")
            all_results.extend(self.run_database_tests())
        
        if "isolation" in test_categories or "all" in test_categories:
            print("\n🔒 Running Data Isolation Tests...")
            all_results.extend(self.run_data_isolation_tests())
        
        # Generate final report
        overall_success = self.print_final_report(all_results)
        
        # Save detailed results to file
        with open(self.project_root / "e2e_test_results.json", "w") as f:
            json.dump({
                "execution_time": time.time() - self.start_time,
                "overall_success": overall_success,
                "results": all_results,
                "performance_report": self.generate_performance_report(all_results)
            }, f, indent=2)
        
        return overall_success


def main():
    """Main entry point for E2E test runner."""
    parser = argparse.ArgumentParser(description="Run end-to-end tests for Local Business Intelligence Bot")
    parser.add_argument("--workflows", action="store_true", help="Run user workflow tests")
    parser.add_argument("--performance", action="store_true", help="Run performance tests")
    parser.add_argument("--database", action="store_true", help="Run database optimization tests")
    parser.add_argument("--isolation", action="store_true", help="Run data isolation tests")
    parser.add_argument("--all", action="store_true", help="Run all test categories")
    parser.add_argument("--setup-only", action="store_true", help="Only setup test environment")
    
    args = parser.parse_args()
    
    # Determine test categories
    test_categories = []
    if args.workflows:
        test_categories.append("workflows")
    if args.performance:
        test_categories.append("performance")
    if args.database:
        test_categories.append("database")
    if args.isolation:
        test_categories.append("isolation")
    if args.all:
        test_categories.append("all")
    
    # Default to all tests if no specific category selected
    if not test_categories:
        test_categories.append("all")
    
    # Setup test environment
    print("Setting up test environment...")
    
    # Install test dependencies
    subprocess.run([
        "pip", "install", "-r", "requirements.txt"
    ], check=True)
    
    subprocess.run([
        "pip", "install", "pytest-json-report", "pytest-asyncio", "psutil"
    ], check=True)
    
    if args.setup_only:
        print("Test environment setup complete.")
        return 0
    
    # Run tests
    runner = E2ETestRunner()
    success = runner.run_all_tests(test_categories)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())