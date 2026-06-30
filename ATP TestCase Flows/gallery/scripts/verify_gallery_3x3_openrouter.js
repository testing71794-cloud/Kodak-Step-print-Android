// OpenRouter vision verify for GA_02 3x3 gallery grid (replaces Maestro Cloud assertWithAI).
// Key resolution (same order as intelligent_platform/config.py):
//   1) Maestro flow/runScript env
//   2) OS process env (Jenkins withCredentials → OPENROUTER_API_KEY)
//   3) repo .env (copy from .env.example)
// Screenshot read also needs:
//   MAESTRO_CLI_DANGEROUS_GRAALJS_ALLOW_HOST_ACCESS=1
//   MAESTRO_CLI_DANGEROUS_GRAALJS_ALLOW_HOST_CLASS_LOOKUP=1

var KEY_NAMES = ["OpenRouterAPI", "OPENROUTER_API_KEY", "OPENROUTER_KEY"];

var screenshotBasename =
  typeof SCREENSHOT_BASENAME !== "undefined" && SCREENSHOT_BASENAME
    ? SCREENSHOT_BASENAME
    : "GA_02_3x3_grid_verify";

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
    for (var depth = 0; depth < 10; depth++) {
      if (dir === null) {
        break;
      }
      if (Files.exists(dir.resolve("Jenkinsfile")) || Files.exists(dir.resolve(".env.example"))) {
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
    var text = Files.readString(envPath);
    return parseDotEnvText(text);
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
  var i;
  for (i = 0; i < KEY_NAMES.length; i++) {
    var v = resolveEnvValue(KEY_NAMES[i]);
    if (v) {
      return v;
    }
  }
  return "";
}

var apiKey = resolveApiKey();

if (!apiKey) {
  throw new Error(
    "OpenRouter API key not found. Set OpenRouterAPI or OPENROUTER_API_KEY in OS env, repo .env, or Maestro Env."
  );
}

var model = resolveEnvValue("OPENROUTER_MODEL_VISION") || "openrouter/free";
var referer = resolveEnvValue("OPENROUTER_HTTP_REFERER") || "http://localhost";
var appTitle = resolveEnvValue("OPENROUTER_APP_TITLE") || "Kodak Step Print Maestro";
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
    var depth;
    for (depth = 0; depth < 12; depth++) {
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
      roots.push(repo.resolve("reports/gallery"));
      roots.push(repo.resolve("reports/gallery/maestro-debug"));
      roots.push(repo.resolve("ATP TestCase Flows/gallery"));
      roots.push(repo.resolve("ATP TestCase Flows/gallery/.maestro/screenshots"));
    }
    roots.push(Paths.get(userHome, ".maestro", "screenshots"));
    roots.push(Paths.get(userHome, ".maestro", "tests"));
    if (typeof MAESTRO_TEST_OUTPUT !== "undefined" && MAESTRO_TEST_OUTPUT) {
      roots.push(Paths.get(MAESTRO_TEST_OUTPUT));
    }
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
    console.log("Screenshot lookup via Java failed: " + e);
  }
  return null;
}

function applyVerifyResult(result) {
  output.grid_3x3_verified = result.grid_3x3 === true;
  output.grid_3x3_summary = result.summary || "";
  output.grid_3x3_model = result.model_used || model;
  console.log("OpenRouter 3x3 verify: " + JSON.stringify(result));
  if (result.skipped) {
    throw new Error(result.summary || "OpenRouter verify skipped");
  }
  if (!output.grid_3x3_verified) {
    throw new Error("3x3 grid not detected: " + output.grid_3x3_summary);
  }
}

function verifyViaLocalServer() {
  var response = http.post("http://127.0.0.1:8765/verify/ga02_3x3", {
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      screenshot_basename: screenshotBasename,
      use_adb: true,
    }),
  });
  if (response.status < 200 || response.status >= 300) {
    throw new Error(
      "Verify server HTTP " +
        response.status +
        ": " +
        (response.body || "").substring(0, 300)
    );
  }
  applyVerifyResult(json(response.body));
}

function verifyViaOpenRouterBase64(b64) {
  var prompt =
    'Answer ONLY with JSON: {"grid_3x3": true/false, "summary": "one sentence"}. ' +
    "grid_3x3 is true when My Gallery shows photo thumbnails in a 3-column by 3-row grid (nine cells), not a single-column list or denser grid.";

  var requestBody = JSON.stringify({
    model: model,
    messages: [
      { role: "system", content: prompt },
      {
        role: "user",
        content: [
          {
            type: "text",
            text: "Verify this My Gallery screenshot shows a 3x3 grid layout.",
          },
          {
            type: "image_url",
            image_url: { url: "data:image/png;base64," + b64 },
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
  applyVerifyResult(result);
}

function captureViaAdb() {
  try {
    var ProcessBuilder = Java.type("java.lang.ProcessBuilder");
    var Files = Java.type("java.nio.file.Files");
    var Paths = Java.type("java.nio.file.Paths");
    var System = Java.type("java.lang.System");
    var serial = resolveEnvValue("ANDROID_SERIAL") || resolveEnvValue("MAESTRO_DEVICE") || resolveEnvValue("DEVICE_ID");
    var cmd = [];
    var adb = resolveEnvValue("ADB_EXE");
    if (adb) {
      cmd.push(adb);
    } else {
      cmd.push("adb");
    }
    if (serial) {
      cmd.push("-s", serial);
    }
    cmd.push("exec-out", "screencap", "-p");
    var pb = new ProcessBuilder(cmd);
    pb.redirectErrorStream(true);
    var proc = pb.start();
    var bytes = proc.getInputStream().readAllBytes();
    proc.waitFor();
    if (proc.exitValue() !== 0 || !bytes || bytes.length < 1000) {
      throw new Error("adb screencap failed (exit " + proc.exitValue() + ")");
    }
    var repo = findRepoRoot();
    if (repo !== null) {
      var outDir = repo.resolve("reports/gallery/maestro-debug");
      Files.createDirectories(outDir);
      var livePath = outDir.resolve(screenshotBasename + "_adb_live.png");
      Files.write(livePath, bytes);
      console.log("Saved adb live capture: " + livePath);
    }
    var Base64 = Java.type("java.util.Base64");
    verifyViaOpenRouterBase64(Base64.getEncoder().encodeToString(bytes));
    return true;
  } catch (e) {
    console.log("adb capture failed: " + e);
    return false;
  }
}

var screenshotPath = findScreenshotPath(screenshotBasename);
if (screenshotPath !== null) {
  try {
    var Files = Java.type("java.nio.file.Files");
    var Base64 = Java.type("java.util.Base64");
    var bytes = Files.readAllBytes(screenshotPath);
    verifyViaOpenRouterBase64(Base64.getEncoder().encodeToString(bytes));
  } catch (readErr) {
    console.log("Direct screenshot read failed, trying adb then verify server: " + readErr);
    if (!captureViaAdb()) {
      verifyViaLocalServer();
    }
  }
} else {
  if (!captureViaAdb()) {
    try {
      verifyViaLocalServer();
    } catch (serverErr) {
      throw new Error(
        "Screenshot " +
          screenshotBasename +
          ".png not found. Start scripts/start_maestro_verify_server.bat (uses adb fallback), or set MAESTRO_CLI_DANGEROUS_GRAALJS_ALLOW_HOST_ACCESS=1 for in-flow adb capture. (" +
          serverErr +
          ")"
      );
    }
  }
}
