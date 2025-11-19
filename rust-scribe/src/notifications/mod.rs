// Notification and sound handling for Scribe.

use anyhow::Result;
use log::{info, warn};
use std::process::Command;

/// Handles desktop notifications and audio alerts.
pub struct NotificationHandler {
    pub show_notification: bool,
    pub play_bell: bool,
    pub bell_sound: String,
    pub notification_timeout: u32,
    notify_tool: Option<String>,
    audio_tool: Option<String>,
}

impl NotificationHandler {
    /// Create a new NotificationHandler.
    ///
    /// # Arguments
    ///
    /// * `show_notification` - Whether to show desktop notifications
    /// * `play_bell` - Whether to play bell sound
    /// * `bell_sound` - Bell sound to play ("system" or path to audio file)
    /// * `notification_timeout` - Notification timeout in milliseconds
    pub fn new(
        show_notification: bool,
        play_bell: bool,
        bell_sound: String,
        notification_timeout: u32,
    ) -> Self {
        let notify_tool = Self::detect_notify_tool();
        let audio_tool = Self::detect_audio_tool();

        info!(
            "NotificationHandler initialized: notify={:?}, audio={:?}",
            notify_tool, audio_tool
        );

        Self {
            show_notification,
            play_bell,
            bell_sound,
            notification_timeout,
            notify_tool,
            audio_tool,
        }
    }

    /// Detect available notification tool.
    fn detect_notify_tool() -> Option<String> {
        // Try notify-send (most common on Linux)
        if which::which("notify-send").is_ok() {
            return Some("notify-send".to_string());
        }

        // Try kdialog (KDE)
        if which::which("kdialog").is_ok() {
            return Some("kdialog".to_string());
        }

        // Try zenity (GNOME)
        if which::which("zenity").is_ok() {
            return Some("zenity".to_string());
        }

        warn!("No notification tool found");
        None
    }

    /// Detect available audio playback tool.
    fn detect_audio_tool() -> Option<String> {
        // Try paplay (PulseAudio)
        if which::which("paplay").is_ok() {
            return Some("paplay".to_string());
        }

        // Try aplay (ALSA)
        if which::which("aplay").is_ok() {
            return Some("aplay".to_string());
        }

        // Try ffplay (FFmpeg)
        if which::which("ffplay").is_ok() {
            return Some("ffplay".to_string());
        }

        // Try mpv
        if which::which("mpv").is_ok() {
            return Some("mpv".to_string());
        }

        warn!("No audio playback tool found");
        None
    }

    /// Show a desktop notification.
    pub fn show_notification(
        &self,
        title: &str,
        message: &str,
        icon: &str,
        urgency: Option<&str>,
        timeout: Option<u32>,
    ) -> Result<()> {
        if !self.show_notification {
            return Ok(());
        }

        let Some(ref tool) = self.notify_tool else {
            return Ok(()); // No notification tool available
        };

        let timeout_ms = timeout.unwrap_or(self.notification_timeout);

        match tool.as_str() {
            "notify-send" => {
                let mut cmd = Command::new("notify-send");
                cmd.arg(title)
                    .arg(message)
                    .arg("--icon")
                    .arg(icon)
                    .arg("--expire-time")
                    .arg(timeout_ms.to_string());

                if let Some(urg) = urgency {
                    cmd.arg("--urgency").arg(urg);
                }

                cmd.output()?;
            }
            "kdialog" => {
                Command::new("kdialog")
                    .arg("--title")
                    .arg(title)
                    .arg("--passivepopup")
                    .arg(message)
                    .arg((timeout_ms / 1000).to_string())
                    .output()?;
            }
            "zenity" => {
                Command::new("zenity")
                    .arg("--notification")
                    .arg("--text")
                    .arg(format!("{}: {}", title, message))
                    .output()?;
            }
            _ => {}
        }

        Ok(())
    }

    /// Play a bell sound.
    fn play_bell(&self) -> Result<()> {
        if !self.play_bell {
            return Ok(());
        }

        let Some(ref tool) = self.audio_tool else {
            return Ok(()); // No audio tool available
        };

        // Use system bell sound
        let bell_path = if self.bell_sound == "system" {
            "/usr/share/sounds/freedesktop/stereo/bell.oga"
        } else {
            &self.bell_sound
        };

        match tool.as_str() {
            "paplay" => {
                Command::new("paplay").arg(bell_path).spawn()?;
            }
            "aplay" => {
                Command::new("aplay").arg(bell_path).spawn()?;
            }
            "ffplay" => {
                Command::new("ffplay")
                    .arg("-nodisp")
                    .arg("-autoexit")
                    .arg(bell_path)
                    .spawn()?;
            }
            "mpv" => {
                Command::new("mpv")
                    .arg("--no-video")
                    .arg(bell_path)
                    .spawn()?;
            }
            _ => {}
        }

        Ok(())
    }

    /// Show notification and play bell when recording starts.
    pub fn notify_recording_started(&self) -> Result<()> {
        self.show_notification(
            "Scribe Recording",
            "Listening... (speak now)",
            "audio-input-microphone",
            None,
            None,
        )?;
        self.play_bell()?;
        Ok(())
    }

    /// Show notification when recording stops.
    pub fn notify_recording_stopped(&self) -> Result<()> {
        self.show_notification(
            "Scribe Processing",
            "Processing audio...",
            "audio-input-microphone",
            None,
            None,
        )
    }

    /// Show notification when transcription is complete.
    pub fn notify_transcription_complete(&self, text: &str) -> Result<()> {
        // Truncate text for notification
        let preview = if text.len() > 100 {
            format!("{}...", &text[..100])
        } else {
            text.to_string()
        };

        self.show_notification(
            "Scribe Complete",
            &format!("Transcribed: {}", preview),
            "dialog-information",
            None,
            None,
        )
    }

    /// Show error notification.
    pub fn notify_error(&self, error: &str) -> Result<()> {
        self.show_notification(
            "Scribe Error",
            error,
            "dialog-error",
            Some("critical"),
            None,
        )
    }
}
