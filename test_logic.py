import unittest
from unittest.mock import patch, MagicMock
import sys

# Mock the UI to prevent windows from showing
sys.modules['customtkinter'] = MagicMock()
sys.modules['tkinter'] = MagicMock()
sys.modules['imageio_ffmpeg'] = MagicMock()

import main
import config

class TestFetchFinalFix(unittest.TestCase):
    def setUp(self):
        # Enable the run flag as if the app is actually running
        main._fetch_event.set() 
        if main._operation_lock.locked():
            main._operation_lock.release()
        main.quality_combo = MagicMock()
        main.quality_combo.get.return_value = "720p"

    @patch('concurrent.futures.wait')
    def test_batch_math_and_zombie_kill(self, mock_wait):
        print("\n🔍 Testing batch math and killing zombie threads...")
        
        # Imagine the user selected 10 videos
        mock_row = {"checkbox": MagicMock(), "frame": MagicMock(), "bytes_size": -1}
        mock_row["checkbox"].get.return_value = 1
        main.video_rows = [mock_row] * 10
        
        # Settings: 5 threads, timeout 45 seconds
        config.SOCKET_TIMEOUT = 45
        config.MAX_THREADS = 5
        
        # Simulate wait finished, but there are still zombie threads hanging
        fake_done = []
        fake_not_done = ['Zombie_Thread_1', 'Zombie_Thread_2']
        mock_wait.return_value = (fake_done, fake_not_done)
        
        # Run the function
        main.fetch_all_sizes_worker()
        
        # 1. Test math: (10 videos / 5 threads) = 2 batches. 2 * 45 = 90 seconds.
        kwargs = mock_wait.call_args.kwargs
        self.assertEqual(kwargs.get('timeout'), 90, "Fail: math is still wrong!")
        print("   [✅] Batch math is 100% correct (90 seconds for 10 videos instead of 450).")
        
        # 2. Test kill: was the kill signal sent?
        self.assertFalse(main._fetch_event.is_set(), "Fail: kill signal was not sent to hanging threads!")
        print("   [✅] Kill signal sent successfully to hanging threads to free resources.")

if __name__ == '__main__':
    unittest.main()