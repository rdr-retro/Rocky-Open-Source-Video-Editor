package rocky.ui.timeline;

/**
 * Stores transformation data for a clip in the project space.
 */
public class ClipTransform {
    private double x = 0; // Center X in project coordinates
    private double y = 0; // Center Y in project coordinates
    private double scaleX = 1.0;
    private double scaleY = 1.0;
    private double rotation = 0; // Degrees
    private double anchorX = 0.5; // Normalized (0-1)
    private double anchorY = 0.5; // Normalized (0-1)

    public ClipTransform() {
    }

    public ClipTransform(ClipTransform other) {
        if (other != null) {
            this.x = other.x;
            this.y = other.y;
            this.scaleX = other.scaleX;
            this.scaleY = other.scaleY;
            this.rotation = other.rotation;
            this.anchorX = other.anchorX;
            this.anchorY = other.anchorY;
        }
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

    public double getScaleX() {
        return scaleX;
    }

    public void setScaleX(double sx) {
        this.scaleX = sx;
    }

    public double getScaleY() {
        return scaleY;
    }

    public void setScaleY(double sy) {
        this.scaleY = sy;
    }

    public double getRotation() {
        return rotation;
    }

    public void setRotation(double r) {
        this.rotation = r;
    }

    public double getAnchorX() {
        return anchorX;
    }

    public void setAnchorX(double ax) {
        this.anchorX = ax;
    }

    public double getAnchorY() {
        return anchorY;
    }

    public void setAnchorY(double ay) {
        this.anchorY = ay;
    }
}
