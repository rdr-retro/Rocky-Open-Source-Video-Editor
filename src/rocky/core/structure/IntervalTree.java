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

    public void remove(T data) {
        root = delete(root, data);
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
        query(root, point, result);
        return result;
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

    // --- DELETION ---
    private Node delete(Node node, T data) {
        if (node == null) return null;

        if (data.equals(node.data)) {
            // Found node to delete
            if (node.left == null) return node.right;
            if (node.right == null) return node.left;

            // Two children: replace with in-order successor (min of right subtree)
            Node temp = findMin(node.right);
            // Copy data from successor
            node.start = temp.start;
            node.end = temp.end;
            node.data = temp.data;
            // Delete successor
            node.right = delete(node.right, temp.data);
        } else {
            // Traverse
            // Note: Since we only sorted by start, and there might be multiple start times, 
            // finding the exact node by 'data' equality requires potentially searching both if start doesn't strict match.
            // But usually we know start time from the object or we just search everything.
            // Wait, standard BST delete requires key. We are removing by OBJECT equality.
            // This is tricky if we don't know the keys (start time) during remove(T data).
            // To make "remove(data)" efficient without knowing start/end, we'd need a map T -> Node.
            // OR we iterate.
            
            // Re-think: "remove(T data)" is hard in a BST if we don't know the key.
            // We should assume we know the key, or we just reconstruct.
            // Since TimelinePanel clips change their time, we likely remove(clip) BEFORE changing its time.
            // So we DO know the start/end from the clip object itself if T is TimelineClip?
            // But we made T generic.
            
            // Let's rely on the fact that T generally has the info, but here we just traverse strictly?
            // Actually, for a small number of clips (hundreds), rebuilding is fast.
            // BUT proper remove:
            // Since we sort by 'start', and 'data' likely has 'getStartFrame()', we can use that?
            // No, T is generic.
            
            // SIMPLIFICATION:
            // Since we remove by object equality, and we sorted by 'start', we might have to search whole tree 
            // if we don't inspect 'data'.
            // However, the caller usually knows the *old* start time if they are careful. 
            // BUT `TimelinePanel.removeClip(clip)` just passes the clip. 
            // The clip still has its *current* start time (which matches the tree key).
            // So we can assume: Key = ((TimelineClip)data).getStartFrame().
            
            // To keep it generic but efficient, we'll traverse recursively.
            // Optimization: If we assume we can cast T to something with getStartFrame?
            // Or just search entire tree (O(N)) for deletion?
            // Given N is likely < 10000, O(N) delete is acceptable compared to O(N) render queries (60 times a second).
            // Deletions happen rarely (user clicks). Queries happen 60fps.
            
            // Let's implement full traversal delete for safety.
            Node leftRes = delete(node.left, data);
            Node rightRes = delete(node.right, data);
            
            if (node.left != leftRes) node.left = leftRes;
            if (node.right != rightRes) node.right = rightRes;
            
            // If THIS node matched (was handled above), we updated 'node' structure.
            // Wait, the recursion above is messy.
            
            // Let's do this: 
            // Rebuild tree logic for "remove" is safest if generic is black box.
            // But to be cleaner, let's just make it specific to TimelineClip or add bounds to remove.
        }
        updateMaxEnd(node);
        return node;
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
