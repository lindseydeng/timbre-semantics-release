const fs = require("fs");
const path = require("path");
const { parseArgs } = require("node:util");
const { buildTrimmedWavBuffer } = require("./wav_utils");

const { values } = parseArgs({ options: {
  input: { type: "string" }, output: { type: "string" },
  effect: { type: "string", default: "eq" },
  config: { type: "string", default: path.resolve(__dirname, "../../configs/experiment2.json") },
  "trim-seconds": { type: "string", default: "11" },
  help: { type: "boolean", default: false }
}});
if (values.help) {
  console.log("Usage: node audealize_batch.js --input DIR --output DIR --effect eq|reverb [--trim-seconds 11]");
  process.exit(0);
}
if (!values.input || !values.output || !["eq", "reverb"].includes(values.effect)) {
  throw new Error("Provide --input, --output and --effect eq|reverb. Use --help for usage.");
}
const trimSeconds = Number(values["trim-seconds"]);
if (!Number.isFinite(trimSeconds) || trimSeconds <= 0) throw new Error("Invalid trim duration");
const design = JSON.parse(fs.readFileSync(values.config, "utf8"));
const BASE_URL = "https://audealize.appspot.com";
const INPUT_DIR = path.resolve(values.input);
const OUTPUT_BASE_DIR = path.resolve(values.output);
const EFFECT_TYPE = values.effect === "eq" ? "EQ" : "Reverb";
const DESCRIPTORS = design.descriptors[values.effect];
const AMOUNTS = design.scales;
const { chromium } = require("playwright");

function getInputWavFiles(inputDir) {
  if (!fs.existsSync(inputDir)) {
    throw new Error(`Input directory does not exist: ${inputDir}`);
  }

  const files = fs
    .readdirSync(inputDir)
    .filter((name) => /\.wav$/i.test(name))
    .map((name) => path.join(inputDir, name));

  if (files.length === 0) {
    throw new Error(`No .wav files found in input directory: ${inputDir}`);
  }

  return files;
}

function getEffectOutputSuffix(effectType) {
  const normalized = String(effectType).toLowerCase();
  if (normalized === "eq") {
    return "eq";
  }

  if (normalized === "reverb") {
    return "rvb";
  }

  throw new Error(`Unsupported effect type: ${effectType}`);
}

function getOutputDirForInput(inputFile, outputBaseDir, effectType) {
  const inputBaseName = path.parse(inputFile).name;
  const effectSuffix = getEffectOutputSuffix(effectType);
  return path.join(outputBaseDir, effectSuffix === "eq" ? "EQ" : "RVB", `${safeName(inputBaseName)}_${effectSuffix}`);
}

function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function safeName(s) {
  return String(s).replace(/[^a-zA-Z0-9._-]+/g, "_");
}

function saveMetadata(outputDir, inputFile, effectType, descriptors, amounts) {
  const metadata = {
    input_file: inputFile,
    effect_type: effectType,
    descriptors,
    amounts,
    expected_num_outputs: descriptors.length * amounts.length,
    generated_at: new Date().toISOString()
  };

  fs.writeFileSync(
    path.join(outputDir, "metadata.json"),
    JSON.stringify(metadata, null, 2)
  );
}

async function clickByText(page, text) {
  const locator = page.getByText(text, { exact: true });
  await locator.waitFor({ state: "visible", timeout: 15000 });

  try {
    await locator.click({ timeout: 15000 });
  } catch (err) {
    await dismissBlockingModal(page);
    await locator.click({ timeout: 15000 });
  }
}

async function dismissBlockingModal(page) {
  const modal = page.locator("#info.modal.in, .modal.in, #info[aria-hidden='false']").first();
  if (!(await modal.isVisible().catch(() => false))) {
    return;
  }

  const closeSelectors = [
    ".modal.in button.close",
    ".modal.in [data-dismiss='modal']",
    "#info button.close",
    "#info [data-dismiss='modal']"
  ];

  for (const selector of closeSelectors) {
    const button = page.locator(selector).first();
    if (await button.isVisible().catch(() => false)) {
      await button.click().catch(() => {});
      break;
    }
  }

  await page.keyboard.press("Escape").catch(() => {});
  await modal.waitFor({ state: "hidden", timeout: 5000 }).catch(() => {});
}

async function importAudio(page, inputFile) {
  const fileInputs = page.locator('input[type="file"]');
  const count = await fileInputs.count();

  if (count === 0) {
    throw new Error("No file input found for importing audio.");
  }

  let uploaded = false;
  for (let i = 0; i < count; i++) {
    const input = fileInputs.nth(i);
    try {
      await input.setInputFiles(inputFile);
      uploaded = true;
      break;
    } catch (err) {
      // try next file input
    }
  }

  if (!uploaded) {
    throw new Error("Failed to upload audio file.");
  }

  await page.waitForTimeout(3000);
}

async function selectEffect(page, effectType) {
  const normalized = String(effectType).toLowerCase();
  if (normalized === "eq") {
    await clickByText(page, "EQ");
  } else if (normalized === "reverb") {
    await clickByText(page, "Reverb");
  } else {
    throw new Error(`Unsupported effect type: ${effectType}`);
  }

  const effectTitle = normalized === "eq" ? "EQ" : "Reverb";
  const turnOn = page.getByText(`Turn ${effectTitle} On`, { exact: true });
  if (await turnOn.isVisible().catch(() => false)) {
    await turnOn.click().catch(() => {});
    await page.waitForTimeout(500);
  }
}

async function searchDescriptor(page, descriptor) {
  const textInputs = page.locator('input[type="text"]');
  const count = await textInputs.count();

  if (count === 0) {
    throw new Error("No text input found for descriptor search.");
  }

  let found = false;
  for (let i = 0; i < count; i++) {
    const input = textInputs.nth(i);
    if (await input.isVisible().catch(() => false)) {
      await input.fill("");
      await input.fill(descriptor);
      await input.press("Enter").catch(() => {});
      found = true;
      break;
    }
  }

  if (!found) {
    throw new Error(`Could not find usable search box for descriptor: ${descriptor}`);
  }

  await page.waitForTimeout(1500);
}

async function findAmountSlider(page) {
  const sliders = page.locator('input[type="range"]');
  const count = await sliders.count();

  if (count === 0) {
    throw new Error("No range slider found on page.");
  }

  for (let i = 0; i < count; i++) {
    const slider = sliders.nth(i);
    if (await slider.isVisible().catch(() => false)) {
      return slider;
    }
  }

  throw new Error("No visible range slider found.");
}

async function setSliderValue(sliderLocator, normalizedValue) {
  await sliderLocator.evaluate((el, v) => {
    const min = el.min === "" ? 0 : parseFloat(el.min);
    const max = el.max === "" ? 1 : parseFloat(el.max);
    const actual = min + v * (max - min);

    el.value = String(actual);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }, normalizedValue);
}

async function clickFirstVisibleByText(page, textMatchers) {
  for (const matcher of textMatchers) {
    const locator = page.getByText(matcher, { exact: true });
    if (await locator.first().isVisible().catch(() => false)) {
      await locator.first().click().catch(() => {});
      return true;
    }
  }

  return false;
}

async function waitForDownload(page, timeout) {
  return Promise.race([
    page.waitForEvent("download", { timeout }),
    page.context().waitForEvent("download", { timeout })
  ]);
}

async function exportFromInPageRenderer(page, outputPath) {
  const result = await page.evaluate(async () => {
    if (!window.music || typeof window.music.download !== "function") {
      throw new Error("Audealize music.download() is unavailable on the page.");
    }

    if (!window.webkitOfflineAudioContext && window.OfflineAudioContext) {
      window.webkitOfflineAudioContext = window.OfflineAudioContext;
    }

    if (!window.Recorder || typeof window.Recorder.forceDownload !== "function") {
      throw new Error("Audealize Recorder.forceDownload() is unavailable on the page.");
    }

    const patchAudioParamMethod = (methodName) => {
      const original = AudioParam.prototype[methodName];
      if (typeof original !== "function") {
        return () => {};
      }

      AudioParam.prototype[methodName] = function patchedAudioParamMethod(value, ...rest) {
        const safeValue = Number.isFinite(value) ? value : 0;
        return original.call(this, safeValue, ...rest);
      };

      return () => {
        AudioParam.prototype[methodName] = original;
      };
    };

    const restoreSetValueAtTime = patchAudioParamMethod("setValueAtTime");
    const restoreLinearRampToValueAtTime = patchAudioParamMethod("linearRampToValueAtTime");
    const restoreExponentialRampToValueAtTime = patchAudioParamMethod("exponentialRampToValueAtTime");
    const restoreSetTargetAtTime = patchAudioParamMethod("setTargetAtTime");

    const originalGraphCurve = window.graphCurve;
    const originalShowCurve = window.showCurve;
    window.graphCurve = () => {};
    window.showCurve = () => {};

    // Reverb-only sessions can leave some EQ params as NaN in Audealize internals,
    // and their exporter crashes when it reconstructs nodes with non-finite values.
    const sanitizeFiniteNumbers = (value, fallback = 0) => {
      if (typeof value === "number") {
        return Number.isFinite(value) ? value : fallback;
      }

      if (Array.isArray(value)) {
        return value.map((item) => sanitizeFiniteNumbers(item, fallback));
      }

      if (value && typeof value === "object") {
        for (const key of Object.keys(value)) {
          value[key] = sanitizeFiniteNumbers(value[key], fallback);
        }
      }

      return value;
    };

    if (window.eq && window.eq.param) {
      sanitizeFiniteNumbers(window.eq.param, 0);
    }

    return await new Promise((resolve, reject) => {
      const originalForceDownload = window.Recorder.forceDownload;
      let settled = false;

      const cleanup = () => {
        window.Recorder.forceDownload = originalForceDownload;
        restoreSetValueAtTime();
        restoreLinearRampToValueAtTime();
        restoreExponentialRampToValueAtTime();
        restoreSetTargetAtTime();
        window.graphCurve = originalGraphCurve;
        window.showCurve = originalShowCurve;
      };

      const timeoutId = setTimeout(() => {
        if (settled) {
          return;
        }

        settled = true;
        cleanup();
        reject(new Error("Timed out waiting for in-page WAV rendering."));
      }, 180000);

      window.Recorder.forceDownload = async (blob, filename) => {
        if (settled) {
          return;
        }

        try {
          const arrayBuffer = await blob.arrayBuffer();
          const bytes = new Uint8Array(arrayBuffer);
          let binary = "";
          const chunkSize = 0x8000;

          for (let i = 0; i < bytes.length; i += chunkSize) {
            const chunk = bytes.subarray(i, i + chunkSize);
            binary += String.fromCharCode(...chunk);
          }

          settled = true;
          clearTimeout(timeoutId);
          cleanup();
          resolve({
            filename,
            base64: btoa(binary)
          });
        } catch (err) {
          settled = true;
          clearTimeout(timeoutId);
          cleanup();
          reject(err);
        }
      };

      try {
        window.music.download();
      } catch (err) {
        if (!settled) {
          settled = true;
          clearTimeout(timeoutId);
          cleanup();
          reject(err);
        }
      }
    });
  });

  fs.writeFileSync(outputPath, Buffer.from(result.base64, "base64"));
}

async function exportCurrentSettings(page, outputPath) {
  const timeoutMs = 180000;
  const exportOptionLabels = [
    "Current Settings",
    "Current settings",
    "Current setting"
  ];
  const downloadLabels = [
    "Download",
    "Download Audio",
    "Download audio",
    "Export audio"
  ];

  try {
    await exportFromInPageRenderer(page, outputPath);
    return;
  } catch (err) {
    console.warn(`In-page render export failed, falling back to UI export: ${err.message}`);
  }

  await clickByText(page, "Export audio");

  await clickFirstVisibleByText(page, exportOptionLabels);

  let download;
  try {
    download = await waitForDownload(page, timeoutMs);
  } catch (err) {
    // Some UI paths require one extra explicit click on a visible download action.
    await clickFirstVisibleByText(page, downloadLabels);
    download = await waitForDownload(page, timeoutMs);
  }

  await download.saveAs(outputPath);

}

async function renderOneAmount(page, inputFile, outputDir, descriptor, amount) {
  const inputBaseName = path.parse(inputFile).name;
  const outName = `${safeName(inputBaseName)}_${safeName(EFFECT_TYPE)}_${safeName(descriptor)}_${amount.toFixed(1)}.wav`;
  const outPath = path.join(outputDir, outName);

  console.log(`Rendering: descriptor=${descriptor}, amount=${amount.toFixed(1)}`);

  await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2500);

  await importAudio(page, inputFile);
  await selectEffect(page, EFFECT_TYPE);
  await searchDescriptor(page, descriptor);

  const slider = await findAmountSlider(page);
  await setSliderValue(slider, amount);
  await page.waitForTimeout(1500);

  if (fs.existsSync(outPath)) throw new Error(`Output already exists: ${outPath}`);
  await exportCurrentSettings(page, outPath);
  const rendered = fs.readFileSync(outPath);
  const trimmed = buildTrimmedWavBuffer(rendered, trimSeconds);
  if (trimmed !== rendered) fs.writeFileSync(outPath, trimmed);
  await page.waitForTimeout(2000);

  console.log(`Saved: ${outPath}`);
}

(async () => {
  const inputFiles = getInputWavFiles(INPUT_DIR);

  const browser = await chromium.launch({
    headless: false
  });

  const context = await browser.newContext({
    acceptDownloads: true
  });

  const page = await context.newPage();

  try {
    for (const inputFile of inputFiles) {
      const outputDir = getOutputDirForInput(inputFile, OUTPUT_BASE_DIR, EFFECT_TYPE);
      ensureDir(outputDir);
      saveMetadata(outputDir, inputFile, EFFECT_TYPE, DESCRIPTORS, AMOUNTS);

      console.log(`Starting batch for input: ${inputFile}`);

      for (const descriptor of DESCRIPTORS) {
        for (const amount of AMOUNTS) {
          await renderOneAmount(page, inputFile, outputDir, descriptor, amount);
        }
      }
    }

    console.log("All renders completed.");
  } catch (err) {
    throw err;
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});