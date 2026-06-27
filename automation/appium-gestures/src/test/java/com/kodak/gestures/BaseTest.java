package com.kodak.gestures;

import io.appium.java_client.android.AndroidDriver;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * JUnit lifecycle for optional {@link PinchZoomTest}.
 */
public abstract class BaseTest {

    protected final Logger log = LoggerFactory.getLogger(getClass());
    protected GestureConfig config;
    protected AndroidDriver driver;

    @BeforeEach
    void baseSetUp() throws Exception {
        config = GestureConfig.loadDefault();
        driver = DriverManager.createDriver(config);
        log.info("BaseTest driver ready");
    }

    @AfterEach
    void baseTearDown() {
        DriverManager.quitQuietly(driver);
        driver = null;
    }
}
