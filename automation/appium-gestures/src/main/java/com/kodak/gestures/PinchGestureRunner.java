package com.kodak.gestures;

import io.appium.java_client.android.AndroidDriver;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;

/**
 * CLI entry point for Jenkins / Maestro shell hooks.
 * Exit codes: 0 = success, 1 = usage/config error, 2 = gesture failure.
 *
 * Usage:
 *   mvn -q exec:java -Dexec.args="pinch-out"
 *   mvn -q exec:java -Dexec.args="pinch-in --udid ZA222RFQ75"
 *   java -jar target/appium-gestures-1.0.0.jar both
 */
public final class PinchGestureRunner {

    private static final Logger LOG = LoggerFactory.getLogger(PinchGestureRunner.class);

    private PinchGestureRunner() {
    }

    public static void main(String[] args) {
        int code = run(args);
        System.exit(code);
    }

    public static int run(String[] args) {
        try {
            applyCliOverrides(args);
            GestureConfig config = GestureConfig.loadDefault();
            String mode = parseMode(args, config.gestureMode());
            execute(mode, config);
            LOG.info("PinchGestureRunner finished successfully mode={}", mode);
            return 0;
        } catch (IllegalArgumentException e) {
            LOG.error("Invalid arguments: {}", e.getMessage());
            printUsage();
            return 1;
        } catch (Exception e) {
            LOG.error("Pinch gesture failed", e);
            return 2;
        }
    }

    private static void execute(String mode, GestureConfig config) throws IOException {
        AndroidDriver driver = null;
        try {
            driver = DriverManager.createDriver(config);
            GestureUtils.Point center = GestureUtils.resolveCenter(driver, config);
            int inner = config.innerOffsetPixels();
            int outer = config.outerOffsetPixels();
            int duration = config.gestureDurationMs();

            switch (mode) {
                case "pinch-out", "pinchout", "out" -> GestureUtils.runWithScreenshots(
                        driver, config, "pinch_out",
                        () -> GestureUtils.pinchOut(driver, center, inner, outer, duration)
                );
                case "pinch-in", "pinchin", "in" -> GestureUtils.runWithScreenshots(
                        driver, config, "pinch_in",
                        () -> GestureUtils.pinchIn(driver, center, inner, outer, duration)
                );
                case "both" -> {
                    GestureUtils.runWithScreenshots(
                            driver, config, "pinch_out",
                            () -> GestureUtils.pinchOut(driver, center, inner, outer, duration)
                    );
                    Thread.sleep(400);
                    GestureUtils.runWithScreenshots(
                            driver, config, "pinch_in",
                            () -> GestureUtils.pinchIn(driver, center, inner, outer, duration)
                    );
                }
                default -> throw new IllegalArgumentException("Unknown gesture mode: " + mode);
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IOException("Interrupted during gesture pause", e);
        } finally {
            DriverManager.quitQuietly(driver);
        }
    }

    private static String parseMode(String[] args, String defaultMode) {
        for (int i = 0; i < args.length; i++) {
            String a = args[i];
            if (a.startsWith("--")) {
                continue;
            }
            return a.toLowerCase();
        }
        return defaultMode.toLowerCase();
    }

    private static void applyCliOverrides(String[] args) {
        for (int i = 0; i < args.length; i++) {
            String a = args[i];
            if ("--udid".equals(a) && i + 1 < args.length) {
                System.setProperty("android.device.udid", args[++i]);
            } else if ("--server".equals(a) && i + 1 < args.length) {
                System.setProperty("appium.server.url", args[++i]);
            } else if ("--x".equals(a) && i + 1 < args.length) {
                System.setProperty("gesture.center.x.percent", args[++i]);
            } else if ("--y".equals(a) && i + 1 < args.length) {
                System.setProperty("gesture.center.y.percent", args[++i]);
            }
        }
    }

    private static void printUsage() {
        System.err.println("""
                PinchGestureRunner — isolated Appium W3C pinch module
                Usage:
                  mvn -q exec:java -Dexec.args="pinch-out"
                  mvn -q exec:java -Dexec.args="pinch-in --udid SERIAL"
                  mvn -q exec:java -Dexec.args="both --server http://127.0.0.1:4723"
                Modes: pinch-out | pinch-in | both
                Config: config.properties (override via -Dkey=value)
                """);
    }
}
