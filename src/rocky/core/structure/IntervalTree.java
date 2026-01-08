package rocky.core.structure;

import java.util.ArrayList;
import java.util.List;

/**
 * A simple Interval Tree implementation for efficient temporal queries.
 * Supports adding, removing, and querying intervals that overlap a point.
 * 
 * @param <T> The type of data stored in the interval (e.g., TimelineClip)
 */
public class IntervalTree<T> {

    private class Node {
        long start;
        long end;
        long maxEnd; // Augmented value: max end in this subtree
        T data;
        Node left;
        Node right;
        int height; // For AVL balancing (optional but good for performance)

        public Node(long start, long end, T data) {
            this.start = start;
            this.end = end;
            this.maxEnd = end;
            this.data = data;
            this.height = 1;
        }
    }

    private Node root;

    public void add(long start, long end, T data) {
        root = insert(root, start, end, data);
    }

    public void clear() {
        root = null;
    }

    /**
     * Returns all items whose interval [start, end) contains the given point.
     * i.e., start <= point < end
     */
    public List<T> query(long point) {
        List<T> result = new ArrayList<>();
        query(point, result);
        return result;
    }

    public void query(long point, List<T> result) {
        query(root, point, result);
    }

    private void query(Node node, long point, List<T> result) {
        if (node == null) return;

        // If point is to the right of the max endpoint of this subtree, 
        // then no node in this subtree can overlap the point.
        if (point >= node.maxEnd) return;

        // Search left child
        if (node.left != null && node.left.maxEnd > point) {
            query(node.left, point, result);
        }

        // Check current node
        if (node.start <= point && point < node.end) {
            result.add(node.data);
        }

        // Search right child
        // Only if point is at least start of current node (optimization for sorted BST)
        // But since this is interval tree sorted by start, we must search right if point >= node.start
        // Actually, standard interval tree search logic:
        if (point >= node.start) {
            if (node.right != null) {
                query(node.right, point, result);
            }
        }
    }
    
    // --- INSERTION (Simple BST insertion sorted by start time) ---
    private Node insert(Node node, long start, long end, T data) {
        if (node == null) return new Node(start, end, data);

        // Sort by start time. If equal, could sort by end, or just put to right.
        if (start < node.start) {
            node.left = insert(node.left, start, end, data);
        } else {
            node.right = insert(node.right, start, end, data);
        }

        updateMaxEnd(node);
        return node; // No balancing for simplicity in this V1, purely random insertion usually ok for timeline
    }

    
    // Better idea for Remove: The caller calls remove(start, end, data).
    // TimelinePanel knows the clip's current start/end.
    public void remove(long start, long end, T data) {
        root = remove(root, start, end, data);
    }
    
    private Node remove(Node node, long start, long end, T data) {
        if (node == null) return null;

        if (start < node.start) {
            node.left = remove(node.left, start, end, data);
        } else if (start > node.start) {
            node.right = remove(node.right, start, end, data);
        } else {
            // Start matches. Check data equality to handle duplicates at same start time
            if (node.data.equals(data)) {
                // Found it
                if (node.left == null) return node.right;
                if (node.right == null) return node.left;
                
                Node temp = findMin(node.right);
                node.start = temp.start;
                node.end = temp.end;
                node.data = temp.data;
                // Delete the successor from right subtree
                node.right = remove(node.right, temp.start, temp.end, temp.data);
            } else {
                // Same start time, but different object. 
                // In a BST, duplicates are usually either right or left. 
                // We put duplicates to right in insert? 
                // "if (start < node.start) left else right". So equal goes to right.
                node.right = remove(node.right, start, end, data);
            }
        }
        updateMaxEnd(node);
        return node;
    }

    private Node findMin(Node node) {
        while (node.left != null) node = node.left;
        return node;
    }

    private void updateMaxEnd(Node node) {
        if (node == null) return;
        long max = node.end;
        if (node.left != null) max = Math.max(max, node.left.maxEnd);
        if (node.right != null) max = Math.max(max, node.right.maxEnd);
        node.maxEnd = max;
    }
}
