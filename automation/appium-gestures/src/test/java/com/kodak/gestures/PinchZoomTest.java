package com.kodak.gestures;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertNotNull;

/**
 * Standalone verification test for pinch-in / pinch-out (Maven: mvn clean test).
 * Requires Appium server + device with app in foreground (e.g. edit canvas).
 */
class PinchZoomTest extends BaseTest {

    @Test
    void pinchOutThenIn_withScreenshots() throws Exception {
        assertNotNull(driver, "driver");
        GestureUtils.Point center = GestureUtils.resolveCenter(driver, config);
        int inner = config.innerOffsetPixels();
        int outer = config.outerOffsetPixels();
        int duration = config.gestureDurationMs();

        GestureUtils.runWithScreenshots(
                driver,
                config,
                "test_pinch_out",
                () -> GestureUtils.pinchOut(driver, center, inner, outer, duration)
        );
        Thread.sleep(400);
        GestureUtils.runWithScreenshots(
                driver,
                config,
                "test_pinch_in",
                () -> GestureUtils.pinchIn(driver, center, inner, outer, duration)
        );
    }
}
