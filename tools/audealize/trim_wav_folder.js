const fs = require("fs");
const path = require("path");
const { buildTrimmedWavBuffer, getWavDurationSeconds } = require("./wav_utils");

function listWavFiles(dir) {
  return fs
    .readdirSync(dir)
    .filter((entry) => entry.toLowerCase().endsWith(".wav"))
    .sort((left, right) => left.localeCompare(right));
}

function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function parseCliArgs() {
  const [, , targetDirArg, maxSecondsArg] = process.argv;

  if (!targetDirArg || !maxSecondsArg) {
    throw new Error("Usage: node trim_wav_folder.js <targetDir> <maxSeconds>");
  }

  const targetDir = path.resolve(targetDirArg);
  const maxSeconds = Number(maxSecondsArg);

  if (!Number.isFinite(maxSeconds) || maxSeconds <= 0) {
    throw new Error("maxSeconds must be a positive number.");
  }

  return { targetDir, maxSeconds };
}

function main() {
  const { targetDir, maxSeconds } = parseCliArgs();

  if (!fs.existsSync(targetDir)) {
    throw new Error(`Target directory does not exist: ${targetDir}`);
  }

  const files = listWavFiles(targetDir);
  if (files.length === 0) {
    console.log(`No WAV files found in ${targetDir}`);
    return;
  }

  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const targetBaseName = path.basename(targetDir);
  const parentDir = path.dirname(targetDir);

  const backupDir = path.join(parentDir, `${targetBaseName}__backup_before_${maxSeconds}s_trim_${timestamp}`);
  const tempDir = path.join(parentDir, `.${targetBaseName}__trim_tmp_${timestamp}`);

  ensureDir(backupDir);
  ensureDir(tempDir);

  const workItems = [];

  for (const fileName of files) {
    const sourcePath = path.join(targetDir, fileName);
    const originalBuffer = fs.readFileSync(sourcePath);
    const originalDuration = getWavDurationSeconds(originalBuffer);
    const trimmedBuffer = buildTrimmedWavBuffer(originalBuffer, maxSeconds);

    workItems.push({
      fileName,
      sourcePath,
      backupPath: path.join(backupDir, fileName),
      tempPath: path.join(tempDir, fileName),
      originalBuffer,
      trimmedBuffer,
      originalDuration
    });
  }

  // Write backups and trimmed temp files first, before replacing originals.
  for (const item of workItems) {
    fs.writeFileSync(item.backupPath, item.originalBuffer);
    fs.writeFileSync(item.tempPath, item.trimmedBuffer);
  }

  for (const item of workItems) {
    const verified = fs.readFileSync(item.tempPath);
    const verifiedDuration = getWavDurationSeconds(verified);

    if (verifiedDuration > maxSeconds + 1e-6) {
      throw new Error(`Trimmed file still exceeds ${maxSeconds}s: ${item.fileName}`);
    }

    fs.renameSync(item.tempPath, item.sourcePath);
    console.log(`${item.fileName}: ${item.originalDuration.toFixed(3)}s -> ${verifiedDuration.toFixed(3)}s`);
  }

  fs.rmSync(tempDir, { recursive: true, force: true });

  console.log(`Trimmed ${workItems.length} WAV files to the first ${maxSeconds} seconds.`);
  console.log(`Backups saved in: ${backupDir}`);
}

main();
