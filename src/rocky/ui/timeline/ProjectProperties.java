package rocky.ui.timeline;

/**
 * Data model for project settings.
 */
public class ProjectProperties {
    private String projectRes = "1920x1080 (Full HD 1080p)";
    private String previewRes = "854x480 (SD 480p)";
    private String displayRes = "1920x1080 (Full HD 1080p)";
    private boolean lowResPreview = true;
    private double fps = 30.0;
    private int audioSampleRate = 48000;
    private int audioChannels = 2;

    // New Vegas-style fields
    private String template = "HD 1080-24p (1920x1080; 23,976 fps)";
    private String fieldOrder = "Ninguno (escaneo progresivo)";
    private String pixelAspectRatio = "1,0000 (Cuadrado)";
    private String pixelFormat = "8 bits";
    private String gamma = "2,222 (Vídeo)";
    private String renderingQuality = "Buena";
    private String deinterlaceMethod = "Ninguno";
    private String resampleMode = "Re-muestreo inteligente";
    private boolean out360 = false;
    private boolean acesEnabled = false;
    private String previewQuality = "Preview"; // Draft, Preview, Good, Best

    // Proxy Settings
    private int proxyHeight = 480; // 360, 480, 720
    private String proxyBitrate = "1000k"; // 500k, 1000k, 2000k

    public int getProxyHeight() {
        return proxyHeight;
    }

    public void setProxyHeight(int h) {
        this.proxyHeight = h;
    }

    public String getProxyBitrate() {
        return proxyBitrate;
    }

    public void setProxyBitrate(String b) {
        this.proxyBitrate = b;
    }

    // performance / Vegas model fields

    public boolean isAcesEnabled() {
        return acesEnabled;
    }

    public void setAcesEnabled(boolean b) {
        this.acesEnabled = b;
    }

    public String getPreviewQuality() {
        return previewQuality;
    }

    public void setPreviewQuality(String q) {
        this.previewQuality = q;
    }

    public double getPreviewScale() {
        // Use manual visor scale if defined, otherwise fallback to quality preset
        return visorScale;
    }

    // Visor / Viewer Settings
    private double visorScale = 0.5; // 1.0 (Full), 0.5 (Half), 0.25 (Quarter)
    private String visorBitrate = "High"; // High, Medium, Low (Controls interpolation/rendering quality)

    public double getVisorScale() {
        return visorScale;
    }

    public void setVisorScale(double s) {
        this.visorScale = s;
    }

    public String getVisorBitrate() {
        return visorBitrate;
    }

    public void setVisorBitrate(String b) {
        this.visorBitrate = b;
    }

    public String getTemplate() {
        return template;
    }

    public void setTemplate(String t) {
        this.template = t;
    }

    public String getFieldOrder() {
        return fieldOrder;
    }

    public void setFieldOrder(String o) {
        this.fieldOrder = o;
    }

    public String getPixelAspectRatio() {
        return pixelAspectRatio;
    }

    public void setPixelAspectRatio(String r) {
        this.pixelAspectRatio = r;
    }

    public String getPixelFormat() {
        return pixelFormat;
    }

    public void setPixelFormat(String f) {
        this.pixelFormat = f;
    }

    public String getGamma() {
        return gamma;
    }

    public void setGamma(String g) {
        this.gamma = g;
    }

    public String getRenderingQuality() {
        return renderingQuality;
    }

    public void setRenderingQuality(String q) {
        this.renderingQuality = q;
    }

    public String getDeinterlaceMethod() {
        return deinterlaceMethod;
    }

    public void setDeinterlaceMethod(String m) {
        this.deinterlaceMethod = m;
    }

    public String getResampleMode() {
        return resampleMode;
    }

    public void setResampleMode(String m) {
        this.resampleMode = m;
    }

    public boolean isOut360() {
        return out360;
    }

    public void setOut360(boolean b) {
        this.out360 = b;
    }

    public String getProjectRes() {
        return projectRes;
    }

    public void setProjectRes(String res) {
        this.projectRes = res;
    }

    public String getPreviewRes() {
        return previewRes;
    }

    public void setPreviewRes(String res) {
        this.previewRes = res;
    }

    public String getDisplayRes() {
        return displayRes;
    }

    public void setDisplayRes(String res) {
        this.displayRes = res;
    }

    public boolean isLowResPreview() {
        return lowResPreview;
    }

    public void setLowResPreview(boolean low) {
        this.lowResPreview = low;
    }

    public double getFPS() {
        return fps;
    }

    public void setFPS(double fps) {
        this.fps = fps;
    }

    public int getAudioSampleRate() {
        return audioSampleRate;
    }

    public void setAudioSampleRate(int rate) {
        this.audioSampleRate = rate;
    }

    public int getAudioChannels() {
        return audioChannels;
    }

    public void setAudioChannels(int channels) {
        this.audioChannels = channels;
    }

    public int getProjectWidth() {
        return parseWidth(projectRes);
    }

    public int getProjectHeight() {
        return parseHeight(projectRes);
    }

    public int getPreviewWidth() {
        return parseWidth(previewRes);
    }

    public int getPreviewHeight() {
        return parseHeight(previewRes);
    }

    private int parseWidth(String res) {
        try {
            return Integer.parseInt(res.split("x")[0]);
        } catch (Exception e) {
            return 1920;
        }
    }

    private int parseHeight(String res) {
        try {
            String part = res.split("x")[1];
            // Might have 'x1080x32' or 'x1080;'
            String hStr = part.split("[x;\\s]")[0];
            return Integer.parseInt(hStr);
        } catch (Exception e) {
            return 1080;
        }
    }
}
