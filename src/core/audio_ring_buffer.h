#pragma once
#include <vector>
#include <atomic>
#include <algorithm>
#include <stdexcept>

/**
 * @brief Lock-Free Single-Producer Single-Consumer (SPSC) Ring Buffer.
 * 
 * Optimized for low-latency audio streaming between the Python AudioWorker 
 * (Producer) and the Hardware Audio Callback (Consumer).
 */
class AudioRingBuffer {
private:
    std::vector<float> buffer;
    size_t capacity;
    std::atomic<size_t> head{0}; // Write index
    std::atomic<size_t> tail{0}; // Read index

public:
    explicit AudioRingBuffer(size_t size) : capacity(size) {
        // Enforce power of two for performance if needed, 
        // but for now simple modulo is fine.
        buffer.resize(size);
    }

    /**
     * @brief Pushes samples into the buffer.
     * Called by the Producer (AudioWorker).
     * @return Number of samples actually written.
     */
    size_t write(const float* data, size_t count) {
        size_t h = head.load(std::memory_order_relaxed);
        size_t t = tail.load(std::memory_order_acquire);

        size_t available = capacity - (h - t + capacity) % capacity;
        if (available <= 1) return 0; // Buffer full (keep 1 gap)

        size_t toWrite = std::min(count, available - 1);
        
        for (size_t i = 0; i < toWrite; ++i) {
            buffer[(h + i) % capacity] = data[i];
        }

        head.store((h + toWrite) % capacity, std::memory_order_release);
        return toWrite;
    }

    /**
     * @brief Reads samples from the buffer.
     * Called by the Consumer (Audio Callback).
     * @return Number of samples actually read.
     */
    size_t read(float* data, size_t count) {
        size_t t = tail.load(std::memory_order_relaxed);
        size_t h = head.load(std::memory_order_acquire);

        if (h == t) return 0; // Buffer empty

        size_t available = (h - t + capacity) % capacity;
        size_t toRead = std::min(count, available);

        for (size_t i = 0; i < toRead; ++i) {
            data[i] = buffer[(t + i) % capacity];
        }

        tail.store((t + toRead) % capacity, std::memory_order_release);
        return toRead;
    }

    size_t getAvailableRead() const {
        size_t h = head.load(std::memory_order_acquire);
        size_t t = tail.load(std::memory_order_acquire);
        return (h - t + capacity) % capacity;
    }

    size_t getAvailableWrite() const {
        size_t h = head.load(std::memory_order_acquire);
        size_t t = tail.load(std::memory_order_acquire);
        return capacity - ((h - t + capacity) % capacity) - 1;
    }

    void clear() {
        head.store(0, std::memory_order_release);
        tail.store(0, std::memory_order_release);
    }
};
