// Single-screen OpenRouter verification for permission module screens.
// Env: SCREEN_BASENAME, SCREEN_LABEL (optional), SCREEN_PROFILE (gallery|permission_required|android_app_settings).

var KEY_NAMES = ["OpenRouterAPI", "OPENROUTER_API_KEY", "OPENROUTER_KEY"];

var screenBasename =
  typeof SCREEN_BASENAME !== "undefined" && SCREEN_BASENAME ? SCREEN_BASENAME : "";
var screenLabel =
  typeof SCREEN_LABEL !== "undefined" && SCREEN_LABEL ? SCREEN_LABEL : "Permission screen";
var screenProfile =
  typeof SCREEN_PROFILE !== "undefined" && SCREEN_PROFILE ? SCREEN_PROFILE : "gallery";

var PROMPTS = {
  gallery:
    'Answer ONLY JSON: {"screen_correct": true/false, "gallery_visible": true/false, "summary": "one sentence"}. ' +
    "screen_correct=true when Kodak Step Print MY GALLERY grid is visible with photo thumbnails. " +
    "gallery_visible=true when MY GALLERY header and gallery grid are clearly shown.",
  permission_required:
    'Answer ONLY JSON: {"screen_correct": true/false, "modal_visible": true/false, "summary": "one sentence"}. ' +
    "screen_correct=true when Kodak Step Print shows in-app Permission Required dialog with OK button. " +
    "modal_visible=true when Permission Required title or text that some permissions are needed is visible.",
  android_app_settings:
    'Answer ONLY JSON: {"screen_correct": true/false, "settings_visible": true/false, "summary": "one sentence"}. ' +
    "screen_correct=true when Android system App info / application settings screen for Kodak Step Print is shown. " +
    "settings_visible=true when Permissions, Force stop, Open, Uninstall, or App info controls are visible.",
};

var DEFAULT_VISION_FALLBACKS = [
  "qwen/qwen2.5-vl-32b-instruct:free",
  "qwen/qwen2.5-vl-72b-instruct:free",
  "google/gemma-3-4b-it:free",
  "mistralai/mistral-small-3.1-24b-instruct:free",
];

function maestroEnvValue(name) {
  if (name === "OpenRouterAPI" && typeof OpenRouterAPI !== "undefined" && OpenRouterAPI) return OpenRouterAPI;
  if (name === "OPENROUTER_API_KEY" && typeof OPENROUTER_API_KEY !== "undefined" && OPENROUTER_API_KEY) return OPENROUTER_API_KEY;
  if (name === "OPENROUTER_KEY" && typeof OPENROUTER_KEY !== "undefined" && OPENROUTER_KEY) return OPENROUTER_KEY;
  if (name === "OPENROUTER_MODEL_VISION" && typeof OPENROUTER_MODEL_VISION !== "undefined" && OPENROUTER_MODEL_VISION) return OPENROUTER_MODEL_VISION;
  if (name === "OPENROUTER_HTTP_REFERER" && typeof OPENROUTER_HTTP_REFERER !== "undefined" && OPENROUTER_HTTP_REFERER) return OPENROUTER_HTTP_REFERER;
  if (name === "OPENROUTER_APP_TITLE" && typeof OPENROUTER_APP_TITLE !== "undefined" && OPENROUTER_APP_TITLE) return OPENROUTER_APP_TITLE;
  if (name === "OPENROUTER_VISION_FALLBACKS" && typeof OPENROUTER_VISION_FALLBACKS !== "undefined" && OPENROUTER_VISION_FALLBACKS) return OPENROUTER_VISION_FALLBACKS;
  return "";
}

function parseDotEnvText(text) {
  var out = {};
  var lines = (text || "").split("\n");
  for (var i = 0; i < lines.length; i++) {
    var line = lines[i].replace(/\r$/, "").trim();
    if (!line || line.indexOf("#") === 0) continue;
    var eq = line.indexOf("=");
    if (eq < 0) continue;
    var k = line.substring(0, eq).trim();
    var v = line.substring(eq + 1).trim();
    if ((v.indexOf('"') === 0 && v.lastIndexOf('"') === v.length - 1) || (v.indexOf("'") === 0 && v.lastIndexOf("'") === v.length - 1)) {
      v = v.substring(1, v.length - 1);
    }
    out[k] = v;
  }
  return out;
}

function findRepoRoot() {
  try {
    var Files = Java.type("java.nio.file.Files");
    var Paths = Java.type("java.nio.file.Paths");
    var System = Java.type("java.lang.System");
    var dir = Paths.get(System.getProperty("user.dir"));
    for (var depth = 0; depth < 12; depth++) {
      if (dir === null) break;
      if (Files.exists(dir.resolve(".env.example")) || Files.exists(dir.resolve("ATP TestCase Flows"))) return dir;
      dir = dir.getParent();
    }
  } catch (e) {
    console.log("Repo root lookup failed: " + e);
  }
  return null;
}

function loadDotEnvMap() {
  try {
    var Files = Java.type("java.nio.file.Files");
    var repo = findRepoRoot();
    if (repo === null) return {};
    var envPath = repo.resolve(".env");
    if (!Files.exists(envPath)) return {};
    return parseDotEnvText(Files.readString(envPath));
  } catch (e) {
    return {};
  }
}

function resolveEnvValue(name) {
  var v = maestroEnvValue(name);
  if (v) return v;
  try {
    var System = Java.type("java.lang.System");
    var fromOs = System.getenv(name);
    if (fromOs !== null && fromOs !== "") return fromOs;
  } catch (e) {}
  var dot = loadDotEnvMap();
  if (dot[name]) return dot[name];
  return "";
}

function resolveApiKey() {
  for (var i = 0; i < KEY_NAMES.length; i++) {
    var value = resolveEnvValue(KEY_NAMES[i]);
    if (value) return value;
  }
  return "";
}

function parseJsonFromModel(raw) {
  var text = (raw || "").trim();
  if (text.indexOf("```") >= 0) {
    var parts = text.split("```");
    for (var i = 0; i < parts.length; i++) {
      var chunk = parts[i].trim();
      if (chunk.indexOf("json") === 0) chunk = chunk.substring(4).trim();
      if (chunk.indexOf("{") === 0) {
        text = chunk;
        break;
      }
    }
  }
  var start = text.indexOf("{");
  var end = text.lastIndexOf("}");
  if (start < 0 || end <= start) return null;
  return json(text.substring(start, end + 1));
}

function findScreenshotPath(name) {
  try {
    var Files = Java.type("java.nio.file.Files");
    var Paths = Java.type("java.nio.file.Paths");
    var System = Java.type("java.lang.System");
    var userHome = System.getProperty("user.home");
    var cwd = Paths.get(System.getProperty("user.dir"));
    var roots = [];
    var dir = cwd;
    for (var depth = 0; depth < 12; depth++) {
      if (dir === null) break;
      roots.push(dir);
      roots.push(dir.resolve(".maestro/screenshots"));
      roots.push(dir.resolve(".maestro/tests"));
      dir = dir.getParent();
    }
    var repo = findRepoRoot();
    if (repo !== null) {
      roots.push(repo);
      roots.push(repo.resolve("reports/permission"));
      roots.push(repo.resolve("reports/atp_permission"));
      roots.push(repo.resolve("reports/editing"));
      roots.push(repo.resolve("ATP TestCase Flows/permission"));
    }
    roots.push(Paths.get(userHome, ".maestro", "screenshots"));
    roots.push(Paths.get(userHome, ".maestro", "tests"));
    var latest = null;
    var latestTime = 0;
    for (var r = 0; r < roots.length; r++) {
      var root = roots[r];
      if (root === null || !Files.exists(root)) continue;
      var direct = root.resolve(name + ".png");
      if (Files.exists(direct) && Files.isRegularFile(direct)) return direct;
      if (!Files.isDirectory(root)) continue;
      try {
        var stream = Files.walk(root);
        var it = stream.iterator();
        while (it.hasNext()) {
          var fp = it.next();
          if (!Files.isRegularFile(fp)) continue;
          var fn = fp.getFileName().toString();
          if (fn.indexOf(name) < 0 || fn.indexOf(".png") < 0) continue;
          var t = Files.getLastModifiedTime(fp).toMillis();
          if (t > latestTime) {
            latestTime = t;
            latest = fp;
          }
        }
        stream.close();
      } catch (walkErr) {}
    }
    return latest;
  } catch (e) {}
  return null;
}

function resolveVerifyPort() {
  return resolveEnvValue("EDITING_VERIFY_PORT") || resolveEnvValue("PERMISSION_VERIFY_PORT") || "8767";
}

function resolveVisionModelChain() {
  var primary = resolveEnvValue("OPENROUTER_MODEL_VISION") || "meta-llama/llama-3.2-11b-vision-instruct:free";
  var chain = [primary];
  var fallbacksRaw = resolveEnvValue("OPENROUTER_VISION_FALLBACKS");
  if (fallbacksRaw && fallbacksRaw.toLowerCase() !== "none" && fallbacksRaw !== "0") {
    fallbacksRaw.split(",").forEach(function (m) {
      m = (m || "").trim();
      if (m && chain.indexOf(m) < 0) chain.push(m);
    });
  } else if (!fallbacksRaw) {
    DEFAULT_VISION_FALLBACKS.forEach(function (m) {
      if (chain.indexOf(m) < 0) chain.push(m);
    });
  }
  return chain;
}

function shouldTryNextVisionModel(status) {
  return status === 400 || status === 402 || status === 404 || status === 429 || (status >= 500 && status < 600);
}

function screenVerifyPassed(result) {
  if (screenProfile === "permission_required") {
    return result.screen_correct === true && (result.modal_visible === true || result.modal_visible === undefined);
  }
  if (screenProfile === "android_app_settings") {
    return result.screen_correct === true && (result.settings_visible === true || result.settings_visible === undefined);
  }
  return result.screen_correct === true && (result.gallery_visible === true || result.gallery_visible === undefined);
}

function applyScreenVerifyResult(result) {
  var ok = result.permission_screen_verified === true;
  output.permission_screen_verified = ok;
  output.permission_screen_summary = result.summary || "";
  console.log(screenLabel + " screen AI: " + JSON.stringify(result));
  if (!ok) {
    throw new Error(screenLabel + " screen AI verify failed: " + output.permission_screen_summary);
  }
}

function verifyViaLocalServer() {
  var port = resolveVerifyPort();
  var response = http.post("http://127.0.0.1:" + port + "/verify/permission_screen", {
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      screenshot_basename: screenBasename,
      screen_label: screenLabel,
      screen_profile: screenProfile,
    }),
  });
  if (response.status < 200 || response.status >= 300) {
    var errBody = response.body || "";
    try {
      var errJson = json(errBody);
      if (errJson.error) errBody = errJson.error;
    } catch (ignore) {}
    throw new Error("Permission verify server HTTP " + response.status + ": " + errBody.substring(0, 300));
  }
  applyScreenVerifyResult(json(response.body));
}

function verifyViaOpenRouterDirect() {
  var apiKey = resolveApiKey();
  if (!apiKey) throw new Error("OpenRouter API key not found in Maestro/OS env");

  var promptText = PROMPTS[screenProfile] || PROMPTS.gallery;
  var modelChain = resolveVisionModelChain();
  var referer = resolveEnvValue("OPENROUTER_HTTP_REFERER") || "http://localhost";
  var appTitle = resolveEnvValue("OPENROUTER_APP_TITLE") || "Kodak Step Print Maestro";
  var screenPath = findScreenshotPath(screenBasename);
  if (screenPath === null) throw new Error("Missing screenshot: " + screenBasename);

  var Files = Java.type("java.nio.file.Files");
  var Base64 = Java.type("java.util.Base64");
  var screenBytes = Files.readAllBytes(screenPath);
  var lastErr = "";

  for (var mi = 0; mi < modelChain.length; mi++) {
    var model = modelChain[mi];
    if (mi > 0) console.log("OpenRouter vision fallback: trying model=" + model);

    var requestBody = JSON.stringify({
      model: model,
      messages: [
        { role: "system", content: "You analyze ONE Kodak Step Print screenshot for: " + screenLabel + ". " + promptText },
        {
          role: "user",
          content: [
            { type: "text", text: screenLabel + ":" },
            { type: "image_url", image_url: { url: "data:image/png;base64," + Base64.getEncoder().encodeToString(screenBytes) } },
          ],
        },
      ],
      max_tokens: 300,
    });

    var response = http.post("https://openrouter.ai/api/v1/chat/completions", {
      headers: {
        Authorization: "Bearer " + apiKey,
        "Content-Type": "application/json",
        "HTTP-Referer": referer,
        "X-Title": appTitle,
      },
      body: requestBody,
    });

    if (response.status < 200 || response.status >= 300) {
      lastErr = "OpenRouter vision HTTP " + response.status + ": " + (response.body || "").substring(0, 300);
      if (shouldTryNextVisionModel(response.status)) {
        console.log("OpenRouter model " + model + " failed (" + response.status + "), trying next");
        continue;
      }
      throw new Error(lastErr);
    }

    var payload = json(response.body);
    var content = payload.choices[0].message.content;
    var result = parseJsonFromModel(content);
    if (result === null) {
      lastErr = "OpenRouter returned non-JSON: " + (content || "").substring(0, 300);
      console.log("OpenRouter model " + model + " returned non-JSON, trying next");
      continue;
    }

    applyScreenVerifyResult({
      permission_screen_verified: screenVerifyPassed(result),
      summary: result.summary || "",
    });
    return;
  }

  throw new Error(lastErr || "OpenRouter vision: all models failed");
}

if (!screenBasename) throw new Error("SCREEN_BASENAME is required");

try {
  verifyViaLocalServer();
} catch (serverErr) {
  console.log("Local permission verify server failed, trying direct OpenRouter: " + serverErr);
  try {
    verifyViaOpenRouterDirect();
  } catch (directErr) {
    throw new Error(
      "OpenRouter permission verify failed. Start editing verify server with EDITING_VERIFY_SOFT=1, " +
        "or set OPENROUTER_API_KEY. Server: " + serverErr + " | Direct: " + directErr
    );
  }
}
