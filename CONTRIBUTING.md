# Contributing to Scribe

Thank you for your interest in contributing to Scribe! This document provides guidelines and instructions for contributing.

## 🚀 Getting Started

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/scribe.git
   cd scribe
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Run tests to verify setup**
   ```bash
   pytest
   ```

## 🧪 Testing

We follow Test-Driven Development (TDD) principles:

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=scribe --cov-report=html

# Run specific test file
pytest tests/test_config.py

# Run specific test
pytest tests/test_config.py::TestConfig::test_default_config
```

### Writing Tests

1. **Write tests first** before implementing features
2. **Test file naming**: `test_<module>.py`
3. **Test class naming**: `TestClassName`
4. **Test method naming**: `test_description_of_what_it_tests`

Example:
```python
def test_audio_recording_with_vad():
    """Test that audio recording works with VAD."""
    recorder = AudioRecorder(vad_aggressiveness=2)
    # ... test implementation
```

## 📝 Code Style

### Python Style Guide

- Follow [PEP 8](https://pep8.org/)
- Maximum line length: 100 characters
- Use type hints where possible
- Write docstrings for all public functions/classes

Example:
```python
def transcribe(
    self,
    audio: np.ndarray,
    sample_rate: int = 16000,
) -> str:
    """Transcribe audio to text.

    Args:
        audio: Audio data as numpy array.
        sample_rate: Sample rate in Hz.

    Returns:
        Transcribed text.
    """
    # implementation
```

### Linting

```bash
# Install linting tools
pip install pylint black isort

# Run linter
pylint scribe/

# Format code
black scribe/
isort scribe/
```

## 🔀 Git Workflow

### Branching Strategy

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write tests first
   - Implement feature
   - Ensure all tests pass

3. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add feature: description"
   ```

### Commit Message Format

```
<type>: <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Maintenance tasks

**Example**:
```
feat: Add support for custom pause duration

Implement configurable silence_duration parameter in AudioRecorder
to allow users to customize pause detection timing.

Closes #42
```

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Description**: Clear description of the bug
2. **Steps to reproduce**: Detailed steps to reproduce the issue
3. **Expected behavior**: What you expected to happen
4. **Actual behavior**: What actually happened
5. **Environment**:
   - OS and version
   - Python version
   - Scribe version
   - Desktop environment (KDE/GNOME/etc.)
6. **Logs**: Relevant log output (run with `--log-level DEBUG`)

## 💡 Feature Requests

When requesting features:

1. **Use case**: Describe your use case
2. **Proposed solution**: How you envision the feature working
3. **Alternatives**: Any alternative solutions you've considered
4. **Additional context**: Screenshots, mockups, or examples

## 🔍 Code Review Process

1. **Submit a Pull Request**
   - Link to related issue(s)
   - Provide clear description of changes
   - Include screenshots/demos if applicable

2. **Code Review Checklist**
   - [ ] Tests pass
   - [ ] Code follows style guidelines
   - [ ] Documentation updated
   - [ ] No breaking changes (or clearly documented)
   - [ ] Commits are clean and well-organized

3. **Address Review Feedback**
   - Respond to comments
   - Make requested changes
   - Push updates to your branch

## 📚 Documentation

### Code Documentation

- Use docstrings for all public functions/classes
- Include type hints
- Provide usage examples in docstrings

### User Documentation

- Update README.md for user-facing changes
- Add examples for new features
- Update configuration documentation

## 🏗️ Architecture Guidelines

### Module Organization

```
scribe/
├── cli.py           # CLI interface only
├── config.py        # Configuration management
├── audio.py         # Audio recording + VAD
├── transcribe.py    # Speech-to-text
├── output.py        # Text output handling
└── notifications.py # Notifications + sounds
```

### Design Principles

1. **Separation of Concerns**: Each module has a single responsibility
2. **Testability**: Write testable code with dependency injection
3. **Configuration**: Make behavior configurable
4. **Error Handling**: Graceful error handling with informative messages
5. **Performance**: Optimize for CPU-only execution

## 📦 Release Process

1. **Version Bump**
   - Update version in `scribe/__init__.py`
   - Update version in `setup.py`

2. **Changelog**
   - Update CHANGELOG.md with changes

3. **Tag Release**
   ```bash
   git tag -a v0.2.0 -m "Release v0.2.0"
   git push origin v0.2.0
   ```

## ❓ Questions?

- Open a [Discussion](https://github.com/Lastofthefirst/scribe/discussions)
- Check existing [Issues](https://github.com/Lastofthefirst/scribe/issues)

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Scribe! 🎉
