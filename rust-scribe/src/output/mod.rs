use anyhow::{Context, Result};
use std::process::Command;
use std::thread;
use std::time::Duration;

pub struct OutputHandler {
    pub mode: String,
    pub typing_delay: f64,
    pub auto_enter: bool,
    typing_tool: Option<String>,
    target_window_id: Option<String>,
}

impl OutputHandler {
    pub fn new(mode: String, typing_delay: f64, auto_enter: bool) -> Self {
        let typing_tool = Self::detect_typing_tool();
        log::info!("OutputHandler initialized: mode={}, tool={:?}", mode, typing_tool);

        Self {
            mode,
            typing_delay,
            auto_enter,
            typing_tool,
            target_window_id: None,
        }
    }

    fn detect_typing_tool() -> Option<String> {
        // Detect display server
        let session_type = std::env::var("XDG_SESSION_TYPE").unwrap_or_default().to_lowercase();
        let wayland_display = std::env::var("WAYLAND_DISPLAY").unwrap_or_default();

        let is_wayland = session_type == "wayland" || !wayland_display.is_empty();
        let is_x11 = session_type == "x11" || std::env::var("DISPLAY").is_ok();

        log::debug!("Display server detection: XDG_SESSION_TYPE={}, is_wayland={}, is_x11={}",
                   session_type, is_wayland, is_x11);

        if is_wayland {
            // Wayland tools (in priority order)
            if which::which("dotool").is_ok() {
                log::info!("Found dotool (Wayland - recommended)");
                return Some("dotool".to_string());
            }
            if which::which("kdotool").is_ok() {
                log::info!("Found kdotool (Wayland/KDE)");
                return Some("kdotool".to_string());
            }
            if which::which("ydotool").is_ok() {
                log::info!("Found ydotool (Wayland)");
                return Some("ydotool".to_string());
            }
            if which::which("wtype").is_ok() {
                log::warn!("Found wtype (only works with wlroots compositors, NOT KDE/GNOME)");
                return Some("wtype".to_string());
            }
            log::warn!("No Wayland typing tool found");
            None
        } else if is_x11 {
            if which::which("xdotool").is_ok() {
                log::info!("Found xdotool (X11)");
                return Some("xdotool".to_string());
            }
            log::warn!("No X11 typing tool found");
            None
        } else {
            // Fallback - try all
            log::warn!("Could not detect display server, trying all tools...");
            for tool in &["dotool", "kdotool", "xdotool", "ydotool", "wtype"] {
                if which::which(tool).is_ok() {
                    log::info!("Found {} (fallback detection)", tool);
                    return Some(tool.to_string());
                }
            }
            log::error!("No typing tool found");
            None
        }
    }

    pub fn capture_target_window(&mut self) {
        if self.typing_tool.as_deref() != Some("xdotool") {
            log::debug!("Window capture only supported for xdotool");
            return;
        }

        match Command::new("xdotool")
            .args(&["getwindowfocus"])
            .output()
        {
            Ok(output) if output.status.success() => {
                let window_id = String::from_utf8_lossy(&output.stdout).trim().to_string();
                log::info!("Captured target window ID: {}", window_id);
                self.target_window_id = Some(window_id);
            }
            Ok(output) => {
                log::warn!("Failed to capture window: {}", String::from_utf8_lossy(&output.stderr));
            }
            Err(e) => {
                log::warn!("Error capturing target window: {}", e);
            }
        }
    }

    pub fn output(&self, text: &str) -> Result<()> {
        if text.is_empty() {
            log::warn!("Empty text provided, nothing to output");
            return Ok(());
        }

        match self.mode.as_str() {
            "clipboard" => self.to_clipboard(text),
            "type" => self.type_text(text),
            _ => {
                log::error!("Unknown output mode: {}", self.mode);
                Err(anyhow::anyhow!("Unknown output mode: {}", self.mode))
            }
        }
    }

    fn to_clipboard(&self, text: &str) -> Result<()> {
        use cli_clipboard::{ClipboardContext, ClipboardProvider};

        let mut ctx = ClipboardContext::new()
            .map_err(|e| anyhow::anyhow!("Failed to create clipboard context: {}", e))?;

        ctx.set_contents(text.to_string())
            .map_err(|e| anyhow::anyhow!("Failed to set clipboard contents: {}", e))?;

        log::info!("Text copied to clipboard ({} chars)", text.len());
        Ok(())
    }

    fn type_text(&self, text: &str) -> Result<()> {
        let tool = self.typing_tool.as_ref()
            .ok_or_else(|| anyhow::anyhow!("No typing tool available"))?;

        log::info!("Attempting to type {} characters with {}", text.len(), tool);

        match tool.as_str() {
            "dotool" => self.type_with_dotool(text),
            "kdotool" => self.type_with_kdotool(text),
            "xdotool" => self.type_with_xdotool(text),
            "ydotool" => self.type_with_ydotool(text),
            "wtype" => self.type_with_wtype(text),
            _ => Err(anyhow::anyhow!("Unknown typing tool: {}", tool)),
        }
    }

    fn type_with_dotool(&self, text: &str) -> Result<()> {
        use std::io::Write;
        use std::process::Stdio;

        log::debug!("Waiting 1.0s for notifications to clear...");
        thread::sleep(Duration::from_secs_f64(1.0));

        let input = format!("type {}", text);

        let mut child = Command::new("dotool")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .context("Failed to spawn dotool")?;

        if let Some(mut stdin) = child.stdin.take() {
            stdin.write_all(input.as_bytes())
                .context("Failed to write to dotool stdin")?;
        }

        let output = child.wait_with_output()
            .context("Failed to wait for dotool")?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(anyhow::anyhow!("dotool failed: {}", stderr));
        }

        log::info!("Text typed successfully with dotool ({} chars)", text.len());
        Ok(())
    }

    fn type_with_kdotool(&self, text: &str) -> Result<()> {
        log::debug!("Waiting 1.0s for notifications to clear...");
        thread::sleep(Duration::from_secs_f64(1.0));

        let output = Command::new("kdotool")
            .args(&["type", text])
            .output()
            .context("Failed to execute kdotool")?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(anyhow::anyhow!("kdotool failed: {}", stderr));
        }

        log::info!("Text typed successfully with kdotool ({} chars)", text.len());
        Ok(())
    }

    fn type_with_xdotool(&self, text: &str) -> Result<()> {
        let window_id = self.target_window_id.as_ref()
            .ok_or_else(|| anyhow::anyhow!("No target window captured"))?;

        log::info!("Using pre-captured window: ID={}", window_id);

        log::debug!("Waiting 1.0s for notifications to clear...");
        thread::sleep(Duration::from_secs_f64(1.0));

        // Activate window
        let activate = Command::new("xdotool")
            .args(&["windowactivate", "--sync", window_id])
            .output()
            .context("Failed to activate window")?;

        if !activate.status.success() {
            return Err(anyhow::anyhow!("Failed to activate window"));
        }

        log::info!("Window activated successfully");
        thread::sleep(Duration::from_millis(500));

        // Type text
        let output = Command::new("xdotool")
            .args(&["type", "--clearmodifiers", "--", text])
            .output()
            .context("Failed to execute xdotool")?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(anyhow::anyhow!("xdotool failed: {}", stderr));
        }

        log::info!("Text typed successfully with xdotool ({} chars)", text.len());
        Ok(())
    }

    fn type_with_ydotool(&self, text: &str) -> Result<()> {
        thread::sleep(Duration::from_millis(100));

        let output = Command::new("ydotool")
            .args(&["type", text])
            .output()
            .context("Failed to execute ydotool")?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(anyhow::anyhow!("ydotool failed: {}", stderr));
        }

        log::info!("Text typed successfully with ydotool ({} chars)", text.len());
        Ok(())
    }

    fn type_with_wtype(&self, text: &str) -> Result<()> {
        thread::sleep(Duration::from_millis(100));

        let output = Command::new("wtype")
            .arg(text)
            .output()
            .context("Failed to execute wtype")?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(anyhow::anyhow!("wtype failed: {}", stderr));
        }

        log::info!("Text typed successfully with wtype ({} chars)", text.len());
        Ok(())
    }
}
