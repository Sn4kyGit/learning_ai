"""
Test organization utilities.

This module provides utilities for organizing and validating
test structure according to OOP principles.
"""

from typing import List, Dict, Any
import os
import ast


class TestOrganizer:
    """Helper class for test organization and validation."""
    
    @staticmethod
    def validate_file_sizes(test_directory: str) -> Dict[str, Any]:
        """Validate that test files comply with size limits."""
        violations = {
            "files_over_500_lines": [],
            "total_files_checked": 0,
            "compliant_files": 0
        }
        
        for root, dirs, files in os.walk(test_directory):
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    file_path = os.path.join(root, file)
                    violations["total_files_checked"] += 1
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            line_count = sum(1 for _ in f)
                        
                        if line_count > 500:
                            violations["files_over_500_lines"].append({
                                "file": file_path,
                                "lines": line_count
                            })
                        else:
                            violations["compliant_files"] += 1
                    except Exception as e:
                        # Skip files that can't be read
                        continue
        
        return violations