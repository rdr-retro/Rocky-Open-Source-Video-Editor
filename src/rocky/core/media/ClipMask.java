package rocky.core.media;

import java.util.ArrayList;
import java.util.List;

/**
 * Manages a collection of anchors forming a mask path.
 */
public class ClipMask {
    private final List<MaskAnchor> anchors = new ArrayList<>();
    private boolean enabled = false;
    private boolean inverted = false;
    private boolean closed = false;

    public List<MaskAnchor> getAnchors() {
        return anchors;
    }

    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public boolean isInverted() {
        return inverted;
    }

    public void setInverted(boolean inverted) {
        this.inverted = inverted;
    }

    public boolean isClosed() {
        return closed;
    }

    public void setClosed(boolean closed) {
        this.closed = closed;
    }

    public void addAnchor(double x, double y) {
        anchors.add(new MaskAnchor(x, y));
    }

    public ClipMask copy() {
        ClipMask clone = new ClipMask();
        clone.setEnabled(this.enabled);
        clone.setInverted(this.inverted);
        clone.setClosed(this.closed);
        for (MaskAnchor a : this.anchors) {
            clone.addAnchor(a.getX(), a.getY());
        }
        return clone;
    }
}
