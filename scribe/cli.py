#!/usr/bin/env python3
"""Command-line interface for Scribe."""

import sys
import logging
import click
from pathlib import Path

from scribe.config import Config
from scribe.audio import AudioRecorder
from scribe.transcribe import Transcriber
from scribe.output import OutputHandler
from scribe.notifications import NotificationHandler

logger = logging.getLogger(__name__)


class Scribe:
    """Main Scribe application class."""

    def __init__(self, config_path: str = None):
        """Initialize Scribe.

        Args:
            config_path: Optional path to configuration file.
        """
        self.config = Config(config_path)

        # Initialize components
        self.audio_recorder = AudioRecorder(
            sample_rate=self.config["audio"]["sample_rate"],
            channels=self.config["audio"]["channels"],
            vad_aggressiveness=self.config["audio"]["vad_aggressiveness"],
            silence_duration=self.config["audio"]["silence_duration"],
            min_audio_duration=self.config["audio"]["min_audio_duration"],
        )

        self.transcriber = Transcriber(
            model_size=self.config["model"]["size"],
            device=self.config["model"]["device"],
            compute_type=self.config["model"]["compute_type"],
            keep_loaded=self.config["advanced"]["keep_model_loaded"],
        )

        self.output_handler = OutputHandler(
            mode=self.config["output"]["mode"],
            typing_delay=self.config["output"]["typing_delay"],
            auto_enter=self.config["output"]["auto_enter"],
        )

        self.notification_handler = NotificationHandler(
            show_notification=self.config["notifications"]["show_notification"],
            play_bell=self.config["notifications"]["play_bell"],
            bell_sound=self.config["notifications"]["bell_sound"],
            notification_timeout=self.config["notifications"]["notification_timeout"],
        )

        logger.info("Scribe initialized successfully")

    def run(self) -> int:
        """Run speech-to-text recording and transcription.

        Returns:
            Exit code (0 for success, 1 for error).
        """
        try:
            # Notify recording start
            self.notification_handler.notify_recording_started()

            # Record audio
            logger.info("Starting audio recording...")
            audio_data = self.audio_recorder.record_with_vad()

            if audio_data is None:
                logger.warning("No audio recorded or recording too short")
                self.notification_handler.notify_error("No audio recorded")
                return 1

            # Notify recording stopped
            self.notification_handler.notify_recording_stopped()

            # Transcribe audio
            logger.info("Starting transcription...")
            transcription = self.transcriber.transcribe(
                audio_data,
                sample_rate=self.config["audio"]["sample_rate"],
            )

            if not transcription:
                logger.warning("No transcription generated")
                self.notification_handler.notify_error("No speech detected")
                return 1

            logger.info(f"Transcription: {transcription}")

            # Output transcription
            success = self.output_handler.output(transcription)

            if success:
                self.notification_handler.notify_transcription_complete(transcription)
                logger.info("Transcription output successfully")
                return 0
            else:
                self.notification_handler.notify_error("Failed to output transcription")
                logger.error("Failed to output transcription")
                return 1

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            return 130
        except Exception as e:
            logger.error(f"Error during execution: {e}", exc_info=True)
            self.notification_handler.notify_error(f"Error: {e}")
            return 1


@click.group(invoke_without_command=True)
@click.option("--config", "-c", type=click.Path(), help="Path to configuration file")
@click.option("--output", "-o", type=click.Choice(["type", "clipboard"]), help="Output mode")
@click.option("--model", "-m", help="Model size (tiny.en, base.en, etc.)")
@click.option("--no-notification", is_flag=True, help="Disable notifications")
@click.option("--no-bell", is_flag=True, help="Disable bell sound")
@click.pass_context
def cli(ctx, config, output, model, no_notification, no_bell):
    """Scribe - Fast, local speech-to-text for KDE/Debian.

    Run without arguments to start recording with voice activity detection.
    The recording will automatically stop after detecting a pause in speech.

    Examples:
        scribe                    # Record and transcribe with VAD
        scribe --output clipboard # Output to clipboard instead of typing
        scribe --model base.en    # Use base.en model for better accuracy
        scribe test               # Test audio recording
        scribe download           # Download/cache the model
    """
    # If invoked without subcommand, run the main application
    if ctx.invoked_subcommand is None:
        # Load configuration
        scribe_app = Scribe(config_path=config)

        # Apply command-line overrides
        if output:
            scribe_app.config.config["output"]["mode"] = output
            scribe_app.output_handler.mode = output

        if model:
            scribe_app.config.config["model"]["size"] = model
            scribe_app.transcriber.model_size = model

        if no_notification:
            scribe_app.notification_handler.show_notification = False

        if no_bell:
            scribe_app.notification_handler.play_bell = False

        # Run the application
        exit_code = scribe_app.run()
        sys.exit(exit_code)


@cli.command()
@click.option("--config", "-c", type=click.Path(), help="Path to configuration file")
def test(config):
    """Test audio recording and system configuration.

    This command verifies that:
    - Audio input is working
    - Required tools are installed (xdotool/ydotool, notify-send, etc.)
    - Configuration is valid
    """
    click.echo("Testing Scribe configuration...\n")

    # Load configuration
    cfg = Config(config_path=config)
    click.echo(f"✓ Configuration loaded from: {cfg.config_path}")

    # Test audio
    click.echo("\nTesting audio recording (3 seconds)...")
    recorder = AudioRecorder(
        sample_rate=cfg["audio"]["sample_rate"],
        channels=cfg["audio"]["channels"],
    )

    if recorder.test_audio(duration=3.0):
        click.echo("✓ Audio recording successful")

        # List available devices
        devices = recorder.get_available_devices()
        click.echo(f"\nAvailable audio input devices ({len(devices)}):")
        for i, device in enumerate(devices):
            click.echo(f"  {i}: {device['name']}")
    else:
        click.echo("✗ Audio recording failed", err=True)
        return

    # Test output handler
    click.echo("\nTesting output handler...")
    output_handler = OutputHandler(mode=cfg["output"]["mode"])
    if output_handler.typing_tool:
        click.echo(f"✓ Typing tool available: {output_handler.typing_tool}")
    else:
        click.echo("⚠ No typing tool found (will use clipboard mode)")

    # Test notifications
    click.echo("\nTesting notifications...")
    notifier = NotificationHandler(
        show_notification=cfg["notifications"]["show_notification"],
        play_bell=cfg["notifications"]["play_bell"],
    )

    if notifier.notify_tool:
        click.echo(f"✓ Notification tool available: {notifier.notify_tool}")
        notifier._show_notification(
            "Scribe Test",
            "This is a test notification",
            "dialog-information",
        )
    else:
        click.echo("⚠ No notification tool found")

    if notifier.audio_tool:
        click.echo(f"✓ Audio playback tool available: {notifier.audio_tool}")
    else:
        click.echo("⚠ No audio playback tool found")

    # Test model
    click.echo(f"\nModel configuration: {cfg['model']['size']}")
    click.echo("✓ All basic tests passed!")
    click.echo("\nYou can now run 'scribe' to start using speech-to-text.")


@cli.command()
@click.option("--config", "-c", type=click.Path(), help="Path to configuration file")
@click.option("--model", "-m", help="Model size to download (default: from config)")
def download(config, model):
    """Download and cache Whisper model.

    This downloads the model to the cache directory so the first run
    is faster. By default, uses the model from configuration.
    """
    cfg = Config(config_path=config)
    model_size = model or cfg["model"]["size"]

    click.echo(f"Downloading model: {model_size}")
    click.echo("This may take a few minutes depending on your connection...\n")

    try:
        transcriber = Transcriber(
            model_size=model_size,
            device=cfg["model"]["device"],
            compute_type=cfg["model"]["compute_type"],
        )
        transcriber.download_model()
        click.echo(f"\n✓ Model '{model_size}' downloaded and cached successfully!")
    except Exception as e:
        click.echo(f"\n✗ Failed to download model: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--config", "-c", type=click.Path(), help="Path to configuration file")
def models(config):
    """List available Whisper models.

    Shows all available model sizes and their characteristics.
    """
    click.echo("Available Whisper models:\n")

    models_info = [
        ("tiny.en", "English only", "~39M params", "Fastest, lowest accuracy"),
        ("tiny", "Multilingual", "~39M params", "Fastest, lowest accuracy"),
        ("base.en", "English only", "~74M params", "Fast, good accuracy"),
        ("base", "Multilingual", "~74M params", "Fast, good accuracy"),
        ("small.en", "English only", "~244M params", "Slower, better accuracy"),
        ("small", "Multilingual", "~244M params", "Slower, better accuracy"),
        ("medium.en", "English only", "~769M params", "Slow, high accuracy"),
        ("medium", "Multilingual", "~769M params", "Slow, high accuracy"),
        ("large-v3", "Multilingual", "~1550M params", "Slowest, highest accuracy"),
    ]

    for name, lang, params, desc in models_info:
        click.echo(f"  {name:12} - {lang:13} {params:12} - {desc}")

    cfg = Config(config_path=config)
    click.echo(f"\nCurrent model: {cfg['model']['size']}")
    click.echo("\nRecommended for CPU: tiny.en or base.en")


@cli.command()
def setup():
    """Setup Scribe configuration and dependencies.

    Creates default configuration file and checks system dependencies.
    """
    click.echo("Setting up Scribe...\n")

    # Create config
    config = Config()
    config_path = config.config_path

    if not config_path.exists():
        config.save()
        click.echo(f"✓ Created configuration file: {config_path}")
    else:
        click.echo(f"Configuration file already exists: {config_path}")

    # Check dependencies
    click.echo("\nChecking system dependencies...")

    dependencies = [
        ("xdotool or ydotool", ["xdotool", "ydotool", "wtype"]),
        ("notify-send", ["notify-send", "kdialog", "zenity"]),
        ("audio playback", ["paplay", "aplay", "ffplay", "mpv"]),
    ]

    import shutil
    all_ok = True

    for dep_name, commands in dependencies:
        found = any(shutil.which(cmd) for cmd in commands)
        if found:
            found_cmd = next(cmd for cmd in commands if shutil.which(cmd))
            click.echo(f"  ✓ {dep_name}: {found_cmd}")
        else:
            click.echo(f"  ✗ {dep_name}: not found", err=True)
            click.echo(f"    Install one of: {', '.join(commands)}")
            all_ok = False

    if all_ok:
        click.echo("\n✓ Setup complete! Run 'scribe test' to verify configuration.")
    else:
        click.echo("\n⚠ Some dependencies are missing. Please install them first.")
        click.echo("See README.md for installation instructions.")


@cli.command()
@click.option("--config", "-c", type=click.Path(), help="Path to configuration file")
def config_path(config):
    """Show configuration file path."""
    cfg = Config(config_path=config)
    click.echo(cfg.config_path)


@cli.command()
@click.option("--config", "-c", type=click.Path(), help="Path to configuration file")
def version(config):
    """Show version information."""
    from scribe import __version__
    click.echo(f"Scribe version {__version__}")


def main():
    """Main entry point."""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
