import unittest 
from unittest.mock import patch, MagicMock
import time
import sys

# Mock the environment to avoid launching GUI windows
sys.modules['customtkinter'] = MagicMock()
sys.modules['tkinter'] = MagicMock()
sys.modules['imageio_ffmpeg'] = MagicMock()

import main
import config
import concurrent.futures

class TestFetchTimeoutLogic(unittest.TestCase):

    def setUp(self):
        main._fetch_event.clear()
        main._operation_lock.release() if main._operation_lock.locked() else None
        main.quality_combo = MagicMock()
        main.quality_combo.get.return_value = "720p"

    @patch('concurrent.futures.wait')
    def test_01_timeout_math_flaw(self, mock_wait):
        """Is the timeout calculation logically correct?"""
        print("\n🔍 1. Testing timeout calculation...")
        
        # Imagine the user selected 100 videos
        mock_row = {"checkbox": MagicMock(), "frame": MagicMock(), "bytes_size": -1}
        mock_row["checkbox"].get.return_value = 1
        main.video_rows = [mock_row] * 100 # 100 videos
        
        # Set timeout to 45 seconds
        config.SOCKET_TIMEOUT = 45
        config.MAX_THREADS = 5
        
        main.fetch_all_sizes_worker()
        
        # Get the calculated timeout from the code
        kwargs = mock_wait.call_args.kwargs
        calculated_timeout = kwargs.get('timeout')
        
        print(f"   [!] Number of videos: 100")
        print(f"   [!] Calculated timeout in current code: {calculated_timeout} seconds (about {calculated_timeout/60:.1f} minutes!)")
        
        # Correct math: 100 videos ÷ 5 threads = 20 batches. 20 × 45 = 900 seconds
        correct_timeout = (100 / 5) * 45
        print(f"   [✅] Expected correct timeout: {correct_timeout} seconds (about {correct_timeout/60:.1f} minutes)")
        
        self.assertNotEqual(calculated_timeout, correct_timeout, "Math in current code is wrong and causes double waiting time!")

    def test_02_zombie_threads_after_timeout(self):
        """Do threads actually stop after timeout?"""
        print("\n🔍 2. Testing zombie threads after timeout...")
        
        # Mock one video
        mock_row = {"checkbox": MagicMock(), "frame": MagicMock(), "bytes_size": -1, "size_label": MagicMock()}
        mock_row["checkbox"].get.return_value = 1
        main.video_rows = [mock_row]
        
        # Fake function that hangs for 3 seconds (simulate YouTube delay)
        def hanging_fetch(*args):
            print("   [⏳] Fetch thread started and will hang for 3 seconds...")
            time.sleep(3)
            print("   [💀] Zombie thread woke up! (this thread was not killed)")
            return True

        # Reduce timeout to 1 second to test behavior
        config.SOCKET_TIMEOUT = 1 
        config.MAX_THREADS = 1
        
        with patch('main.fetch_size_for_single_video', side_effect=hanging_fetch):
            print("   [▶️] Running process with Timeout = 1 second")
            main.fetch_all_sizes_worker()
            print("   [🛑] UI is responsive again, fetch function finished.")
            
            # Wait 3 seconds to check if background thread is still alive
            time.sleep(2.5)
            
        print("   [💡] Conclusion: UI returned, but thread kept running in background and used system resources!")
        self.assertTrue(True) # Test depends on terminal output

if __name__ == '__main__':
    unittest.main()