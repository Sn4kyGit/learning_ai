#!/usr/bin/env python3
"""
Coverage gap analysis and improvement recommendations.

This script analyzes coverage gaps and provides actionable recommendations
for improving test coverage in the Local Business Intelligence Bot.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import ast
import argparse


@dataclass
class FunctionInfo:
    """Information about a function in the codebase."""
    name: str
    line_number: int
    is_async: bool
    is_method: bool
    class_name: str = None
    docstring: str = None
    complexity: int = 0
    is_tested: bool = False


@dataclass
class CoverageGap:
    """Represents a coverage gap with improvement recommendations."""
    file_path: str
    gap_type: str
    severity: str
    description: str
    missing_lines: List[int]
    functions: List[FunctionInfo]
    recommendations: List[str]
    estimated_effort: str


class CoverageGapAnalyzer:
    """Analyzes coverage gaps and provides improvement recommendations."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.coverage_data = None
        self.source_files = {}
        
    def analyze_gaps(self, coverage_file: str = "coverage.json") -> List[CoverageGap]:
        """Analyze coverage gaps and generate recommendations."""
        print("🔍 Analyzing coverage gaps...")
        
        # Load coverage data
        self.coverage_data = self._load_coverage_data(coverage_file)
        
        # Analyze each file
        gaps = []
        files = self.coverage_data.get("files", {})
        
        for file_path, file_data in files.items():
            if self._should_skip_file(file_path):
                continue
            
            file_gaps = self._analyze_file_gaps(file_path, file_data)
            gaps.extend(file_gaps)
        
        # Sort gaps by severity and impact
        gaps.sort(key=lambda x: (
            {"critical": 0, "high": 1, "medium": 2, "low": 3}[x.severity],
            -len(x.missing_lines)
        ))
        
        print(f"  Found {len(gaps)} coverage gaps")
        return gaps
    
    def _load_coverage_data(self, coverage_file: str) -> Dict[str, Any]:
        """Load coverage data from JSON file."""
        if not os.path.exists(coverage_file):
            raise FileNotFoundError(f"Coverage file not found: {coverage_file}")
        
        with open(coverage_file, 'r') as f:
            return json.load(f)
    
    def _should_skip_file(self, file_path: str) -> bool:
        """Check if file should be skipped from gap analysis."""
        skip_patterns = [
            "/tests/",
            "/migrations/",
            "/alembic/",
            "__pycache__",
            "conftest.py",
            "test_",
            "_test.py"
        ]
        
        return any(pattern in file_path for pattern in skip_patterns)
    
    def _analyze_file_gaps(self, file_path: str, file_data: Dict[str, Any]) -> List[CoverageGap]:
        """Analyze coverage gaps for a specific file."""
        gaps = []
        
        summary = file_data.get("summary", {})
        coverage_pct = summary.get("percent_covered", 0)
        missing_lines = file_data.get("missing_lines", [])
        
        if not missing_lines:
            return gaps
        
        # Parse source file to understand structure
        functions = self._parse_source_file(file_path)
        
        # Identify different types of gaps
        if coverage_pct == 0:
            gaps.append(self._create_untested_file_gap(file_path, functions, missing_lines))
        elif coverage_pct < 50:
            gaps.append(self._create_low_coverage_gap(file_path, functions, missing_lines, coverage_pct))
        elif len(missing_lines) > 20:
            gaps.append(self._create_many_missing_lines_gap(file_path, functions, missing_lines, coverage_pct))
        else:
            gaps.append(self._create_partial_coverage_gap(file_path, functions, missing_lines, coverage_pct))
        
        return gaps
    
    def _parse_source_file(self, file_path: str) -> List[FunctionInfo]:
        """Parse source file to extract function information."""
        functions = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_info = FunctionInfo(
                        name=node.name,
                        line_number=node.lineno,
                        is_async=isinstance(node, ast.AsyncFunctionDef),
                        is_method=self._is_method(node, tree),
                        class_name=self._get_class_name(node, tree),
                        docstring=ast.get_docstring(node),
                        complexity=self._calculate_complexity(node)
                    )
                    functions.append(func_info)
        
        except Exception as e:
            if self.verbose:
                print(f"  ⚠️  Could not parse {file_path}: {e}")
        
        return functions
    
    def _is_method(self, func_node: ast.FunctionDef, tree: ast.AST) -> bool:
        """Check if function is a class method."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if item == func_node:
                        return True
        return False
    
    def _get_class_name(self, func_node: ast.FunctionDef, tree: ast.AST) -> str:
        """Get class name if function is a method."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if item == func_node:
                        return node.name
        return None
    
    def _calculate_complexity(self, func_node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of function."""
        complexity = 1  # Base complexity
        
        for node in ast.walk(func_node):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, (ast.And, ast.Or)):
                complexity += 1
        
        return complexity
    
    def _create_untested_file_gap(self, file_path: str, functions: List[FunctionInfo], missing_lines: List[int]) -> CoverageGap:
        """Create gap for completely untested file."""
        recommendations = [
            "Create comprehensive test file with unit tests for all functions",
            "Start with testing public API methods and critical business logic",
            "Use pytest fixtures for common test setup",
            "Mock external dependencies (database, APIs, file system)"
        ]
        
        if any(f.is_async for f in functions):
            recommendations.append("Use pytest-asyncio for async function testing")
        
        if any(f.class_name for f in functions):
            recommendations.append("Create test classes mirroring source class structure")
        
        return CoverageGap(
            file_path=file_path,
            gap_type="untested_file",
            severity="critical",
            description=f"File has 0% coverage with {len(functions)} untested functions",
            missing_lines=missing_lines,
            functions=functions,
            recommendations=recommendations,
            estimated_effort="high"
        )
    
    def _create_low_coverage_gap(self, file_path: str, functions: List[FunctionInfo], missing_lines: List[int], coverage_pct: float) -> CoverageGap:
        """Create gap for low coverage file."""
        untested_functions = self._identify_untested_functions(functions, missing_lines)
        
        recommendations = [
            f"Increase coverage from {coverage_pct:.1f}% to at least 80%",
            "Focus on testing untested functions first",
            "Add tests for error handling and edge cases",
            "Review existing tests for completeness"
        ]
        
        if untested_functions:
            recommendations.append(f"Priority functions to test: {', '.join(f.name for f in untested_functions[:3])}")
        
        return CoverageGap(
            file_path=file_path,
            gap_type="low_coverage",
            severity="high",
            description=f"File has low coverage ({coverage_pct:.1f}%) with {len(untested_functions)} untested functions",
            missing_lines=missing_lines,
            functions=untested_functions,
            recommendations=recommendations,
            estimated_effort="medium"
        )
    
    def _create_many_missing_lines_gap(self, file_path: str, functions: List[FunctionInfo], missing_lines: List[int], coverage_pct: float) -> CoverageGap:
        """Create gap for file with many missing lines."""
        untested_functions = self._identify_untested_functions(functions, missing_lines)
        
        recommendations = [
            f"Address {len(missing_lines)} missing lines of coverage",
            "Focus on complex functions with high cyclomatic complexity",
            "Add tests for conditional branches and error paths",
            "Consider breaking down large functions for better testability"
        ]
        
        complex_functions = [f for f in untested_functions if f.complexity > 5]
        if complex_functions:
            recommendations.append(f"High complexity functions to prioritize: {', '.join(f.name for f in complex_functions)}")
        
        return CoverageGap(
            file_path=file_path,
            gap_type="many_missing_lines",
            severity="medium",
            description=f"File has {len(missing_lines)} missing lines ({coverage_pct:.1f}% coverage)",
            missing_lines=missing_lines,
            functions=untested_functions,
            recommendations=recommendations,
            estimated_effort="medium"
        )
    
    def _create_partial_coverage_gap(self, file_path: str, functions: List[FunctionInfo], missing_lines: List[int], coverage_pct: float) -> CoverageGap:
        """Create gap for partially covered file."""
        untested_functions = self._identify_untested_functions(functions, missing_lines)
        
        recommendations = [
            "Add tests for remaining uncovered code paths",
            "Focus on error handling and edge cases",
            "Improve existing test assertions and coverage"
        ]
        
        if untested_functions:
            recommendations.append(f"Complete testing for: {', '.join(f.name for f in untested_functions)}")
        
        return CoverageGap(
            file_path=file_path,
            gap_type="partial_coverage",
            severity="low",
            description=f"File needs {len(missing_lines)} additional lines covered ({coverage_pct:.1f}% coverage)",
            missing_lines=missing_lines,
            functions=untested_functions,
            recommendations=recommendations,
            estimated_effort="low"
        )
    
    def _identify_untested_functions(self, functions: List[FunctionInfo], missing_lines: List[int]) -> List[FunctionInfo]:
        """Identify which functions are likely untested based on missing lines."""
        untested = []
        
        for func in functions:
            # Simple heuristic: if function start line is in missing lines, it's likely untested
            if func.line_number in missing_lines:
                untested.append(func)
        
        return untested
    
    def generate_improvement_plan(self, gaps: List[CoverageGap]) -> Dict[str, Any]:
        """Generate comprehensive improvement plan."""
        print("📋 Generating coverage improvement plan...")
        
        # Categorize gaps by severity
        critical_gaps = [g for g in gaps if g.severity == "critical"]
        high_gaps = [g for g in gaps if g.severity == "high"]
        medium_gaps = [g for g in gaps if g.severity == "medium"]
        low_gaps = [g for g in gaps if g.severity == "low"]
        
        # Calculate effort estimates
        effort_mapping = {"low": 1, "medium": 3, "high": 8}
        total_effort = sum(effort_mapping.get(gap.estimated_effort, 3) for gap in gaps)
        
        # Generate prioritized action items
        action_items = []
        
        # Phase 1: Critical gaps (untested files)
        if critical_gaps:
            action_items.append({
                "phase": 1,
                "title": "Address Critical Coverage Gaps",
                "description": "Create tests for completely untested files",
                "gaps": len(critical_gaps),
                "estimated_effort": f"{sum(effort_mapping.get(g.estimated_effort, 3) for g in critical_gaps)} story points",
                "files": [g.file_path for g in critical_gaps]
            })
        
        # Phase 2: High priority gaps (low coverage)
        if high_gaps:
            action_items.append({
                "phase": 2,
                "title": "Improve Low Coverage Files",
                "description": "Increase coverage for files below 50%",
                "gaps": len(high_gaps),
                "estimated_effort": f"{sum(effort_mapping.get(g.estimated_effort, 3) for g in high_gaps)} story points",
                "files": [g.file_path for g in high_gaps]
            })
        
        # Phase 3: Medium priority gaps
        if medium_gaps:
            action_items.append({
                "phase": 3,
                "title": "Address Remaining Gaps",
                "description": "Complete coverage for partially tested files",
                "gaps": len(medium_gaps),
                "estimated_effort": f"{sum(effort_mapping.get(g.estimated_effort, 3) for g in medium_gaps)} story points",
                "files": [g.file_path for g in medium_gaps]
            })
        
        # Generate specific recommendations
        recommendations = []
        
        # Testing framework recommendations
        async_functions = sum(len([f for f in gap.functions if f.is_async]) for gap in gaps)
        if async_functions > 0:
            recommendations.append("Set up pytest-asyncio for async function testing")
        
        # Mock recommendations
        external_deps = any("external" in gap.file_path or "client" in gap.file_path for gap in gaps)
        if external_deps:
            recommendations.append("Implement comprehensive mocking for external dependencies")
        
        # Database testing
        db_files = any("db" in gap.file_path or "repository" in gap.file_path for gap in gaps)
        if db_files:
            recommendations.append("Set up test database fixtures and transaction rollback")
        
        plan = {
            "summary": {
                "total_gaps": len(gaps),
                "critical_gaps": len(critical_gaps),
                "high_priority_gaps": len(high_gaps),
                "medium_priority_gaps": len(medium_gaps),
                "low_priority_gaps": len(low_gaps),
                "estimated_total_effort": f"{total_effort} story points"
            },
            "action_items": action_items,
            "recommendations": recommendations,
            "gaps_by_file": {gap.file_path: gap for gap in gaps}
        }
        
        return plan
    
    def print_gap_analysis(self, gaps: List[CoverageGap], plan: Dict[str, Any]):
        """Print detailed gap analysis."""
        print("\n" + "=" * 80)
        print("🔍 COVERAGE GAP ANALYSIS")
        print("=" * 80)
        
        summary = plan["summary"]
        print(f"Total Gaps: {summary['total_gaps']}")
        print(f"Critical: {summary['critical_gaps']}, High: {summary['high_priority_gaps']}, "
              f"Medium: {summary['medium_priority_gaps']}, Low: {summary['low_priority_gaps']}")
        print(f"Estimated Effort: {summary['estimated_total_effort']}")
        print()
        
        # Show top gaps by severity
        print("🎯 Top Priority Gaps:")
        top_gaps = gaps[:10]  # Show top 10
        
        for i, gap in enumerate(top_gaps, 1):
            severity_icon = {
                "critical": "🔴",
                "high": "🟠", 
                "medium": "🟡",
                "low": "🟢"
            }[gap.severity]
            
            print(f"{i:2d}. {severity_icon} {gap.file_path}")
            print(f"     {gap.description}")
            print(f"     Missing lines: {len(gap.missing_lines)}, Functions: {len(gap.functions)}")
            
            if self.verbose and gap.recommendations:
                print(f"     Recommendations:")
                for rec in gap.recommendations[:2]:  # Show first 2 recommendations
                    print(f"       • {rec}")
            print()
        
        # Show improvement plan
        print("📋 Improvement Plan:")
        for item in plan["action_items"]:
            print(f"Phase {item['phase']}: {item['title']}")
            print(f"  {item['description']}")
            print(f"  Files: {item['gaps']}, Effort: {item['estimated_effort']}")
            print()
        
        # Show general recommendations
        if plan["recommendations"]:
            print("💡 General Recommendations:")
            for rec in plan["recommendations"]:
                print(f"  • {rec}")
            print()
        
        print("=" * 80)
    
    def save_gap_analysis(self, gaps: List[CoverageGap], plan: Dict[str, Any], filename: str = "coverage-gaps.json"):
        """Save gap analysis to JSON file."""
        try:
            # Convert gaps to serializable format
            gaps_data = []
            for gap in gaps:
                gap_dict = {
                    "file_path": gap.file_path,
                    "gap_type": gap.gap_type,
                    "severity": gap.severity,
                    "description": gap.description,
                    "missing_lines": gap.missing_lines,
                    "functions": [
                        {
                            "name": f.name,
                            "line_number": f.line_number,
                            "is_async": f.is_async,
                            "is_method": f.is_method,
                            "class_name": f.class_name,
                            "complexity": f.complexity
                        }
                        for f in gap.functions
                    ],
                    "recommendations": gap.recommendations,
                    "estimated_effort": gap.estimated_effort
                }
                gaps_data.append(gap_dict)
            
            report = {
                "gaps": gaps_data,
                "improvement_plan": plan,
                "timestamp": __import__("time").strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            
            print(f"📄 Gap analysis saved to {filename}")
            
        except Exception as e:
            print(f"⚠️  Failed to save gap analysis: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Coverage gap analysis tool")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose output")
    parser.add_argument("--coverage-file", default="coverage.json",
                       help="Coverage JSON file to analyze")
    parser.add_argument("--output", default="coverage-gaps.json",
                       help="Output file for gap analysis")
    
    args = parser.parse_args()
    
    try:
        # Initialize analyzer
        analyzer = CoverageGapAnalyzer(verbose=args.verbose)
        
        # Analyze gaps
        gaps = analyzer.analyze_gaps(args.coverage_file)
        
        # Generate improvement plan
        plan = analyzer.generate_improvement_plan(gaps)
        
        # Print analysis
        analyzer.print_gap_analysis(gaps, plan)
        
        # Save analysis
        analyzer.save_gap_analysis(gaps, plan, args.output)
        
        # Exit with appropriate code based on critical gaps
        critical_gaps = [g for g in gaps if g.severity == "critical"]
        if critical_gaps:
            print(f"\n❌ Found {len(critical_gaps)} critical coverage gaps")
            sys.exit(1)
        else:
            print(f"\n✅ No critical coverage gaps found")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n⚠️  Gap analysis interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Gap analysis failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()