"""
Base performance testing utilities.

This module contains the core performance testing classes and utilities
that are used by all specialized performance testers.
"""

import time
import asyncio
from typing import Callable, Any, List, Dict, Optional
from dataclasses import dataclass


@dataclass
class PerformanceResult:
    """Performance test result data."""
    operation_name: str
    execution_time: float
    success: bool
    error_message: Optional[str] = None
    additional_metrics: Optional[Dict[str, Any]] = None


class PerformanceTester:
    """Base performance testing utilities."""
    
    def __init__(self, max_response_time: float = 0.5):
        self.max_response_time = max_response_time
        self.results: List[PerformanceResult] = []
    
    async def measure_async_operation(
        self,
        operation: Callable,
        operation_name: str,
        *args,
        **kwargs
    ) -> PerformanceResult:
        """Measure execution time of async operation."""
        start_time = time.time()
        error_message = None
        additional_metrics = {}
        
        try:
            result = await operation(*args, **kwargs)
            execution_time = time.time() - start_time
            success = execution_time <= self.max_response_time
            
            # Extract additional metrics if result is a dict
            if isinstance(result, dict) and 'metrics' in result:
                additional_metrics = result['metrics']
            
            if not success:
                error_message = f"Exceeded {self.max_response_time}s limit"
                
        except Exception as e:
            execution_time = time.time() - start_time
            success = False
            error_message = str(e)
        
        result = PerformanceResult(
            operation_name=operation_name,
            execution_time=execution_time,
            success=success,
            error_message=error_message,
            additional_metrics=additional_metrics
        )
        
        self.results.append(result)
        return result
    
    def measure_sync_operation(
        self,
        operation: Callable,
        operation_name: str,
        *args,
        **kwargs
    ) -> PerformanceResult:
        """Measure execution time of synchronous operation."""
        start_time = time.time()
        error_message = None
        additional_metrics = {}
        
        try:
            result = operation(*args, **kwargs)
            execution_time = time.time() - start_time
            success = execution_time <= self.max_response_time
            
            if isinstance(result, dict) and 'metrics' in result:
                additional_metrics = result['metrics']
            
            if not success:
                error_message = f"Exceeded {self.max_response_time}s limit"
                
        except Exception as e:
            execution_time = time.time() - start_time
            success = False
            error_message = str(e)
        
        result = PerformanceResult(
            operation_name=operation_name,
            execution_time=execution_time,
            success=success,
            error_message=error_message,
            additional_metrics=additional_metrics
        )
        
        self.results.append(result)
        return result
    
    async def measure_batch_operation(
        self,
        operation: Callable,
        batch_size: int,
        max_batch_time: float,
        operation_name: str,
        data_generator: Optional[Callable] = None
    ) -> PerformanceResult:
        """Measure batch operation performance."""
        start_time = time.time()
        error_message = None
        additional_metrics = {"batch_size": batch_size}
        
        try:
            # Create batch data
            if data_generator:
                batch_data = data_generator(batch_size)
            else:
                batch_data = [f"test_item_{i}" for i in range(batch_size)]
            
            result = await operation(batch_data)
            execution_time = time.time() - start_time
            success = execution_time <= max_batch_time
            
            # Calculate throughput
            throughput = batch_size / execution_time if execution_time > 0 else 0
            additional_metrics.update({
                "throughput_per_second": throughput,
                "avg_time_per_item": execution_time / batch_size if batch_size > 0 else 0
            })
            
            if not success:
                error_message = f"Batch exceeded {max_batch_time}s limit"
                
        except Exception as e:
            execution_time = time.time() - start_time
            success = False
            error_message = str(e)
        
        result = PerformanceResult(
            operation_name=f"{operation_name}_batch_{batch_size}",
            execution_time=execution_time,
            success=success,
            error_message=error_message,
            additional_metrics=additional_metrics
        )
        
        self.results.append(result)
        return result
    
    async def measure_concurrent_operations(
        self,
        operation: Callable,
        operation_name: str,
        concurrent_count: int,
        max_total_time: float,
        *args,
        **kwargs
    ) -> PerformanceResult:
        """Measure concurrent operation performance."""
        start_time = time.time()
        error_message = None
        additional_metrics = {"concurrent_count": concurrent_count}
        
        try:
            # Create concurrent tasks
            tasks = [
                operation(*args, **kwargs) 
                for _ in range(concurrent_count)
            ]
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            execution_time = time.time() - start_time
            
            # Count successful operations
            successful_ops = sum(1 for r in results if not isinstance(r, Exception))
            failed_ops = concurrent_count - successful_ops
            
            success = execution_time <= max_total_time and failed_ops == 0
            
            additional_metrics.update({
                "successful_operations": successful_ops,
                "failed_operations": failed_ops,
                "success_rate": successful_ops / concurrent_count,
                "avg_time_per_operation": execution_time / concurrent_count
            })
            
            if not success:
                if execution_time > max_total_time:
                    error_message = f"Concurrent operations exceeded {max_total_time}s limit"
                if failed_ops > 0:
                    error_message = f"{failed_ops} operations failed"
                    
        except Exception as e:
            execution_time = time.time() - start_time
            success = False
            error_message = str(e)
        
        result = PerformanceResult(
            operation_name=f"{operation_name}_concurrent_{concurrent_count}",
            execution_time=execution_time,
            success=success,
            error_message=error_message,
            additional_metrics=additional_metrics
        )
        
        self.results.append(result)
        return result
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of all performance test results."""
        if not self.results:
            return {
                "total_tests": 0,
                "successful_tests": 0,
                "success_rate": 0,
                "average_execution_time": 0,
                "failed_operations": []
            }
        
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.success)
        avg_time = sum(r.execution_time for r in self.results) / total_tests
        
        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": successful_tests / total_tests,
            "average_execution_time": avg_time,
            "fastest_operation": min(self.results, key=lambda r: r.execution_time),
            "slowest_operation": max(self.results, key=lambda r: r.execution_time),
            "failed_operations": [r for r in self.results if not r.success]
        }
    
    def assert_all_operations_successful(self):
        """Assert that all measured operations were successful."""
        failed_operations = [r for r in self.results if not r.success]
        if failed_operations:
            error_details = "\n".join([
                f"- {op.operation_name}: {op.error_message} ({op.execution_time:.3f}s)"
                for op in failed_operations
            ])
            raise AssertionError(f"Performance test failures:\n{error_details}")
    
    def clear_results(self):
        """Clear all performance test results."""
        self.results.clear()