import pytest
# Import logic tools directly from the new library
import core.utils as m 

def test_benchmark_format_duration(benchmark):
    """Test speed of time format function"""
    # Pass function name directly to tool to get correct measure
    result = benchmark(m.format_duration, 86400)
    assert "00" in result

def test_benchmark_apply_bidi_arabic(benchmark):
    """Test speed of Arabic text processing"""
    long_arabic_text = "تجربة نص عربي طويل جدا للتحقق من سرعة التطبيق " * 10
    benchmark(m.apply_bidi, long_arabic_text)

def test_benchmark_format_size(benchmark):
    """Test speed of file size format function"""
    benchmark(m.format_size, 1024 * 1024 * 5)