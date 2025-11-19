// Streaming speech-to-text with real-time output.

use crate::audio::AudioRecorder;
use crate::notifications::NotificationHandler;
use crate::output::OutputHandler;
use crate::transcribe::Transcriber;
use anyhow::Result;
use cpal::traits::{DeviceTrait, StreamTrait};
use cpal::{StreamConfig};
use log::{info, warn};
use std::collections::VecDeque;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

/// Streaming recorder that records and transcribes audio in real-time chunks.
pub struct StreamingRecorder {
    sample_rate: u32,
    channels: u16,
    frame_size: usize,
    chunk_pause: f64,
    final_pause: f64,
    max_duration: f64,
}

impl StreamingRecorder {
    /// Create a new StreamingRecorder.
    ///
    /// # Arguments
    ///
    /// * `audio_recorder` - Reference to AudioRecorder for settings
    /// * `chunk_pause` - Short pause duration (seconds) to trigger chunk transcription
    /// * `final_pause` - Long pause duration (seconds) to end recording
    /// * `max_duration` - Maximum recording duration (seconds) before auto-stop
    pub fn new(
        audio_recorder: &AudioRecorder,
        chunk_pause: f64,
        final_pause: f64,
        max_duration: f64,
    ) -> Self {
        Self {
            sample_rate: audio_recorder.sample_rate,
            channels: audio_recorder.channels,
            frame_size: audio_recorder.frame_size,
            chunk_pause,
            final_pause,
            max_duration,
        }
    }

    /// Record and transcribe in real-time streaming mode.
    ///
    /// Returns the complete transcribed text.
    pub fn record_and_transcribe_streaming(
        &self,
        audio_recorder: &mut AudioRecorder,
        transcriber: &mut Transcriber,
        output_handler: &mut OutputHandler,
        notification_handler: Option<&NotificationHandler>,
    ) -> Result<String> {
        info!("Starting streaming recording...");

        let device = audio_recorder.get_default_input_device()?;
        let config = StreamConfig {
            channels: self.channels,
            sample_rate: cpal::SampleRate(self.sample_rate),
            buffer_size: cpal::BufferSize::Fixed(self.frame_size as u32),
        };

        // Shared state
        let audio_buffer: Arc<Mutex<Vec<Vec<i16>>>> = Arc::new(Mutex::new(Vec::new()));
        let audio_buffer_clone = Arc::clone(&audio_buffer);

        // Build input stream
        let stream = device.build_input_stream(
            &config,
            move |data: &[i16], _: &cpal::InputCallbackInfo| {
                let mut buffer = audio_buffer_clone.lock().unwrap();
                buffer.push(data.to_vec());
            },
            |err| {
                warn!("Stream error: {}", err);
            },
            None,
        )?;

        stream.play()?;

        info!("Streaming mode active (speak continuously)...");

        let mut current_chunk: Vec<i16> = Vec::new();
        let mut total_audio: Vec<i16> = Vec::new();
        let mut transcribed_text: Vec<String> = Vec::new();

        let mut silence_start: Option<Instant> = None;
        let mut last_speech_time: Option<Instant> = None;  // Track when speech last occurred (for final pause)
        let recording_start = Instant::now();
        let mut speech_detected = false;

        // Rolling buffer for VAD debouncing (10 frames)
        let mut vad_buffer: VecDeque<bool> = VecDeque::with_capacity(10);

        // Continuous silence counter
        let mut continuous_silence_frames = 0;
        const SILENCE_FRAMES_THRESHOLD: u32 = 5;  // Require 5 consecutive silence frames to start timer

        loop {
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
                        continue; // Incomplete frame
                    }

                    current_chunk.extend_from_slice(chunk);
                    total_audio.extend_from_slice(chunk);

                    // Check for speech with VAD
                    let is_speech = audio_recorder.is_speech(chunk);
                    vad_buffer.push_back(is_speech);

                    // Use majority vote from VAD buffer (debouncing)
                    let is_speech_smoothed = if vad_buffer.len() >= 5 {
                        let speech_count = vad_buffer.iter().filter(|&&x| x).count();
                        speech_count as f64 / vad_buffer.len() as f64 > 0.5
                    } else {
                        is_speech
                    };

                    if is_speech_smoothed {
                        // Speech detected
                        speech_detected = true;
                        last_speech_time = Some(Instant::now());
                        silence_start = None;
                        continuous_silence_frames = 0;
                    } else {
                        // Silence frame detected
                        continuous_silence_frames += 1;

                        // Only start silence timer after multiple consecutive silence frames
                        if speech_detected && silence_start.is_none() && continuous_silence_frames >= SILENCE_FRAMES_THRESHOLD {
                            silence_start = Some(Instant::now());
                            log::debug!("Silence started after {} continuous frames", continuous_silence_frames);
                        }

                        if let Some(start) = silence_start {
                            let silence_duration = start.elapsed().as_secs_f64();

                            // Check for chunk pause (transcribe but continue recording)
                            if silence_duration >= self.chunk_pause && !current_chunk.is_empty() {
                                let chunk_duration = current_chunk.len() as f64 / self.sample_rate as f64;

                                // Only transcribe if chunk is substantial
                                if chunk_duration > 0.5 {
                                    info!("Chunk pause detected ({:.1}s), transcribing...", silence_duration);

                                    // Transcribe and output chunk
                                    if let Ok(text) = transcriber.transcribe(
                                        &current_chunk,
                                        self.sample_rate,
                                        Some("en"),
                                    ) {
                                        if !text.trim().is_empty() {
                                            info!("Chunk transcribed: '{}'", text.trim());
                                            transcribed_text.push(text.trim().to_string());

                                            // Output immediately
                                            let output_text = if transcribed_text.len() > 1 {
                                                format!(" {}", text.trim())
                                            } else {
                                                text.trim().to_string()
                                            };

                                            if let Err(e) = output_handler.output(&output_text) {
                                                warn!("Chunk output failed: {}", e);
                                            } else {
                                                info!("Chunk output successful");
                                            }
                                        }
                                    }

                                    // Show brief "still listening" notification
                                    if let Some(notif) = notification_handler {
                                        let _ = notif.show_notification(
                                            "Scribe Streaming",
                                            "Still listening...",
                                            "audio-input-microphone",
                                            Some("low"),
                                            Some(500),
                                        );
                                    }

                                    current_chunk.clear();
                                    // Don't reset silence_start - keep tracking for final pause
                                }
                            }

                            // Check for final pause (end recording)
                            // Only end if we have detected speech AND have transcribed something
                            if last_speech_time.is_some() && silence_duration >= self.final_pause {
                                // Additional check: only end if we've transcribed at least one chunk
                                if !transcribed_text.is_empty() {
                                    let time_since_last_speech = last_speech_time.unwrap().elapsed().as_secs_f64();
                                    info!("Final pause detected ({:.1}s since last speech), ending recording", time_since_last_speech);
                                    break;
                                } else {
                                    log::debug!("Silence detected but no content transcribed yet, continuing...");
                                }
                            }
                        }
                    }
                }
            }

            // Break outer loop if we broke from inner loop
            if silence_start.is_some() {
                if let Some(last_speech) = last_speech_time {
                    if last_speech.elapsed().as_secs_f64() >= self.final_pause {
                        break;
                    }
                }
            }

            // Check for maximum duration timeout
            let elapsed_time = recording_start.elapsed().as_secs_f64();
            if elapsed_time >= self.max_duration {
                info!("Maximum duration reached ({:.1}s), ending recording", elapsed_time);
                break;
            }

            // Small sleep to avoid busy-waiting
            std::thread::sleep(Duration::from_millis(10));
        }

        drop(stream);

        // Transcribe any remaining audio
        if !current_chunk.is_empty() {
            let chunk_duration = current_chunk.len() as f64 / self.sample_rate as f64;
            if chunk_duration > 0.3 {
                info!("Transcribing final chunk...");
                if let Ok(text) = transcriber.transcribe(&current_chunk, self.sample_rate, Some("en")) {
                    if !text.trim().is_empty() {
                        transcribed_text.push(text.trim().to_string());

                        let output_text = if transcribed_text.len() > 1 {
                            format!(" {}", text.trim())
                        } else {
                            text.trim().to_string()
                        };

                        let _ = output_handler.output(&output_text);
                    }
                }
            }
        }

        let recording_duration = recording_start.elapsed().as_secs_f64();
        info!("Streaming recording complete: {:.1}s total", recording_duration);

        // Show "finished" notification
        if let Some(notif) = notification_handler {
            let total_text = transcribed_text.join(" ");
            if !total_text.is_empty() {
                let preview = if total_text.len() > 50 {
                    format!("{}...", &total_text[..50])
                } else {
                    total_text.clone()
                };
                let _ = notif.show_notification(
                    "Scribe Complete",
                    &format!("Transcription finished: {}", preview),
                    "dialog-information",
                    None,
                    None,
                );
            } else {
                let _ = notif.show_notification(
                    "Scribe Complete",
                    "Recording ended (no speech detected)",
                    "dialog-information",
                    None,
                    None,
                );
            }
        }

        Ok(transcribed_text.join(" "))
    }
}
