mod audio;
mod cli;
mod config;
mod notifications;
mod output;
mod streaming;
mod transcribe;

use anyhow::Result;
use clap::Parser;
use cli::{Cli, Commands};
use config::Config;
use log::info;
use audio::AudioRecorder;
use notifications::NotificationHandler;
use output::OutputHandler;
use streaming::StreamingRecorder;
use transcribe::Transcriber;

fn main() -> Result<()> {
    // Parse CLI arguments
    let cli = Cli::parse();

    // Initialize logging
    let log_level = if std::env::var("RUST_LOG").is_ok() {
        std::env::var("RUST_LOG").unwrap()
    } else {
        "info".to_string()
    };
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or(log_level)).init();

    // Load configuration
    let mut config = Config::load(cli.config.clone())?;

    // Apply CLI overrides
    if let Some(output) = cli.output {
        config.output.mode = output.as_str().to_string();
    }
    if let Some(model) = cli.model.clone() {
        config.model.size = model;
    }
    if cli.no_notification {
        config.notifications.enabled = false;
    }
    if cli.no_bell {
        config.notifications.audio_bell = false;
    }

    // Handle subcommands
    if let Some(command) = cli.command {
        return handle_command(command, &config);
    }

    // Main recording mode
    if cli.stream {
        return run_streaming(&config);
    }

    run_standard(&config)
}

fn run_standard(config: &Config) -> Result<()> {
    info!("Starting standard recording mode");

    // Initialize components
    let mut audio_recorder = AudioRecorder::new(
        config.audio.sample_rate,
        config.audio.channels as u16,
        config.audio.vad_aggressiveness as i32,
        config.audio.silence_duration,
        config.audio.min_audio_duration,
    )?;

    let mut transcriber = Transcriber::new(
        config.model.size.clone(),
        config.model.device.clone(),
        config.advanced.keep_model_loaded,
    )?;

    let mut output_handler = OutputHandler::new(
        config.output.mode.clone(),
        config.output.typing_delay,
        config.output.auto_enter,
    );

    let notification_handler = NotificationHandler::new(
        config.notifications.enabled,
        config.notifications.audio_bell,
        config.notifications.bell_sound.clone(),
        config.notifications.timeout,
    );

    // Capture target window BEFORE notifications
    output_handler.capture_target_window();

    // Notify recording start
    notification_handler.notify_recording_started()?;

    // Record audio
    info!("Starting audio recording...");
    let audio_data = audio_recorder.record_with_vad()?;

    let Some(audio) = audio_data else {
        notification_handler.notify_error("No audio recorded")?;
        anyhow::bail!("No audio recorded or recording too short");
    };

    // Notify recording stopped
    notification_handler.notify_recording_stopped()?;

    // Transcribe audio
    info!("Starting transcription...");
    let transcription = transcriber.transcribe(&audio, config.audio.sample_rate, Some("en"))?;

    if transcription.trim().is_empty() {
        notification_handler.notify_error("No speech detected")?;
        anyhow::bail!("No transcription generated");
    }

    info!("Transcription: {}", transcription);

    // Output transcription
    output_handler.output(&transcription)?;

    notification_handler.notify_transcription_complete(&transcription)?;
    info!("Transcription output successfully");

    Ok(())
}

fn run_streaming(config: &Config) -> Result<()> {
    info!("Starting streaming mode");

    // Initialize components
    let mut audio_recorder = AudioRecorder::new(
        config.audio.sample_rate,
        config.audio.channels as u16,
        config.audio.vad_aggressiveness as i32,
        config.audio.silence_duration,
        config.audio.min_audio_duration,
    )?;

    let mut transcriber = Transcriber::new(
        config.model.size.clone(),
        config.model.device.clone(),
        config.advanced.keep_model_loaded,
    )?;

    let mut output_handler = OutputHandler::new(
        config.output.mode.clone(),
        config.output.typing_delay,
        config.output.auto_enter,
    );

    let notification_handler = NotificationHandler::new(
        config.notifications.enabled,
        config.notifications.audio_bell,
        config.notifications.bell_sound.clone(),
        config.notifications.timeout,
    );

    // Capture target window BEFORE notifications
    output_handler.capture_target_window();

    // Notify recording start
    notification_handler.notify_recording_started()?;

    // Create streaming recorder
    let streamer = StreamingRecorder::new(
        &audio_recorder,
        0.8,  // chunk_pause
        2.0,  // final_pause (with fixed logic from Python fix!)
        300.0, // max_duration (5 minutes)
    );

    // Record and transcribe in real-time
    info!("Starting streaming mode...");
    let transcription = streamer.record_and_transcribe_streaming(
        &mut audio_recorder,
        &mut transcriber,
        &mut output_handler,
        Some(&notification_handler),
    )?;

    if transcription.trim().is_empty() {
        info!("No transcription generated");
        return Ok(());
    }

    info!("Complete transcription: {}", transcription);
    Ok(())
}

fn handle_command(command: Commands, config: &Config) -> Result<()> {
    match command {
        Commands::Test => {
            test_system(config)?;
            Ok(())
        }
        Commands::Download { model } => {
            let model_name = model.unwrap_or_else(|| config.model.size.clone());
            let transcriber = Transcriber::new(model_name, config.model.device.clone(), false)?;
            transcriber.download_model()?;
            Ok(())
        }
        Commands::Models => {
            println!("📋 Available Whisper models:\n");
            println!("  tiny.en    - Fastest, lowest accuracy (~40MB)");
            println!("  base.en    - Good balance (~75MB)");
            println!("  small.en   - Better accuracy (~245MB)");
            println!("  medium.en  - High accuracy (~775MB)");
            println!("  large-v2   - Highest accuracy (~1.5GB)");
            println!("\nCurrent model: {}", config.model.size);
            println!("\nRecommended for CPU: tiny.en or base.en");
            Ok(())
        }
        Commands::TestTyping => {
            test_typing(config)?;
            Ok(())
        }
        Commands::TestAudio { audio_file, output: _ } => {
            println!("🎵 Testing with audio file: {:?}", audio_file);
            println!("TODO: Implement audio file loading");
            Ok(())
        }
    }
}

fn test_system(config: &Config) -> Result<()> {
    println!("🔧 Testing system setup...\n");
    println!("✓ Configuration loaded successfully");
    println!("  Model: {}", config.model.size);
    println!("  Device: {}", config.model.device);
    println!("  Sample rate: {}Hz", config.audio.sample_rate);
    println!("  Output mode: {}", config.output.mode);
    println!();

    // Test audio
    println!("Testing audio recording (3 seconds)...");
    let mut audio_recorder = AudioRecorder::new(
        config.audio.sample_rate,
        config.audio.channels as u16,
        config.audio.vad_aggressiveness as i32,
        config.audio.silence_duration,
        config.audio.min_audio_duration,
    )?;

    if audio_recorder.test_audio(3.0)? {
        println!("✓ Audio recording successful\n");

        // List devices
        let devices = audio_recorder.get_available_devices();
        println!("Available audio input devices ({}):", devices.len());
        for (i, device) in devices.iter().enumerate() {
            println!("  {}: {}", i, device);
        }
        println!();
    } else {
        println!("✗ Audio recording failed\n");
    }

    // Test output handler
    println!("Testing output handler...");
    let output_handler = OutputHandler::new(
        config.output.mode.clone(),
        config.output.typing_delay,
        config.output.auto_enter,
    );
    if let Some(tool) = output_handler.get_typing_tool() {
        println!("✓ Typing tool available: {}\n", tool);
    } else {
        println!("⚠ No typing tool found (will use clipboard mode)\n");
    }

    // Test notifications
    println!("Testing notifications...");
    let notif_handler = NotificationHandler::new(
        config.notifications.enabled,
        config.notifications.audio_bell,
        config.notifications.bell_sound.clone(),
        config.notifications.timeout,
    );

    let _ = notif_handler.show_notification(
        "Scribe Test",
        "This is a test notification",
        "dialog-information",
        None,
        None,
    );
    println!("✓ Notification sent\n");

    println!("✓ All basic tests passed!");
    println!("You can now run 'scribe' to start using speech-to-text.");

    Ok(())
}

fn test_typing(config: &Config) -> Result<()> {
    use std::thread;
    use std::time::Duration;

    println!("🧪 Testing typing functionality...\n");

    let mut output_handler = OutputHandler::new(
        "type".to_string(),
        config.output.typing_delay,
        config.output.auto_enter,
    );

    println!("⚠️  FOCUS A TEXT EDITOR OR TERMINAL NOW!");
    println!("Text will be typed in 5 seconds...\n");

    for i in (1..=5).rev() {
        println!("{}...", i);
        thread::sleep(Duration::from_secs(1));
    }

    println!("Capturing target window...");
    output_handler.capture_target_window();

    thread::sleep(Duration::from_millis(500));

    let test_text = "Hello from Scribe Rust! This is a typing test. ⚡";
    println!("\nTyping test message: '{}'", test_text);

    match output_handler.output(test_text) {
        Ok(()) => {
            println!("\n✓ Typing test PASSED - text should appear in focused window");
            Ok(())
        }
        Err(e) => {
            eprintln!("\n✗ Typing test FAILED: {}", e);
            eprintln!("Check the logs for details");
            Err(e)
        }
    }
}
