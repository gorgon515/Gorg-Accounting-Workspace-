'use strict';

// Pre-downloads the local Whisper model so push-to-talk works fully offline
// afterward. Run: npm run model
//
// Without this, the model downloads automatically on your first use of the
// Talk button (one time), then runs locally from cache.

(async () => {
  let transformers;
  try {
    transformers = await import('@huggingface/transformers');
  } catch {
    console.error('@huggingface/transformers is not installed. Run `npm install` first.');
    process.exit(1);
  }
  const { pipeline } = transformers;
  const model = process.env.WHISPER_MODEL || 'Xenova/whisper-tiny.en';
  console.log(`Downloading local speech model: ${model} …`);
  await pipeline('automatic-speech-recognition', model);
  console.log('Done. The model is cached locally and now works offline.');
})().catch((e) => {
  console.error('Failed:', e.message);
  process.exit(1);
});
