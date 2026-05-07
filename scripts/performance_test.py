#!/usr/bin/env python3
"""
Performance testing script for Smart Static architecture.

Tests memory usage, response times, and resource consumption.
Designed to run on Raspberry Pi to verify optimization goals.

Usage:
    python3 scripts/performance_test.py [--duration SECONDS] [--api-url URL]

Goals:
    - Memory usage < 50MB (80% reduction from 250MB)
    - API response time < 100ms
    - Concurrent requests handled efficiently
    - Cron jobs complete within time limits
"""

import argparse
import json
import os
import psutil
import requests
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


class PerformanceTest:
    """Performance testing for Smart Static architecture."""
    
    def __init__(self, api_url: str = "http://localhost:5000", duration: int = 60):
        self.api_url = api_url
        self.duration = duration
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'system_info': {},
            'memory_tests': {},
            'api_tests': {},
            'cron_tests': {},
            'summary': {}
        }
    
    def get_system_info(self) -> Dict:
        """Collect system information."""
        print("\n📊 Collecting system information...")
        
        info = {
            'platform': sys.platform,
            'python_version': sys.version,
            'cpu_count': psutil.cpu_count(),
            'total_memory_mb': round(psutil.virtual_memory().total / 1024 / 1024, 2),
            'available_memory_mb': round(psutil.virtual_memory().available / 1024 / 1024, 2),
            'disk_usage_percent': psutil.disk_usage('/').percent
        }
        
        # Check if running on Raspberry Pi
        try:
            with open('/proc/device-tree/model', 'r') as f:
                info['device_model'] = f.read().strip()
                info['is_raspberry_pi'] = 'Raspberry Pi' in info['device_model']
        except FileNotFoundError:
            info['device_model'] = 'Unknown'
            info['is_raspberry_pi'] = False
        
        self.results['system_info'] = info
        
        print(f"  Platform: {info['platform']}")
        print(f"  Device: {info['device_model']}")
        print(f"  CPU Cores: {info['cpu_count']}")
        print(f"  Total Memory: {info['total_memory_mb']} MB")
        print(f"  Available Memory: {info['available_memory_mb']} MB")
        
        return info
    
    def test_api_memory_usage(self) -> Dict:
        """Test API server memory usage."""
        print("\n🧠 Testing API memory usage...")
        
        # Find API process
        api_process = None
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and 'api.py' in ' '.join(cmdline):
                    api_process = psutil.Process(proc.info['pid'])
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if not api_process:
            print("  ⚠️  API process not found. Start with: python3 api.py")
            return {'error': 'API process not found'}
        
        # Measure memory over time
        measurements = []
        for i in range(10):
            try:
                mem_info = api_process.memory_info()
                mem_mb = mem_info.rss / 1024 / 1024
                measurements.append(mem_mb)
                time.sleep(1)
            except psutil.NoSuchProcess:
                break
        
        if not measurements:
            return {'error': 'Could not measure memory'}
        
        results = {
            'min_mb': round(min(measurements), 2),
            'max_mb': round(max(measurements), 2),
            'avg_mb': round(statistics.mean(measurements), 2),
            'median_mb': round(statistics.median(measurements), 2),
            'target_mb': 50,
            'meets_target': statistics.mean(measurements) < 50
        }
        
        self.results['memory_tests']['api_server'] = results
        
        print(f"  Min: {results['min_mb']} MB")
        print(f"  Max: {results['max_mb']} MB")
        print(f"  Avg: {results['avg_mb']} MB")
        print(f"  Target: < {results['target_mb']} MB")
        print(f"  Status: {'✅ PASS' if results['meets_target'] else '❌ FAIL'}")
        
        return results
    
    def test_api_response_times(self) -> Dict:
        """Test API endpoint response times."""
        print("\n⚡ Testing API response times...")
        
        endpoints = [
            '/api/status',
            '/api/weather?lat=40.7128&lon=-74.0060',
            '/api/recommendation',
            '/api/routes'
        ]
        
        results = {}
        
        for endpoint in endpoints:
            print(f"\n  Testing {endpoint}...")
            times = []
            errors = 0
            
            for i in range(20):
                try:
                    start = time.time()
                    response = requests.get(f"{self.api_url}{endpoint}", timeout=5)
                    duration = (time.time() - start) * 1000  # Convert to ms
                    
                    if response.status_code in [200, 400]:  # 400 is OK for weather without config
                        times.append(duration)
                    else:
                        errors += 1
                except Exception as e:
                    errors += 1
                    print(f"    Error: {e}")
            
            if times:
                endpoint_results = {
                    'min_ms': round(min(times), 2),
                    'max_ms': round(max(times), 2),
                    'avg_ms': round(statistics.mean(times), 2),
                    'median_ms': round(statistics.median(times), 2),
                    'p95_ms': round(statistics.quantiles(times, n=20)[18], 2),
                    'errors': errors,
                    'target_ms': 100,
                    'meets_target': statistics.mean(times) < 100
                }
                
                results[endpoint] = endpoint_results
                
                print(f"    Avg: {endpoint_results['avg_ms']} ms")
                print(f"    P95: {endpoint_results['p95_ms']} ms")
                print(f"    Status: {'✅ PASS' if endpoint_results['meets_target'] else '❌ FAIL'}")
            else:
                results[endpoint] = {'error': 'All requests failed'}
                print(f"    ❌ All requests failed")
        
        self.results['api_tests']['response_times'] = results
        return results
    
    def test_concurrent_requests(self) -> Dict:
        """Test API under concurrent load."""
        print("\n🔄 Testing concurrent requests...")
        
        import concurrent.futures
        
        def make_request():
            try:
                start = time.time()
                response = requests.get(f"{self.api_url}/api/status", timeout=5)
                duration = (time.time() - start) * 1000
                return duration if response.status_code == 200 else None
            except:
                return None
        
        # Test with 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            times = [f.result() for f in concurrent.futures.as_completed(futures) if f.result()]
        
        if times:
            results = {
                'total_requests': 50,
                'successful_requests': len(times),
                'failed_requests': 50 - len(times),
                'avg_ms': round(statistics.mean(times), 2),
                'max_ms': round(max(times), 2),
                'target_ms': 200,
                'meets_target': statistics.mean(times) < 200
            }
            
            self.results['api_tests']['concurrent_load'] = results
            
            print(f"  Successful: {results['successful_requests']}/50")
            print(f"  Avg Response: {results['avg_ms']} ms")
            print(f"  Max Response: {results['max_ms']} ms")
            print(f"  Status: {'✅ PASS' if results['meets_target'] else '❌ FAIL'}")
        else:
            results = {'error': 'All concurrent requests failed'}
            print(f"  ❌ All requests failed")
        
        return results
    
    def test_cron_performance(self) -> Dict:
        """Test cron script performance."""
        print("\n⏰ Testing cron script performance...")
        
        scripts = [
            ('cache_cleanup.py', 5),
            ('system_health.py', 10),
            ('weather_refresh.py', 30),
            ('daily_analysis.py', 60)
        ]
        
        results = {}
        
        for script_name, target_seconds in scripts:
            script_path = Path('cron') / script_name
            
            if not script_path.exists():
                print(f"  ⚠️  {script_name} not found")
                continue
            
            print(f"\n  Testing {script_name}...")
            
            try:
                start = time.time()
                result = subprocess.run(
                    ['python3', str(script_path)],
                    capture_output=True,
                    timeout=target_seconds * 2
                )
                duration = time.time() - start
                
                script_results = {
                    'duration_seconds': round(duration, 2),
                    'target_seconds': target_seconds,
                    'meets_target': duration < target_seconds,
                    'exit_code': result.returncode,
                    'success': result.returncode == 0
                }
                
                results[script_name] = script_results
                
                print(f"    Duration: {script_results['duration_seconds']}s")
                print(f"    Target: < {target_seconds}s")
                print(f"    Status: {'✅ PASS' if script_results['meets_target'] and script_results['success'] else '❌ FAIL'}")
                
            except subprocess.TimeoutExpired:
                results[script_name] = {
                    'error': f'Timeout (>{target_seconds * 2}s)',
                    'meets_target': False
                }
                print(f"    ❌ Timeout")
            except Exception as e:
                results[script_name] = {
                    'error': str(e),
                    'meets_target': False
                }
                print(f"    ❌ Error: {e}")
        
        self.results['cron_tests'] = results
        return results
    
    def generate_summary(self) -> Dict:
        """Generate test summary."""
        print("\n📋 Generating summary...")
        
        summary = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'memory_goal_met': False,
            'performance_goal_met': False,
            'overall_status': 'FAIL'
        }
        
        # Check memory goal
        if 'api_server' in self.results['memory_tests']:
            mem_test = self.results['memory_tests']['api_server']
            if 'meets_target' in mem_test:
                summary['memory_goal_met'] = mem_test['meets_target']
                summary['total_tests'] += 1
                if mem_test['meets_target']:
                    summary['passed_tests'] += 1
                else:
                    summary['failed_tests'] += 1
        
        # Check API performance
        if 'response_times' in self.results['api_tests']:
            for endpoint, test in self.results['api_tests']['response_times'].items():
                if 'meets_target' in test:
                    summary['total_tests'] += 1
                    if test['meets_target']:
                        summary['passed_tests'] += 1
                    else:
                        summary['failed_tests'] += 1
        
        # Check concurrent load
        if 'concurrent_load' in self.results['api_tests']:
            test = self.results['api_tests']['concurrent_load']
            if 'meets_target' in test:
                summary['total_tests'] += 1
                if test['meets_target']:
                    summary['passed_tests'] += 1
                else:
                    summary['failed_tests'] += 1
        
        # Overall status
        summary['performance_goal_met'] = summary['passed_tests'] == summary['total_tests']
        summary['overall_status'] = 'PASS' if summary['performance_goal_met'] else 'FAIL'
        
        self.results['summary'] = summary
        
        print(f"\n  Total Tests: {summary['total_tests']}")
        print(f"  Passed: {summary['passed_tests']}")
        print(f"  Failed: {summary['failed_tests']}")
        print(f"  Memory Goal: {'✅ MET' if summary['memory_goal_met'] else '❌ NOT MET'}")
        print(f"  Performance Goal: {'✅ MET' if summary['performance_goal_met'] else '❌ NOT MET'}")
        print(f"\n  Overall Status: {'✅ PASS' if summary['overall_status'] == 'PASS' else '❌ FAIL'}")
        
        return summary
    
    def save_results(self, output_file: str = 'performance_test_results.json'):
        """Save test results to JSON file."""
        output_path = Path(output_file)
        
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_path}")
    
    def run_all_tests(self):
        """Run all performance tests."""
        print("=" * 60)
        print("🚀 Smart Static Architecture Performance Test")
        print("=" * 60)
        
        self.get_system_info()
        self.test_api_memory_usage()
        self.test_api_response_times()
        self.test_concurrent_requests()
        self.test_cron_performance()
        self.generate_summary()
        self.save_results()
        
        print("\n" + "=" * 60)
        print("✅ Performance testing complete!")
        print("=" * 60)
        
        return self.results['summary']['overall_status'] == 'PASS'


def main():
    parser = argparse.ArgumentParser(description='Performance testing for Smart Static architecture')
    parser.add_argument('--duration', type=int, default=60, help='Test duration in seconds')
    parser.add_argument('--api-url', type=str, default='http://localhost:5000', help='API base URL')
    parser.add_argument('--output', type=str, default='performance_test_results.json', help='Output file')
    
    args = parser.parse_args()
    
    tester = PerformanceTest(api_url=args.api_url, duration=args.duration)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()


# Made with Bob