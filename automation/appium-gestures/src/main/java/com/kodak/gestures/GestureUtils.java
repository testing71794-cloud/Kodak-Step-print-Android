package com.kodak.gestures;

import io.appium.java_client.android.AndroidDriver;
import org.openqa.selenium.Dimension;
import org.openqa.selenium.OutputType;
import org.openqa.selenium.TakesScreenshot;
import org.openqa.selenium.interactions.PointerInput;
import org.openqa.selenium.interactions.Sequence;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Arrays;
import java.util.List;

/**
 * W3C multi-touch pinch gestures for Android (Appium 2.x).
 */
public final class GestureUtils {

    private static final Logger LOG = LoggerFactory.getLogger(GestureUtils.class);
    private static final DateTimeFormatter TS = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss_SSS");

    private GestureUtils() {
    }

    public record Point(int x, int y) {
    }

    public static Point resolveCenter(AndroidDriver driver, GestureConfig config) {
        Dimension size = driver.manage().window().getSize();
        int x = (size.width * config.centerXPercent()) / 100;
        int y = (size.height * config.centerYPercent()) / 100;
        LOG.debug("Viewport {}x{} center=({}, {})", size.width, size.height, x, y);
        return new Point(x, y);
    }

    /**
     * Pinch out (spread fingers) — zoom into content / tighter crop.
     */
    public static void pinchOut(AndroidDriver driver, Point center, int innerOffset, int outerOffset, int durationMs) {
        LOG.info("pinchOut center=({}, {}) inner={} outer={} durationMs={}", center.x(), center.y(), innerOffset, outerOffset, durationMs);
        performPinch(driver, center, innerOffset, outerOffset, durationMs);
    }

    /**
     * Pinch in (close fingers) — zoom out / fit more content.
     */
    public static void pinchIn(AndroidDriver driver, Point center, int innerOffset, int outerOffset, int durationMs) {
        LOG.info("pinchIn center=({}, {}) inner={} outer={} durationMs={}", center.x(), center.y(), innerOffset, outerOffset, durationMs);
        performPinch(driver, center, outerOffset, innerOffset, durationMs);
    }

    private static void performPinch(
            AndroidDriver driver,
            Point center,
            int startOffset,
            int endOffset,
            int durationMs
    ) {
        int leftStart = center.x() - startOffset;
        int leftEnd = center.x() - endOffset;
        int rightStart = center.x() + startOffset;
        int rightEnd = center.x() + endOffset;

        PointerInput finger1 = new PointerInput(PointerInput.Kind.TOUCH, "finger1");
        PointerInput finger2 = new PointerInput(PointerInput.Kind.TOUCH, "finger2");

        Sequence seq1 = buildFingerSequence(finger1, leftStart, center.y(), leftEnd, center.y(), durationMs);
        Sequence seq2 = buildFingerSequence(finger2, rightStart, center.y(), rightEnd, center.y(), durationMs);

        try {
            driver.perform(Arrays.asList(seq1, seq2));
            LOG.info("pinch gesture completed");
        } catch (Exception e) {
            throw new GestureException("W3C pinch gesture failed", e);
        }
    }

    private static Sequence buildFingerSequence(
            PointerInput finger,
            int startX,
            int startY,
            int endX,
            int endY,
            int durationMs
    ) {
        Sequence sequence = new Sequence(finger, 0);
        sequence.addAction(finger.createPointerMove(Duration.ZERO, PointerInput.Origin.viewport(), startX, startY));
        sequence.addAction(finger.createPointerDown(PointerInput.MouseButton.LEFT.asArg()));
        sequence.addAction(finger.createPointerMove(
                Duration.ofMillis(Math.max(100, durationMs)),
                PointerInput.Origin.viewport(),
                endX,
                endY
        ));
        sequence.addAction(finger.createPointerUp(PointerInput.MouseButton.LEFT.asArg()));
        return sequence;
    }

    public static Path captureScreenshot(AndroidDriver driver, Path dir, String label) throws IOException {
        Files.createDirectories(dir);
        String name = label + "_" + LocalDateTime.now().format(TS) + ".png";
        Path file = dir.resolve(name);
        byte[] png = ((TakesScreenshot) driver).getScreenshotAs(OutputType.BYTES);
        Files.write(file, png);
        LOG.info("Screenshot saved: {}", file.toAbsolutePath());
        return file;
    }

    public static void runWithScreenshots(
            AndroidDriver driver,
            GestureConfig config,
            String label,
            Runnable gesture
    ) throws IOException {
        Path dir = config.screenshotsDir();
        if (config.screenshotsEnabled()) {
            captureScreenshot(driver, dir, label + "_before");
        }
        gesture.run();
        if (config.screenshotsEnabled()) {
            captureScreenshot(driver, dir, label + "_after");
        }
    }

    public static class GestureException extends RuntimeException {
        public GestureException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}
