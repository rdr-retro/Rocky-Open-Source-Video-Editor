package rocky.core.logic;

import java.util.Comparator;
import java.util.List;
import rocky.core.model.ClipTransform;
import rocky.core.model.TimelineClip;
import rocky.core.model.TimelineKeyframe;

/**
 * Encapsulates temporal calculations, easing, and interpolation.
 * Independent of UI and rendering frameworks.
 */
public class TemporalMath {

    public static long getSourceFrameAt(TimelineClip clip, long clipFrame) {
        List<TimelineKeyframe> keyframes = clip.getTimeKeyframes();
        synchronized(keyframes) {
            if (keyframes.isEmpty()) {
                return clip.getSourceOffsetFrames() + clipFrame;
            }

            TimelineKeyframe left = null;
            TimelineKeyframe right = null;

            for (TimelineKeyframe k : keyframes) {
                if (k.getClipFrame() <= clipFrame) {
                    left = k;
                } else {
                    right = k;
                    break;
                }
            }

            if (left == null)
                return keyframes.get(0).getSourceFrame();
            if (right == null)
                return left.getSourceFrame();

            double t = (double) (clipFrame - left.getClipFrame()) / (right.getClipFrame() - left.getClipFrame());
            return left.getSourceFrame() + Math.round(t * (right.getSourceFrame() - left.getSourceFrame()));
        }
    }

    public static ClipTransform getInterpolatedTransform(TimelineClip clip, long clipFrame) {
        ClipTransform target = new ClipTransform();
        getInterpolatedTransform(clip, clipFrame, target);
        return target;
    }

    public static void getInterpolatedTransform(TimelineClip clip, long clipFrame, ClipTransform result) {
        List<TimelineKeyframe> keyframes = clip.getTimeKeyframes();
        synchronized (keyframes) {
            if (keyframes.isEmpty()) {
                ClipTransform source = clip.getTransform();
                result.setX(source.getX());
                result.setY(source.getY());
                result.setScaleX(source.getScaleX());
                result.setScaleY(source.getScaleY());
                result.setRotation(source.getRotation());
                result.setAnchorX(source.getAnchorX());
                result.setAnchorY(source.getAnchorY());
                return;
            }

            TimelineKeyframe left = null;
            TimelineKeyframe right = null;

            for (TimelineKeyframe k : keyframes) {
                if (k.getClipFrame() <= clipFrame) {
                    left = k;
                } else {
                    right = k;
                    break;
                }
            }

            if (left == null) {
                ClipTransform source = keyframes.get(0).getTransform();
                result.copyFrom(source);
                return;
            }
            if (right == null) {
                ClipTransform source = left.getTransform();
                result.copyFrom(source);
                return;
            }

            double t = (double) (clipFrame - left.getClipFrame()) / (right.getClipFrame() - left.getClipFrame());

            ClipTransform lt = left.getTransform();
            ClipTransform rt = right.getTransform();

            result.setX(lt.getX() + t * (rt.getX() - lt.getX()));
            result.setY(lt.getY() + t * (rt.getY() - lt.getY()));
            result.setScaleX(lt.getScaleX() + t * (rt.getScaleX() - lt.getScaleX()));
            result.setScaleY(lt.getScaleY() + t * (rt.getScaleY() - lt.getScaleY()));
            result.setRotation(lt.getRotation() + t * (rt.getRotation() - lt.getRotation()));
            result.setAnchorX(lt.getAnchorX() + t * (rt.getAnchorX() - lt.getAnchorX()));
            result.setAnchorY(lt.getAnchorY() + t * (rt.getAnchorY() - lt.getAnchorY()));
        }
    }

    public static double getOpacityAt(TimelineClip clip, long clipFrame) {
        double duration = clip.getDurationFrames();
        double progress = (double) clipFrame / duration;
        if (progress < 0) progress = 0;
        if (progress > 1) progress = 1;

        double baseOpacityAtFrame = clip.getStartOpacity() + progress * (clip.getEndOpacity() - clip.getStartOpacity());
        double opacity = baseOpacityAtFrame;

        // Fade In
        if (clipFrame < clip.getFadeInFrames()) {
            double t = (double) clipFrame / clip.getFadeInFrames();
            opacity *= getFadeValue(clip.getFadeInType(), t, true);
        }
        // Fade Out
        else if (clipFrame > duration - clip.getFadeOutFrames()) {
            long fadeOutStart = (long) (duration - clip.getFadeOutFrames());
            double t = (double) (clipFrame - fadeOutStart) / clip.getFadeOutFrames();
            opacity *= getFadeValue(clip.getFadeOutType(), t, false);
        }

        return opacity;
    }

    public static double getFadeValue(TimelineClip.FadeType type, double t, boolean isFadeIn) {
        if (t < 0) t = 0;
        if (t > 1) t = 1;

        double val = t;
        switch (type) {
            case LINEAR: val = t; break;
            case FAST:   val = Math.pow(t, 0.25); break;
            case SLOW:   val = Math.pow(t, 4.0); break;
            case SMOOTH: val = t * t * (3 - 2 * t); break;
            case SHARP:  val = 0.5 * (Math.sin(Math.PI * (t - 0.5)) + 1); break;
        }

        return isFadeIn ? val : 1.0 - val;
    }
}
