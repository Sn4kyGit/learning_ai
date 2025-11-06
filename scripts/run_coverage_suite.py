#!/usr/bin/env python3
"""
Master coverage analysis suite.

This script orchestrates all coverage analysis tools to provide comprehensive
coverage reporting, gap analysis, and critical path validation.
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse


class CoverageSuite:
    """Master coverage analysis suite orchestrator."""
    
    def __init__(self, verbose: bool = False, ci_mode: bool = False):
        self.verbose = verbose
        self.ci_mode = ci_mode
        self.start_time = time.time()
        self.results = {}
        
        # Coverage analysis tools
        self.tools = {
            "coverage_analysis": "scripts/coverage_analysis.py",
            "gap_analysis": "scripts/coverage_gap_analysis.py", 
            "critical_path_validation": "scripts/critical_path_validator.py",
            "ci_integration": "scripts/coverage_ci_integration.py"
        }
    
    def run_comprehensive_analysis(self, environment: str = "development") -> Dict[str, Any]:
        """Run comprehensive coverage analysis suite."""
        print("🚀 Starting comprehensive coverage analysis suite...")
        print(f"Environment: {environment}")
        print(f"CI Mode: {self.ci_mode}")
        print()
        
        # Step 1: Run basic coverage analysis
        print("📊 Step 1: Running coverage analysis...")
        coverage_result = self._run_coverage_analysis()
        self.results["coverage_analysis"] = coverage_result
        
        if not coverage_result["success"]:
            print("❌ Coverage analysis failed, stopping suite")
            return self._generate_final_report(False)
        
        # Step 2: Run gap analysis
        print("\n🔍 Step 2: Running gap analysis...")
        gap_result = self._run_gap_analysis()
        self.results["gap_analysis"] = gap_result
        
        # Step 3: Run critical path validation
        print("\n🎯 Step 3: Running critical path validation...")
        critical_result = self._run_critical_path_validation()
        self.results["critical_path_validation"] = critical_result
        
        # Step 4: Run CI integration (if in CI mode)
        if self.ci_mode:
            print("\n🔧 Step 4: Running CI integration...")
            ci_result = self._run_ci_integration(environment)
            self.results["ci_integration"] = ci_result
        
        # Step 5: Generate comprehensive report
        print("\n📋 Step 5: Generating comprehensive report...")
        success = self._determine_overall_success()
        final_report = self._generate_final_report(success)
        
        return final_report
    
    def _run_coverage_analysis(self) -> Dict[str, Any]:
        """Run basic coverage analysis."""
        try:
            cmd = [sys.executable, self.tools["coverage_analysis"]]
            if self.verbose:
                cmd.append("--verbose")
            if self.ci_mode:
                cmd.append("--ci")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            
            # Load coverage report if available
            coverage_data = None
            if os.path.exists("coverage-report.json"):
                with open("coverage-report.json", 'r') as f:
                    coverage_data = json.load(f)
            
            return {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "data": coverage_data
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Coverage analysis timed out",
                "timeout": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "exception": True
            }
    
    def _run_gap_analysis(self) -> Dict[str, Any]:
        """Run coverage gap analysis."""
        try:
            cmd = [sys.executable, self.tools["gap_analysis"]]
            if self.verbose:
                cmd.append("--verbose")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            # Load gap analysis report if available
            gap_data = None
            if os.path.exists("coverage-gaps.json"):
                with open("coverage-gaps.json", 'r') as f:
                    gap_data = json.load(f)
            
            return {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "data": gap_data
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Gap analysis timed out",
                "timeout": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "exception": True
            }
    
    def _run_critical_path_validation(self) -> Dict[str, Any]:
        """Run critical path validation."""
        try:
            cmd = [sys.executable, self.tools["critical_path_validation"]]
            if self.verbose:
                cmd.append("--verbose")
            cmd.extend(["--fail-on-gaps"])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            # Load validation report if available
            validation_data = None
            if os.path.exists("critical-path-validation.json"):
                with open("critical-path-validation.json", 'r') as f:
                    validation_data = json.load(f)
            
            return {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "data": validation_data
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Critical path validation timed out",
                "timeout": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "exception": True
            }
    
    def _run_ci_integration(self, environment: str) -> Dict[str, Any]:
        """Run CI integration."""
        try:
            cmd = [sys.executable, self.tools["ci_integration"], "--environment", environment]
            if self.verbose:
                cmd.append("--verbose")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            return {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "CI integration timed out",
                "timeout": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "exception": True
            }
    
    def _determine_overall_success(self) -> bool:
        """Determine if the overall coverage suite passed."""
        # Coverage analysis must succeed
        if not self.results.get("coverage_analysis", {}).get("success", False):
            return False
        
        # Critical path validation must pass
        critical_result = self.results.get("critical_path_validation", {})
        if not critical_result.get("success", False):
            return False
        
        # CI integration must pass (if run)
        if self.ci_mode:
            ci_result = self.results.get("ci_integration", {})
            if not ci_result.get("success", False):
                return False
        
        return True
    
    def _generate_final_report(self, success: bool) -> Dict[str, Any]:
        """Generate final comprehensive report."""
        duration = time.time() - self.start_time
        
        # Extract key metrics
        coverage_data = self.results.get("coverage_analysis", {}).get("data")
        gap_data = self.results.get("gap_analysis", {}).get("data")
        critical_data = self.results.get("critical_path_validation", {}).get("data")
        
        # Calculate summary metrics
        total_coverage = 0.0
        critical_coverage = 0.0
        total_gaps = 0
        critical_gaps = 0
        
        if coverage_data:
            total_coverage = coverage_data.get("total_coverage", 0.0)
            critical_coverage = coverage_data.get("critical_path_coverage", 0.0)
        
        if gap_data:
            gaps = gap_data.get("gaps", [])
            total_gaps = len(gaps)
            critical_gaps = len([g for g in gaps if g.get("severity") == "critical"])
        
        # Generate recommendations
        recommendations = self._generate_recommendations()
        
        report = {
            "success": success,
            "duration": duration,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "summary": {
                "total_coverage": total_coverage,
                "critical_path_coverage": critical_coverage,
                "total_gaps": total_gaps,
                "critical_gaps": critical_gaps,
                "tools_run": len([r for r in self.results.values() if r.get("success")]),
                "tools_failed": len([r for r in self.results.values() if not r.get("success")])
            },
            "results": self.results,
            "recommendations": recommendations,
            "artifacts": self._collect_artifacts()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on all analysis results."""
        recommendations = []
        
        # Coverage-based recommendations
        coverage_data = self.results.get("coverage_analysis", {}).get("data")
        if coverage_data:
            total_coverage = coverage_data.get("total_coverage", 0.0)
            if total_coverage < 80:
                recommendations.append(f"Increase overall coverage from {total_coverage:.1f}% to at least 80%")
            
            critical_coverage = coverage_data.get("critical_path_coverage", 0.0)
            if critical_coverage < 95:
                recommendations.append(f"Improve critical path coverage from {critical_coverage:.1f}% to 95%+")
        
        # Gap-based recommendations
        gap_data = self.results.get("gap_analysis", {}).get("data")
        if gap_data:
            improvement_plan = gap_data.get("improvement_plan", {})
            if improvement_plan.get("recommendations"):
                recommendations.extend(improvement_plan["recommendations"][:3])  # Top 3
        
        # Critical path recommendations
        critical_data = self.results.get("critical_path_validation", {}).get("data")
        if critical_data and not critical_data.get("validation_passed", True):
            recommendations.extend(critical_data.get("recommendations", [])[:2])  # Top 2
        
        # General recommendations
        if not recommendations:
            recommendations.extend([
                "Maintain current coverage levels with regular monitoring",
                "Focus on testing edge cases and error handling",
                "Consider adding property-based tests for data validation"
            ])
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _collect_artifacts(self) -> List[str]:
        """Collect all generated artifacts."""
        artifacts = []
        
        artifact_files = [
            "coverage.xml",
            "coverage.json", 
            "coverage-report.json",
            "coverage-gaps.json",
            "critical-path-validation.json",
            "coverage-badge.json",
            "pr-comment.md",
            "coverage-summary.md",
            "htmlcov/index.html"
        ]
        
        for artifact in artifact_files:
            if os.path.exists(artifact):
                artifacts.append(artifact)
        
        return artifacts
    
    def print_final_report(self, report: Dict[str, Any]):
        """Print comprehensive final report."""
        print("\n" + "=" * 80)
        print("🏆 COMPREHENSIVE COVERAGE ANALYSIS REPORT")
        print("=" * 80)
        
        summary = report["summary"]
        
        # Overall status
        if report["success"]:
            print("✅ COVERAGE ANALYSIS SUITE PASSED")
        else:
            print("❌ COVERAGE ANALYSIS SUITE FAILED")
        
        print(f"Duration: {report['duration']:.1f}s")
        print(f"Timestamp: {report['timestamp']}")
        print()
        
        # Summary metrics
        print("📊 Summary Metrics:")
        print(f"  Overall Coverage: {summary['total_coverage']:.1f}%")
        print(f"  Critical Path Coverage: {summary['critical_path_coverage']:.1f}%")
        print(f"  Coverage Gaps: {summary['total_gaps']} (Critical: {summary['critical_gaps']})")
        print(f"  Tools: {summary['tools_run']} passed, {summary['tools_failed']} failed")
        print()
        
        # Tool results
        print("🔧 Tool Results:")
        for tool_name, result in report["results"].items():
            status = "✅" if result.get("success", False) else "❌"
            tool_display = tool_name.replace("_", " ").title()
            
            if result.get("timeout"):
                print(f"  {status} {tool_display}: Timeout")
            elif result.get("exception"):
                print(f"  {status} {tool_display}: Exception")
            elif "error" in result:
                print(f"  {status} {tool_display}: {result['error']}")
            else:
                print(f"  {status} {tool_display}: Completed")
        
        print()
        
        # Recommendations
        if report["recommendations"]:
            print("💡 Key Recommendations:")
            for i, rec in enumerate(report["recommendations"], 1):
                print(f"  {i}. {rec}")
            print()
        
        # Artifacts
        if report["artifacts"]:
            print("📄 Generated Artifacts:")
            for artifact in report["artifacts"]:
                print(f"  • {artifact}")
            print()
        
        print("=" * 80)
    
    def save_final_report(self, report: Dict[str, Any], filename: str = "coverage-suite-report.json"):
        """Save final report to JSON file."""
        try:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            
            print(f"📄 Coverage suite report saved to {filename}")
            
        except Exception as e:
            print(f"⚠️  Failed to save suite report: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Comprehensive coverage analysis suite")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose output")
    parser.add_argument("--ci", action="store_true",
                       help="Run in CI mode with additional integrations")
    parser.add_argument("--environment", choices=["production", "development", "pull_request"],
                       default="development", help="Environment for analysis")
    parser.add_argument("--report", default="coverage-suite-report.json",
                       help="Output file for final report")
    
    args = parser.parse_args()
    
    try:
        # Initialize coverage suite
        suite = CoverageSuite(verbose=args.verbose, ci_mode=args.ci)
        
        # Run comprehensive analysis
        report = suite.run_comprehensive_analysis(args.environment)
        
        # Print final report
        suite.print_final_report(report)
        
        # Save report
        suite.save_final_report(report, args.report)
        
        # Exit with appropriate code
        if report["success"]:
            print("\n✅ Coverage analysis suite completed successfully")
            sys.exit(0)
        else:
            print("\n❌ Coverage analysis suite failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Coverage suite interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Coverage suite failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()