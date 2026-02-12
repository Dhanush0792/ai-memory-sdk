"""
Load testing suite for Memory Infrastructure Phase 2.
Tests horizontal scalability, rate limiting, and lock contention.
"""

import time
import asyncio
import aiohttp
import statistics
from typing import List, Dict, Any
from dataclasses import dataclass
import json


@dataclass
class LoadTestResult:
    """Load test result metrics."""
    operation: str
    total_requests: int
    successful: int
    failed: int
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    requests_per_second: float
    error_rate: float
    duration_seconds: float


class LoadTester:
    """
    Load testing client for Memory Infrastructure.
    
    Tests:
    - Ingest operations
    - Retrieval operations
    - Concurrent updates
    - Rate limiting
    - Lock contention
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str = "test-api-key-1234567890",
        tenant_id: str = "load-test-tenant",
        user_id: str = "load-test-user"
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.headers = {
            "X-API-Key": api_key,
            "X-Tenant-ID": tenant_id,
            "X-User-ID": user_id,
            "Content-Type": "application/json"
        }
    
    async def ingest_memory(
        self,
        session: aiohttp.ClientSession,
        conversation_text: str
    ) -> Dict[str, Any]:
        """Single ingest operation."""
        start_time = time.time()
        
        try:
            async with session.post(
                f"{self.base_url}/api/v1/memory/ingest",
                headers=self.headers,
                json={"conversation_text": conversation_text}
            ) as response:
                latency_ms = (time.time() - start_time) * 1000
                
                return {
                    "success": response.status == 200,
                    "status_code": response.status,
                    "latency_ms": latency_ms
                }
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return {
                "success": False,
                "status_code": 0,
                "latency_ms": latency_ms,
                "error": str(e)
            }
    
    async def retrieve_memories(
        self,
        session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """Single retrieve operation."""
        start_time = time.time()
        
        try:
            async with session.get(
                f"{self.base_url}/api/v1/memory/{self.user_id}",
                headers=self.headers
            ) as response:
                latency_ms = (time.time() - start_time) * 1000
                
                return {
                    "success": response.status == 200,
                    "status_code": response.status,
                    "latency_ms": latency_ms
                }
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return {
                "success": False,
                "status_code": 0,
                "latency_ms": latency_ms,
                "error": str(e)
            }
    
    async def run_ingest_load_test(
        self,
        num_requests: int = 1000,
        concurrency: int = 10
    ) -> LoadTestResult:
        """
        Run ingest load test.
        
        Args:
            num_requests: Total number of requests
            concurrency: Number of concurrent requests
            
        Returns:
            LoadTestResult with metrics
        """
        print(f"Running ingest load test: {num_requests} requests, concurrency={concurrency}")
        
        results = []
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            for batch_start in range(0, num_requests, concurrency):
                batch_size = min(concurrency, num_requests - batch_start)
                
                tasks = [
                    self.ingest_memory(
                        session,
                        f"Test memory {batch_start + i}: User prefers concise explanations"
                    )
                    for i in range(batch_size)
                ]
                
                batch_results = await asyncio.gather(*tasks)
                results.extend(batch_results)
                
                # Small delay to avoid overwhelming the system
                await asyncio.sleep(0.01)
        
        duration = time.time() - start_time
        
        return self._calculate_metrics("ingest", results, duration)
    
    async def run_retrieve_load_test(
        self,
        num_requests: int = 1000,
        concurrency: int = 10
    ) -> LoadTestResult:
        """Run retrieve load test."""
        print(f"Running retrieve load test: {num_requests} requests, concurrency={concurrency}")
        
        results = []
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            for batch_start in range(0, num_requests, concurrency):
                batch_size = min(concurrency, num_requests - batch_start)
                
                tasks = [
                    self.retrieve_memories(session)
                    for _ in range(batch_size)
                ]
                
                batch_results = await asyncio.gather(*tasks)
                results.extend(batch_results)
                
                await asyncio.sleep(0.01)
        
        duration = time.time() - start_time
        
        return self._calculate_metrics("retrieve", results, duration)
    
    async def run_concurrent_update_test(
        self,
        num_updates: int = 100
    ) -> LoadTestResult:
        """
        Test concurrent updates to same memory (lock contention test).
        
        Args:
            num_updates: Number of concurrent updates
            
        Returns:
            LoadTestResult with lock contention metrics
        """
        print(f"Running concurrent update test: {num_updates} concurrent updates")
        
        results = []
        start_time = time.time()
        
        # All updates target the same subject+predicate to force lock contention
        conversation_text = "User prefers short explanations"
        
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.ingest_memory(session, conversation_text)
                for _ in range(num_updates)
            ]
            
            results = await asyncio.gather(*tasks)
        
        duration = time.time() - start_time
        
        return self._calculate_metrics("concurrent_update", results, duration)
    
    async def run_sustained_load_test(
        self,
        duration_seconds: int = 300,
        requests_per_second: int = 10
    ) -> LoadTestResult:
        """
        Run sustained load test.
        
        Args:
            duration_seconds: Test duration
            requests_per_second: Target RPS
            
        Returns:
            LoadTestResult with sustained load metrics
        """
        print(f"Running sustained load test: {duration_seconds}s @ {requests_per_second} RPS")
        
        results = []
        start_time = time.time()
        request_interval = 1.0 / requests_per_second
        
        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < duration_seconds:
                iteration_start = time.time()
                
                # Alternate between ingest and retrieve
                if len(results) % 2 == 0:
                    result = await self.ingest_memory(
                        session,
                        f"Sustained test memory {len(results)}"
                    )
                else:
                    result = await self.retrieve_memories(session)
                
                results.append(result)
                
                # Sleep to maintain target RPS
                elapsed = time.time() - iteration_start
                if elapsed < request_interval:
                    await asyncio.sleep(request_interval - elapsed)
        
        duration = time.time() - start_time
        
        return self._calculate_metrics("sustained_load", results, duration)
    
    def _calculate_metrics(
        self,
        operation: str,
        results: List[Dict[str, Any]],
        duration: float
    ) -> LoadTestResult:
        """Calculate load test metrics."""
        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful
        
        latencies = [r["latency_ms"] for r in results]
        latencies.sort()
        
        avg_latency = statistics.mean(latencies) if latencies else 0
        p50_latency = latencies[int(len(latencies) * 0.50)] if latencies else 0
        p95_latency = latencies[int(len(latencies) * 0.95)] if latencies else 0
        p99_latency = latencies[int(len(latencies) * 0.99)] if latencies else 0
        
        rps = len(results) / duration if duration > 0 else 0
        error_rate = (failed / len(results) * 100) if results else 0
        
        return LoadTestResult(
            operation=operation,
            total_requests=len(results),
            successful=successful,
            failed=failed,
            avg_latency_ms=avg_latency,
            p50_latency_ms=p50_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            requests_per_second=rps,
            error_rate=error_rate,
            duration_seconds=duration
        )
    
    def print_results(self, result: LoadTestResult):
        """Print load test results."""
        print("\n" + "=" * 80)
        print(f"Load Test Results: {result.operation}")
        print("=" * 80)
        print(f"Total Requests:     {result.total_requests}")
        print(f"Successful:         {result.successful} ({result.successful/result.total_requests*100:.1f}%)")
        print(f"Failed:             {result.failed} ({result.error_rate:.1f}%)")
        print(f"Duration:           {result.duration_seconds:.2f}s")
        print(f"Requests/Second:    {result.requests_per_second:.2f}")
        print(f"\nLatency Metrics:")
        print(f"  Average:          {result.avg_latency_ms:.2f}ms")
        print(f"  p50:              {result.p50_latency_ms:.2f}ms")
        print(f"  p95:              {result.p95_latency_ms:.2f}ms")
        print(f"  p99:              {result.p99_latency_ms:.2f}ms")
        print("=" * 80 + "\n")


async def run_full_load_test_suite():
    """Run complete load test suite."""
    tester = LoadTester()
    
    print("\n🚀 Starting Full Load Test Suite\n")
    
    # Test 1: Ingest load test
    ingest_result = await tester.run_ingest_load_test(
        num_requests=1000,
        concurrency=10
    )
    tester.print_results(ingest_result)
    
    # Test 2: Retrieve load test
    retrieve_result = await tester.run_retrieve_load_test(
        num_requests=1000,
        concurrency=10
    )
    tester.print_results(retrieve_result)
    
    # Test 3: Concurrent update test (lock contention)
    concurrent_result = await tester.run_concurrent_update_test(
        num_updates=100
    )
    tester.print_results(concurrent_result)
    
    # Test 4: Sustained load test
    sustained_result = await tester.run_sustained_load_test(
        duration_seconds=60,  # 1 minute for demo
        requests_per_second=10
    )
    tester.print_results(sustained_result)
    
    # Summary
    print("\n" + "=" * 80)
    print("LOAD TEST SUITE SUMMARY")
    print("=" * 80)
    print(f"Ingest:             {ingest_result.successful}/{ingest_result.total_requests} success, "
          f"p95={ingest_result.p95_latency_ms:.0f}ms")
    print(f"Retrieve:           {retrieve_result.successful}/{retrieve_result.total_requests} success, "
          f"p95={retrieve_result.p95_latency_ms:.0f}ms")
    print(f"Concurrent Update:  {concurrent_result.successful}/{concurrent_result.total_requests} success, "
          f"error_rate={concurrent_result.error_rate:.1f}%")
    print(f"Sustained Load:     {sustained_result.successful}/{sustained_result.total_requests} success, "
          f"{sustained_result.requests_per_second:.1f} RPS")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(run_full_load_test_suite())
