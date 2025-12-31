package b.timeline;

/**
 * Data model for project settings.
 */
public class ProjectProperties {
    private String projectRes = "1920x1080x32; 29,970i";
    private String previewRes = "480x270x32; 29,970p";
    private String displayRes = "597x336x32";
    private boolean lowResPreview = true; // Default to true as requested

    public String getProjectRes() { return projectRes; }
    public void setProjectRes(String res) { this.projectRes = res; }

    public String getPreviewRes() { return previewRes; }
    public void setPreviewRes(String res) { this.previewRes = res; }

    public String getDisplayRes() { return displayRes; }
    public void setDisplayRes(String res) { this.displayRes = res; }

    public boolean isLowResPreview() { return lowResPreview; }
    public void setLowResPreview(boolean low) { this.lowResPreview = low; }
}
