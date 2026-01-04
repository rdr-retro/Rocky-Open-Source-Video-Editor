package rocky.core.media;

/**
 * Stores a single coordinate point for a mask path.
 */
public class MaskAnchor {
    private double x;
    private double y;

    public MaskAnchor(double x, double y) {
        this.x = x;
        this.y = y;
    }

    public double getX() {
        return x;
    }

    public void setX(double x) {
        this.x = x;
    }

    public double getY() {
        return y;
    }

    public void setY(double y) {
        this.y = y;
    }
}
