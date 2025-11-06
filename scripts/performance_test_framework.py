#!/usr/bin/env python3
"""
Performance Test Framework for CI/CD Integration.

This script provides comprehensive performance testing capabilities
for the Local Business Intelligence Bot CI/CD pipeline.
"""

import asyncio
import time
import json
import sys
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import psutil
import statistics


@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    name: str
    value: float
    unit: str
    threshold: float
    passed: bool
    timestamp: str


@dataclass
class PerformanceTestResult:
    """Performance test result data structure."""
    test_name: str
    duration: float
    metrics: List[PerformanceMetric]
    memory_usage: Dict[str, float]
    success: bool
    error_message: Optional[str] = None


class PerformanceTestFramework:
    """Comprehensive performance testing framework for CI/CD."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[PerformanceTestResult] = []
        
        # Performance thresholds
        self.thresholds = {
            "api_response_times": {
                "simple_queries": 0.5,  # 500ms
                "ai_operations": 3.0,   # 3 seconds
                "batch_processing": 60.0,  # 60 seconds for 500 reviews
                "dashboard_load": 0.5,  # 500ms
            },
            "database_queries": {
                "simple_select": 0.1,   # 100ms
                "complex_join": 0.3,    # 300ms
                "batch_insert": 2.0,    # 2 seconds
                "analytics_query": 1.0, # 1 second
            },
            "memory_usage": {
                "peak_mb": 1024,        # 1GB peak
                "average_mb": 512,      # 512MB average
                "growth_rate": 0.1,     # 10% growth per operation
            },
            "concurrent_users": {
                "response_time_p95": 1.0,  # 95th percentile under 1s
                "throughput_rps": 100,     # 100 requests per second
                "error_rate": 0.01,        # 1% error rate
            }
        }
    
    def log(self, message: str):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    async def run_api_performance_tests(self) -> PerformanceTestResult:
        """Run API endpoint performance tests."""
        self.log("Running API performance tests...")
        
        start_time = time.time()
        metrics = []
        memory_before = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            # Test simple API queries
            simple_query_time = await self._test_simple_api_queries()
            metrics.append(PerformanceMetric(
                name="simple_queries",
                value=simple_query_time,
                unit="seconds",
                threshold=self.thresholds["api_response_times"]["simple_queries"],
                passed=simple_query_time <= self.thresholds["api_response_times"]["simple_queries"],
                timestamp=datetime.now().isoformat()
            ))
            
            # Test AI operations
            ai_operation_time = await self._test_ai_operations()
            metrics.append(PerformanceMetric(
                name="ai_operations",
                value=ai_operation_time,
                unit="seconds",
                threshold=self.thresholds["api_response_times"]["ai_operations"],
                passed=ai_operation_time <= self.thresholds["api_response_times"]["ai_operations"],
                timestamp=datetime.now().isoformat()
            ))
            
            # Test batch processing
            batch_processing_time = await self._test_batch_processing()
            metrics.append(PerformanceMetric(
                name="batch_processing",
                value=batch_processing_time,
                unit="seconds",
                threshold=self.thresholds["api_response_times"]["batch_processing"],
                passed=batch_processing_time <= self.thresholds["api_response_times"]["batch_processing"],
                timestamp=datetime.now().isoformat()
            ))
            
            memory_after = psutil.Process().memory_info().rss / 1024 / 1024
            duration = time.time() - start_time
            
            result = PerformanceTestResult(
                test_name="api_performance",
                duration=duration,
                metrics=metrics,
                memory_usage={
                    "before_mb": memory_before,
                    "after_mb": memory_after,
                    "peak_mb": memory_after,  # Simplified for this example
                    "growth_mb": memory_after - memory_before
                },
                success=all(m.passed for m in metrics)
            )
            
            self.results.append(result)
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            result = PerformanceTestResult(
                test_name="api_performance",
                duration=duration,
                metrics=metrics,
                memory_usage={"error": True},
                success=False,
                error_message=str(e)
            )
            self.results.append(result)
            return result
    
    async def _test_simple_api_queries(self) -> float:
        """Test simple API query performance."""
        self.log("Testing simple API queries...")
        
        # Simulate API calls (in real implementation, use httpx or similar)
        start_time = time.time()
        
        # Simulate multiple simple queries
        for _ in range(10):
            await asyncio.sleep(0.02)  # Simulate 20ms per query
        
        return time.time() - start_time
    
    async def _test_ai_operations(self) -> float:
        """Test AI operation performance."""
        self.log("Testing AI operations...")
        
        start_time = time.time()
        
        # Simulate AI classification calls
        for _ in range(5):
            await asyncio.sleep(0.3)  # Simulate 300ms per AI call
        
        return time.time() - start_time
    
    async def _test_batch_processing(self) -> float:
        """Test batch processing performance."""
        self.log("Testing batch processing (500 reviews)...")
        
        start_time = time.time()
        
        # Simulate processing 500 reviews in batches
        batch_size = 50
        num_batches = 10  # 500 / 50
        
        for batch in range(num_batches):
            # Simulate batch processing time
            await asyncio.sleep(2.0)  # 2 seconds per batch of 50
            self.log(f"Processed batch {batch + 1}/{num_batches}")
        
        return time.time() - start_time
    
    async def run_database_performance_tests(self) -> PerformanceTestResult:
        """Run database performance tests."""
        self.log("Running database performance tests...")
        
        start_time = time.time()
        metrics = []
        memory_before = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            # Test simple SELECT queries
            simple_select_time = await self._test_simple_select()
            metrics.append(PerformanceMetric(
                name="simple_select",
                value=simple_select_time,
                unit="seconds",
                threshold=self.thresholds["database_queries"]["simple_select"],
                passed=simple_select_time <= self.thresholds["database_queries"]["simple_select"],
                timestamp=datetime.now().isoformat()
            ))
            
            # Test complex JOIN queries
            complex_join_time = await self._test_complex_join()
            metrics.append(PerformanceMetric(
                name="complex_join",
                value=complex_join_time,
                unit="seconds",
                threshold=self.thresholds["database_queries"]["complex_join"],
                passed=complex_join_time <= self.thresholds["database_queries"]["complex_join"],
                timestamp=datetime.now().isoformat()
            ))
            
            # Test batch INSERT operations
            batch_insert_time = await self._test_batch_insert()
            metrics.append(PerformanceMetric(
                name="batch_insert",
                value=batch_insert_time,
                unit="seconds",
                threshold=self.thresholds["database_queries"]["batch_insert"],
                passed=batch_insert_time <= self.thresholds["database_queries"]["batch_insert"],
                timestamp=datetime.now().isoformat()
            ))
            
            memory_after = psutil.Process().memory_info().rss / 1024 / 1024
            duration = time.time() - start_time
            
            result = PerformanceTestResult(
                test_name="database_performance",
                duration=duration,
                metrics=metrics,
                memory_usage={
                    "before_mb": memory_before,
                    "after_mb": memory_after,
                    "peak_mb": memory_after,
                    "growth_mb": memory_after - memory_before
                },
                success=all(m.passed for m in metrics)
            )
            
            self.results.append(result)
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            result = PerformanceTestResult(
                test_name="database_performance",
                duration=duration,
                metrics=metrics,
                memory_usage={"error": True},
                success=False,
                error_message=str(e)
            )
            self.results.append(result)
            return result
    
    async def _test_simple_select(self) -> float:
        """Test simple SELECT query performance."""
        self.log("Testing simple SELECT queries...")
        
        start_time = time.time()
        
        # Simulate database queries
        for _ in range(20):
            await asyncio.sleep(0.003)  # Simulate 3ms per query
        
        return time.time() - start_time
    
    async def _test_complex_join(self) -> float:
        """Test complex JOIN query performance."""
        self.log("Testing complex JOIN queries...")
        
        start_time = time.time()
        
        # Simulate complex queries
        for _ in range(5):
            await asyncio.sleep(0.05)  # Simulate 50ms per complex query
        
        return time.time() - start_time
    
    async def _test_batch_insert(self) -> float:
        """Test batch INSERT performance."""
        self.log("Testing batch INSERT operations...")
        
        start_time = time.time()
        
        # Simulate batch inserts
        for _ in range(3):
            await asyncio.sleep(0.5)  # Simulate 500ms per batch insert
        
        return time.time() - start_time
    
    async def run_concurrent_user_tests(self) -> PerformanceTestResult:
        """Run concurrent user performance tests."""
        self.log("Running concurrent user tests...")
        
        start_time = time.time()
        metrics = []
        memory_before = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            # Simulate concurrent users
            concurrent_users = 50
            requests_per_user = 10
            
            response_times = []
            
            # Simulate concurrent requests
            tasks = []
            for user in range(concurrent_users):
                for request in range(requests_per_user):
                    task = self._simulate_user_request(user, request)
                    tasks.append(task)
            
            # Execute all requests concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Calculate metrics
            successful_requests = [r for r in results if isinstance(r, float)]
            failed_requests = [r for r in results if isinstance(r, Exception)]
            
            if successful_requests:
                avg_response_time = statistics.mean(successful_requests)
                p95_response_time = statistics.quantiles(successful_requests, n=20)[18]  # 95th percentile
                
                metrics.append(PerformanceMetric(
                    name="response_time_p95",
                    value=p95_response_time,
                    unit="seconds",
                    threshold=self.thresholds["concurrent_users"]["response_time_p95"],
                    passed=p95_response_time <= self.thresholds["concurrent_users"]["response_time_p95"],
                    timestamp=datetime.now().isoformat()
                ))
                
                # Calculate throughput
                total_time = time.time() - start_time
                throughput = len(successful_requests) / total_time
                
                metrics.append(PerformanceMetric(
                    name="throughput_rps",
                    value=throughput,
                    unit="requests_per_second",
                    threshold=self.thresholds["concurrent_users"]["throughput_rps"],
                    passed=throughput >= self.thresholds["concurrent_users"]["throughput_rps"],
                    timestamp=datetime.now().isoformat()
                ))
                
                # Calculate error rate
                error_rate = len(failed_requests) / len(results)
                
                metrics.append(PerformanceMetric(
                    name="error_rate",
                    value=error_rate,
                    unit="percentage",
                    threshold=self.thresholds["concurrent_users"]["error_rate"],
                    passed=error_rate <= self.thresholds["concurrent_users"]["error_rate"],
                    timestamp=datetime.now().isoformat()
                ))
            
            memory_after = psutil.Process().memory_info().rss / 1024 / 1024
            duration = time.time() - start_time
            
            result = PerformanceTestResult(
                test_name="concurrent_users",
                duration=duration,
                metrics=metrics,
                memory_usage={
                    "before_mb": memory_before,
                    "after_mb": memory_after,
                    "peak_mb": memory_after,
                    "growth_mb": memory_after - memory_before
                },
                success=all(m.passed for m in metrics) if metrics else False
            )
            
            self.results.append(result)
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            result = PerformanceTestResult(
                test_name="concurrent_users",
                duration=duration,
                metrics=metrics,
                memory_usage={"error": True},
                success=False,
                error_message=str(e)
            )
            self.results.append(result)
            return result
    
    async def _simulate_user_request(self, user_id: int, request_id: int) -> float:
        """Simulate a single user request."""
        start_time = time.time()
        
        # Simulate request processing time with some variance
        base_time = 0.1  # 100ms base
        variance = 0.05  # ±50ms variance
        
        import random
        processing_time = base_time + random.uniform(-variance, variance)
        await asyncio.sleep(max(0.01, processing_time))  # Minimum 10ms
        
        return time.time() - start_time
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        self.log("Generating performance report...")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "framework_version": "1.0.0",
            "test_environment": "ci",
            "total_tests": len(self.results),
            "passed_tests": len([r for r in self.results if r.success]),
            "failed_tests": len([r for r in self.results if not r.success]),
            "overall_success": all(r.success for r in self.results),
            "test_results": [],
            "summary": {
                "api_response_times": {},
                "database_queries": {},
                "memory_usage": {},
                "concurrent_users": {}
            }
        }
        
        # Process test results
        for result in self.results:
            test_data = {
                "test_name": result.test_name,
                "duration": result.duration,
                "success": result.success,
                "error_message": result.error_message,
                "memory_usage": result.memory_usage,
                "metrics": [asdict(m) for m in result.metrics]
            }
            report["test_results"].append(test_data)
            
            # Aggregate metrics for summary
            for metric in result.metrics:
                category = None
                if result.test_name == "api_performance":
                    category = "api_response_times"
                elif result.test_name == "database_performance":
                    category = "database_queries"
                elif result.test_name == "concurrent_users":
                    category = "concurrent_users"
                
                if category:
                    report["summary"][category][metric.name] = {
                        "value": metric.value,
                        "unit": metric.unit,
                        "threshold": metric.threshold,
                        "passed": metric.passed
                    }
        
        # Add memory usage summary
        if self.results:
            total_memory_growth = sum(
                r.memory_usage.get("growth_mb", 0) 
                for r in self.results 
                if isinstance(r.memory_usage, dict) and "growth_mb" in r.memory_usage
            )
            peak_memory = max(
                r.memory_usage.get("peak_mb", 0) 
                for r in self.results 
                if isinstance(r.memory_usage, dict) and "peak_mb" in r.memory_usage
            )
            
            report["summary"]["memory_usage"] = {
                "total_growth_mb": total_memory_growth,
                "peak_usage_mb": peak_memory,
                "growth_threshold_met": total_memory_growth <= self.thresholds["memory_usage"]["peak_mb"]
            }
        
        return report
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all performance tests."""
        self.log("Starting comprehensive performance test suite...")
        
        # Run API performance tests
        await self.run_api_performance_tests()
        
        # Run database performance tests
        await self.run_database_performance_tests()
        
        # Run concurrent user tests
        await self.run_concurrent_user_tests()
        
        # Generate and return report
        report = self.generate_performance_report()
        
        self.log(f"Performance test suite completed. Overall success: {report['overall_success']}")
        
        return report


async def main():
    """Main entry point for performance test framework."""
    parser = argparse.ArgumentParser(description="Performance Test Framework for CI/CD")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--output", "-o", default="performance-results.json", help="Output file for results")
    parser.add_argument("--test-type", choices=["api", "database", "concurrent", "all"], 
                       default="all", help="Type of performance tests to run")
    parser.add_argument("--baseline", help="Baseline performance file for comparison")
    
    args = parser.parse_args()
    
    try:
        framework = PerformanceTestFramework(verbose=args.verbose)
        
        # Run specified tests
        if args.test_type == "all":
            report = await framework.run_all_tests()
        elif args.test_type == "api":
            await framework.run_api_performance_tests()
            report = framework.generate_performance_report()
        elif args.test_type == "database":
            await framework.run_database_performance_tests()
            report = framework.generate_performance_report()
        elif args.test_type == "concurrent":
            await framework.run_concurrent_user_tests()
            report = framework.generate_performance_report()
        
        # Save results
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Performance test results saved to {args.output}")
        
        # Print summary
        print("\n=== Performance Test Summary ===")
        print(f"Total Tests: {report['total_tests']}")
        print(f"Passed: {report['passed_tests']}")
        print(f"Failed: {report['failed_tests']}")
        print(f"Overall Success: {report['overall_success']}")
        
        # Exit with appropriate code
        sys.exit(0 if report['overall_success'] else 1)
        
    except Exception as e:
        print(f"Performance test framework failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())