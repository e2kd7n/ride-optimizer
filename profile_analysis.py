#!/usr/bin/env python3
"""
Profile the analysis to identify performance bottlenecks.

Usage:
    python3 profile_analysis.py
"""

import cProfile
import pstats
import io
from pathlib import Path

# Import main analysis function
from main import analyze_routes, load_config

def profile_analysis():
    """Profile the analysis with cProfile."""
    print("Starting profiled analysis...")
    print("This will take a while but will show where time is spent.\n")
    
    # Load config
    config = load_config('config/config.yaml')
    
    # Create profiler
    profiler = cProfile.Profile()
    
    # Profile the analysis
    profiler.enable()
    try:
        analyze_routes(config, 'output/reports', n_workers=2)
    except Exception as e:
        print(f"Analysis error: {e}")
    finally:
        profiler.disable()
    
    # Print results
    print("\n" + "="*80)
    print("PROFILING RESULTS - Top 30 Time Consumers")
    print("="*80 + "\n")
    
    # Create stats object
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)
    
    # Sort by cumulative time and print top 30
    ps.sort_stats('cumulative')
    ps.print_stats(30)
    
    print(s.getvalue())
    
    # Also sort by total time
    print("\n" + "="*80)
    print("PROFILING RESULTS - Top 30 by Total Time")
    print("="*80 + "\n")
    
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.sort_stats('tottime')
    ps.print_stats(30)
    
    print(s.getvalue())
    
    # Save detailed stats to file
    stats_file = Path('output/profile_stats.txt')
    stats_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(stats_file, 'w') as f:
        ps = pstats.Stats(profiler, stream=f)
        ps.sort_stats('cumulative')
        ps.print_stats()
    
    print(f"\n📊 Detailed stats saved to: {stats_file}")
    print("\nKey metrics to look for:")
    print("  - cumtime: Total time spent in function and subfunctions")
    print("  - tottime: Time spent in function itself (excluding subfunctions)")
    print("  - ncalls: Number of times function was called")

if __name__ == '__main__':
    profile_analysis()

# Made with Bob
