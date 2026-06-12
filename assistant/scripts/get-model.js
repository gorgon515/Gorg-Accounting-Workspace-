'use strict';

// Pre-downloads the local models so everything works fully offline afterward:
//   • the Whisper speech model (push-to-talk), and
//   • the built-in chat model (the zero-setup brain).
// Run: npm run model
//
// Without this, each model downloads automatically the first time it's used
// (one time), then runs locally from cache.

(async () => {
  let transformers;
  try {
    transformers = await import('@huggingface/transformers');
  } catch {
    console.error('@huggingface/transformers is not installed. Run `npm install` first.');
    process.exit(1);
  }
  const { pipeline } = transformers;

  const whisper = process.env.WHISPER_MODEL || 'Xenova/whisper-tiny.en';
  console.log(`Downloading local speech model: ${whisper} …`);
  try {
    await pipeline('automatic-speech-recognition', whisper);
    console.log('Speech model cached — push-to-talk now works offline.');
  } catch (e) {
    console.error(`Speech model failed: ${e.message}`);
  }

  const chat = process.env.EMBEDDED_MODEL || 'onnx-community/Qwen2.5-0.5B-Instruct';
  const dtype = process.env.EMBEDDED_DTYPE || 'q4';
  console.log(`Downloading built-in brain model: ${chat} (${dtype}) …`);
  try {
    await pipeline('text-generation', chat, { dtype });
    console.log('Brain model cached — the built-in brain now works offline.');
  } catch (e) {
    console.error(`Brain model failed: ${e.message}`);
  }
})().catch((e) => {
  console.error('Failed:', e.message);
  process.exit(1);
});
