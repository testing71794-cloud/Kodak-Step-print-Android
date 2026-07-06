// Single-screen OpenRouter verification for printing module screens.
// Env: SCREEN_BASENAME, SCREEN_LABEL (optional), SCREEN_PROFILE (print_preview|print_success).

var KEY_NAMES = ["OpenRouterAPI", "OPENROUTER_API_KEY", "OPENROUTER_KEY"];

var screenBasename =
  typeof SCREEN_BASENAME !== "undefined" && SCREEN_BASENAME ? SCREEN_BASENAME : "";
var screenLabel =
  typeof SCREEN_LABEL !== "undefined" && SCREEN_LABEL ? SCREEN_LABEL : "Print screen";
var screenProfile =
  typeof SCREEN_PROFILE !== "undefined" && SCREEN_PROFILE ? SCREEN_PROFILE : "print_preview";

var PROMPTS = {
  print_preview:
    'Answer ONLY JSON: {"screen_correct": true/false, "print_ui_visible": true/false, "summary": "one sentence"}. ' +
    "screen_correct=true when this is Kodak Step Print preview before printing with photo preview visible. " +
    "print_ui_visible=true when Print button, copies control, or printer connection UI is visible.",
  print_success:
    'Answer ONLY JSON: {"screen_correct": true/false, "success_visible": true/false, "summary": "one sentence"}. ' +
    "screen_correct=true when print completed successfully (Print Successful message or confirmation). " +
    "success_visible=true when success text, checkmark, or completion dialog is clearly visible.",
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
      roots.push(repo.resolve("reports/printing"));
      roots.push(repo.resolve("reports/editing"));
      roots.push(repo.resolve("ATP TestCase Flows/printing"));
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
  var port = resolveEnvValue("EDITING_VERIFY_PORT") || resolveEnvValue("PRINTING_VERIFY_PORT") || "8767";
  return port;
}

function profilePass(result) {
  if (screenProfile === "print_success") {
    return result.screen_correct === true && result.success_visible === true;
  }
  return result.screen_correct === true && result.print_ui_visible === true;
}

function applyScreenVerifyResult(result) {
  var ok = result.print_screen_verified === true;
  output.print_screen_verified = ok;
  output.print_screen_summary = result.summary || "";
  console.log(screenLabel + " screen AI: " + JSON.stringify(result));
  if (!ok) {
    throw new Error(screenLabel + " screen AI verify failed: " + output.print_screen_summary);
  }
}

function verifyViaLocalServer() {
  var port = resolveVerifyPort();
  var response = http.post("http://127.0.0.1:" + port + "/verify/print_screen", {
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
      if (errJson.error) {
        errBody = errJson.error;
      }
    } catch (ignore) {}
    throw new Error("Print verify server HTTP " + response.status + ": " + errBody.substring(0, 300));
  }
  applyScreenVerifyResult(json(response.body));
}

function verifyViaOpenRouterDirect() {
  var apiKey = resolveApiKey();
  if (!apiKey) {
    throw new Error("OpenRouter API key not found in Maestro/OS env");
  }

  var promptText = PROMPTS[screenProfile] || PROMPTS.print_preview;
  var model = resolveEnvValue("OPENROUTER_MODEL_VISION") || "meta-llama/llama-3.2-11b-vision-instruct:free";
  var referer = resolveEnvValue("OPENROUTER_HTTP_REFERER") || "http://localhost";
  var appTitle = resolveEnvValue("OPENROUTER_APP_TITLE") || "Kodak Step Print Maestro";

  var screenPath = findScreenshotPath(screenBasename);
  if (screenPath === null) {
    throw new Error("Missing screenshot: " + screenBasename);
  }

  var Files = Java.type("java.nio.file.Files");
  var Base64 = Java.type("java.util.Base64");
  var screenBytes = Files.readAllBytes(screenPath);

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
    throw new Error("OpenRouter vision HTTP " + response.status + ": " + (response.body || "").substring(0, 300));
  }

  var payload = json(response.body);
  var content = payload.choices[0].message.content;
  var result = parseJsonFromModel(content);
  if (result === null) {
    throw new Error("OpenRouter returned non-JSON: " + (content || "").substring(0, 300));
  }

  var ok = profilePass(result);
  applyScreenVerifyResult({
    print_screen_verified: ok,
    summary: result.summary || "",
  });
}

if (!screenBasename) {
  throw new Error("SCREEN_BASENAME is required");
}

try {
  verifyViaOpenRouterDirect();
} catch (directErr) {
  console.log("Direct OpenRouter verify failed, trying local verify server: " + directErr);
  try {
    verifyViaLocalServer();
  } catch (serverErr) {
    throw new Error(
      "OpenRouter print verify failed. Start ATP TestCase Flows/editing/scripts/start_editing_studio_verify.bat " +
        "(reads repo .env), or set OPENROUTER_API_KEY in Windows env + GraalJS host access. " +
        "Direct: " +
        directErr +
        " | Server: " +
        serverErr
    );
  }
}
