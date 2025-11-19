mod cli;
mod config;
mod output;
// TODO: Implement these modules
// mod audio;
// mod transcribe;
// mod notifications;
// mod streaming;

use anyhow::Result;
use clap::Parser;
use cli::{Cli, Commands, OutputMode};
use config::Config;
use output::OutputHandler;

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
        println!("🎤 Streaming mode not yet implemented");
        println!("TODO: Implement streaming mode with real-time transcription");
        return Ok(());
    }

    println!("🎤 Standard recording mode not yet implemented");
    println!("TODO: Implement audio recording, VAD, and transcription");
    println!("\nFor now, try:");
    println!("  scribe test-typing  - Test typing functionality");

    Ok(())
}

fn handle_command(command: Commands, config: &Config) -> Result<()> {
    match command {
        Commands::Test => {
            println!("🔧 Testing system setup...\n");
            test_system(config)?;
            Ok(())
        }
        Commands::Download { model } => {
            let model_name = model.unwrap_or_else(|| config.model.size.clone());
            println!("📥 Downloading model: {}", model_name);
            println!("TODO: Implement model download");
            Ok(())
        }
        Commands::Models => {
            println!("📋 Available Whisper models:\n");
            println!("  tiny.en    - Fastest, lowest accuracy (~40MB)");
            println!("  base.en    - Good balance (~75MB)");
            println!("  small.en   - Better accuracy (~245MB)");
            println!("  medium.en  - High accuracy (~775MB)");
            println!("  large-v2   - Highest accuracy (~1.5GB)");
            Ok(())
        }
        Commands::TestTyping => {
            test_typing(config)?;
            Ok(())
        }
        Commands::TestAudio { audio_file, output } => {
            println!("🎵 Testing with audio file: {:?}", audio_file);
            println!("TODO: Implement audio file transcription");
            if let Some(mode) = output {
                println!("Output mode: {}", mode.as_str());
            }
            Ok(())
        }
    }
}

fn test_system(config: &Config) -> Result<()> {
    println!("✓ Configuration loaded successfully");
    println!("  Model: {}", config.model.size);
    println!("  Device: {}", config.model.device);
    println!("  Sample rate: {}Hz", config.audio.sample_rate);
    println!("  Output mode: {}", config.output.mode);
    println!();

    // Test typing tool detection
    let _output_handler = OutputHandler::new(
        config.output.mode.clone(),
        config.output.typing_delay,
        config.output.auto_enter,
    );

    println!("⚠️  Audio recording not yet implemented");
    println!("⚠️  Whisper transcription not yet implemented");
    println!("⚠️  Notifications not yet implemented");
    println!();
    println!("To test typing, run: scribe test-typing");

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
