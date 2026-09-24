const RIFF_HEADER_SIZE = 12;

function parseWavBuffer(buffer) {
  if (!Buffer.isBuffer(buffer)) {
    throw new TypeError("Expected a Buffer when parsing WAV data.");
  }

  if (buffer.length < RIFF_HEADER_SIZE) {
    throw new Error("WAV file is too small to contain a valid RIFF header.");
  }

  const riffId = buffer.toString("ascii", 0, 4);
  const waveId = buffer.toString("ascii", 8, 12);

  if (riffId !== "RIFF" || waveId !== "WAVE") {
    throw new Error("File is not a RIFF/WAVE WAV file.");
  }

  const chunks = [];
  let fmtChunk = null;
  let dataChunk = null;
  let offset = RIFF_HEADER_SIZE;

  while (offset + 8 <= buffer.length) {
    const id = buffer.toString("ascii", offset, offset + 4);
    const size = buffer.readUInt32LE(offset + 4);
    const dataStart = offset + 8;
    const dataEnd = dataStart + size;

    if (dataEnd > buffer.length) {
      throw new Error(`Chunk ${id} extends past the end of the WAV file.`);
    }

    const padByteCount = size % 2;
    const nextOffset = dataEnd + padByteCount;

    if (nextOffset > buffer.length) {
      throw new Error(`Chunk ${id} padding extends past the end of the WAV file.`);
    }

    const chunk = {
      id,
      size,
      start: offset,
      dataStart,
      dataEnd,
      nextOffset
    };

    if (id === "fmt ") {
      if (size < 16) {
        throw new Error("fmt chunk is too small to describe a valid WAV format.");
      }

      const audioFormat = buffer.readUInt16LE(dataStart);
      const numChannels = buffer.readUInt16LE(dataStart + 2);
      const sampleRate = buffer.readUInt32LE(dataStart + 4);
      const byteRate = buffer.readUInt32LE(dataStart + 8);
      const blockAlign = buffer.readUInt16LE(dataStart + 12);
      const bitsPerSample = buffer.readUInt16LE(dataStart + 14);

      fmtChunk = {
        audioFormat,
        numChannels,
        sampleRate,
        byteRate,
        blockAlign,
        bitsPerSample
      };
    } else if (id === "data") {
      dataChunk = chunk;
    }

    chunks.push(chunk);
    offset = nextOffset;
  }

  if (offset !== buffer.length) {
    throw new Error("WAV file contains trailing bytes that are not part of a chunk.");
  }

  if (!fmtChunk) {
    throw new Error("WAV file does not contain a fmt chunk.");
  }

  if (!dataChunk) {
    throw new Error("WAV file does not contain a data chunk.");
  }

  return {
    buffer,
    chunks,
    fmtChunk,
    dataChunk
  };
}

function buildTrimmedWavBuffer(buffer, maxSeconds) {
  const parsed = parseWavBuffer(buffer);
  const { fmtChunk, dataChunk, chunks } = parsed;

  if (!Number.isFinite(maxSeconds) || maxSeconds <= 0) {
    throw new Error("maxSeconds must be a positive finite number.");
  }

  const derivedBlockAlign = (fmtChunk.numChannels * fmtChunk.bitsPerSample) / 8;
  const blockAlign = fmtChunk.blockAlign || derivedBlockAlign;

  if (!Number.isInteger(blockAlign) || blockAlign <= 0) {
    throw new Error("WAV block alignment is invalid.");
  }

  if (fmtChunk.blockAlign && fmtChunk.blockAlign !== derivedBlockAlign) {
    throw new Error("WAV fmt chunk reports inconsistent block alignment.");
  }

  if (fmtChunk.byteRate !== fmtChunk.sampleRate * blockAlign) {
    throw new Error("WAV fmt chunk reports inconsistent byte rate.");
  }

  const availableFrames = Math.floor(dataChunk.size / blockAlign);
  const targetFrames = Math.min(availableFrames, Math.floor(fmtChunk.sampleRate * maxSeconds));
  const targetBytes = targetFrames * blockAlign;

  if (targetBytes >= dataChunk.size) {
    return buffer;
  }

  const outputParts = [];

  for (const chunk of chunks) {
    if (chunk.id !== "data") {
      outputParts.push(buffer.subarray(chunk.start, chunk.nextOffset));
      continue;
    }

    const dataSlice = buffer.subarray(chunk.dataStart, chunk.dataStart + targetBytes);
    const dataHeader = Buffer.alloc(8);
    dataHeader.write("data", 0, 4, "ascii");
    dataHeader.writeUInt32LE(dataSlice.length, 4);
    outputParts.push(dataHeader, dataSlice);

    if (dataSlice.length % 2 === 1) {
      outputParts.push(Buffer.from([0]));
    }
  }

  const payloadSize = outputParts.reduce((total, part) => total + part.length, 0);
  const riffHeader = Buffer.alloc(RIFF_HEADER_SIZE);
  riffHeader.write("RIFF", 0, 4, "ascii");
  riffHeader.writeUInt32LE(payloadSize + 4, 4);
  riffHeader.write("WAVE", 8, 4, "ascii");

  return Buffer.concat([riffHeader, ...outputParts]);
}

function getWavDurationSeconds(buffer) {
  const parsed = parseWavBuffer(buffer);
  const { fmtChunk, dataChunk } = parsed;
  const blockAlign = fmtChunk.blockAlign || ((fmtChunk.numChannels * fmtChunk.bitsPerSample) / 8);

  if (!Number.isInteger(blockAlign) || blockAlign <= 0) {
    throw new Error("WAV block alignment is invalid.");
  }

  return dataChunk.size / blockAlign / fmtChunk.sampleRate;
}

module.exports = {
  buildTrimmedWavBuffer,
  getWavDurationSeconds,
  parseWavBuffer
};