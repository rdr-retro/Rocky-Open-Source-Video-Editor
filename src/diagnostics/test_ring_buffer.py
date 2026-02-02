import sys
import os
import numpy as np

# Add project root to path (two levels up from src/diagnostics)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.append(project_root)

import rocky_core

def test_ring_buffer():
    print("[TEST] AudioRingBuffer (C++ Binding)")
    
    # Initialize 1024 sample buffer
    rb = rocky_core.AudioRingBuffer(1024)
    
    # 1. Test Write/Read
    data = np.random.rand(512).astype(np.float32)
    written = rb.write(data)
    print(f"Written: {written} samples")
    assert written == 512
    
    # Read back as bytes
    # 512 samples * 4 bytes/sample = 2048 bytes
    read_bytes = rb.read_bytes(2048)
    print(f"Read: {len(read_bytes)} bytes")
    assert len(read_bytes) == 2048
    
    # Compare data
    read_np = np.frombuffer(read_bytes, dtype=np.float32)
    np.testing.assert_array_almost_equal(data, read_np)
    print("PASS: Data integrity OK")
    
    # 2. Test Availability
    assert rb.get_available_read() == 0
    assert rb.get_available_write() == 1023 # 1024 - 1 gap
    
    # 3. Test Overflow
    big_data = np.zeros(2000, dtype=np.float32)
    written = rb.write(big_data)
    print(f"Overflow Write: {written} samples (expected 1023)")
    assert written == 1023
    
    # 4. Test Clear
    rb.clear()
    assert rb.get_available_read() == 0
    print("PASS: Clear/Availability OK")
    
    print("\nALL BINDING TESTS PASSED.")

if __name__ == "__main__":
    test_ring_buffer()
