package egine.persistence;

import b.timeline.TimelineClip;
import b.timeline.TimelinePanel;
import b.timeline.ProjectProperties;
import egine.media.MediaPool;
import egine.media.MediaSource;
import java.io.*;
import java.util.*;

/**
 * Handles saving and loading of .rocky project files.
 */
public class ProjectManager {

    public static void saveProject(TimelinePanel panel, ProjectProperties props, MediaPool pool, File file) {
        try (PrintWriter writer = new PrintWriter(new FileWriter(file))) {
            writer.println("ROCKY_V4"); // Updated version
            writer.println("FPS:" + 30);

            // Save Project Settings
            writer.println("SET_PROJ:" + props.getProjectRes());
            writer.println("SET_PREV:" + props.getPreviewRes());
            writer.println("SET_DISP:" + props.getDisplayRes());

            // Save Tracks (Heights)
            StringBuilder tracksStr = new StringBuilder("TRACKS:");
            List<Integer> heights = panel.getTrackHeights();
            for (int i = 0; i < heights.size(); i++) {
                tracksStr.append(heights.get(i)).append(i < heights.size() - 1 ? "," : "");
            }
            writer.println(tracksStr.toString());

            // Save Media Pool
            for (MediaSource ms : pool.getAllSources().values()) {
                writer.println("MEDIA:" + ms.getId() + "|" + ms.getFilePath());
            }

            // Save Clips
            for (TimelineClip clip : panel.getClips()) {
                b.timeline.ClipTransform ct = clip.getTransform();
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
                        ct.getAnchorX() + "|" + ct.getAnchorY());

                // Save Mask
                egine.media.ClipMask mask = clip.getMask();
                if (mask != null && !mask.getAnchors().isEmpty()) {
                    StringBuilder maskStr = new StringBuilder("MASK:");
                    maskStr.append(mask.isEnabled()).append("|");
                    maskStr.append(mask.isInverted()).append("|");
                    maskStr.append(mask.isClosed()).append("|");

                    List<egine.media.MaskAnchor> anchors = mask.getAnchors();
                    for (int i = 0; i < anchors.size(); i++) {
                        egine.media.MaskAnchor a = anchors.get(i);
                        maskStr.append(a.getX()).append(",").append(a.getY());
                        if (i < anchors.size() - 1)
                            maskStr.append(";");
                    }
                    writer.println(maskStr.toString());
                }
            }
            System.out.println("Project saved to: " + file.getAbsolutePath());
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public static void loadProject(TimelinePanel panel, ProjectProperties props, MediaPool pool, File file) {
        if (!file.exists())
            return;

        try (BufferedReader reader = new BufferedReader(new FileReader(file))) {
            String header = reader.readLine();
            if (header == null || (!header.startsWith("ROCKY_V") && !header.startsWith("BERGA_V"))) {
                System.err.println("Invalid .rocky file format");
                return;
            }

            panel.clearClips();
            pool.clear();
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
                    for (String p : parts) {
                        try {
                            heights.add(Integer.parseInt(p));
                        } catch (NumberFormatException e) {
                        }
                    }
                    if (!heights.isEmpty()) {
                        panel.setTrackHeights(heights);
                    }
                } else if (line.startsWith("MEDIA:")) {
                    String[] data = line.substring(6).split("\\|");
                    if (data.length >= 2) {
                        pool.addSource(new MediaSource(data[0], data[1]));
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

                        // Handle V3 fields (Media Source)
                        if (data.length >= 10) {
                            clip.setMediaSourceId(data[8]);
                            clip.setSourceOffsetFrames(Long.parseLong(data[9]));
                        }

                        // Handle V4 fields (Transform)
                        if (data.length >= 17) {
                            b.timeline.ClipTransform ct = clip.getTransform();
                            ct.setX(Double.parseDouble(data[10]));
                            ct.setY(Double.parseDouble(data[11]));
                            ct.setScaleX(Double.parseDouble(data[12]));
                            ct.setScaleY(Double.parseDouble(data[13]));
                            ct.setRotation(Double.parseDouble(data[14]));
                            ct.setAnchorX(Double.parseDouble(data[15]));
                            ct.setAnchorY(Double.parseDouble(data[16]));
                        }

                        panel.addClip(clip);
                        lastClip = clip;
                    }
                } else if (line.startsWith("MASK:") && lastClip != null) {
                    String[] data = line.substring(5).split("\\|");
                    if (data.length >= 3) {
                        egine.media.ClipMask mask = lastClip.getMask();
                        mask.setEnabled(Boolean.parseBoolean(data[0]));
                        mask.setInverted(Boolean.parseBoolean(data[1]));
                        mask.setClosed(Boolean.parseBoolean(data[2]));

                        if (data.length >= 4) {
                            String[] anchorPairs = data[3].split(";");
                            for (String pair : anchorPairs) {
                                String[] coords = pair.split(",");
                                if (coords.length == 2) {
                                    mask.addAnchor(Double.parseDouble(coords[0]), Double.parseDouble(coords[1]));
                                }
                            }
                        }
                    }
                }
            }
            System.out.println("Project loaded from: " + file.getAbsolutePath());
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
