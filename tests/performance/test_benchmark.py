"""
tests/performance/test_benchmark.py
==================================================================
Extreme Performance Benchmarking & Profiling (From Gemini 1)
Uses pytest-benchmark to find avg/min/max execution time.
Uses tracemalloc to track RAM usage.
"""

import pytest
import tracemalloc

@pytest.fixture(scope="module")
def m(main_module):
    """Shorthand alias for the main module."""
    return main_module

def test_benchmark_format_duration(benchmark, m):
    """
    Measures the execution time of format_duration in microseconds.
    Pytest-benchmark runs this thousands of times to find the average.
    """
    # We test formatting 24 hours (86400 seconds)
    result = benchmark(m.format_duration, 86400)
    assert result == "24:00:00"

def test_benchmark_apply_bidi_arabic(benchmark, m):
    """Measures the CPU cost of the RTL text injection algorithm."""
    long_arabic_text = "تجربة نص عربي طويل جدا للتحقق من سرعة التطبيق في معالجة النصوص" * 5
    benchmark(m.apply_bidi, long_arabic_text)

def test_benchmark_format_size(benchmark, m):
    """Measures speed of byte conversion math."""
    result = benchmark(m.format_size, 52428800) # 50 MB
    assert result == "50.0 MB"

def test_memory_profile_render_chunk(m):
    """
    Tracks the exact amount of RAM consumed when generating UI components.
    Critical for the monolithic refactoring to detect Memory Leaks.
    """
    # Create 50 fake video entries
    entries_data = [
        {'idx': i, 'title': f"Video {i}", 'dur': "05:00", 'url': "url"} 
        for i in range(50)
    ]
    qualities = ["Best", "Low"]
    
    # Start tracking RAM
    tracemalloc.start()
    
    # Run the UI rendering function
    m.render_chunk(entries_data, 0, qualities, chunk_size=50)
    
    # Get memory usage
    current_memory, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    # Convert bytes to Kilobytes for readability
    peak_kb = peak_memory / 1024
    
    # Assert that rendering 50 rows uses less than 15 MB (15000 KB) of RAM
    # If this test fails post-refactor, you have a memory leak!
    assert peak_kb < 15000, f"Memory spike detected! Used {peak_kb:.2f} KB for 50 rows."