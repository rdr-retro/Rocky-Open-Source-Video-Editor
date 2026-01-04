package rocky.core.persistence;

import rocky.ui.timeline.TimelineClip;
import rocky.ui.timeline.TimelinePanel;
import rocky.ui.timeline.ProjectProperties;
import rocky.ui.keyframes.TimelineKeyframe;
import rocky.core.media.MediaPool;
import rocky.core.media.MediaSource;
import java.io.*;
import java.util.*;

/**
 * Handles saving and loading of .rocky project files.
 */
public class ProjectManager {

    public static void saveProject(TimelinePanel panel, ProjectProperties props, MediaPool pool, File file) {
        String state = serializeProject(panel, props, pool);
        try (PrintWriter writer = new PrintWriter(new FileWriter(file))) {
            writer.print(state);
            System.out.println("Project saved to: " + file.getAbsolutePath());
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public static void loadProject(TimelinePanel panel, ProjectProperties props, MediaPool pool, rocky.ui.timeline.SidebarPanel sidebar, File file) {
        if (!file.exists())
            return;
        try (BufferedReader reader = new BufferedReader(new FileReader(file))) {
            loadFromReader(panel, props, pool, sidebar, reader);
            System.out.println("Project loaded from: " + file.getAbsolutePath());
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static String serializeProject(TimelinePanel panel, ProjectProperties props, MediaPool pool) {
        StringWriter sw = new StringWriter();
        try (PrintWriter writer = new PrintWriter(sw)) {
            writer.println("ROCKY_V6");
            writer.println("FPS:" + props.getFPS());

            // Save Project Settings
            writer.println("SET_PROJ:" + props.getProjectRes());
            writer.println("SET_PREV:" + props.getPreviewRes());
            writer.println("SET_DISP:" + props.getDisplayRes());

            // Save Tracks (Types and Heights)
            StringBuilder tracksStr = new StringBuilder("TRACKS:");
            List<Integer> heights = panel.getTrackHeights();
            List<rocky.ui.timeline.TrackControlPanel.TrackType> types = panel.getTrackTypes();
            for (int i = 0; i < heights.size(); i++) {
                String type = (i < types.size() && types.get(i) != null) ? types.get(i).name() : "VIDEO";
                tracksStr.append(type).append(":").append(heights.get(i));
                if (i < heights.size() - 1)
                    tracksStr.append(",");
            }
            writer.println(tracksStr.toString());

            // Save Media Pool
            for (MediaSource ms : pool.getAllSources().values()) {
                writer.println("MEDIA:" + ms.getId() + "|" + ms.getFilePath());
            }

            // Save Clips
            for (TimelineClip clip : panel.getClips()) {
                rocky.ui.timeline.ClipTransform ct = clip.getTransform();
                writer.println("CLIP:" +
                        clip.getName() + "|" +
                        clip.getStartFrame() + "|" +
                        clip.getDurationFrames() + "|" +
                        clip.getTrackIndex() + "|" +
                        clip.getFadeInFrames() + "|" +
                        clip.getFadeOutFrames() + "|" +
                        clip.getFadeInType() + "|" +
                        clip.getFadeOutType() + "|" +
                        clip.getMediaSourceId() + "|" +
                        clip.getSourceOffsetFrames() + "|" +
                        ct.getX() + "|" + ct.getY() + "|" +
                        ct.getScaleX() + "|" + ct.getScaleY() + "|" +
                        ct.getRotation() + "|" +
                        ct.getAnchorX() + "|" + ct.getAnchorY() + "|" +
                        clip.getStartOpacity() + "|" + clip.getEndOpacity());

                // Save Mask
                rocky.core.media.ClipMask mask = clip.getMask();
                if (mask != null && !mask.getAnchors().isEmpty()) {
                    StringBuilder maskStr = new StringBuilder("MASK:");
                    maskStr.append(mask.isEnabled()).append("|");
                    maskStr.append(mask.isInverted()).append("|");
                    maskStr.append(mask.isClosed()).append("|");

                    List<rocky.core.media.MaskAnchor> anchors = mask.getAnchors();
                    for (int i = 0; i < anchors.size(); i++) {
                        rocky.core.media.MaskAnchor a = anchors.get(i);
                        maskStr.append(a.getX()).append(",").append(a.getY());
                        if (i < anchors.size() - 1)
                            maskStr.append(";");
                    }
                    writer.println(maskStr.toString());
                }

                // Save Keyframes
                synchronized (clip.getTimeKeyframes()) {
                    for (TimelineKeyframe k : clip.getTimeKeyframes()) {
                        rocky.ui.timeline.ClipTransform kt = k.getTransform();
                        writer.println("KEYFRAME:" +
                                k.getClipFrame() + "|" +
                                k.getSourceFrame() + "|" +
                                kt.getX() + "|" + kt.getY() + "|" +
                                kt.getScaleX() + "|" + kt.getScaleY() + "|" +
                                kt.getRotation() + "|" +
                                kt.getAnchorX() + "|" + kt.getAnchorY());
                    }
                }
            }
        }
        return sw.toString();
    }

    public static void deserializeProject(TimelinePanel panel, ProjectProperties props, MediaPool pool, rocky.ui.timeline.SidebarPanel sidebar, String state) {
        try (BufferedReader reader = new BufferedReader(new StringReader(state))) {
            loadFromReader(panel, props, pool, sidebar, reader);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void loadFromReader(TimelinePanel panel, ProjectProperties props, MediaPool pool, rocky.ui.timeline.SidebarPanel sidebar, BufferedReader reader)
            throws Exception {
        String header = reader.readLine();
        if (header == null || (!header.startsWith("ROCKY_V") && !header.startsWith("BERGA_V"))) {
            return;
        }

        panel.clearClips();
        // NOTE: We usually don't clear the pool for undo/redo to avoid reloading assets
        // But if a file was removed, it should be reflected? 
        // For simplicity, let's keep assets in memory.
        
        String line;
        TimelineClip lastClip = null;

        while ((line = reader.readLine()) != null) {
            if (line.startsWith("SET_PROJ:")) {
                props.setProjectRes(line.substring(9));
            } else if (line.startsWith("SET_PREV:")) {
                props.setPreviewRes(line.substring(9));
            } else if (line.startsWith("SET_DISP:")) {
                props.setDisplayRes(line.substring(9));
            } else if (line.startsWith("TRACKS:")) {
                String[] parts = line.substring(7).split(",");
                List<Integer> heights = new ArrayList<>();
                List<rocky.ui.timeline.TrackControlPanel.TrackType> types = new ArrayList<>();
                for (String p : parts) {
                    try {
                        if (p.contains(":")) {
                            String[] tp = p.split(":");
                            types.add(rocky.ui.timeline.TrackControlPanel.TrackType.valueOf(tp[0]));
                            heights.add(Integer.parseInt(tp[1]));
                        } else {
                            // Backward compatibility
                            heights.add(Integer.parseInt(p));
                            types.add(rocky.ui.timeline.TrackControlPanel.TrackType.VIDEO);
                        }
                    } catch (Exception e) {
                    }
                }
                if (!heights.isEmpty()) {
                    panel.setTrackHeights(heights);
                    panel.setTrackTypes(types);
                    if (sidebar != null) {
                        sidebar.reconstructTracks(types, heights);
                    }
                }
            } else if (line.startsWith("MEDIA:")) {
                String[] data = line.substring(6).split("\\|");
                if (data.length >= 2) {
                    if (!pool.getAllSources().containsKey(data[0])) {
                        pool.addSource(new MediaSource(data[0], data[1], props.getPreviewScale()));
                    }
                }
            } else if (line.startsWith("CLIP:")) {
                String[] data = line.substring(5).split("\\|");
                if (data.length >= 8) {
                    String name = data[0];
                    long start = Long.parseLong(data[1]);
                    long duration = Long.parseLong(data[2]);
                    int track = Integer.parseInt(data[3]);
                    long fadeIn = Long.parseLong(data[4]);
                    long fadeOut = Long.parseLong(data[5]);
                    TimelineClip.FadeType fadeInType = TimelineClip.FadeType.valueOf(data[6]);
                    TimelineClip.FadeType fadeOutType = TimelineClip.FadeType.valueOf(data[7]);

                    TimelineClip clip = new TimelineClip(name, start, duration, track);
                    clip.setFadeInFrames(fadeIn);
                    clip.setFadeOutFrames(fadeOut);
                    clip.setFadeInType(fadeInType);
                    clip.setFadeOutType(fadeOutType);

                    if (data.length >= 10) {
                        clip.setMediaSourceId(data[8]);
                        clip.setSourceOffsetFrames(Long.parseLong(data[9]));
                    }
                    if (data.length >= 17) {
                        rocky.ui.timeline.ClipTransform ct = clip.getTransform();
                        ct.setX(Double.parseDouble(data[10]));
                        ct.setY(Double.parseDouble(data[11]));
                        ct.setScaleX(Double.parseDouble(data[12]));
                        ct.setScaleY(Double.parseDouble(data[13]));
                        ct.setRotation(Double.parseDouble(data[14]));
                        ct.setAnchorX(Double.parseDouble(data[15]));
                        ct.setAnchorY(Double.parseDouble(data[16]));
                    }
                    if (data.length >= 19) {
                        clip.setStartOpacity(Double.parseDouble(data[17]));
                        clip.setEndOpacity(Double.parseDouble(data[18]));
                    } else if (data.length == 18) {
                        double op = Double.parseDouble(data[17]);
                        clip.setStartOpacity(op);
                        clip.setEndOpacity(op);
                    }

                    panel.addClip(clip);
                    lastClip = clip;
                }
            } else if (line.startsWith("KEYFRAME:") && lastClip != null) {
                String[] data = line.substring(9).split("\\|");
                if (data.length >= 9) {
                    long cf = Long.parseLong(data[0]);
                    long sf = Long.parseLong(data[1]);
                    TimelineKeyframe k = new TimelineKeyframe(cf, sf);
                    rocky.ui.timeline.ClipTransform kt = k.getTransform();
                    kt.setX(Double.parseDouble(data[2]));
                    kt.setY(Double.parseDouble(data[3]));
                    kt.setScaleX(Double.parseDouble(data[4]));
                    kt.setScaleY(Double.parseDouble(data[5]));
                    kt.setRotation(Double.parseDouble(data[6]));
                    kt.setAnchorX(Double.parseDouble(data[7]));
                    kt.setAnchorY(Double.parseDouble(data[8]));
                    lastClip.getTimeKeyframes().add(k);
                }
            }
        }
    }
}
