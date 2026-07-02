#!/usr/bin/env node
/**
 * True two-finger pinch via Appium W3C Actions (WebdriverIO).
 * Usage: node pinch_w3c.mjs [both|pinch-out|pinch-in] [DEVICE_SERIAL]
 */
import { remote } from 'webdriverio';
import { mkdir, writeFile } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execSync } from 'node:child_process';

const __dirname = dirname(fileURLToPath(import.meta.url));
const moduleRoot = join(__dirname, '..');

const gesture = (process.argv[2] || 'both').toLowerCase();
const device = process.argv[3] || process.env.ANDROID_SERIAL || '';
const appiumUrl = process.env.APPIUM_SERVER_URL || 'http://127.0.0.1:4723';
const appPackage = process.env.APP_PACKAGE || 'com.kodak.steptouch';
const galleryPinch = process.env.GALLERY_PINCH === '1';
const galleryGa05ZoomOut = process.env.GALLERY_GA05_ZOOM_OUT === '1';
const galleryImageId = process.env.GALLERY_IMAGE_RESOURCE_ID || `${appPackage}:id/camera_image`;
const sdkRoot = process.env.ANDROID_SDK_ROOT || process.env.ANDROID_HOME || join(process.env.LOCALAPPDATA || '', 'Android', 'Sdk');
const adb = join(sdkRoot, 'platform-tools', process.platform === 'win32' ? 'adb.exe' : 'adb');

function adbShell(cmd) {
  execSync(`"${adb}" -s ${device} shell ${cmd}`, { stdio: 'ignore' });
}

function prepareDeviceForAppium() {
  console.log('[INFO] Releasing UiAutomation before Appium pinch (stop Maestro + Appium servers)');
  const stops = [
    'am force-stop dev.mobile.maestro',
    'am force-stop dev.mobile.maestro.test',
    'am force-stop io.appium.uiautomator2.server',
    'am force-stop io.appium.uiautomator2.server.test',
  ];
  for (const cmd of stops) {
    try {
      adbShell(cmd);
    } catch {
      /* ignore */
    }
  }
  execSync('ping 127.0.0.1 -n 4', { stdio: 'ignore', shell: true });
}

function prepareDeviceForMaestro() {
  console.log('[INFO] Stopping Appium servers so Maestro can reconnect for ED_03b');
  const stops = [
    'am force-stop io.appium.uiautomator2.server',
    'am force-stop io.appium.uiautomator2.server.test',
  ];
  for (const cmd of stops) {
    try {
      adbShell(cmd);
    } catch {
      /* ignore */
    }
  }
  try {
    execSync(`"${adb}" reconnect`, { stdio: 'ignore' });
  } catch {
    /* ignore */
  }
  execSync('ping 127.0.0.1 -n 4', { stdio: 'ignore', shell: true });
}

const centerXPercent = 50;
const centerYPercent = parseInt(process.env.PINCH_CENTER_Y_PERCENT || '45', 10);
const pinchStyle = (process.env.PINCH_STYLE || (process.env.GALLERY_PINCH === '1' ? 'diagonal' : 'horizontal')).toLowerCase();
const inner = 60;
const outer = 140;
const durationMs = 650;

if (!device) {
  console.error('ERROR: device serial required (arg 2 or ANDROID_SERIAL)');
  process.exit(1);
}

const screenshotDir = join(moduleRoot, 'target', 'screenshots', 'w3c');

function ts() {
  return new Date().toISOString().replace(/[-:]/g, '').replace('T', '_').slice(0, 18);
}

async function saveScreenshot(driver, label) {
  const path = join(screenshotDir, `${label}_${ts()}.png`);
  const png = await driver.takeScreenshot();
  await writeFile(path, png, 'base64');
  console.log(`[INFO] Screenshot ${path}`);
}

function fingerSequence(id, startX, startY, endX, endY) {
  return {
    type: 'pointer',
    id,
    parameters: { pointerType: 'touch' },
    actions: [
      { type: 'pointerMove', duration: 0, x: startX, y: startY },
      { type: 'pointerDown', button: 0 },
      { type: 'pointerMove', duration: durationMs, x: endX, y: endY },
      { type: 'pointerUp', button: 0 },
    ],
  };
}

async function logForegroundActivity() {
  try {
    const out = execSync(`"${adb}" -s ${device} shell dumpsys window | findstr /i mCurrentFocus`, {
      encoding: 'utf8',
      shell: true,
    }).trim();
    if (out) console.log(`[INFO] Foreground window: ${out.split('\n')[0]}`);
  } catch {
    /* ignore */
  }
}

async function findPinchTarget(driver, timeoutMs = 10000) {
  const fullIds = [
    galleryImageId.includes(':id/') ? galleryImageId : `${appPackage}:id/camera_image`,
    `${appPackage}:id/camera_image`,
    `${appPackage}:id/cameara_layout`,
  ];
  const selectors = [];
  for (const fullId of [...new Set(fullIds)]) {
    selectors.push(`android=new UiSelector().resourceId("${fullId}")`);
    selectors.push(`-android uiautomator:new UiSelector().resourceId("${fullId}")`);
    const shortId = fullId.split(':id/')[1];
    if (shortId) selectors.push(`id=${shortId}`);
  }
  let lastErr = null;
  for (const sel of selectors) {
    try {
      const el = await driver.$(sel);
      await el.waitForExist({ timeout: Math.min(timeoutMs, 4000) });
      console.log(`[INFO] Pinch target found via selector: ${sel}`);
      return { el, selector: sel };
    } catch (err) {
      lastErr = err;
    }
  }
  throw lastErr ?? new Error('pinch target not found');
}

async function elementBounds(el) {
  try {
    return await el.getElementRect();
  } catch {
    const loc = await el.getLocation();
    const size = await el.getSize();
    return { x: loc.x, y: loc.y, width: size.width, height: size.height };
  }
}

async function resolvePinchTargetBounds(driver, width, height) {
  const skipActivate = galleryPinch || process.env.SKIP_ACTIVATE_APP === '1';
  try {
    if (!skipActivate) {
      await driver.activateApp(appPackage);
      await driver.pause(800);
    } else {
      await driver.pause(1200);
    }
    const { el, selector } = await findPinchTarget(driver, skipActivate ? 10000 : 8000);
    const rect = await elementBounds(el);
    const cx = Math.round(rect.x + rect.width / 2);
    const cy = Math.round(rect.y + rect.height / 2);
    const span = Math.round(Math.min(rect.width, rect.height) * 0.32);
    console.log(`[INFO] Pinch center from ${selector} bounds [${rect.x},${rect.y}][${rect.x + rect.width},${rect.y + rect.height}] -> ${cx},${cy} span=${span}`);
    return { cx, cy, inner: Math.round(span * 0.35), outer: span, rect, selector };
  } catch (err) {
    const msg = `Pinch center element lookup failed for ${galleryImageId}: ${err.message}`;
    if (galleryPinch) {
      throw new Error(`${msg} (gallery detail must stay open after Maestro pre-pinch)`);
    }
    console.log(`[INFO] ${msg}`);
  }
  const cx = Math.round((width * centerXPercent) / 100);
  const cy = Math.round((height * centerYPercent) / 100);
  console.log(`[INFO] Pinch center fallback ${centerXPercent}%,${centerYPercent}% -> ${cx},${cy}`);
  return { cx, cy, inner, outer, rect: null, selector: 'fallback' };
}

async function performMobilePinch(driver, spread, rect) {
  const percent = parseFloat(process.env.PINCH_GESTURE_PERCENT || '0.85', 10);
  const args = {
    left: Math.round(rect.x),
    top: Math.round(rect.y),
    width: Math.round(rect.width),
    height: Math.round(rect.height),
    percent,
  };
  const cmd = spread ? 'mobile: pinchOpenGesture' : 'mobile: pinchCloseGesture';
  console.log(`[INFO] ${cmd} ${JSON.stringify(args)}`);
  await driver.execute(cmd, args);
  await driver.pause(durationMs + 500);
}

async function performW3cPinchFromTarget(driver, spread, target) {
  const { cx, cy } = target;
  const innerRadius = target.inner ?? inner;
  const outerRadius = target.outer ?? outer;

  let finger1Start;
  let finger1End;
  let finger2Start;
  let finger2End;

  if (pinchStyle === 'diagonal') {
    if (spread) {
      finger1Start = [cx + innerRadius, cy + innerRadius];
      finger1End = [cx + outerRadius, cy + outerRadius];
      finger2Start = [cx - innerRadius, cy - innerRadius];
      finger2End = [cx - outerRadius, cy - outerRadius];
      console.log(`[INFO] diagonal pinch-out F1 ${finger1Start}->${finger1End} F2 ${finger2Start}->${finger2End}`);
    } else {
      finger1Start = [cx + outerRadius, cy + outerRadius];
      finger1End = [cx + innerRadius, cy + innerRadius];
      finger2Start = [cx - outerRadius, cy - outerRadius];
      finger2End = [cx - innerRadius, cy - innerRadius];
      console.log(`[INFO] diagonal pinch-in F1 ${finger1Start}->${finger1End} F2 ${finger2Start}->${finger2End}`);
    }
  } else if (spread) {
    finger1Start = [cx - innerRadius, cy];
    finger1End = [cx - outerRadius, cy];
    finger2Start = [cx + innerRadius, cy];
    finger2End = [cx + outerRadius, cy];
    console.log(`[INFO] horizontal pinch-out F1 ${finger1Start}->${finger1End} F2 ${finger2Start}->${finger2End}`);
  } else {
    finger1Start = [cx - outerRadius, cy];
    finger1End = [cx - innerRadius, cy];
    finger2Start = [cx + outerRadius, cy];
    finger2End = [cx + innerRadius, cy];
    console.log(`[INFO] horizontal pinch-in F1 ${finger1Start}->${finger1End} F2 ${finger2Start}->${finger2End}`);
  }

  await driver.performActions([
    fingerSequence('finger1', finger1Start[0], finger1Start[1], finger1End[0], finger1End[1]),
    fingerSequence('finger2', finger2Start[0], finger2Start[1], finger2End[0], finger2End[1]),
  ]);
  await driver.releaseActions();
  await driver.pause(durationMs + 500);
}

async function performPinch(driver, spread) {
  const { width, height } = await driver.getWindowSize();
  const target = await resolvePinchTargetBounds(driver, width, height);
  if (galleryPinch && spread && target.rect) {
    await performMobilePinch(driver, true, target.rect);
    return;
  }
  if (galleryPinch && !spread) {
    console.log('[INFO] GA_05 zoom-out: W3C two-finger pinch-in (mobile pinchClose unreliable on this app)');
    await performW3cPinchFromTarget(driver, false, target);
    return;
  }
  if (galleryPinch && target.rect) {
    await performMobilePinch(driver, spread, target.rect);
    return;
  }
  await performW3cPinchFromTarget(driver, spread, target);
}

let driver;
try {
  await mkdir(screenshotDir, { recursive: true });
  console.log(`[INFO] Appium W3C pinch gesture=${gesture} device=${device} server=${appiumUrl}`);

  prepareDeviceForAppium();
  await logForegroundActivity();

  const capabilities = {
    platformName: 'Android',
    'appium:automationName': 'UiAutomator2',
    'appium:udid': device,
    'appium:noReset': true,
    'appium:dontStopAppOnReset': true,
    'appium:disableWindowAnimation': true,
    'appium:newCommandTimeout': 120,
    'appium:skipServerInstallation': false,
    'appium:settings[waitForIdleTimeout]': 0,
  };
  if (galleryPinch) {
    // Maestro pre-pinch leaves photo detail open — attach without relaunching main activity.
    capabilities['appium:autoLaunch'] = false;
    console.log('[INFO] Gallery pinch: autoLaunch=false (keep Maestro photo detail screen)');
  } else {
    capabilities['appium:appPackage'] = appPackage;
  }

  driver = await remote({
    hostname: new URL(appiumUrl).hostname,
    port: Number(new URL(appiumUrl).port || 4723),
    path: new URL(appiumUrl).pathname === '/' ? '/' : new URL(appiumUrl).pathname,
    capabilities,
    connectionRetryCount: 2,
    logLevel: 'warn',
  });

  const size = await driver.getWindowSize();
  console.log(`[INFO] viewport=${size.width}x${size.height}`);
  await logForegroundActivity();

  const ga05ZoomOutTest = galleryPinch && galleryGa05ZoomOut && gesture === 'pinch-in';

  if (ga05ZoomOutTest) {
    console.log('[INFO] GA_05: default fit -> mobile pinchOpen (setup) -> W3C pinch-in (zoom out test)');
    await saveScreenshot(driver, 'default_fit');
    await performPinch(driver, true);
    await driver.pause(1500);
    await saveScreenshot(driver, 'before_pinch');
    await performPinch(driver, false);
    await driver.pause(1500);
    await saveScreenshot(driver, 'after_pinch');
  } else {
    await saveScreenshot(driver, 'before_pinch');

    if (gesture === 'pinch-out' || gesture === 'both') {
      await performPinch(driver, true);
      if (gesture === 'both') {
        await saveScreenshot(driver, 'after_pinch_out');
      }
    }
    if (gesture === 'pinch-in' || gesture === 'both') {
      if (gesture === 'both') await driver.pause(600);
      await performPinch(driver, false);
    }

    await saveScreenshot(driver, 'after_pinch');
  }
  console.log('[OK] W3C pinch completed');
  prepareDeviceForMaestro();
  await driver.deleteSession();
  process.exit(0);
} catch (err) {
  console.error(`ERROR: ${err.message}`);
  if (driver) {
    try {
      await driver.deleteSession();
    } catch {
      /* ignore */
    }
  }
  process.exit(2);
}
