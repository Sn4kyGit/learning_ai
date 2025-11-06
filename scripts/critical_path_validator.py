#!/usr/bin/env python3
"""
Critical path coverage validator.

This script validates that critical code paths have 100% test coverage
and provides detailed analysis of any gaps in critical functionality.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Set
import argparse
import ast
import re


class CriticalPathValidator:
    """Validates coverage for critical code paths."""
    
    # Critical paths that MUST have 100% coverage
    CRITICAL_PATHS = {
        "AI Services": {
            "paths": [
                "backend/ai/gpt5_classifier.py",
                "backend/ai/claude_advisor.py", 
                "backend/ai/cost_tracker.py",
                "backend/ai/language_detector.py"
            ],
            "required_coverage": 100.0,
            "justification": "AI integrations handle sensitive data and API costs"
        },
        "Authentication": {
            "paths": [
                "backend/services/auth_service.py",
                "backend/services/auth_dependencies.py",
                "backend/routes/auth.py"
            ],
            "required_coverage": 100.0,
            "justification": "Security-critical authentication and authorization"
        },
        "Data Processing": {
            "paths": [
                "backend/services/review/processor.py",
                "backend/db/repositories/review.py",
                "backend/db/repositories/business.py"
            ],
            "required_coverage": 100.0,
            "justification": "Core business logic for review processing"
        },
        "External APIs": {
            "paths": [
                "backend/external/google_places.py",
                "backend/external/base_client.py"
            ],
            "required_coverage": 95.0,
            "justification": "External API integrations with error handling"
        },
        "Database Models": {
            "paths": [
                "backend/db/models.py",
                "backend/db/schemas.py"
            ],
            "required_coverage": 95.0,
            "justification": "Data integrity and validation logic"
        }
    }
    
    # Critical functions that must be tested (regex patterns)
    CRITICAL_FUNCTION_PATTERNS = [
        r".*authenticate.*",
        r".*authorize.*", 
        r".*validate.*",
        r".*process.*review.*",
        r".*classify.*",
        r".*generate.*response.*",
        r".*calculate.*cost.*",
        r".*save.*",
        r".*create.*",
        r".*update.*",
        r".*delete.*"
    ]
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.coverage_data = None
        self.validation_results = {}
    
    def validate_critical_paths(self, coverage_file: str = "coverage.json") -> Dict[str, Any]:
        """Validate coverage for all critical paths."""
        print("🎯 Validating critical path coverage...")
        
        # Load coverage data
        self.coverage_data = self._load_coverage_data(coverage_file)
        
        # Validate each critical path category
        for category, config in self.CRITICAL_PATHS.items():
            result = self._validate_path_category(category, config)
            self.validation_results[category] = result
        
        # Generate overall validation report
        report = self._generate_validation_report()
        
        return report
    
    def _load_coverage_data(self, coverage_file: str) -> Dict[str, Any]:
        """Load coverage data from JSON file."""
        if not os.path.exists(coverage_file):
            raise FileNotFoundError(f"Coverage file not found: {coverage_file}")
        
        with open(coverage_file, 'r') as f:
            return json.load(f)
    
    def _validate_path_category(self, category: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate coverage for a specific critical path category."""
        print(f"  Validating {category}...")
        
        paths = config["paths"]
        required_coverage = config["required_coverage"]
        files = self.coverage_data.get("files", {})
        
        category_result = {
            "category": category,
            "required_coverage": required_coverage,
            "justification": config["justification"],
            "files": [],
            "overall_coverage": 0.0,
            "passes_threshold": False,
            "critical_gaps": []
        }
        
        total_statements = 0
        total_missing = 0
        
        for path in paths:
            file_result = self._validate_file_coverage(path, required_coverage, files)
            category_result["files"].append(file_result)
            
            if file_result["exists"]:
                total_statements += file_result["statements"]
                total_missing += file_result["missing_lines"]
        
        # Calculate overall coverage for this category
        if total_statements > 0:
            category_result["overall_coverage"] = ((total_statements - total_missing) / total_statements) * 100
        else:
            category_result["overall_coverage"] = 100.0
        
        category_result["passes_threshold"] = category_result["overall_coverage"] >= required_coverage
        
        # Identify critical gaps
        category_result["critical_gaps"] = self._identify_critical_gaps(category_result["files"])
        
        status = "✅" if category_result["passes_threshold"] else "❌"
        print(f"    {status} {category}: {category_result['overall_coverage']:.1f}% (required: {required_coverage}%)")
        
        return category_result
    
    def _validate_file_coverage(self, file_path: str, required_coverage: float, files: Dict[str, Any]) -> Dict[str, Any]:
        """Validate coverage for a specific file."""
        file_result = {
            "path": file_path,
            "exists": False,
            "coverage": 0.0,
            "statements": 0,
            "missing_lines": 0,
            "missing_line_numbers": [],
            "passes_threshold": False,
            "critical_functions": [],
            "untested_critical_functions": []
        }
        
        # Check if file exists in coverage data
        if file_path not in files:
            if self.verbose:
                print(f"    ⚠️  File not found in coverage: {file_path}")
            return file_result
        
        file_data = files[file_path]
        summary = file_data.get("summary", {})
        
        file_result.update({
            "exists": True,
            "coverage": summary.get("percent_covered", 0),
            "statements": summary.get("num_statements", 0),
            "missing_lines": len(file_data.get("missing_lines", [])),
            "missing_line_numbers": file_data.get("missing_lines", []),
            "passes_threshold": summary.get("percent_covered", 0) >= required_coverage
        })
        
        # Analyze critical functions in this file
        if os.path.exists(file_path):
            critical_analysis = self._analyze_critical_functions(file_path, file_result["missing_line_numbers"])
            file_result.update(critical_analysis)
        
        return file_result
    
    def _analyze_critical_functions(self, file_path: str, missing_lines: List[int]) -> Dict[str, Any]:
        """Analyze critical functions in a file and check their coverage."""
        critical_functions = []
        untested_critical_functions = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_name = node.name
                    
                    # Check if function matches critical patterns
                    is_critical = any(
                        re.match(pattern, func_name, re.IGNORECASE)
                        for pattern in self.CRITICAL_FUNCTION_PATTERNS
                    )
                    
                    if is_critical:
                        func_info = {
                            "name": func_name,
                            "line_number": node.lineno,
                            "is_async": isinstance(node, ast.AsyncFunctionDef),
                            "is_tested": node.lineno not in missing_lines
                        }
                        
                        critical_functions.append(func_info)
                        
                        if not func_info["is_tested"]:
                            untested_critical_functions.append(func_info)
        
        except Exception as e:
            if self.verbose:
                print(f"    ⚠️  Could not analyze {file_path}: {e}")
        
        return {
            "critical_functions": critical_functions,
            "untested_critical_functions": untested_critical_functions
        }
    
    def _identify_critical_gaps(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify critical coverage gaps that need immediate attention."""
        gaps = []
        
        for file_result in files:
            if not file_result["exists"]:
                gaps.append({
                    "type": "missing_file",
                    "file": file_result["path"],
                    "severity": "critical",
                    "description": "File not found in coverage data"
                })
                continue
            
            if not file_result["passes_threshold"]:
                gaps.append({
                    "type": "low_coverage",
                    "file": file_result["path"],
                    "severity": "high",
                    "coverage": file_result["coverage"],
                    "missing_lines": file_result["missing_lines"],
                    "description": f"Coverage {file_result['coverage']:.1f}% below required threshold"
                })
            
            # Check for untested critical functions
            if file_result["untested_critical_functions"]:
                for func in file_result["untested_critical_functions"]:
                    gaps.append({
                        "type": "untested_critical_function",
                        "file": file_result["path"],
                        "severity": "critical",
                        "function": func["name"],
                        "line_number": func["line_number"],
                        "description": f"Critical function '{func['name']}' is not tested"
                    })
        
        return gaps
    
    def _generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        print("📋 Generating critical path validation report...")
        
        # Calculate overall metrics
        total_categories = len(self.validation_results)
        passing_categories = len([r for r in self.validation_results.values() if r["passes_threshold"]])
        
        # Collect all critical gaps
        all_gaps = []
        for result in self.validation_results.values():
            all_gaps.extend(result["critical_gaps"])
        
        # Categorize gaps by severity
        critical_gaps = [g for g in all_gaps if g["severity"] == "critical"]
        high_gaps = [g for g in all_gaps if g["severity"] == "high"]
        
        # Determine overall validation status
        validation_passed = (
            passing_categories == total_categories and
            len(critical_gaps) == 0
        )
        
        report = {
            "validation_passed": validation_passed,
            "summary": {
                "total_categories": total_categories,
                "passing_categories": passing_categories,
                "total_gaps": len(all_gaps),
                "critical_gaps": len(critical_gaps),
                "high_priority_gaps": len(high_gaps)
            },
            "categories": self.validation_results,
            "critical_gaps": critical_gaps,
            "high_priority_gaps": high_gaps,
            "recommendations": self._generate_recommendations(all_gaps)
        }
        
        return report
    
    def _generate_recommendations(self, gaps: List[Dict[str, Any]]) -> List[str]:
        """Generate actionable recommendations based on gaps."""
        recommendations = []
        
        # Group gaps by type
        gap_types = {}
        for gap in gaps:
            gap_type = gap["type"]
            if gap_type not in gap_types:
                gap_types[gap_type] = []
            gap_types[gap_type].append(gap)
        
        # Generate recommendations for each gap type
        if "missing_file" in gap_types:
            recommendations.append(
                f"Create test files for {len(gap_types['missing_file'])} missing critical path files"
            )
        
        if "low_coverage" in gap_types:
            recommendations.append(
                f"Increase coverage for {len(gap_types['low_coverage'])} critical files below threshold"
            )
        
        if "untested_critical_function" in gap_types:
            recommendations.append(
                f"Add tests for {len(gap_types['untested_critical_function'])} untested critical functions"
            )
        
        # Add specific recommendations
        recommendations.extend([
            "Focus on testing error handling and edge cases in critical paths",
            "Ensure all authentication and authorization flows are fully tested",
            "Validate all data processing pipelines with comprehensive test cases",
            "Mock external API calls to ensure reliable testing",
            "Use property-based testing for data validation functions"
        ])
        
        return recommendations
    
    def print_validation_report(self, report: Dict[str, Any]):
        """Print detailed validation report."""
        print("\n" + "=" * 80)
        print("🎯 CRITICAL PATH COVERAGE VALIDATION")
        print("=" * 80)
        
        summary = report["summary"]
        
        # Overall status
        if report["validation_passed"]:
            print("✅ ALL CRITICAL PATHS MEET COVERAGE REQUIREMENTS")
        else:
            print("❌ CRITICAL PATH COVERAGE VALIDATION FAILED")
        
        print()
        print(f"Categories: {summary['passing_categories']}/{summary['total_categories']} passing")
        print(f"Critical Gaps: {summary['critical_gaps']}")
        print(f"High Priority Gaps: {summary['high_priority_gaps']}")
        print()
        
        # Category details
        print("📊 Category Results:")
        for category, result in report["categories"].items():
            status = "✅" if result["passes_threshold"] else "❌"
            print(f"  {status} {category}: {result['overall_coverage']:.1f}% (required: {result['required_coverage']}%)")
            
            if self.verbose and not result["passes_threshold"]:
                print(f"      Justification: {result['justification']}")
                for file_result in result["files"]:
                    if file_result["exists"] and not file_result["passes_threshold"]:
                        print(f"      - {file_result['path']}: {file_result['coverage']:.1f}%")
        
        print()
        
        # Critical gaps
        if report["critical_gaps"]:
            print("🔴 Critical Gaps (Must Fix):")
            for gap in report["critical_gaps"][:10]:  # Show top 10
                if gap["type"] == "untested_critical_function":
                    print(f"  • {gap['file']}:{gap['line_number']} - Function '{gap['function']}' not tested")
                else:
                    print(f"  • {gap['file']} - {gap['description']}")
            print()
        
        # High priority gaps
        if report["high_priority_gaps"]:
            print("🟠 High Priority Gaps:")
            for gap in report["high_priority_gaps"][:5]:  # Show top 5
                print(f"  • {gap['file']} - {gap['description']}")
            print()
        
        # Recommendations
        if report["recommendations"]:
            print("💡 Recommendations:")
            for rec in report["recommendations"]:
                print(f"  • {rec}")
            print()
        
        print("=" * 80)
    
    def save_validation_report(self, report: Dict[str, Any], filename: str = "critical-path-validation.json"):
        """Save validation report to JSON file."""
        try:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            
            print(f"📄 Critical path validation report saved to {filename}")
            
        except Exception as e:
            print(f"⚠️  Failed to save validation report: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Critical path coverage validator")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose output")
    parser.add_argument("--coverage-file", default="coverage.json",
                       help="Coverage JSON file to validate")
    parser.add_argument("--output", default="critical-path-validation.json",
                       help="Output file for validation report")
    parser.add_argument("--fail-on-gaps", action="store_true",
                       help="Exit with error code if critical gaps found")
    
    args = parser.parse_args()
    
    try:
        # Initialize validator
        validator = CriticalPathValidator(verbose=args.verbose)
        
        # Run validation
        report = validator.validate_critical_paths(args.coverage_file)
        
        # Print report
        validator.print_validation_report(report)
        
        # Save report
        validator.save_validation_report(report, args.output)
        
        # Exit with appropriate code
        if args.fail_on_gaps and not report["validation_passed"]:
            print(f"\n❌ Critical path validation failed")
            sys.exit(1)
        else:
            print(f"\n✅ Critical path validation completed")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n⚠️  Validation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Validation failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()