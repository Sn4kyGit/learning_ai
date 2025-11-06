#!/usr/bin/env python3
"""
Comprehensive coverage analysis and reporting tool.

This script provides detailed coverage analysis with critical path validation,
gap analysis, and CI/CD integration for the Local Business Intelligence Bot.
"""

import os
import sys
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import argparse
import time


@dataclass
class CoverageResult:
    """Coverage analysis result for a module or package."""
    name: str
    statements: int
    missing: int
    excluded: int
    coverage: float
    missing_lines: List[str]
    is_critical_path: bool = False


@dataclass
class CoverageReport:
    """Complete coverage analysis report."""
    timestamp: str
    total_coverage: float
    critical_path_coverage: float
    modules: List[CoverageResult]
    gaps: List[Dict[str, Any]]
    thresholds_met: bool
    ci_status: str


class CoverageAnalyzer:
    """Comprehensive coverage analysis tool."""
    
    # Critical path modules that require 100% coverage
    CRITICAL_PATHS = {
        "backend.ai": {
            "threshold": 100.0,
            "description": "AI service integrations (GPT-5, Claude)"
        },
        "backend.services.auth_service": {
            "threshold": 100.0,
            "description": "Authentication and authorization"
        },
        "backend.services.review.processor": {
            "threshold": 100.0,
            "description": "Review data processing pipeline"
        },
        "backend.db.repositories": {
            "threshold": 95.0,
            "description": "Data access layer"
        },
        "backend.external": {
            "threshold": 90.0,
            "description": "External API integrations"
        }
    }
    
    # General coverage thresholds
    COVERAGE_THRESHOLDS = {
        "overall": 80.0,
        "unit_tests": 85.0,
        "integration_tests": 90.0,
        "services": 85.0,
        "routes": 80.0,
        "models": 90.0
    }
    
    # Files to exclude from coverage analysis
    EXCLUDED_PATTERNS = [
        "*/tests/*",
        "*/migrations/*",
        "*/alembic/*",
        "*/__pycache__/*",
        "*/venv/*",
        "*/env/*",
        "conftest.py",
        "*/test_*.py",
        "*_test.py"
    ]

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.coverage_data_file = ".coverage"
        self.html_report_dir = "htmlcov"
        self.xml_report_file = "coverage.xml"
        self.json_report_file = "coverage.json"

    def run_coverage_analysis(self, test_paths: List[str] = None) -> CoverageReport:
        """Run comprehensive coverage analysis."""
        print("🔍 Running comprehensive coverage analysis...")
        
        # Clean previous coverage data
        self._clean_coverage_data()
        
        # Run tests with coverage
        if not self._run_tests_with_coverage(test_paths):
            raise RuntimeError("Test execution failed")
        
        # Generate coverage reports
        self._generate_coverage_reports()
        
        # Parse coverage data
        coverage_data = self._parse_coverage_data()
        
        # Analyze critical paths
        critical_analysis = self._analyze_critical_paths(coverage_data)
        
        # Identify coverage gaps
        gaps = self._identify_coverage_gaps(coverage_data)
        
        # Generate final report
        report = self._generate_final_report(coverage_data, critical_analysis, gaps)
        
        return report

    def _clean_coverage_data(self):
        """Clean previous coverage data files."""
        files_to_clean = [
            self.coverage_data_file,
            self.xml_report_file,
            self.json_report_file
        ]
        
        for file_path in files_to_clean:
            if os.path.exists(file_path):
                os.remove(file_path)
                if self.verbose:
                    print(f"  Cleaned {file_path}")
        
        if os.path.exists(self.html_report_dir):
            import shutil
            shutil.rmtree(self.html_report_dir)
            if self.verbose:
                print(f"  Cleaned {self.html_report_dir}")

    def _run_tests_with_coverage(self, test_paths: List[str] = None) -> bool:
        """Run tests with coverage collection."""
        print("🧪 Running tests with coverage collection...")
        
        # Build pytest command
        cmd = [
            sys.executable, "-m", "pytest",
            "--cov=backend",
            "--cov-report=xml",
            "--cov-report=json",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-config=pytest.ini",
            "-v" if self.verbose else "-q"
        ]
        
        # Add test paths
        if test_paths:
            cmd.extend(test_paths)
        else:
            cmd.extend(["backend/tests/unit/", "backend/tests/integration/"])
        
        # Add markers to exclude slow tests
        cmd.extend(["-m", "not slow and not external"])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            
            if result.returncode != 0:
                print(f"❌ Test execution failed with return code {result.returncode}")
                if self.verbose:
                    print("STDOUT:", result.stdout)
                    print("STDERR:", result.stderr)
                return False
            
            print("✅ Tests completed successfully")
            return True
            
        except subprocess.TimeoutExpired:
            print("⏰ Test execution timed out")
            return False
        except Exception as e:
            print(f"💥 Test execution failed: {e}")
            return False

    def _generate_coverage_reports(self):
        """Generate additional coverage reports."""
        print("📊 Generating coverage reports...")
        
        # Generate detailed HTML report
        try:
            subprocess.run([
                sys.executable, "-m", "coverage", "html",
                "--directory", self.html_report_dir,
                "--title", "Local Business Intelligence Bot Coverage Report"
            ], check=True, capture_output=True)
            print(f"  ✅ HTML report: {self.html_report_dir}/index.html")
        except subprocess.CalledProcessError as e:
            print(f"  ❌ HTML report generation failed: {e}")
        
        # Generate JSON report for programmatic analysis
        try:
            subprocess.run([
                sys.executable, "-m", "coverage", "json",
                "--output-file", self.json_report_file
            ], check=True, capture_output=True)
            print(f"  ✅ JSON report: {self.json_report_file}")
        except subprocess.CalledProcessError as e:
            print(f"  ❌ JSON report generation failed: {e}")

    def _parse_coverage_data(self) -> Dict[str, Any]:
        """Parse coverage data from JSON report."""
        if not os.path.exists(self.json_report_file):
            raise FileNotFoundError(f"Coverage JSON report not found: {self.json_report_file}")
        
        with open(self.json_report_file, 'r') as f:
            return json.load(f)

    def _analyze_critical_paths(self, coverage_data: Dict[str, Any]) -> Dict[str, CoverageResult]:
        """Analyze coverage for critical paths."""
        print("🎯 Analyzing critical path coverage...")
        
        critical_results = {}
        files = coverage_data.get("files", {})
        
        for critical_path, config in self.CRITICAL_PATHS.items():
            matching_files = []
            
            # Find files matching the critical path
            for file_path in files.keys():
                # Convert file path to module path
                module_path = file_path.replace("/", ".").replace(".py", "")
                if module_path.startswith(critical_path):
                    matching_files.append(file_path)
            
            if not matching_files:
                print(f"  ⚠️  No files found for critical path: {critical_path}")
                continue
            
            # Calculate aggregate coverage for this critical path
            total_statements = 0
            total_missing = 0
            total_excluded = 0
            all_missing_lines = []
            
            for file_path in matching_files:
                file_data = files[file_path]
                summary = file_data.get("summary", {})
                
                total_statements += summary.get("num_statements", 0)
                total_missing += summary.get("missing_lines", 0)
                total_excluded += summary.get("excluded_lines", 0)
                
                missing_lines = file_data.get("missing_lines", [])
                if missing_lines:
                    all_missing_lines.extend([f"{file_path}:{line}" for line in missing_lines])
            
            # Calculate coverage percentage
            if total_statements > 0:
                coverage_pct = ((total_statements - total_missing) / total_statements) * 100
            else:
                coverage_pct = 100.0
            
            result = CoverageResult(
                name=critical_path,
                statements=total_statements,
                missing=total_missing,
                excluded=total_excluded,
                coverage=coverage_pct,
                missing_lines=all_missing_lines,
                is_critical_path=True
            )
            
            critical_results[critical_path] = result
            
            # Check threshold
            threshold = config["threshold"]
            status = "✅" if coverage_pct >= threshold else "❌"
            print(f"  {status} {critical_path}: {coverage_pct:.1f}% (threshold: {threshold}%)")
            
            if coverage_pct < threshold and self.verbose:
                print(f"      Missing lines: {len(all_missing_lines)}")
                for line in all_missing_lines[:5]:  # Show first 5 missing lines
                    print(f"        {line}")
                if len(all_missing_lines) > 5:
                    print(f"        ... and {len(all_missing_lines) - 5} more")
        
        return critical_results

    def _identify_coverage_gaps(self, coverage_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify coverage gaps and improvement opportunities."""
        print("🔍 Identifying coverage gaps...")
        
        gaps = []
        files = coverage_data.get("files", {})
        
        for file_path, file_data in files.items():
            summary = file_data.get("summary", {})
            coverage_pct = summary.get("percent_covered", 0)
            
            # Skip test files and excluded patterns
            if self._should_exclude_file(file_path):
                continue
            
            # Identify low coverage files
            if coverage_pct < 70:
                gaps.append({
                    "type": "low_coverage",
                    "file": file_path,
                    "coverage": coverage_pct,
                    "missing_lines": len(file_data.get("missing_lines", [])),
                    "priority": "high" if coverage_pct < 50 else "medium"
                })
            
            # Identify files with many missing lines
            missing_lines = file_data.get("missing_lines", [])
            if len(missing_lines) > 20:
                gaps.append({
                    "type": "many_missing_lines",
                    "file": file_path,
                    "coverage": coverage_pct,
                    "missing_lines": len(missing_lines),
                    "priority": "medium"
                })
            
            # Identify completely untested files
            if coverage_pct == 0 and summary.get("num_statements", 0) > 0:
                gaps.append({
                    "type": "untested_file",
                    "file": file_path,
                    "statements": summary.get("num_statements", 0),
                    "priority": "high"
                })
        
        # Sort gaps by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        gaps.sort(key=lambda x: (priority_order.get(x["priority"], 3), -x.get("missing_lines", 0)))
        
        print(f"  Found {len(gaps)} coverage gaps")
        
        return gaps

    def _should_exclude_file(self, file_path: str) -> bool:
        """Check if file should be excluded from coverage analysis."""
        for pattern in self.EXCLUDED_PATTERNS:
            # Simple pattern matching
            pattern_clean = pattern.replace("*", "")
            if pattern_clean in file_path:
                return True
        return False

    def _generate_final_report(
        self, 
        coverage_data: Dict[str, Any], 
        critical_analysis: Dict[str, CoverageResult],
        gaps: List[Dict[str, Any]]
    ) -> CoverageReport:
        """Generate final coverage report."""
        print("📋 Generating final coverage report...")
        
        # Calculate overall metrics
        totals = coverage_data.get("totals", {})
        total_coverage = totals.get("percent_covered", 0)
        
        # Calculate critical path coverage
        if critical_analysis:
            critical_coverages = [r.coverage for r in critical_analysis.values()]
            critical_path_coverage = sum(critical_coverages) / len(critical_coverages)
        else:
            critical_path_coverage = 0.0
        
        # Convert file data to CoverageResult objects
        modules = []
        files = coverage_data.get("files", {})
        
        for file_path, file_data in files.items():
            if self._should_exclude_file(file_path):
                continue
            
            summary = file_data.get("summary", {})
            missing_lines = file_data.get("missing_lines", [])
            
            result = CoverageResult(
                name=file_path,
                statements=summary.get("num_statements", 0),
                missing=len(missing_lines),
                excluded=summary.get("excluded_lines", 0),
                coverage=summary.get("percent_covered", 0),
                missing_lines=[str(line) for line in missing_lines],
                is_critical_path=any(
                    file_path.replace("/", ".").replace(".py", "").startswith(cp)
                    for cp in self.CRITICAL_PATHS.keys()
                )
            )
            modules.append(result)
        
        # Check if thresholds are met
        overall_threshold_met = total_coverage >= self.COVERAGE_THRESHOLDS["overall"]
        critical_threshold_met = all(
            result.coverage >= self.CRITICAL_PATHS[path]["threshold"]
            for path, result in critical_analysis.items()
        )
        thresholds_met = overall_threshold_met and critical_threshold_met
        
        # Determine CI status
        if thresholds_met:
            ci_status = "PASS"
        elif not critical_threshold_met:
            ci_status = "FAIL_CRITICAL"
        else:
            ci_status = "FAIL_OVERALL"
        
        report = CoverageReport(
            timestamp=time.strftime('%Y-%m-%d %H:%M:%S'),
            total_coverage=total_coverage,
            critical_path_coverage=critical_path_coverage,
            modules=modules,
            gaps=gaps,
            thresholds_met=thresholds_met,
            ci_status=ci_status
        )
        
        return report

    def print_report_summary(self, report: CoverageReport):
        """Print coverage report summary."""
        print("\n" + "=" * 80)
        print("📊 COVERAGE ANALYSIS REPORT")
        print("=" * 80)
        
        print(f"Timestamp: {report.timestamp}")
        print(f"Overall Coverage: {report.total_coverage:.1f}%")
        print(f"Critical Path Coverage: {report.critical_path_coverage:.1f}%")
        print(f"CI Status: {report.ci_status}")
        print()
        
        # Threshold status
        print("🎯 Threshold Status:")
        overall_status = "✅" if report.total_coverage >= self.COVERAGE_THRESHOLDS["overall"] else "❌"
        print(f"  {overall_status} Overall: {report.total_coverage:.1f}% (threshold: {self.COVERAGE_THRESHOLDS['overall']}%)")
        
        critical_status = "✅" if report.critical_path_coverage >= 95.0 else "❌"
        print(f"  {critical_status} Critical Paths: {report.critical_path_coverage:.1f}% (threshold: 95%)")
        print()
        
        # Critical path details
        print("🎯 Critical Path Coverage:")
        critical_modules = [m for m in report.modules if m.is_critical_path]
        if critical_modules:
            for module in sorted(critical_modules, key=lambda x: x.coverage):
                status = "✅" if module.coverage >= 90 else "❌"
                print(f"  {status} {module.name}: {module.coverage:.1f}%")
        else:
            print("  No critical path modules found")
        print()
        
        # Coverage gaps
        if report.gaps:
            print(f"🔍 Coverage Gaps ({len(report.gaps)} found):")
            high_priority_gaps = [g for g in report.gaps if g["priority"] == "high"]
            medium_priority_gaps = [g for g in report.gaps if g["priority"] == "medium"]
            
            if high_priority_gaps:
                print(f"  High Priority ({len(high_priority_gaps)}):")
                for gap in high_priority_gaps[:5]:  # Show top 5
                    print(f"    ❌ {gap['file']}: {gap.get('coverage', 0):.1f}% coverage")
            
            if medium_priority_gaps:
                print(f"  Medium Priority ({len(medium_priority_gaps)}):")
                for gap in medium_priority_gaps[:3]:  # Show top 3
                    print(f"    ⚠️  {gap['file']}: {gap.get('coverage', 0):.1f}% coverage")
        else:
            print("🎉 No significant coverage gaps found!")
        
        print()
        
        # Final status
        if report.thresholds_met:
            print("🎉 ALL COVERAGE THRESHOLDS MET!")
        else:
            print("💥 COVERAGE THRESHOLDS NOT MET")
        
        print("=" * 80)

    def save_report(self, report: CoverageReport, filename: str = "coverage-report.json"):
        """Save coverage report to JSON file."""
        try:
            # Convert dataclasses to dict
            report_dict = asdict(report)
            
            with open(filename, 'w') as f:
                json.dump(report_dict, f, indent=2)
            
            print(f"📄 Coverage report saved to {filename}")
            
        except Exception as e:
            print(f"⚠️  Failed to save coverage report: {e}")

    def generate_ci_artifacts(self, report: CoverageReport):
        """Generate CI/CD artifacts for coverage reporting."""
        print("🔧 Generating CI/CD artifacts...")
        
        # Create coverage badge data
        badge_data = {
            "schemaVersion": 1,
            "label": "coverage",
            "message": f"{report.total_coverage:.1f}%",
            "color": "green" if report.total_coverage >= 80 else "orange" if report.total_coverage >= 60 else "red"
        }
        
        with open("coverage-badge.json", 'w') as f:
            json.dump(badge_data, f)
        
        # Create GitHub Actions summary
        summary_lines = [
            "## Coverage Report",
            f"- **Overall Coverage**: {report.total_coverage:.1f}%",
            f"- **Critical Path Coverage**: {report.critical_path_coverage:.1f}%",
            f"- **Status**: {report.ci_status}",
            "",
            "### Critical Paths",
        ]
        
        critical_modules = [m for m in report.modules if m.is_critical_path]
        for module in critical_modules:
            status_icon = "✅" if module.coverage >= 90 else "❌"
            summary_lines.append(f"- {status_icon} `{module.name}`: {module.coverage:.1f}%")
        
        if report.gaps:
            summary_lines.extend([
                "",
                "### Coverage Gaps",
            ])
            for gap in report.gaps[:5]:  # Top 5 gaps
                priority_icon = "🔴" if gap["priority"] == "high" else "🟡"
                summary_lines.append(f"- {priority_icon} `{gap['file']}`: {gap.get('coverage', 0):.1f}%")
        
        with open("coverage-summary.md", 'w') as f:
            f.write("\n".join(summary_lines))
        
        print("  ✅ CI artifacts generated")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Coverage analysis tool")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose output")
    parser.add_argument("--test-paths", nargs="+",
                       help="Specific test paths to run")
    parser.add_argument("--report", default="coverage-report.json",
                       help="Coverage report output file")
    parser.add_argument("--ci", action="store_true",
                       help="Generate CI/CD artifacts")
    parser.add_argument("--fail-under", type=float, default=80.0,
                       help="Fail if coverage is under this threshold")
    
    args = parser.parse_args()
    
    try:
        # Initialize analyzer
        analyzer = CoverageAnalyzer(verbose=args.verbose)
        
        # Run analysis
        report = analyzer.run_coverage_analysis(args.test_paths)
        
        # Print summary
        analyzer.print_report_summary(report)
        
        # Save report
        analyzer.save_report(report, args.report)
        
        # Generate CI artifacts if requested
        if args.ci:
            analyzer.generate_ci_artifacts(report)
        
        # Exit with appropriate code
        if not report.thresholds_met or report.total_coverage < args.fail_under:
            print(f"\n❌ Coverage analysis failed (threshold: {args.fail_under}%)")
            sys.exit(1)
        else:
            print(f"\n✅ Coverage analysis passed")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n⚠️  Coverage analysis interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Coverage analysis failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()