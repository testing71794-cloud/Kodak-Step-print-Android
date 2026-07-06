// Generic OpenRouter before/after visual verification for editing module tests.
// Env: BEFORE_BASENAME, AFTER_BASENAME, VERIFY_LABEL, VERIFY_PROFILE (optional).

var KEY_NAMES = ["OpenRouterAPI", "OPENROUTER_API_KEY", "OPENROUTER_KEY"];

var beforeBasename =
  typeof BEFORE_BASENAME !== "undefined" && BEFORE_BASENAME ? BEFORE_BASENAME : "";
var afterBasename =
  typeof AFTER_BASENAME !== "undefined" && AFTER_BASENAME ? AFTER_BASENAME : "";
var verifyLabel =
  typeof VERIFY_LABEL !== "undefined" && VERIFY_LABEL ? VERIFY_LABEL : "Edit change";
var verifyProfile =
  typeof VERIFY_PROFILE !== "undefined" && VERIFY_PROFILE ? VERIFY_PROFILE : "generic";

var PROFILES = {
  filter: {
    passKeys: ["screen_correct", "change_applied"],
    prompt:
      'Answer ONLY JSON: {"screen_correct": true/false, "change_applied": true/false, "summary": "one sentence"}. ' +
      "Both images must show Kodak Edit Photo with the photo in the white frame. " +
      "change_applied=true only when AFTER shows a visible filter/color-grade change vs BEFORE.",
  },
  frame: {
    passKeys: ["change_applied", "looks_different"],
    prompt:
      'Answer ONLY JSON: {"change_applied": true/false, "looks_different": true/false, "summary": "one sentence"}. ' +
      "change_applied=true when AFTER shows a decorative frame/border around the photo that BEFORE lacks.",
  },
  sticker: {
    passKeys: ["change_applied", "looks_different"],
    prompt:
      'Answer ONLY JSON: {"change_applied": true/false, "looks_different": true/false, "summary": "one sentence"}. ' +
      "change_applied=true when AFTER shows a visible sticker/overlay on the photo.",
  },
  crop: {
    passKeys: ["change_applied", "looks_different"],
    prompt:
      'Answer ONLY JSON: {"change_applied": true/false, "looks_different": true/false, "summary": "one sentence"}. ' +
      "change_applied=true when AFTER shows zoom/crop/reframe vs BEFORE (photo scale or visible area changed).",
  },
  rotate: {
    passKeys: ["change_applied"],
    prompt:
      'Answer ONLY JSON: {"change_applied": true/false, "summary": "one sentence"}. ' +
      "change_applied=true only when AFTER photo content is rotated vs BEFORE inside the frame.",
  },
  flip: {
    passKeys: ["change_applied"],
    prompt:
      'Answer ONLY JSON: {"change_applied": true/false, "summary": "one sentence"}. ' +
      "change_applied=true when AFTER is horizontally or vertically mirrored vs BEFORE.",
  },
  adjust: {
    passKeys: ["change_applied", "looks_different"],
    prompt:
      'Answer ONLY JSON: {"change_applied": true/false, "looks_different": true/false, "summary": "one sentence"}. ' +
      "change_applied=true when exposure/color/contrast/saturation visibly changed vs BEFORE.",
  },
  brightness: {
    passKeys: ["change_applied", "looks_different"],
    prompt:
      'Answer ONLY JSON: {"change_applied": true/false, "brighter_in_after": true/false, "looks_different": true/false, "summary": "one sentence"}. ' +
      "change_applied=true when AFTER photo preview is noticeably brighter or darker than BEFORE inside the white frame. " +
      "brighter_in_after=true when AFTER is clearly lighter/brighter than BEFORE. Ignore slider UI chrome.",
  },
  text: {
    passKeys: ["change_applied", "looks_different"],
    prompt:
      'Answer ONLY JSON: {"change_applied": true/false, "looks_different": true/false, "summary": "one sentence"}. ' +
      "change_applied=true when AFTER shows user text overlay on the photo.",
  },
  draw: {
    passKeys: ["change_applied", "looks_different"],
    prompt:
      'Answer ONLY JSON: {"change_applied": true/false, "looks_different": true/false, "summary": "one sentence"}. ' +
      "change_applied=true when AFTER shows paint/doodle strokes on the photo.",
  },
  blur: {
    passKeys: ["change_applied", "looks_different"],
    prompt:
      'Answer ONLY JSON: {"change_applied": true/false, "looks_different": true/false, "summary": "one sentence"}. ' +
      "change_applied=true when AFTER shows blur/focus effect vs BEFORE.",
  },
  save: {
    passKeys: ["saved_to_gallery", "looks_different"],
    prompt:
      'Answer ONLY JSON: {"saved_to_gallery": true/false, "looks_different": true/false, "summary": "one sentence"}. ' +
      "saved_to_gallery=true when AFTER shows MY GALLERY grid with the edited photo visible.",
  },
  generic: {
    passKeys: ["change_applied", "looks_different"],
    prompt:
      'Answer ONLY JSON: {"change_applied": true/false, "looks_different": true/false, "summary": "one sentence"}. ' +
      "change_applied=true when AFTER clearly differs from BEFORE in photo content inside the editor or gallery.",
  },
};

function maestroEnvValue(name) {
  if (name === "OpenRouterAPI" && typeof OpenRouterAPI !== "undefined" && OpenRouterAPI) {
    return OpenRouterAPI;
  }
  if (name === "OPENROUTER_API_KEY" && typeof OPENROUTER_API_KEY !== "undefined" && OPENROUTER_API_KEY) {
    return OPENROUTER_API_KEY;
  }
  if (name === "OPENROUTER_KEY" && typeof OPENROUTER_KEY !== "undefined" && OPENROUTER_KEY) {
    return OPENROUTER_KEY;
  }
  if (name === "OPENROUTER_MODEL_VISION" && typeof OPENROUTER_MODEL_VISION !== "undefined" && OPENROUTER_MODEL_VISION) {
    return OPENROUTER_MODEL_VISION;
  }
  if (name === "OPENROUTER_HTTP_REFERER" && typeof OPENROUTER_HTTP_REFERER !== "undefined" && OPENROUTER_HTTP_REFERER) {
    return OPENROUTER_HTTP_REFERER;
  }
  if (name === "OPENROUTER_APP_TITLE" && typeof OPENROUTER_APP_TITLE !== "undefined" && OPENROUTER_APP_TITLE) {
    return OPENROUTER_APP_TITLE;
  }
  return "";
}

function parseDotEnvText(text) {
  var out = {};
  var lines = (text || "").split("\n");
  for (var i = 0; i < lines.length; i++) {
    var line = lines[i].replace(/\r$/, "").trim();
    if (!line || line.indexOf("#") === 0) {
      continue;
    }
    var eq = line.indexOf("=");
    if (eq < 0) {
      continue;
    }
    var k = line.substring(0, eq).trim();
    var v = line.substring(eq + 1).trim();
    if (
      (v.indexOf('"') === 0 && v.lastIndexOf('"') === v.length - 1) ||
      (v.indexOf("'") === 0 && v.lastIndexOf("'") === v.length - 1)
    ) {
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
      if (dir === null) {
        break;
      }
      if (Files.exists(dir.resolve(".env.example")) || Files.exists(dir.resolve("ATP TestCase Flows"))) {
        return dir;
      }
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
    if (repo === null) {
      return {};
    }
    var envPath = repo.resolve(".env");
    if (!Files.exists(envPath)) {
      return {};
    }
    return parseDotEnvText(Files.readString(envPath));
  } catch (e) {
    console.log(".env read failed: " + e);
    return {};
  }
}

function resolveEnvValue(name) {
  var v = maestroEnvValue(name);
  if (v) {
    return v;
  }
  try {
    var System = Java.type("java.lang.System");
    var fromOs = System.getenv(name);
    if (fromOs !== null && fromOs !== "") {
      return fromOs;
    }
  } catch (e) {
    console.log("OS env lookup failed for " + name + ": " + e);
  }
  var dot = loadDotEnvMap();
  if (dot[name]) {
    return dot[name];
  }
  return "";
}

function resolveApiKey() {
  for (var i = 0; i < KEY_NAMES.length; i++) {
    var value = resolveEnvValue(KEY_NAMES[i]);
    if (value) {
      return value;
    }
  }
  return "";
}

function parseJsonFromModel(raw) {
  var text = (raw || "").trim();
  if (text.indexOf("```") >= 0) {
    var parts = text.split("```");
    for (var i = 0; i < parts.length; i++) {
      var chunk = parts[i].trim();
      if (chunk.indexOf("json") === 0) {
        chunk = chunk.substring(4).trim();
      }
      if (chunk.indexOf("{") === 0) {
        text = chunk;
        break;
      }
    }
  }
  var start = text.indexOf("{");
  var end = text.lastIndexOf("}");
  if (start < 0 || end <= start) {
    return null;
  }
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
      if (dir === null) {
        break;
      }
      roots.push(dir);
      roots.push(dir.resolve(".maestro/screenshots"));
      roots.push(dir.resolve(".maestro/tests"));
      dir = dir.getParent();
    }
    var repo = findRepoRoot();
    if (repo !== null) {
      roots.push(repo);
      roots.push(repo.resolve(".maestro/screenshots"));
      roots.push(repo.resolve(".maestro/tests"));
      roots.push(repo.resolve("reports/editing"));
      roots.push(repo.resolve("ATP TestCase Flows/editing"));
      roots.push(repo.resolve("ATP TestCase Flows/editing/.maestro/screenshots"));
    }
    roots.push(Paths.get(userHome, ".maestro", "screenshots"));
    roots.push(Paths.get(userHome, ".maestro", "tests"));
    var latest = null;
    var latestTime = 0;
    for (var r = 0; r < roots.length; r++) {
      var root = roots[r];
      if (root === null || !Files.exists(root)) {
        continue;
      }
      var direct = root.resolve(name + ".png");
      if (Files.exists(direct) && Files.isRegularFile(direct)) {
        return direct;
      }
      if (!Files.isDirectory(root)) {
        continue;
      }
      try {
        var stream = Files.walk(root);
        var it = stream.iterator();
        while (it.hasNext()) {
          var fp = it.next();
          if (!Files.isRegularFile(fp)) {
            continue;
          }
          var fn = fp.getFileName().toString();
          if (fn.indexOf(name) < 0 || fn.indexOf(".png") < 0) {
            continue;
          }
          var t = Files.getLastModifiedTime(fp).toMillis();
          if (t > latestTime) {
            latestTime = t;
            latest = fp;
          }
        }
        stream.close();
      } catch (walkErr) {
        console.log("Screenshot walk failed for " + root + ": " + walkErr);
      }
    }
    return latest;
  } catch (e) {
    console.log("Screenshot lookup failed: " + e);
  }
  return null;
}

function profileConfig(name) {
  if (PROFILES[name]) {
    return PROFILES[name];
  }
  return PROFILES.generic;
}

function passesProfile(result, cfg) {
  for (var i = 0; i < cfg.passKeys.length; i++) {
    if (result[cfg.passKeys[i]] !== true) {
      return false;
    }
  }
  return true;
}

function applyVerifyResult(result, model, cfg) {
  var ok;
  if (result.visual_pair_verified === true || result.visual_pair_verified === false) {
    ok = result.visual_pair_verified === true;
  } else {
    ok = passesProfile(result, cfg);
  }
  output.visual_pair_verified = ok;
  output.filter_pair_verified = ok;
  output.visual_pair_summary = result.summary || "";
  output.visual_pair_model = result.model_used || model || "";
  output.filter_pair_summary = output.visual_pair_summary;
  output.filter_pair_model = output.visual_pair_model;
  console.log(verifyLabel + " [" + verifyProfile + "] AI verify: " + JSON.stringify(result));
  if (result.skipped) {
    throw new Error(result.summary || (verifyLabel + " AI verify skipped"));
  }
  if (!ok) {
    throw new Error(verifyLabel + " AI verify failed: " + output.visual_pair_summary);
  }
}

function verifyViaLocalServer() {
  var response = http.post("http://127.0.0.1:8767/verify/ed_pair", {
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      before_basename: beforeBasename,
      after_basename: afterBasename,
      verify_label: verifyLabel,
      verify_profile: verifyProfile,
    }),
  });
  if (response.status < 200 || response.status >= 300) {
    var errBody = response.body || "";
    try {
      var errJson = json(errBody);
      if (errJson.error) {
        errBody = errJson.error;
      }
    } catch (ignore) {}
    throw new Error("Editing verify server HTTP " + response.status + ": " + errBody.substring(0, 300));
  }
  applyVerifyResult(json(response.body), "", cfg);
}

function verifyViaOpenRouterDirect() {
  var apiKey = resolveApiKey();
  if (!apiKey) {
    throw new Error("OpenRouter API key not found in Maestro/OS env");
  }

  var model = resolveEnvValue("OPENROUTER_MODEL_VISION") || "meta-llama/llama-3.2-11b-vision-instruct:free";
  var referer = resolveEnvValue("OPENROUTER_HTTP_REFERER") || "http://localhost";
  var appTitle = resolveEnvValue("OPENROUTER_APP_TITLE") || "Kodak Step Print Maestro";

  var beforePath = findScreenshotPath(beforeBasename);
  var afterPath = findScreenshotPath(afterBasename);
  if (beforePath === null || afterPath === null) {
    throw new Error("Missing screenshots: before=" + beforeBasename + " after=" + afterBasename);
  }

  var Files = Java.type("java.nio.file.Files");
  var Base64 = Java.type("java.util.Base64");
  var Arrays = Java.type("java.util.Arrays");
  var beforeBytes = Files.readAllBytes(beforePath);
  var afterBytes = Files.readAllBytes(afterPath);
  if (Arrays.equals(beforeBytes, afterBytes)) {
    throw new Error(verifyLabel + " before/after screenshots are identical");
  }

  var prompt =
    "You analyze TWO Kodak Step Print mobile screenshots for: " + verifyLabel + ". " + cfg.prompt;

  var requestBody = JSON.stringify({
    model: model,
    messages: [
      { role: "system", content: prompt },
      {
        role: "user",
        content: [
          { type: "text", text: "BEFORE (" + verifyLabel + "):" },
          {
            type: "image_url",
            image_url: { url: "data:image/png;base64," + Base64.getEncoder().encodeToString(beforeBytes) },
          },
          { type: "text", text: "AFTER (" + verifyLabel + "):" },
          {
            type: "image_url",
            image_url: { url: "data:image/png;base64," + Base64.getEncoder().encodeToString(afterBytes) },
          },
        ],
      },
    ],
    max_tokens: 400,
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
    throw new Error(
      "OpenRouter vision HTTP " + response.status + ": " + (response.body || "").substring(0, 300)
    );
  }

  var payload = json(response.body);
  var content = payload.choices[0].message.content;
  var result = parseJsonFromModel(content);
  if (result === null) {
    throw new Error("OpenRouter returned non-JSON: " + (content || "").substring(0, 300));
  }
  result.model_used = model;
  applyVerifyResult(result, model, cfg);
}

if (!beforeBasename || !afterBasename) {
  throw new Error("BEFORE_BASENAME and AFTER_BASENAME are required");
}

var cfg = profileConfig(verifyProfile);

try {
  verifyViaOpenRouterDirect();
} catch (directErr) {
  console.log("Direct OpenRouter pair verify failed, trying local editing server: " + directErr);
  try {
    verifyViaLocalServer();
  } catch (serverErr) {
    throw new Error(
      "OpenRouter pair verify failed. Start ATP TestCase Flows/editing/scripts/start_editing_studio_verify.bat " +
        "(reads repo .env), or set OPENROUTER_API_KEY in Windows env + GraalJS host access. " +
        "Direct: " +
        directErr +
        " | Server: " +
        serverErr
    );
  }
}
