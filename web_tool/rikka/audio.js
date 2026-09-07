export async function recordMicProbe(durationMs = 900) {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("browser microphone API unavailable");
  }
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const context = new AudioContext({ sampleRate: 16000 });
  const source = context.createMediaStreamSource(stream);
  const processor = context.createScriptProcessor(4096, 1, 1);
  const chunks = [];
  processor.onaudioprocess = (event) => {
    chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
  };
  source.connect(processor);
  processor.connect(context.destination);
  await new Promise((resolve) => window.setTimeout(resolve, durationMs));
  processor.disconnect();
  source.disconnect();
  stream.getTracks().forEach((track) => track.stop());
  const sampleRate = context.sampleRate;
  await context.close();
  return encodeWav(chunks, sampleRate);
}

export async function startMicStream({ onChunk, onLevel }) {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("browser microphone API unavailable");
  }
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const context = new AudioContext();
  const source = context.createMediaStreamSource(stream);
  const processor = context.createScriptProcessor(4096, 1, 1);
  let stopped = false;
  processor.onaudioprocess = (event) => {
    if (stopped) return;
    const input = event.inputBuffer.getChannelData(0);
    let energy = 0;
    for (let index = 0; index < input.length; index += 1) {
      energy += input[index] * input[index];
    }
    const level = Math.sqrt(energy / Math.max(1, input.length));
    if (onLevel) onLevel(level);
    if (onChunk) {
      onChunk({
        audio: Array.from(input),
        sample_rate: event.inputBuffer.sampleRate || context.sampleRate || 16000,
        level,
      });
    }
  };
  source.connect(processor);
  processor.connect(context.destination);
  return {
    sampleRate: context.sampleRate,
    stop() {
      stopped = true;
      processor.disconnect();
      source.disconnect();
      stream.getTracks().forEach((track) => track.stop());
      context.close().catch(() => {});
    },
  };
}

function encodeWav(chunks, sampleRate) {
  const length = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const pcm = new Int16Array(length);
  let offset = 0;
  chunks.forEach((chunk) => {
    chunk.forEach((sample) => {
      const clipped = Math.max(-1, Math.min(1, sample));
      pcm[offset] = clipped < 0 ? clipped * 0x8000 : clipped * 0x7fff;
      offset += 1;
    });
  });
  const buffer = new ArrayBuffer(44 + pcm.byteLength);
  const view = new DataView(buffer);
  writeString(view, 0, "RIFF");
  view.setUint32(4, 36 + pcm.byteLength, true);
  writeString(view, 8, "WAVE");
  writeString(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(view, 36, "data");
  view.setUint32(40, pcm.byteLength, true);
  new Int16Array(buffer, 44).set(pcm);
  return new Blob([buffer], { type: "audio/wav" });
}

function writeString(view, offset, value) {
  for (let index = 0; index < value.length; index += 1) {
    view.setUint8(offset + index, value.charCodeAt(index));
  }
}
