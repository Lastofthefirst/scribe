use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Config {
    pub model: ModelConfig,
    pub audio: AudioConfig,
    pub output: OutputConfig,
    pub notifications: NotificationsConfig,
    #[serde(default)]
    pub advanced: AdvancedConfig,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ModelConfig {
    #[serde(default = "default_model_size")]
    pub size: String,
    #[serde(default = "default_device")]
    pub device: String,
    #[serde(default = "default_compute_type")]
    pub compute_type: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct AudioConfig {
    #[serde(default = "default_sample_rate")]
    pub sample_rate: u32,
    #[serde(default = "default_channels")]
    pub channels: u16,
    #[serde(default = "default_vad_aggressiveness")]
    pub vad_aggressiveness: u8,
    #[serde(default = "default_silence_duration")]
    pub silence_duration: f64,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct OutputConfig {
    #[serde(default = "default_mode")]
    pub mode: String,
    #[serde(default)]
    pub typing_delay: f64,
    #[serde(default)]
    pub auto_enter: bool,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct NotificationsConfig {
    #[serde(default = "default_true")]
    pub enabled: bool,
    #[serde(default = "default_true")]
    pub audio_bell: bool,
    #[serde(default = "default_notification_timeout")]
    pub timeout: u32,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct AdvancedConfig {
    #[serde(default = "default_log_level")]
    pub log_level: String,
}

// Default values
fn default_model_size() -> String {
    "tiny.en".to_string()
}
fn default_device() -> String {
    "cpu".to_string()
}
fn default_compute_type() -> String {
    "int8".to_string()
}
fn default_sample_rate() -> u32 {
    16000
}
fn default_channels() -> u16 {
    1
}
fn default_vad_aggressiveness() -> u8 {
    3
}
fn default_silence_duration() -> f64 {
    1.5
}
fn default_mode() -> String {
    "type".to_string()
}
fn default_true() -> bool {
    true
}
fn default_notification_timeout() -> u32 {
    3000
}
fn default_log_level() -> String {
    "info".to_string()
}

impl Default for Config {
    fn default() -> Self {
        Self {
            model: ModelConfig {
                size: default_model_size(),
                device: default_device(),
                compute_type: default_compute_type(),
            },
            audio: AudioConfig {
                sample_rate: default_sample_rate(),
                channels: default_channels(),
                vad_aggressiveness: default_vad_aggressiveness(),
                silence_duration: default_silence_duration(),
            },
            output: OutputConfig {
                mode: default_mode(),
                typing_delay: 0.0,
                auto_enter: false,
            },
            notifications: NotificationsConfig {
                enabled: true,
                audio_bell: true,
                timeout: default_notification_timeout(),
            },
            advanced: AdvancedConfig::default(),
        }
    }
}

impl Config {
    pub fn load(path: Option<PathBuf>) -> Result<Self> {
        let config_path = match path {
            Some(p) => p,
            None => Self::default_config_path()?,
        };

        if !config_path.exists() {
            log::info!("Config file not found, using defaults: {:?}", config_path);
            return Ok(Self::default());
        }

        let content = std::fs::read_to_string(&config_path)
            .with_context(|| format!("Failed to read config file: {:?}", config_path))?;

        let config: Config = toml::from_str(&content)
            .with_context(|| format!("Failed to parse config file: {:?}", config_path))?;

        log::info!("Config loaded from {:?}", config_path);
        Ok(config)
    }

    pub fn save(&self, path: Option<PathBuf>) -> Result<()> {
        let config_path = match path {
            Some(p) => p,
            None => Self::default_config_path()?,
        };

        if let Some(parent) = config_path.parent() {
            std::fs::create_dir_all(parent)
                .with_context(|| format!("Failed to create config directory: {:?}", parent))?;
        }

        let content = toml::to_string_pretty(self)
            .context("Failed to serialize config to TOML")?;

        std::fs::write(&config_path, content)
            .with_context(|| format!("Failed to write config file: {:?}", config_path))?;

        log::info!("Config saved to {:?}", config_path);
        Ok(())
    }

    fn default_config_path() -> Result<PathBuf> {
        let config_dir = dirs::config_dir()
            .context("Failed to get config directory")?;
        Ok(config_dir.join("scribe").join("config.toml"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = Config::default();
        assert_eq!(config.model.size, "tiny.en");
        assert_eq!(config.audio.sample_rate, 16000);
        assert_eq!(config.output.mode, "type");
    }

    #[test]
    fn test_config_roundtrip() {
        let config = Config::default();
        let toml_str = toml::to_string(&config).unwrap();
        let parsed: Config = toml::from_str(&toml_str).unwrap();
        assert_eq!(config.model.size, parsed.model.size);
    }
}
