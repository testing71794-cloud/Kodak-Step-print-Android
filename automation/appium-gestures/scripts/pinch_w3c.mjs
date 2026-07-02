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

async function resolvePinchCenter(driver, width, height) {
  try {
    await driver.activateApp(appPackage);
    await driver.pause(800);
    const shortId = galleryImageId.includes(':id/')
      ? galleryImageId.split(':id/')[1]
      : galleryImageId.replace(/^id[=/]/, '');
    const el = await driver.$(`id=${shortId}`);
    await el.waitForExist({ timeout: 8000 });
    const rect = await el.getElementRect();
    const cx = Math.round(rect.x + rect.width / 2);
    const cy = Math.round(rect.y + rect.height / 2);
    const span = Math.round(Math.min(rect.width, rect.height) * 0.22);
    console.log(`[INFO] Pinch center from ${galleryImageId} bounds [${rect.x},${rect.y}][${rect.x + rect.width},${rect.y + rect.height}] -> ${cx},${cy} span=${span}`);
    return { cx, cy, inner: Math.round(span * 0.35), outer: span };
  } catch (err) {
    console.log(`[INFO] Pinch center element lookup failed: ${err.message}`);
  }
  const cx = Math.round((width * centerXPercent) / 100);
  const cy = Math.round((height * centerYPercent) / 100);
  console.log(`[INFO] Pinch center fallback ${centerXPercent}%,${centerYPercent}% -> ${cx},${cy}`);
  return { cx, cy, inner, outer };
}

async function performPinch(driver, spread) {
  const { width, height } = await driver.getWindowSize();
  const center = await resolvePinchCenter(driver, width, height);
  const { cx, cy } = center;
  const innerRadius = center.inner ?? inner;
  const outerRadius = center.outer ?? outer;

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
  await driver.pause(durationMs + 200);
}

let driver;
try {
  await mkdir(screenshotDir, { recursive: true });
  console.log(`[INFO] Appium W3C pinch gesture=${gesture} device=${device} server=${appiumUrl}`);

  prepareDeviceForAppium();

  driver = await remote({
    hostname: new URL(appiumUrl).hostname,
    port: Number(new URL(appiumUrl).port || 4723),
    path: new URL(appiumUrl).pathname === '/' ? '/' : new URL(appiumUrl).pathname,
    capabilities: {
      platformName: 'Android',
      'appium:automationName': 'UiAutomator2',
      'appium:udid': device,
      'appium:appPackage': appPackage,
      'appium:noReset': true,
      'appium:dontStopAppOnReset': true,
      'appium:disableWindowAnimation': true,
      'appium:newCommandTimeout': 120,
      'appium:skipServerInstallation': false,
      'appium:settings[waitForIdleTimeout]': 0,
    },
    connectionRetryCount: 2,
    logLevel: 'warn',
  });

  const size = await driver.getWindowSize();
  console.log(`[INFO] viewport=${size.width}x${size.height}`);

  await saveScreenshot(driver, 'before_pinch');

  if (gesture === 'pinch-out' || gesture === 'both') {
    await performPinch(driver, true);
  }
  if (gesture === 'pinch-in' || gesture === 'both') {
    if (gesture === 'both') await driver.pause(400);
    await performPinch(driver, false);
  }

  await saveScreenshot(driver, 'after_pinch');
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
