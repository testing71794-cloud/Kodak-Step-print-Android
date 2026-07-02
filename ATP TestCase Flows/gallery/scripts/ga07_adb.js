// GA_07 adb via local verify server (no GraalJS Java host access required).
// Jenkins gallery stage starts scripts/maestro_openrouter_verify_server.py on :8765.

var action =
  typeof GA07_ACTION !== "undefined" && GA07_ACTION ? String(GA07_ACTION).toLowerCase() : "baseline";

var response = http.post("http://127.0.0.1:8765/verify/ga07/" + action, {
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({}),
});

if (response.status < 200 || response.status >= 300) {
  throw new Error(
    "GA_07 verify server HTTP " +
      response.status +
      ": " +
      (response.body || "").substring(0, 300) +
      " — start scripts/maestro_openrouter_verify_server.py or run gallery via Jenkins"
  );
}

var result = json(response.body);

if (action === "baseline") {
  output.dcim_count_before = result.dcim_count_before;
  console.log("[GA_07] DCIM/Camera baseline count=" + result.dcim_count_before);
} else if (action === "launch") {
  output.native_camera_launched = result.native_camera_launched === true;
  console.log("[GA_07] Native camera launched");
} else if (action === "verify") {
  output.dcim_count_before = result.dcim_count_before;
  output.dcim_count_after = result.dcim_count_after;
  output.new_photo_in_gallery = result.new_photo_in_gallery === true;
  console.log(
    "[GA_07] DCIM/Camera before=" +
      result.dcim_count_before +
      " after=" +
      result.dcim_count_after +
      " new_photo_in_gallery=" +
      output.new_photo_in_gallery
  );
  if (!output.new_photo_in_gallery) {
    throw new Error(result.error || "Gallery refresh verify failed");
  }
} else {
  throw new Error("Unknown GA07_ACTION: " + action);
}
