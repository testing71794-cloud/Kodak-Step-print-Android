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
const centerYPercent = 42;
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

async function performPinch(driver, spread) {
  const { width, height } = await driver.getWindowSize();
  const cx = Math.round((width * centerXPercent) / 100);
  const cy = Math.round((height * centerYPercent) / 100);

  let leftStart, leftEnd, rightStart, rightEnd;
  if (spread) {
    leftStart = cx - inner;
    leftEnd = cx - outer;
    rightStart = cx + inner;
    rightEnd = cx + outer;
    console.log(`[INFO] pinch-out L ${leftStart},${cy}->${leftEnd},${cy}  R ${rightStart},${cy}->${rightEnd},${cy}`);
  } else {
    leftStart = cx - outer;
    leftEnd = cx - inner;
    rightStart = cx + outer;
    rightEnd = cx + inner;
    console.log(`[INFO] pinch-in L ${leftStart},${cy}->${leftEnd},${cy}  R ${rightStart},${cy}->${rightEnd},${cy}`);
  }

  await driver.performActions([
    fingerSequence('finger1', leftStart, cy, leftEnd, cy),
    fingerSequence('finger2', rightStart, cy, rightEnd, cy),
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
