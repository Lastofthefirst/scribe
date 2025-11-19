// Speech transcription using whisper.cpp via whisper-rs.

use anyhow::{Context, Result};
use log::info;
use std::path::PathBuf;
use std::time::Instant;
use whisper_rs::{FullParams, SamplingStrategy, WhisperContext, WhisperContextParameters};

/// Transcriber for audio using Whisper.
pub struct Transcriber {
    pub model_size: String,
    pub device: String,
    pub keep_loaded: bool,
    model: Option<WhisperContext>,
    model_path: Option<PathBuf>,
}

impl Transcriber {
    /// Create a new Transcriber.
    ///
    /// # Arguments
    ///
    /// * `model_size` - Whisper model size (tiny, tiny.en, base, base.en, small, etc.)
    /// * `device` - Device to use ("cpu" or "cuda")
    /// * `keep_loaded` - Keep model loaded in memory for faster subsequent runs
    pub fn new(
        model_size: String,
        device: String,
        keep_loaded: bool,
    ) -> Result<Self> {
        info!("Transcriber initialized: model={}, device={}", model_size, device);

        let mut transcriber = Self {
            model_size,
            device,
            keep_loaded,
            model: None,
            model_path: None,
        };

        // Preload model if requested
        if keep_loaded {
            transcriber.load_model()?;
        }

        Ok(transcriber)
    }

    /// Get the model path for a given model size.
    ///
    /// Models should be in ~/.cache/scribe/models/
    fn get_model_path(&self) -> Result<PathBuf> {
        let home = dirs::home_dir().context("Could not find home directory")?;
        let model_dir = home.join(".cache/scribe/models");

        // Create models directory if it doesn't exist
        std::fs::create_dir_all(&model_dir)
            .with_context(|| format!("Failed to create model directory: {:?}", model_dir))?;

        // Model filename: ggml-{model_size}.bin
        let model_filename = format!("ggml-{}.bin", self.model_size);
        let model_path = model_dir.join(model_filename);

        Ok(model_path)
    }

    /// Load the Whisper model.
    fn load_model(&mut self) -> Result<&WhisperContext> {
        if self.model.is_none() {
            info!("Loading Whisper model: {}", self.model_size);
            let start_time = Instant::now();

            let model_path = self.get_model_path()?;

            if !model_path.exists() {
                anyhow::bail!(
                    "Model file not found: {:?}\n\
                     Please download the model first:\n\
                     1. Visit: https://huggingface.co/ggerganov/whisper.cpp\n\
                     2. Download ggml-{}.bin\n\
                     3. Place it in: {:?}",
                    model_path,
                    self.model_size,
                    model_path.parent().unwrap()
                );
            }

            // Load model with whisper-rs
            let ctx_params = WhisperContextParameters::default();
            let ctx = WhisperContext::new_with_params(&model_path.to_string_lossy(), ctx_params)
                .context("Failed to load Whisper model")?;

            let load_time = start_time.elapsed().as_secs_f64();
            info!("Model loaded in {:.2}s", load_time);

            self.model = Some(ctx);
            self.model_path = Some(model_path);
        }

        Ok(self.model.as_ref().unwrap())
    }

    /// Transcribe audio to text.
    ///
    /// # Arguments
    ///
    /// * `audio` - Audio data as i16 samples
    /// * `sample_rate` - Audio sample rate in Hz
    /// * `language` - Language code (e.g., "en")
    pub fn transcribe(
        &mut self,
        audio: &[i16],
        sample_rate: u32,
        language: Option<&str>,
    ) -> Result<String> {
        let start_time = Instant::now();

        // Load model if not already loaded
        let ctx = self.load_model()?;

        // Convert i16 samples to f32 samples (whisper.cpp expects f32)
        let audio_f32: Vec<f32> = audio.iter().map(|&x| x as f32 / 32768.0).collect();

        // Create transcription parameters
        let mut params = FullParams::new(SamplingStrategy::Greedy { best_of: 1 });

        // Set language
        if let Some(lang) = language {
            params.set_language(Some(lang));
        }

        // Disable printing to stdout
        params.set_print_special(false);
        params.set_print_progress(false);
        params.set_print_realtime(false);
        params.set_print_timestamps(false);

        // Create a new state for this transcription
        let mut state = ctx.create_state().context("Failed to create whisper state")?;

        // Run transcription
        state
            .full(params, &audio_f32)
            .context("Failed to run transcription")?;

        // Get number of segments
        let num_segments = state
            .full_n_segments()
            .context("Failed to get number of segments")?;

        // Collect all text segments
        let mut result = String::new();
        for i in 0..num_segments {
            let segment = state
                .full_get_segment_text(i)
                .context("Failed to get segment text")?;
            result.push_str(&segment);
        }

        // Trim whitespace
        let result = result.trim().to_string();

        let transcribe_time = start_time.elapsed().as_secs_f64();
        info!(
            "Transcription complete: {:.2}s for {:.2}s audio",
            transcribe_time,
            audio.len() as f64 / sample_rate as f64
        );

        Ok(result)
    }

    /// Download a Whisper model.
    ///
    /// This is a placeholder - user needs to manually download for now.
    pub fn download_model(&self) -> Result<()> {
        let model_path = self.get_model_path()?;

        if model_path.exists() {
            info!("Model already exists: {:?}", model_path);
            return Ok(());
        }

        // For now, just provide instructions
        println!("To download the model:");
        println!("1. Visit: https://huggingface.co/ggerganov/whisper.cpp");
        println!("2. Download: ggml-{}.bin", self.model_size);
        println!("3. Place it in: {:?}", model_path.parent().unwrap());
        println!("\nAlternatively, use wget:");
        println!("  mkdir -p {:?}", model_path.parent().unwrap());
        println!(
            "  wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-{}.bin -O {:?}",
            self.model_size, model_path
        );

        Ok(())
    }
}
