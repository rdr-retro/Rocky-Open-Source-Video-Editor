

import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;

public class ToolbarActionAdapter extends MouseAdapter {
    private final java.util.function.Consumer<MouseEvent> action;
    
    public ToolbarActionAdapter(java.util.function.Consumer<MouseEvent> action) {
        this.action = action;
    }

    @Override
    public void mousePressed(MouseEvent e) {
        action.accept(e);
    }
}
