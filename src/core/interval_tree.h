#pragma once
#include <vector>
#include <memory>
#include <algorithm>

template <typename T>
class IntervalTree {
    struct Node {
        long start, end, maxEnd;
        T data;
        std::unique_ptr<Node> left, right;
        Node(long s, long e, T d) : start(s), end(e), maxEnd(e), data(d) {}
    };

    std::unique_ptr<Node> root;

    void updateMaxEnd(Node* node) {
        if (!node) return;
        node->maxEnd = node->end;
        if (node->left) node->maxEnd = std::max(node->maxEnd, node->left->maxEnd);
        if (node->right) node->maxEnd = std::max(node->maxEnd, node->right->maxEnd);
    }

    void insert(std::unique_ptr<Node>& node, long start, long end, T data) {
        if (!node) {
            node = std::make_unique<Node>(start, end, data);
            return;
        }
        if (start < node->start) insert(node->left, start, end, data);
        else insert(node->right, start, end, data);
        updateMaxEnd(node.get());
    }

    void query(Node* node, long point, std::vector<T>& result) {
        if (!node || point >= node->maxEnd) return;
        if (node->left && node->left->maxEnd > point) query(node->left.get(), point, result);
        if (node->start <= point && point < node->end) result.push_back(node->data);
        if (point >= node->start && node->right) query(node->right.get(), point, result);
    }

public:
    void add(long start, long end, T data) { insert(root, start, end, data); }
    void clear() { root.reset(); }
    std::vector<T> query(long point) {
        std::vector<T> result;
        query(root.get(), point, result);
        return result;
    }

    void queryRange(Node* node, long start, long end, std::vector<T>& result) {
        if (!node || start >= node->maxEnd) return;
        if (node->left) queryRange(node->left.get(), start, end, result);
        if (node->start < end && start < node->end) result.push_back(node->data);
        if (end > node->start && node->right) queryRange(node->right.get(), start, end, result);
    }

    std::vector<T> query(long start, long end) {
        std::vector<T> result;
        queryRange(root.get(), start, end, result);
        return result;
    }
};
