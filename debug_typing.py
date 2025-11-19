#!/usr/bin/env python3
"""Debug script to test typing functionality with generated audio."""

import sys
import time
import logging
from pathlib import Path

# Add scribe to path
sys.path.insert(0, str(Path(__file__).parent))

from scribe.test_utils import generate_test_audio, save_audio_file
from scribe.transcribe import Transcriber
from scribe.output import OutputHandler
from scribe.config import Config

# Set up verbose logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    logger.info("="*60)
    logger.info("SCRIBE TYPING DEBUG TEST")
    logger.info("="*60)

    # Step 1: Generate test audio
    logger.info("\n[1/5] Generating test audio...")
    audio_data = generate_test_audio(duration=3.0, frequency=440)
    test_file = "/tmp/scribe_test.wav"
    save_audio_file(audio_data, test_file)
    logger.info(f"Test audio saved to: {test_file}")
    logger.info(f"Audio shape: {audio_data.shape}, dtype: {audio_data.dtype}")

    # Step 2: Initialize components
    logger.info("\n[2/5] Initializing transcriber...")
    cfg = Config()
    transcriber = Transcriber(
        model_name=cfg["model"]["size"],
        device=cfg["model"]["device"],
        compute_type=cfg["model"]["compute_type"],
    )

    # Step 3: Test transcription
    logger.info("\n[3/5] Testing transcription...")
    try:
        text = transcriber.transcribe(audio_data, sample_rate=16000)
        logger.info(f"Transcription result: '{text}'")
        if not text or not text.strip():
            logger.warning("Transcription produced empty text - this is expected for pure tone audio")
            text = "This is a test message from Scribe"
            logger.info(f"Using fallback text: '{text}'")
    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        text = "Test message"

    # Step 4: Test typing with countdown
    logger.info("\n[4/5] Testing typing functionality...")
    logger.info("⚠️  FOCUS A TEXT EDITOR, TERMINAL, OR TEXT INPUT NOW!")
    for i in range(5, 0, -1):
        print(f"  {i}...", flush=True)
        time.sleep(1)

    logger.info("\n[5/5] Attempting to type text...")
    output_handler = OutputHandler(mode="type", typing_delay=0.0)

    logger.info("Calling output_handler.output()...")
    success = output_handler.output(text)

    logger.info("\n" + "="*60)
    if success:
        logger.info("✓ TYPING TEST COMPLETED SUCCESSFULLY")
        logger.info("Did you see the text appear in your focused application?")
    else:
        logger.error("✗ TYPING TEST FAILED")
        logger.error("Check the logs above for details")
    logger.info("="*60)

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
