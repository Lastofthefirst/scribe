// Audio recording and voice activity detection for Scribe.

use anyhow::{Context, Result};
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use cpal::{Device, SampleFormat, Stream, StreamConfig};
use log::{debug, info, warn};
use std::collections::VecDeque;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use webrtc_vad::{SampleRate, Vad};

/// Audio recorder with voice activity detection.
pub struct AudioRecorder {
    pub sample_rate: u32,
    pub channels: u16,
    pub vad_aggressiveness: i32,
    pub silence_duration: f64,
    pub min_audio_duration: f64,
    pub frame_duration_ms: u32,
    pub frame_size: usize,
    vad: Vad,
}

impl AudioRecorder {
    /// Create a new AudioRecorder.
    ///
    /// # Arguments
    ///
    /// * `sample_rate` - Audio sample rate in Hz (must be 8000, 16000, 32000, or 48000 for VAD)
    /// * `channels` - Number of audio channels (1 for mono)
    /// * `vad_aggressiveness` - VAD aggressiveness level (0-3, higher = more aggressive)
    /// * `silence_duration` - Duration of silence in seconds before stopping recording
    /// * `min_audio_duration` - Minimum audio duration in seconds to avoid accidental triggers
    pub fn new(
        sample_rate: u32,
        channels: u16,
        vad_aggressiveness: i32,
        silence_duration: f64,
        min_audio_duration: f64,
    ) -> Result<Self> {
        // Validate sample rate for VAD
        let vad_sample_rate = match sample_rate {
            8000 => SampleRate::Rate8kHz,
            16000 => SampleRate::Rate16kHz,
            32000 => SampleRate::Rate32kHz,
            48000 => SampleRate::Rate48kHz,
            _ => anyhow::bail!("Sample rate must be 8000, 16000, 32000, or 48000 for VAD, got {}", sample_rate),
        };

        // Create VAD
        let mut vad = Vad::new();
        vad.set_sample_rate(vad_sample_rate);
        vad.set_mode(vad_aggressiveness.try_into().context("VAD aggressiveness must be 0-3")?);

        // Frame duration for VAD (30ms - must be 10, 20, or 30ms)
        let frame_duration_ms = 30;
        let frame_size = (sample_rate * frame_duration_ms / 1000) as usize;

        info!(
            "AudioRecorder initialized: {}Hz, {}ch, VAD={}",
            sample_rate, channels, vad_aggressiveness
        );

        Ok(Self {
            sample_rate,
            channels,
            vad_aggressiveness,
            silence_duration,
            min_audio_duration,
            frame_duration_ms,
            frame_size,
            vad,
        })
    }

    /// Check if audio frame contains speech using VAD.
    pub fn is_speech(&mut self, audio_frame: &[i16]) -> bool {
        match self.vad.is_voice_segment(audio_frame) {
            Ok(is_speech) => is_speech,
            Err(e) => {
                debug!("VAD error: {}", e);
                false
            }
        }
    }

    /// Get the default input device.
    pub fn get_default_input_device(&self) -> Result<Device> {
        let host = cpal::default_host();
        host.default_input_device()
            .context("No default input device found")
    }

    /// Record audio with voice activity detection.
    ///
    /// Returns a vector of i16 audio samples, or None if recording was too short.
    pub fn record_with_vad(&mut self) -> Result<Option<Vec<i16>>> {
        info!("Starting audio recording with VAD...");

        let device = self.get_default_input_device()?;
        let config = StreamConfig {
            channels: self.channels,
            sample_rate: cpal::SampleRate(self.sample_rate),
            buffer_size: cpal::BufferSize::Fixed(self.frame_size as u32),
        };

        // Shared state between stream and main thread
        let audio_buffer: Arc<Mutex<Vec<Vec<i16>>>> = Arc::new(Mutex::new(Vec::new()));
        let audio_buffer_clone = Arc::clone(&audio_buffer);

        let stream_error = Arc::new(Mutex::new(None));
        let stream_error_clone = Arc::clone(&stream_error);

        // Build input stream
        let stream = device.build_input_stream(
            &config,
            move |data: &[i16], _: &cpal::InputCallbackInfo| {
                // Copy audio data to buffer
                let mut buffer = audio_buffer_clone.lock().unwrap();
                buffer.push(data.to_vec());
            },
            move |err| {
                let mut error = stream_error_clone.lock().unwrap();
                *error = Some(format!("Stream error: {}", err));
            },
            None,
        )
        .context("Failed to build input stream")?;

        stream.play().context("Failed to start audio stream")?;

        info!("Recording started (speak now)...");

        let mut speech_detected = false;
        let mut silence_start: Option<Instant> = None;
        let recording_start = Instant::now();
        let mut frame_buffer: VecDeque<bool> = VecDeque::with_capacity(2);
        let mut all_audio: Vec<i16> = Vec::new();

        loop {
            // Check for stream errors
            {
                let error = stream_error.lock().unwrap();
                if let Some(ref err_msg) = *error {
                    anyhow::bail!("{}", err_msg);
                }
            }

            // Get audio frames from buffer
            let frames: Vec<Vec<i16>> = {
                let mut buffer = audio_buffer.lock().unwrap();
                let frames = buffer.drain(..).collect();
                frames
            };

            for audio_chunk in frames {
                // Process in frame_size chunks
                for chunk in audio_chunk.chunks(self.frame_size) {
                    if chunk.len() < self.frame_size {
                        // Incomplete frame, skip
                        continue;
                    }

                    all_audio.extend_from_slice(chunk);

                    // Check for speech
                    let is_speech = self.is_speech(chunk);
                    frame_buffer.push_back(is_speech);
                    if frame_buffer.len() > 2 {
                        frame_buffer.pop_front();
                    }

                    // Use majority vote from buffered frames
                    let speech_in_buffer = frame_buffer.iter().filter(|&&x| x).count() > frame_buffer.len() / 2;

                    if speech_in_buffer {
                        speech_detected = true;
                        silence_start = None;
                    } else {
                        // Speech not detected in this frame
                        if speech_detected && silence_start.is_none() {
                            // Start tracking silence
                            silence_start = Some(Instant::now());
                        } else if let Some(start) = silence_start {
                            // Check if silence duration exceeded
                            let silence_elapsed = start.elapsed().as_secs_f64();
                            if silence_elapsed >= self.silence_duration {
                                info!("Silence detected for {:.2}s, stopping recording", silence_elapsed);
                                drop(stream); // Stop recording
                                let recording_duration = recording_start.elapsed().as_secs_f64();
                                info!("Recording finished: {:.2}s", recording_duration);

                                // Check minimum duration
                                if recording_duration < self.min_audio_duration {
                                    warn!(
                                        "Recording too short ({:.2}s < {:.2}s), ignoring",
                                        recording_duration, self.min_audio_duration
                                    );
                                    return Ok(None);
                                }

                                if !all_audio.is_empty() {
                                    info!(
                                        "Recorded {} samples ({:.2}s)",
                                        all_audio.len(),
                                        all_audio.len() as f64 / self.sample_rate as f64
                                    );
                                    return Ok(Some(all_audio));
                                } else {
                                    warn!("No audio data recorded");
                                    return Ok(None);
                                }
                            }
                        }
                    }
                }
            }

            // Small sleep to avoid busy-waiting
            std::thread::sleep(Duration::from_millis(10));
        }
    }

    /// Test audio recording for a fixed duration.
    pub fn test_audio(&mut self, duration: f64) -> Result<bool> {
        info!("Testing audio recording for {:.1}s...", duration);

        let device = self.get_default_input_device()?;
        let config = StreamConfig {
            channels: self.channels,
            sample_rate: cpal::SampleRate(self.sample_rate),
            buffer_size: cpal::BufferSize::Fixed(self.frame_size as u32),
        };

        let audio_buffer: Arc<Mutex<Vec<i16>>> = Arc::new(Mutex::new(Vec::new()));
        let audio_buffer_clone = Arc::clone(&audio_buffer);

        let stream = device.build_input_stream(
            &config,
            move |data: &[i16], _: &cpal::InputCallbackInfo| {
                let mut buffer = audio_buffer_clone.lock().unwrap();
                buffer.extend_from_slice(data);
            },
            |err| {
                warn!("Stream error: {}", err);
            },
            None,
        )?;

        stream.play()?;

        std::thread::sleep(Duration::from_secs_f64(duration));

        drop(stream);

        let buffer = audio_buffer.lock().unwrap();
        let sample_count = buffer.len();
        info!("Recorded {} samples in {:.1}s", sample_count, duration);

        Ok(sample_count > 0)
    }

    /// List available audio input devices.
    pub fn get_available_devices(&self) -> Vec<String> {
        let host = cpal::default_host();
        host.input_devices()
            .map(|devices| {
                devices
                    .filter_map(|device| device.name().ok())
                    .collect()
            })
            .unwrap_or_default()
    }
}
