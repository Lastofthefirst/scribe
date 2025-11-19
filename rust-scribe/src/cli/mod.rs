use clap::{Parser, Subcommand};
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "scribe")]
#[command(author, version, about = "Fast, local speech-to-text for Linux", long_about = None)]
pub struct Cli {
    /// Path to configuration file
    #[arg(short, long, value_name = "FILE")]
    pub config: Option<PathBuf>,

    /// Output mode (type or clipboard)
    #[arg(short, long, value_enum)]
    pub output: Option<OutputMode>,

    /// Model size (tiny.en, base.en, small.en, etc.)
    #[arg(short, long)]
    pub model: Option<String>,

    /// Enable streaming mode (real-time transcription)
    #[arg(short, long)]
    pub stream: bool,

    /// Disable notifications
    #[arg(long)]
    pub no_notification: bool,

    /// Disable audio bell
    #[arg(long)]
    pub no_bell: bool,

    #[command(subcommand)]
    pub command: Option<Commands>,
}

#[derive(Copy, Clone, PartialEq, Eq, PartialOrd, Ord, clap::ValueEnum)]
pub enum OutputMode {
    /// Type text at cursor position
    Type,
    /// Copy to clipboard
    Clipboard,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Test system setup
    Test,

    /// Download and cache Whisper model
    Download {
        /// Model size to download
        #[arg(short, long)]
        model: Option<String>,
    },

    /// List available Whisper models
    Models,

    /// Test typing functionality
    TestTyping,

    /// Test with audio file
    TestAudio {
        /// Path to audio file
        audio_file: PathBuf,

        /// Output mode
        #[arg(short, long, value_enum)]
        output: Option<OutputMode>,
    },
}

impl OutputMode {
    pub fn as_str(&self) -> &'static str {
        match self {
            OutputMode::Type => "type",
            OutputMode::Clipboard => "clipboard",
        }
    }
}
