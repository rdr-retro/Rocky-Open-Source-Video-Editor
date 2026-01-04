package rocky.ui.timeline;

import javax.swing.*;
import java.awt.*;
import java.awt.event.*;

public class SidebarPanel extends JPanel {
    private JLabel timecodeLabel;

    // Aesthetic colors
    private final Color BG_COLOR = Color.decode("#0f051d");
    private final Color HEADER_BG = Color.decode("#1a0b2e"); 
    // Image shows Top Left is darker/blackish?
    // Actually looking at the image: Top Left box with numbers is NOT the same
    // color as the ruler. It looks like a dark grey/black box.
    // Ruler is lighter.

    private final Color TIMECODE_BG = Color.decode("#1a0b2e"); 
    private final Color TIMECODE_TEXT = Color.decode("#dcd0ff");
    private final Font TIMECODE_FONT = new Font("SansSerif", Font.PLAIN, 20);

    private JPanel tracksContainer;
    private Runnable onAddTrack; // Callback for parent to sync with timeline

    private int videoTrackCount = 0;
    private int audioTrackCount = 0;

    private JPanel bodyPanel;
    private JPanel headerPanel;

    public SidebarPanel() {
        // ... (Same constructor logic up to ScrollPane) ...
        setLayout(new BorderLayout());
        setBackground(BG_COLOR);

        // Initial size, but JSplitPane will control it
        setPreferredSize(new Dimension(250, 0));
        setMinimumSize(new Dimension(100, 0)); // Allow shrinking

        // Top Header Area (Timecode)
        headerPanel = new JPanel(new BorderLayout());
        headerPanel.setPreferredSize(new Dimension(250, 30)); // Match ruler height (30px)
        headerPanel.setBackground(TIMECODE_BG);
        headerPanel.setBorder(BorderFactory.createMatteBorder(0, 0, 1, 1, Color.BLACK)); // Bottom and Right border

        timecodeLabel = new JLabel("00:00:00;00", SwingConstants.CENTER);
        timecodeLabel.setFont(TIMECODE_FONT);
        timecodeLabel.setForeground(TIMECODE_TEXT);

        headerPanel.add(timecodeLabel, BorderLayout.CENTER);

        // Tracks Container
        tracksContainer = new JPanel();
        tracksContainer.setLayout(new BoxLayout(tracksContainer, BoxLayout.Y_AXIS));
        tracksContainer.setBackground(BG_COLOR);

        // Scroll pane for tracks if they overflow (Vertical only)
        // Matches structure where tracks might grow
        bodyPanel = new JPanel(new BorderLayout()) {
            @Override
            public Dimension getPreferredSize() {
                // Enforce Width 250
                // Enforce Height Min (Match timeline min height logic)
                Dimension d = super.getPreferredSize();
                int minHeight = 800;
                if (getParent() instanceof JViewport) {
                    minHeight = Math.max(minHeight, getParent().getHeight());
                }
                return new Dimension(250, Math.max(minHeight, d.height));
            }
        };
        bodyPanel.setBackground(BG_COLOR);
        bodyPanel.add(tracksContainer, BorderLayout.NORTH); // Tracks stack at top

        // Context Menu
        JPopupMenu popup = new JPopupMenu();

        JMenuItem addVideoItem = new JMenuItem("Añadir pista de video");
        addVideoItem.addActionListener(e -> addTrack(TrackControlPanel.TrackType.VIDEO));
        popup.add(addVideoItem);

        JMenuItem addAudioItem = new JMenuItem("Añadir pista de audio");
        addAudioItem.addActionListener(e -> addTrack(TrackControlPanel.TrackType.AUDIO));
        popup.add(addAudioItem);

        // Add mouse listener for right click on empty area
        MouseAdapter rightClicker = new MouseAdapter() {
            @Override
            public void mouseReleased(MouseEvent e) {
                if (e.isPopupTrigger())
                    popup.show(e.getComponent(), e.getX(), e.getY());
            }

            @Override
            public void mousePressed(MouseEvent e) {
                if (e.isPopupTrigger())
                    popup.show(e.getComponent(), e.getX(), e.getY());
            }
        };
        // Add to both tracksContainer and (if used) bodyPanel
        tracksContainer.addMouseListener(rightClicker);
        bodyPanel.addMouseListener(rightClicker);

        add(headerPanel, BorderLayout.NORTH);
        add(bodyPanel, BorderLayout.CENTER);
    }

    public interface ReorderListener {
        void onReorder(int from, int to);
    }

    private ReorderListener onReorderTracks;

    public interface OnRemoveTrackListener {
        void onRemove(int index);
    }

    private OnRemoveTrackListener onRemoveTrack;

    public void setOnAddTrack(Runnable callback) {
        this.onAddTrack = callback;
    }

    public void setOnReorderTracks(ReorderListener listener) {
        this.onReorderTracks = listener;
    }

    public void setOnRemoveTrack(OnRemoveTrackListener listener) {
        this.onRemoveTrack = listener;
    }

    private java.util.List<TrackControlPanel> tracks = new java.util.ArrayList<>();

    // Keep strict signature if used by interface, or overload
    public void addTrack(TrackControlPanel.TrackType type) {
        addTrack(type, tracks.size());
    }

    public void addTrack(TrackControlPanel.TrackType type, int index) {
        int num = tracks.size() + 1;
        TrackControlPanel track = new TrackControlPanel(type, num);

        // Listener for resize
        track.setResizeListener(() -> {
            tracksContainer.revalidate(); // Re-layout sidebar
            if (onAddTrack != null)
                onAddTrack.run();
        });

        track.setMoveListener(new TrackControlPanel.MoveTrackListener() {
            private int initialIndex;

            @Override
            public void onMoveRequested(MouseEvent e) {
                initialIndex = tracks.indexOf(track);
            }

            @Override
            public void onMoveDragged(MouseEvent e) {
                Point p = SwingUtilities.convertPoint(track, e.getPoint(), tracksContainer);
                int targetIndex = -1;
                int currentY = 0;
                for (int i = 0; i < tracks.size(); i++) {
                    int h = tracks.get(i).getHeight();
                    if (p.y >= currentY && p.y < currentY + h) {
                        targetIndex = i;
                        break;
                    }
                    currentY += h;
                }

                if (targetIndex != -1 && targetIndex != tracks.indexOf(track)) {
                    reorderTracks(tracks.indexOf(track), targetIndex);
                }
            }

            @Override
            public void onMoveReleased(MouseEvent e) {
                if (onAddTrack != null)
                    onAddTrack.run(); // Final sync
            }
        });

        // Context Menu for Track
        JPopupMenu trackPopup = new JPopupMenu();
        JMenuItem deleteItem = new JMenuItem("Eliminar Pista");
        deleteItem.addActionListener(e -> removeTrack(track));
        trackPopup.add(deleteItem);

        track.addMouseListener(new MouseAdapter() {
            @Override
            public void mouseReleased(MouseEvent e) {
                if (e.isPopupTrigger())
                    trackPopup.show(e.getComponent(), e.getX(), e.getY());
            }

            @Override
            public void mousePressed(MouseEvent e) {
                if (e.isPopupTrigger())
                    trackPopup.show(e.getComponent(), e.getX(), e.getY());
            }
        });

        if (index >= 0 && index <= tracks.size()) {
            tracks.add(index, track);
            tracksContainer.add(track, index);
        } else {
            tracks.add(track);
            tracksContainer.add(track);
        }

        refreshTrackNumbering();
        tracksContainer.revalidate();
        tracksContainer.repaint();

        if (onAddTrack != null) {
            onAddTrack.run();
        }
    }

    public void removeTrack(TrackControlPanel track) {
        int index = tracks.indexOf(track);
        if (index != -1) {
            tracks.remove(index);
            tracksContainer.remove(track);
            refreshTrackNumbering();

            if (onRemoveTrack != null) {
                onRemoveTrack.onRemove(index);
            }
            if (onAddTrack != null) {
                onAddTrack.run(); // Sync heights
            }
        }
    }

    private void refreshTrackNumbering() {
        tracksContainer.removeAll();
        int globalCount = 1;
        for (TrackControlPanel t : tracks) {
            tracksContainer.add(t);
            t.updateTrackNumber(globalCount++);
        }
        tracksContainer.revalidate();
        tracksContainer.repaint();
    }

    private void reorderTracks(int fromIndex, int toIndex) {
        TrackControlPanel movingTrack = tracks.remove(fromIndex);
        tracks.add(toIndex, movingTrack);

        refreshTrackNumbering();

        if (onReorderTracks != null)
            onReorderTracks.onReorder(fromIndex, toIndex);
        if (onAddTrack != null)
            onAddTrack.run();
    }

    // For compatibility if needed
    public void addTrack() {
        addTrack(TrackControlPanel.TrackType.VIDEO);
    }

    public java.util.List<Integer> getTrackHeights() {
        java.util.List<Integer> heights = new java.util.ArrayList<>();
        for (TrackControlPanel track : tracks) {
            heights.add(track.getPreferredSize().height);
        }
        return heights;
    }

    public java.util.List<TrackControlPanel.TrackType> getTrackTypesList() {
        java.util.List<TrackControlPanel.TrackType> types = new java.util.ArrayList<>();
        for (TrackControlPanel track : tracks) {
            types.add(track.getTrackType());
        }
        return types;
    }

    public void setTrackHeights(java.util.List<Integer> heights) {
        for (int i = 0; i < Math.min(heights.size(), tracks.size()); i++) {
            tracks.get(i).setPreferredSize(new Dimension(250, heights.get(i)));
        }
        tracksContainer.revalidate();
        tracksContainer.repaint();
    }

    public int getTrackCount() {
        return tracks.size();
    }

    public TrackControlPanel.TrackType getTrackType(int index) {
        if (index >= 0 && index < tracks.size()) {
            return tracks.get(index).getTrackType();
        }
        return null;
    }

    public JPanel getHeaderPanel() {
        return headerPanel;
    }

    public JPanel getSidebarContent() {
        return bodyPanel;
    }

    public JPanel getTracksContainer() {
        return tracksContainer;
    }

    public void setTimecode(String code) {
        timecodeLabel.setText(code);
    }

    public void reconstructTracks(java.util.List<TrackControlPanel.TrackType> types, java.util.List<Integer> heights) {
        tracks.clear();
        tracksContainer.removeAll();

        for (int i = 0; i < types.size(); i++) {
            TrackControlPanel.TrackType type = types.get(i);
            int h = heights.get(i);

            int num = i + 1;
            TrackControlPanel track = new TrackControlPanel(type, num);
            track.setPreferredSize(new Dimension(250, h));

            // Wire listeners (Copied from addTrack for consistency)
            track.setResizeListener(() -> {
                tracksContainer.revalidate();
                if (onAddTrack != null)
                    onAddTrack.run();
            });

            track.setMoveListener(new TrackControlPanel.MoveTrackListener() {
                @Override
                public void onMoveRequested(MouseEvent e) {
                }

                @Override
                public void onMoveDragged(MouseEvent e) {
                }

                @Override
                public void onMoveReleased(MouseEvent e) {
                    if (onAddTrack != null)
                        onAddTrack.run();
                }
            });

            // Context Menu for Track
            JPopupMenu trackPopup = new JPopupMenu();
            JMenuItem deleteItem = new JMenuItem("Eliminar Pista");
            deleteItem.addActionListener(e -> removeTrack(track));
            trackPopup.add(deleteItem);

            track.addMouseListener(new MouseAdapter() {
                @Override
                public void mouseReleased(MouseEvent e) {
                    if (e.isPopupTrigger())
                        trackPopup.show(e.getComponent(), e.getX(), e.getY());
                }

                @Override
                public void mousePressed(MouseEvent e) {
                    if (e.isPopupTrigger())
                        trackPopup.show(e.getComponent(), e.getX(), e.getY());
                }
            });

            tracks.add(track);
            tracksContainer.add(track);
        }

        tracksContainer.revalidate();
        tracksContainer.repaint();
    }
}
