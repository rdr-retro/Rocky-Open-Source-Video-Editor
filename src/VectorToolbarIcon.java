

import javax.swing.JComponent;
import java.awt.*;

public class VectorToolbarIcon extends JComponent {
    private String type;
    private int size;
    private Color tint;

    public VectorToolbarIcon(String type, int size, Color tint) {
        this.type = type;
        this.size = size;
        this.tint = tint;
        setPreferredSize(new Dimension(size + 4, size + 4));
    }

    @Override
    protected void paintComponent(Graphics g) {
        Graphics2D g2d = (Graphics2D) g.create();
        g2d.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g2d.setRenderingHint(RenderingHints.KEY_STROKE_CONTROL, RenderingHints.VALUE_STROKE_PURE);
        
        int w = getWidth();
        int h = getHeight();
        int iconSize = size;
        int x = (w - iconSize) / 2;
        int y = (h - iconSize) / 2;

        g2d.setColor(tint);
        float strokeW = 1.5f;
        g2d.setStroke(new BasicStroke(strokeW, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));

        switch (type) {
            case "LOAD":
                java.awt.geom.Path2D folder = new java.awt.geom.Path2D.Double();
                folder.moveTo(x, y + 3);
                folder.lineTo(x + 5, y + 3);
                folder.lineTo(x + 7, y + 5);
                folder.lineTo(x + iconSize, y + 5);
                folder.lineTo(x + iconSize, y + iconSize);
                folder.lineTo(x, y + iconSize);
                folder.closePath();
                g2d.draw(folder);
                break;
            case "SAVE":
                java.awt.geom.Path2D disk = new java.awt.geom.Path2D.Double();
                disk.moveTo(x, y);
                disk.lineTo(x + iconSize - 4, y);
                disk.lineTo(x + iconSize, y + 4);
                disk.lineTo(x + iconSize, y + iconSize);
                disk.lineTo(x, y + iconSize);
                disk.closePath();
                g2d.draw(disk);
                g2d.drawRect(x + 4, y, iconSize - 8, 5);
                g2d.drawRect(x + 4, y + iconSize - 6, iconSize - 8, 6);
                break;
            case "RENDER":
                java.awt.geom.Path2D clap = new java.awt.geom.Path2D.Double();
                clap.moveTo(x, y + 5);
                clap.lineTo(x + iconSize, y + 5);
                clap.lineTo(x + iconSize, y + iconSize);
                clap.lineTo(x, y + iconSize);
                clap.closePath();
                g2d.draw(clap);
                // Top part angled
                g2d.rotate(Math.toRadians(-15), x, y + 5);
                g2d.drawRect(x, y + 1, iconSize, 4);
                break;
            case "SETTINGS":
                int cx = x + iconSize / 2;
                int cy = y + iconSize / 2;
                int rInner = iconSize / 4;
                int rOuter = iconSize / 2;
                for (int i = 0; i < 8; i++) {
                    g2d.rotate(Math.toRadians(45), cx, cy);
                    g2d.drawRect(cx - 1, y, 2, 4);
                }
                g2d.drawOval(cx - rInner, cy - rInner, rInner * 2, rInner * 2);
                break;
            case "UNDO":
            case "REDO":
                boolean isRedo = type.equals("REDO");
                if (isRedo) {
                    g2d.drawArc(x, y + 2, iconSize - 4, iconSize - 4, 120, -240);
                    java.awt.geom.Path2D head = new java.awt.geom.Path2D.Double();
                    head.moveTo(x + iconSize - 4, y + 4);
                    head.lineTo(x + iconSize, y - 1);
                    head.lineTo(x + iconSize - 8, y - 1);
                    head.closePath();
                    g2d.fill(head);
                } else {
                    g2d.drawArc(x + 4, y + 2, iconSize - 4, iconSize - 4, 60, 240);
                    java.awt.geom.Path2D head = new java.awt.geom.Path2D.Double();
                    head.moveTo(x + 4, y + 4);
                    head.lineTo(x, y - 1);
                    head.lineTo(x + 8, y - 1);
                    head.closePath();
                    g2d.fill(head);
                }
                break;
        }
        g2d.dispose();
    }
}
