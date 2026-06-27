package com.kodak.gestures;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Properties;

/**
 * Loads config.properties with system-property overrides (Jenkins / CLI friendly).
 */
public final class GestureConfig {

    private final Properties props = new Properties();

    public GestureConfig(Path configFile) throws IOException {
        if (configFile != null && Files.isRegularFile(configFile)) {
            try (InputStream in = Files.newInputStream(configFile)) {
                props.load(in);
            }
        }
    }

    public static GestureConfig loadDefault() throws IOException {
        String explicit = System.getProperty("gesture.config", "").trim();
        if (!explicit.isEmpty()) {
            return new GestureConfig(Paths.get(explicit));
        }
        Path cwd = Paths.get("config.properties");
        if (Files.isRegularFile(cwd)) {
            return new GestureConfig(cwd);
        }
        return new GestureConfig(null);
    }

    public String get(String key, String defaultValue) {
        String sys = System.getProperty(key);
        if (sys != null && !sys.isBlank()) {
            return sys.trim();
        }
        return props.getProperty(key, defaultValue).trim();
    }

    public int getInt(String key, int defaultValue) {
        String raw = get(key, String.valueOf(defaultValue));
        try {
            return Integer.parseInt(raw);
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }

    public boolean getBoolean(String key, boolean defaultValue) {
        String raw = get(key, String.valueOf(defaultValue));
        return raw.equalsIgnoreCase("true") || raw.equals("1") || raw.equalsIgnoreCase("yes");
    }

    public String appiumServerUrl() {
        return get("appium.server.url", "http://127.0.0.1:4723");
    }

    public String deviceUdid() {
        return get("android.device.udid", "");
    }

    public String appPackage() {
        return get("app.package", "com.kodak.steptouch");
    }

    public String appActivity() {
        return get("app.activity", "");
    }

    public boolean noReset() {
        return getBoolean("app.no.reset", true);
    }

    public boolean fullReset() {
        return getBoolean("app.full.reset", false);
    }

    public boolean autoLaunch() {
        return getBoolean("auto.launch", false);
    }

    public int centerXPercent() {
        return getInt("gesture.center.x.percent", 50);
    }

    public int centerYPercent() {
        return getInt("gesture.center.y.percent", 42);
    }

    public int innerOffsetPixels() {
        return getInt("gesture.inner.offset.pixels", 60);
    }

    public int outerOffsetPixels() {
        return getInt("gesture.outer.offset.pixels", 140);
    }

    public int gestureDurationMs() {
        return getInt("gesture.duration.ms", 650);
    }

    public String gestureMode() {
        return get("gesture.mode", "both").toLowerCase();
    }

    public Path screenshotsDir() {
        return Paths.get(get("screenshots.dir", "target/screenshots"));
    }

    public boolean screenshotsEnabled() {
        return getBoolean("screenshots.enabled", true);
    }
}
