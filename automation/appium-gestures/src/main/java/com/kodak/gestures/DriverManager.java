package com.kodak.gestures;

import io.appium.java_client.android.AndroidDriver;
import io.appium.java_client.android.options.UiAutomator2Options;
import org.openqa.selenium.WebDriver;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.MalformedURLException;
import java.net.URL;
import java.time.Duration;

/**
 * Creates and quits a single Appium AndroidDriver session (physical device).
 */
public final class DriverManager {

    private static final Logger LOG = LoggerFactory.getLogger(DriverManager.class);

    private DriverManager() {
    }

    public static AndroidDriver createDriver(GestureConfig config) throws MalformedURLException {
        UiAutomator2Options options = new UiAutomator2Options();
        options.setPlatformName("Android");
        options.setAutomationName("UiAutomator2");
        options.setAppPackage(config.appPackage());
        if (!config.appActivity().isBlank()) {
            options.setAppActivity(config.appActivity());
        }
        options.setNoReset(config.noReset());
        options.setFullReset(config.fullReset());
        options.dontStopAppOnReset();
        String udid = config.deviceUdid();
        if (!udid.isBlank()) {
            options.setUdid(udid);
            options.setCapability("appium:udid", udid);
        }
        options.setNewCommandTimeout(Duration.ofSeconds(120));
        options.setCapability("appium:skipServerInstallation", false);
        options.setCapability("appium:disableWindowAnimation", true);

        URL server = new URL(config.appiumServerUrl());
        LOG.info("Connecting Appium server={} udid={} package={}", server, udid.isBlank() ? "(default)" : udid, config.appPackage());
        AndroidDriver driver = new AndroidDriver(server, options);
        driver.manage().timeouts().implicitlyWait(Duration.ofSeconds(2));
        return driver;
    }

    public static void quitQuietly(WebDriver driver) {
        if (driver == null) {
            return;
        }
        try {
            driver.quit();
            LOG.info("Appium session closed");
        } catch (Exception e) {
            LOG.warn("Error closing driver: {}", e.getMessage());
        }
    }
}
