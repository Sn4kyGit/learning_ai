"""
Test documentation utilities.

This module provides utilities for generating test documentation
and maintaining test metadata.
"""

from typing import Dict, List, Any
from dataclasses import dataclass
import inspect


@dataclass
class TestMethodInfo:
    """Information about a test method."""
    name: str
    docstring: str
    class_name: str
    module_name: str
    line_count: int
    requirements_covered: List[str]


class TestDocumentationHelper:
    """Helper class for test documentation and metadata."""
    
    @staticmethod
    def extract_test_info(test_class) -> List[TestMethodInfo]:
        """Extract information about test methods in a class."""
        test_methods = []
        
        for method_name in dir(test_class):
            if method_name.startswith('test_'):
                method = getattr(test_class, method_name)
                if callable(method):
                    # Get method source to count lines
                    try:
                        source_lines = inspect.getsourcelines(method)[0]
                        line_count = len(source_lines)
                    except (OSError, TypeError):
                        line_count = 0
                    
                    # Extract requirements from docstring
                    docstring = method.__doc__ or ""
                    requirements = TestDocumentationHelper._extract_requirements(docstring)
                    
                    test_info = TestMethodInfo(
                        name=method_name,
                        docstring=docstring.strip(),
                        class_name=test_class.__name__,
                        module_name=test_class.__module__,
                        line_count=line_count,
                        requirements_covered=requirements
                    )
                    test_methods.append(test_info)
        
        return test_methods
    
    @staticmethod
    def _extract_requirements(docstring: str) -> List[str]:
        """Extract requirement references from docstring."""
        requirements = []
        lines = docstring.split('\n')
        
        for line in lines:
            line = line.strip()
            if 'requirement' in line.lower() or 'req' in line.lower():
                # Simple extraction - can be enhanced
                if ':' in line:
                    req_part = line.split(':')[-1].strip()
                    requirements.append(req_part)
        
        return requirements
    
    @staticmethod
    def generate_test_summary(test_classes: List[type]) -> Dict[str, Any]:
        """Generate a summary of test coverage and organization."""
        summary = {
            "total_classes": len(test_classes),
            "total_methods": 0,
            "total_lines": 0,
            "classes_over_limit": [],
            "methods_over_limit": [],
            "requirements_coverage": {}
        }
        
        for test_class in test_classes:
            test_methods = TestDocumentationHelper.extract_test_info(test_class)
            summary["total_methods"] += len(test_methods)
            
            # Check class size (approximate)
            class_lines = sum(method.line_count for method in test_methods)
            summary["total_lines"] += class_lines
            
            if class_lines > 200:  # Class size limit
                summary["classes_over_limit"].append({
                    "name": test_class.__name__,
                    "lines": class_lines
                })
            
            # Check method sizes
            for method in test_methods:
                if method.line_count > 50:  # Method size limit
                    summary["methods_over_limit"].append({
                        "name": f"{method.class_name}.{method.name}",
                        "lines": method.line_count
                    })
                
                # Track requirements coverage
                for req in method.requirements_covered:
                    if req not in summary["requirements_coverage"]:
                        summary["requirements_coverage"][req] = []
                    summary["requirements_coverage"][req].append(
                        f"{method.class_name}.{method.name}"
                    )
        
        return summary