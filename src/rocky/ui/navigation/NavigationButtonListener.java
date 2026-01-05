package rocky.ui.navigation;

import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import javax.swing.*;
import java.awt.Color;

public class NavigationButtonListener extends MouseAdapter {
    private final Color hoverBg;
    private final Color hoverBorder;
    private final Color normalBg;
    private final Color normalBorder;

    public NavigationButtonListener(Color hoverBg, Color hoverBorder, Color normalBg, Color normalBorder) {
        this.hoverBg = hoverBg;
        this.hoverBorder = hoverBorder;
        this.normalBg = normalBg;
        this.normalBorder = normalBorder;
    }

    @Override
    public void mouseEntered(MouseEvent e) {
        JButton btn = (JButton) e.getSource();
        btn.setBackground(hoverBg);
        btn.setBorder(BorderFactory.createCompoundBorder(
            BorderFactory.createLineBorder(hoverBorder, 1),
            BorderFactory.createEmptyBorder(10, 10, 10, 10)
        ));
    }

    @Override
    public void mouseExited(MouseEvent e) {
        JButton btn = (JButton) e.getSource();
        btn.setBackground(normalBg);
        btn.setBorder(BorderFactory.createCompoundBorder(
            BorderFactory.createLineBorder(normalBorder, 1),
            BorderFactory.createEmptyBorder(10, 10, 10, 10)
        ));
    }
}
