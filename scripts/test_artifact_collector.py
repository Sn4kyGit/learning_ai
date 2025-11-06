#!/usr/bin/env python3
"""
Test Artifact Collector for CI/CD Integration.

This script collects, analyzes, and organizes test artifacts
for comprehensive CI/CD reporting and debugging.
"""

import os
import sys
import json
import shutil
import zipfile
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import argparse
import subprocess


class TestArtifactCollector:
    """Comprehensive test artifact collection and analysis."""
    
    def __init__(self, workspace_root: str = ".", verbose: bool = False):
        self.workspace_root = Path(workspace_root)
        self.verbose = verbose
        self.artifacts = {}
        self.collection_timestamp = datetime.now().isoformat()
        
        # Define artifact patterns and locations
        self.artifact_patterns = {
            "test_results": [
                "test-results-*.json",
                "frontend-test-results-*.json",
                "**/test_results.json",
                "pytest-results.xml",
                "vitest-results.json"
            ],
            "coverage_reports": [
                "coverage.xml",
                "coverage.json",
                "coverage-*.xml",
                "coverage-*.json",
                "htmlcov/**/*",
                "frontend/coverage/**/*",
                ".coverage*"
            ],
            "performance_data": [
                "benchmark-*.json",
                "performance-*.json",
                "current-performance.json",
                "performance-baseline.json",
                "load-test-results.json"
            ],
            "quality_reports": [
                "flake8-report.json",
                "mypy-report/**/*",
                "black-report.txt",
                "isort-report.txt",
                "frontend-lint-report.json",
                "frontend-typecheck-report.txt"
            ],
            "security_scans": [
                "trivy-results.sarif",
                "security-summary.txt",
                "bandit-report.json",
                "safety-report.json"
            ],
            "logs": [
                "pytest.log",
                "test-*.log",
                "ci-*.log",
                "backend/logs/**/*",
                "frontend/logs/**/*"
            ],
            "screenshots": [
                "screenshots/**/*",
                "test-screenshots/**/*",
                "e2e-screenshots/**/*",
                "cypress/screenshots/**/*"
            ],
            "videos": [
                "videos/**/*",
                "test-videos/**/*",
                "cypress/videos/**/*"
            ]
        }
    
    def log(self, message: str):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    def collect_artifacts(self) -> Dict[str, Any]:
        """Collect all test artifacts from the workspace."""
        self.log("Starting artifact collection...")
        
        collected_artifacts = {
            "collection_info": {
                "timestamp": self.collection_timestamp,
                "workspace_root": str(self.workspace_root.absolute()),
                "collector_version": "1.0.0"
            },
            "artifacts": {},
            "summary": {
                "total_files": 0,
                "total_size_bytes": 0,
                "categories": {}
            }
        }
        
        for category, patterns in self.artifact_patterns.items():
            self.log(f"Collecting {category} artifacts...")
            
            category_artifacts = []
            category_size = 0
            
            for pattern in patterns:
                matching_files = list(self.workspace_root.glob(pattern))
                
                for file_path in matching_files:
                    if file_path.is_file():
                        try:
                            file_size = file_path.stat().st_size
                            relative_path = file_path.relative_to(self.workspace_root)
                            
                            artifact_info = {
                                "path": str(relative_path),
                                "absolute_path": str(file_path),
                                "size_bytes": file_size,
                                "modified_time": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                                "pattern": pattern
                            }
                            
                            # Add content analysis for specific file types
                            if file_path.suffix == '.json':
                                artifact_info.update(self._analyze_json_file(file_path))
                            elif file_path.suffix in ['.xml', '.sarif']:
                                artifact_info.update(self._analyze_xml_file(file_path))
                            elif file_path.suffix in ['.log', '.txt']:
                                artifact_info.update(self._analyze_text_file(file_path))
                            
                            category_artifacts.append(artifact_info)
                            category_size += file_size
                            
                        except Exception as e:
                            self.log(f"Error processing {file_path}: {e}")
            
            collected_artifacts["artifacts"][category] = category_artifacts
            collected_artifacts["summary"]["categories"][category] = {
                "file_count": len(category_artifacts),
                "total_size_bytes": category_size
            }
            
            collected_artifacts["summary"]["total_files"] += len(category_artifacts)
            collected_artifacts["summary"]["total_size_bytes"] += category_size
            
            self.log(f"Collected {len(category_artifacts)} {category} artifacts ({category_size} bytes)")
        
        self.artifacts = collected_artifacts
        return collected_artifacts
    
    def _analyze_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze JSON file content."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            analysis = {
                "content_type": "json",
                "json_keys": list(data.keys()) if isinstance(data, dict) else [],
                "json_size": len(str(data))
            }
            
            # Specific analysis for test results
            if "summary" in data and isinstance(data["summary"], dict):
                analysis["test_summary"] = {
                    "total": data["summary"].get("total", 0),
                    "passed": data["summary"].get("passed", 0),
                    "failed": data["summary"].get("failed", 0),
                    "skipped": data["summary"].get("skipped", 0)
                }
            
            # Coverage analysis
            if "totals" in data and "percent_covered" in data["totals"]:
                analysis["coverage_percentage"] = data["totals"]["percent_covered"]
            
            return analysis
            
        except Exception as e:
            return {"content_type": "json", "analysis_error": str(e)}
    
    def _analyze_xml_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze XML file content."""
        try:
            file_size = file_path.stat().st_size
            
            # Basic XML analysis
            with open(file_path, 'r') as f:
                content = f.read(1000)  # Read first 1KB
            
            analysis = {
                "content_type": "xml",
                "xml_preview": content[:200] + "..." if len(content) > 200 else content
            }
            
            # Check for specific XML types
            if "testsuite" in content.lower():
                analysis["xml_type"] = "junit_results"
            elif "coverage" in content.lower():
                analysis["xml_type"] = "coverage_report"
            elif "sarif" in content.lower():
                analysis["xml_type"] = "security_scan"
            
            return analysis
            
        except Exception as e:
            return {"content_type": "xml", "analysis_error": str(e)}
    
    def _analyze_text_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze text file content."""
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            analysis = {
                "content_type": "text",
                "line_count": len(lines),
                "preview": "".join(lines[:5])  # First 5 lines
            }
            
            # Look for error patterns
            error_patterns = ["ERROR", "FAILED", "Exception", "Traceback"]
            error_lines = []
            
            for i, line in enumerate(lines):
                if any(pattern in line for pattern in error_patterns):
                    error_lines.append({"line_number": i + 1, "content": line.strip()})
                    if len(error_lines) >= 10:  # Limit to first 10 errors
                        break
            
            if error_lines:
                analysis["errors_found"] = error_lines
            
            return analysis
            
        except Exception as e:
            return {"content_type": "text", "analysis_error": str(e)}
    
    def generate_artifact_report(self) -> Dict[str, Any]:
        """Generate comprehensive artifact analysis report."""
        self.log("Generating artifact analysis report...")
        
        if not self.artifacts:
            self.collect_artifacts()
        
        report = {
            "report_info": {
                "generated_at": datetime.now().isoformat(),
                "collection_timestamp": self.collection_timestamp,
                "workspace": str(self.workspace_root.absolute())
            },
            "summary": self.artifacts["summary"],
            "analysis": {
                "test_results": self._analyze_test_results(),
                "coverage_analysis": self._analyze_coverage_data(),
                "performance_analysis": self._analyze_performance_data(),
                "quality_analysis": self._analyze_quality_reports(),
                "security_analysis": self._analyze_security_scans()
            },
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _analyze_test_results(self) -> Dict[str, Any]:
        """Analyze collected test results."""
        test_artifacts = self.artifacts["artifacts"].get("test_results", [])
        
        analysis = {
            "total_test_files": len(test_artifacts),
            "test_suites": [],
            "overall_stats": {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "skipped_tests": 0
            }
        }
        
        for artifact in test_artifacts:
            if "test_summary" in artifact:
                summary = artifact["test_summary"]
                suite_info = {
                    "file": artifact["path"],
                    "total": summary.get("total", 0),
                    "passed": summary.get("passed", 0),
                    "failed": summary.get("failed", 0),
                    "skipped": summary.get("skipped", 0)
                }
                analysis["test_suites"].append(suite_info)
                
                # Aggregate stats
                analysis["overall_stats"]["total_tests"] += suite_info["total"]
                analysis["overall_stats"]["passed_tests"] += suite_info["passed"]
                analysis["overall_stats"]["failed_tests"] += suite_info["failed"]
                analysis["overall_stats"]["skipped_tests"] += suite_info["skipped"]
        
        # Calculate success rate
        total = analysis["overall_stats"]["total_tests"]
        passed = analysis["overall_stats"]["passed_tests"]
        analysis["overall_stats"]["success_rate"] = (passed / total * 100) if total > 0 else 0
        
        return analysis
    
    def _analyze_coverage_data(self) -> Dict[str, Any]:
        """Analyze coverage reports."""
        coverage_artifacts = self.artifacts["artifacts"].get("coverage_reports", [])
        
        analysis = {
            "coverage_files": len(coverage_artifacts),
            "coverage_data": []
        }
        
        for artifact in coverage_artifacts:
            if "coverage_percentage" in artifact:
                coverage_info = {
                    "file": artifact["path"],
                    "percentage": artifact["coverage_percentage"]
                }
                analysis["coverage_data"].append(coverage_info)
        
        # Calculate average coverage if multiple files
        if analysis["coverage_data"]:
            percentages = [c["percentage"] for c in analysis["coverage_data"]]
            analysis["average_coverage"] = sum(percentages) / len(percentages)
        
        return analysis
    
    def _analyze_performance_data(self) -> Dict[str, Any]:
        """Analyze performance test data."""
        perf_artifacts = self.artifacts["artifacts"].get("performance_data", [])
        
        analysis = {
            "performance_files": len(perf_artifacts),
            "benchmarks": [],
            "regressions_detected": False
        }
        
        for artifact in perf_artifacts:
            if artifact["path"].endswith(".json"):
                try:
                    with open(artifact["absolute_path"], 'r') as f:
                        data = json.load(f)
                    
                    if "benchmarks" in data:
                        analysis["benchmarks"].extend(data["benchmarks"])
                    
                    if "has_regressions" in data:
                        analysis["regressions_detected"] = data["has_regressions"]
                        
                except Exception as e:
                    self.log(f"Error analyzing performance file {artifact['path']}: {e}")
        
        return analysis
    
    def _analyze_quality_reports(self) -> Dict[str, Any]:
        """Analyze code quality reports."""
        quality_artifacts = self.artifacts["artifacts"].get("quality_reports", [])
        
        analysis = {
            "quality_files": len(quality_artifacts),
            "linting_issues": 0,
            "type_errors": 0,
            "format_issues": 0
        }
        
        for artifact in quality_artifacts:
            if "flake8" in artifact["path"]:
                # Analyze flake8 report
                try:
                    with open(artifact["absolute_path"], 'r') as f:
                        data = json.load(f)
                    analysis["linting_issues"] += len(data)
                except:
                    pass
            
            elif "mypy" in artifact["path"]:
                # Count mypy errors
                if "errors_found" in artifact:
                    analysis["type_errors"] += len(artifact["errors_found"])
        
        return analysis
    
    def _analyze_security_scans(self) -> Dict[str, Any]:
        """Analyze security scan results."""
        security_artifacts = self.artifacts["artifacts"].get("security_scans", [])
        
        analysis = {
            "security_files": len(security_artifacts),
            "vulnerabilities": 0,
            "severity_breakdown": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            }
        }
        
        for artifact in security_artifacts:
            if artifact["path"].endswith(".sarif"):
                try:
                    with open(artifact["absolute_path"], 'r') as f:
                        data = json.load(f)
                    
                    if "runs" in data and data["runs"]:
                        results = data["runs"][0].get("results", [])
                        analysis["vulnerabilities"] += len(results)
                        
                        # Analyze severity levels
                        for result in results:
                            level = result.get("level", "unknown")
                            if level in analysis["severity_breakdown"]:
                                analysis["severity_breakdown"][level] += 1
                                
                except Exception as e:
                    self.log(f"Error analyzing security file {artifact['path']}: {e}")
        
        return analysis
    
    def _generate_recommendations(self) -> List[Dict[str, str]]:
        """Generate recommendations based on artifact analysis."""
        recommendations = []
        
        # Analyze test results
        test_analysis = self._analyze_test_results()
        if test_analysis["overall_stats"]["success_rate"] < 95:
            recommendations.append({
                "category": "testing",
                "priority": "high",
                "message": f"Test success rate is {test_analysis['overall_stats']['success_rate']:.1f}%. Consider investigating failing tests."
            })
        
        # Analyze coverage
        coverage_analysis = self._analyze_coverage_data()
        if coverage_analysis.get("average_coverage", 0) < 80:
            recommendations.append({
                "category": "coverage",
                "priority": "medium",
                "message": f"Code coverage is {coverage_analysis.get('average_coverage', 0):.1f}%. Consider adding more tests."
            })
        
        # Analyze performance
        perf_analysis = self._analyze_performance_data()
        if perf_analysis["regressions_detected"]:
            recommendations.append({
                "category": "performance",
                "priority": "high",
                "message": "Performance regressions detected. Review performance test results."
            })
        
        # Analyze security
        security_analysis = self._analyze_security_scans()
        if security_analysis["vulnerabilities"] > 0:
            critical = security_analysis["severity_breakdown"]["critical"]
            high = security_analysis["severity_breakdown"]["high"]
            
            if critical > 0 or high > 0:
                recommendations.append({
                    "category": "security",
                    "priority": "critical",
                    "message": f"Found {critical} critical and {high} high severity vulnerabilities. Address immediately."
                })
        
        return recommendations
    
    def create_artifact_archive(self, output_path: str = "test-artifacts.zip") -> str:
        """Create a compressed archive of all collected artifacts."""
        self.log(f"Creating artifact archive: {output_path}")
        
        if not self.artifacts:
            self.collect_artifacts()
        
        archive_path = Path(output_path)
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add artifact metadata
            metadata = {
                "archive_info": {
                    "created_at": datetime.now().isoformat(),
                    "collection_timestamp": self.collection_timestamp,
                    "total_files": self.artifacts["summary"]["total_files"],
                    "total_size_bytes": self.artifacts["summary"]["total_size_bytes"]
                },
                "artifacts": self.artifacts
            }
            
            zipf.writestr("artifact-metadata.json", json.dumps(metadata, indent=2))
            
            # Add all collected artifacts
            for category, artifacts in self.artifacts["artifacts"].items():
                for artifact in artifacts:
                    file_path = Path(artifact["absolute_path"])
                    if file_path.exists() and file_path.is_file():
                        # Use relative path in archive
                        archive_name = f"{category}/{artifact['path']}"
                        zipf.write(file_path, archive_name)
        
        self.log(f"Artifact archive created: {archive_path} ({archive_path.stat().st_size} bytes)")
        return str(archive_path)
    
    def save_report(self, report: Dict[str, Any], output_path: str = "artifact-analysis-report.json"):
        """Save artifact analysis report to file."""
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.log(f"Artifact analysis report saved: {output_path}")


def main():
    """Main entry point for test artifact collector."""
    parser = argparse.ArgumentParser(description="Test Artifact Collector for CI/CD")
    parser.add_argument("--workspace", "-w", default=".", help="Workspace root directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--output-report", default="artifact-analysis-report.json", 
                       help="Output file for analysis report")
    parser.add_argument("--output-archive", default="test-artifacts.zip", 
                       help="Output file for artifact archive")
    parser.add_argument("--collect-only", action="store_true", 
                       help="Only collect artifacts, don't create archive")
    parser.add_argument("--analyze-only", action="store_true", 
                       help="Only analyze existing artifacts, don't collect new ones")
    
    args = parser.parse_args()
    
    try:
        collector = TestArtifactCollector(
            workspace_root=args.workspace,
            verbose=args.verbose
        )
        
        if not args.analyze_only:
            # Collect artifacts
            artifacts = collector.collect_artifacts()
            print(f"Collected {artifacts['summary']['total_files']} artifacts "
                  f"({artifacts['summary']['total_size_bytes']} bytes)")
        
        # Generate analysis report
        report = collector.generate_artifact_report()
        collector.save_report(report, args.output_report)
        
        # Print summary
        print("\n=== Artifact Analysis Summary ===")
        print(f"Test Files: {report['analysis']['test_results']['total_test_files']}")
        print(f"Overall Test Success Rate: {report['analysis']['test_results']['overall_stats']['success_rate']:.1f}%")
        
        if report['analysis']['coverage_analysis'].get('average_coverage'):
            print(f"Average Coverage: {report['analysis']['coverage_analysis']['average_coverage']:.1f}%")
        
        print(f"Performance Files: {report['analysis']['performance_analysis']['performance_files']}")
        print(f"Security Vulnerabilities: {report['analysis']['security_analysis']['vulnerabilities']}")
        
        # Print recommendations
        if report['recommendations']:
            print("\n=== Recommendations ===")
            for rec in report['recommendations']:
                priority_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(rec['priority'], "ℹ️")
                print(f"{priority_icon} [{rec['category'].upper()}] {rec['message']}")
        
        # Create archive if requested
        if not args.collect_only:
            archive_path = collector.create_artifact_archive(args.output_archive)
            print(f"\nArtifact archive created: {archive_path}")
        
        # Exit with appropriate code based on critical issues
        critical_issues = any(rec['priority'] == 'critical' for rec in report['recommendations'])
        sys.exit(1 if critical_issues else 0)
        
    except Exception as e:
        print(f"Artifact collection failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()