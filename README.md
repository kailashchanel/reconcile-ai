# Reconcile AI 🤖⚔️

<div align="center">

[![PyPI version](https://badge.fury.io/py/reconcile-ai.svg)](https://badge.fury.io/py/reconcile-ai)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Tests](https://github.com/kailashchanel/reconcile-ai/workflows/CI/badge.svg)](https://github.com/kailashchanel/reconcile-ai/actions)

**AI-powered headless merge conflict resolver for Git repositories**

*Automatically resolve merge conflicts using large language models, with enterprise-grade hook management and comprehensive logging.*

</div>

---

## 🌟 Features

### 🤖 **AI-Powered Conflict Resolution**
- **Smart Merging**: Uses OpenAI GPT models to intelligently resolve conflicts
- **Batch Processing**: Resolves multiple conflicts in single API calls (up to 80% cost reduction)
- **Fallback Safety**: Graceful degradation to individual resolution if batch processing fails
- **Model Selection**: Support for GPT-4, GPT-3.5-turbo, and other OpenAI models

### 🔧 **Enterprise-Grade Hook Management**
- **Multiple Hook Types**: Support for `pre-commit`, `post-merge`, `pre-push`, `pre-merge`
- **Automatic Backup**: Safely backs up existing hooks before installation
- **Interactive Restoration**: Restore previous hooks during uninstallation
- **Smart Detection**: Prevents duplicate installations and overwrites

### 📊 **Advanced Logging & Monitoring**
- **Structured JSON Logs**: Machine-readable logs for monitoring and analytics
- **Performance Metrics**: Track AI resolution latency, token usage, and success rates
- **Verbose Debugging**: Detailed step-by-step execution logging
- **Conflict Hashing**: Unique identifiers for tracking individual conflicts

### ⚙️ **Flexible Configuration**
- **YAML Configuration**: Project-specific settings and preferences
- **CLI Overrides**: Command-line arguments override config files
- **File-Type Specific**: Different models and prompts for different languages
- **Branch Preferences**: Customize resolution strategies per branch

---

## 🚀 Quick Start

### Installation

```bash
# Install from PyPI
pip install reconcile-ai

# Or install from source
git clone https://github.com/yourusername/reconcile-ai.git
cd reconcile-ai
pip install -e .
```

### Set up OpenAI API Key

```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

### Basic Usage

```bash
# Resolve conflicts in current repository
reconcile run

# Preview conflicts without AI resolution
reconcile run --dry-run

# Install as a Git hook (runs automatically after merges)
reconcile install --hook post-merge
```

---

## 📚 User Guide

### 🎯 **Basic Workflow Integration**

#### 1. **Manual Conflict Resolution**
Use reconcile when you encounter merge conflicts:

```bash
# Create a merge conflict
git merge feature-branch

# Resolve conflicts with AI
reconcile run --verbose

# Review the resolved files
git diff --cached

# Commit the resolution
git commit -m "Resolved conflicts with AI assistance"
```

#### 2. **Automated Hook Integration**
Set up reconcile to run automatically:

```bash
# Install post-merge hook (runs after successful merges)
reconcile install --hook post-merge

# Install pre-commit hook (runs before commits)
reconcile install --hook pre-commit

# Install pre-push hook (runs before pushes)
reconcile install --hook pre-push
```

#### 3. **Team Workflow Integration**

**For Project Maintainers:**
```bash
# Add reconcile config to your repository
cat > reconcile.yaml << EOF
model: "gpt-4"
max_batch_size: 5
temperature: 0
file_types:
  python:
    model: "gpt-4"
    custom_prompt: "Follow PEP 8 and Python best practices"
  javascript:
    model: "gpt-3.5-turbo"
    custom_prompt: "Follow ESLint rules and modern JS conventions"
EOF

# Commit the config
git add reconcile.yaml
git commit -m "Add reconcile AI configuration"
```

**For Team Members:**
```bash
# Install reconcile and set up hooks
pip install reconcile-ai
export OPENAI_API_KEY="your-key-here"
reconcile install --hook post-merge

# The hook will now run automatically on merges
git merge feature-branch  # Conflicts resolved automatically!
```

---

## 🛠️ Configuration

### Configuration File (`reconcile.yaml`)

Create a `reconcile.yaml` file in your repository root:

```yaml
# Model Configuration
model: "gpt-4"                    # Default AI model
max_batch_size: 5                 # Conflicts per batch (1-10)
temperature: 0                    # AI creativity (0-1)
timeout: 30                       # API timeout in seconds

# Branch Strategy
branch_preference: "feature"      # Prefer changes from specific branches
preserve_whitespace: true         # Maintain original formatting

# File-Type Specific Settings
file_types:
  python:
    model: "gpt-4"
    custom_prompt: "Follow PEP 8, use type hints, prefer comprehensions"
    max_batch_size: 3
  
  javascript:
    model: "gpt-3.5-turbo"
    custom_prompt: "Use modern ES6+, follow ESLint rules"
    max_batch_size: 5
  
  go:
    model: "gpt-4"
    custom_prompt: "Follow Go conventions, use gofmt style"

# Logging Configuration
logging:
  level: "INFO"                   # DEBUG, INFO, WARNING, ERROR
  json_format: true               # Enable structured logging
  file_path: ".reconcile/logs"    # Custom log directory

# Hook Configuration
hooks:
  post_merge:
    enabled: true
    auto_stage: true              # Automatically stage resolved files
    
  pre_commit:
    enabled: false
    check_conflicts: true         # Prevent commits with unresolved conflicts
```

### Environment Variables

```bash
# Required
export OPENAI_API_KEY="sk-..."

# Optional
export RECONCILE_MODEL="gpt-4"
export RECONCILE_BATCH_SIZE="3"
export RECONCILE_LOG_LEVEL="DEBUG"
```

---

## 💻 Command Line Interface

### Core Commands

#### `reconcile run` - Resolve Conflicts
```bash
# Basic conflict resolution
reconcile run

# With verbose logging
reconcile run --verbose

# Dry-run (show conflicts without resolving)
reconcile run --dry-run

# Override configuration
reconcile run --model gpt-3.5-turbo --max-batch-size 3

# Enable JSON logging
reconcile run --json-logs --verbose

# Specify repository path
reconcile run --repo /path/to/repo
```

#### `reconcile install` - Install Git Hooks
```bash
# Install post-merge hook (default)
reconcile install

# Install specific hook type
reconcile install --hook pre-commit
reconcile install --hook pre-push
reconcile install --hook pre-merge

# List available hooks
reconcile install --help
```

#### `reconcile uninstall` - Remove Git Hooks
```bash
# Uninstall post-merge hook (with interactive backup restoration)
reconcile uninstall

# Uninstall specific hook
reconcile uninstall --hook pre-commit

# View available backups and restore previous hooks
reconcile uninstall --hook post-merge
```

### Advanced Usage Examples

#### Batch Processing for Large Conflicts
```bash
# Process conflicts in larger batches (faster, more cost-effective)
reconcile run --max-batch-size 8 --verbose

# Use smaller batches for complex conflicts
reconcile run --max-batch-size 2 --model gpt-4
```

#### Development and Debugging
```bash
# Debug mode with detailed logging
reconcile run --verbose --json-logs

# Check logs
tail -f .reconcile/reconcile.jsonl | jq '.'

# Dry-run with configuration preview
reconcile run --dry-run --verbose
```

---

## 🔍 Advanced Features

### 📊 **Batch Processing**

Reconcile AI can process multiple conflicts in a single API call:

```python
# Automatically batches conflicts for efficiency
reconcile run  # Uses config max_batch_size

# Override batch size
reconcile run --max-batch-size 8
```

**Benefits:**
- ⚡ **80% faster** processing for multiple conflicts
- 💰 **Reduced API costs** through batch requests
- 🧠 **Better context awareness** across related conflicts
- 🔄 **Automatic fallback** to individual resolution if batch fails

### 📈 **Performance Monitoring**

Track AI resolution performance with structured logging:

```bash
# Enable JSON logging
reconcile run --json-logs

# Analyze performance
cat .reconcile/reconcile.jsonl | jq '.latency_seconds' | awk '{sum+=$1; count++} END {print "Avg:", sum/count "s"}'

# Token usage analysis
cat .reconcile/reconcile.jsonl | jq '.tokens_used' | awk '{sum+=$1; count++} END {print "Total tokens:", sum}'
```

### 🔒 **Enterprise Security**

**Safe Hook Management:**
- Automatic backup of existing hooks
- Interactive restoration during uninstallation
- Verification of hook ownership before removal

**API Key Security:**
- Environment variable-based configuration
- No API keys stored in configuration files
- Clear error messages for missing credentials

---

## 🏢 Enterprise Workflows

### CI/CD Integration

#### GitHub Actions
```yaml
name: AI Conflict Resolution
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  resolve-conflicts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install Reconcile AI
        run: pip install reconcile-ai
      
      - name: Check for conflicts
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          git config user.name "AI Bot"
          git config user.email "bot@company.com"
          reconcile run --dry-run --json-logs
```

#### Jenkins Pipeline
```groovy
pipeline {
    agent any
    environment {
        OPENAI_API_KEY = credentials('openai-api-key')
    }
    stages {
        stage('Resolve Conflicts') {
            steps {
                sh 'pip install reconcile-ai'
                sh 'reconcile run --verbose --json-logs'
                archiveArtifacts artifacts: '.reconcile/*.jsonl', allowEmptyArchive: true
            }
        }
    }
}
```

### Team Standards

#### Code Review Integration
```bash
# Pre-commit hook for conflict prevention
reconcile install --hook pre-commit

# Pre-push hook for final validation
reconcile install --hook pre-push
```

#### Monitoring and Analytics
```bash
# Aggregate team metrics
find . -name "reconcile.jsonl" -exec cat {} \; | \
  jq -s 'group_by(.level) | map({level: .[0].level, count: length})'

# Resolution success rate
cat .reconcile/reconcile.jsonl | \
  jq 'select(.message | contains("Successfully resolved")) | .tokens_used' | \
  awk '{sum+=$1; count++} END {print "Success rate:", count " resolutions"}'
```

---

## 🤝 Development & Contributing

### Local Development Setup

```bash
# Clone and setup
git clone https://github.com/yourusername/reconcile-ai.git
cd reconcile-ai

# Install in development mode
pip install -e ".[dev,yaml]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/ -v

# Run linting
black src/ tests/
flake8 src/ tests/
mypy src/
```

### Running Tests

```bash
# Unit tests
pytest tests/test_reconcile.py -v

# Integration tests (requires Git)
pytest tests/test_integration.py -v

# Hook installation tests
pytest tests/test_hooks.py -v

# All tests with coverage
pytest --cov=reconcile --cov-report=html
```

### Project Structure

```
reconcile-ai/
├── src/reconcile/
│   └── __init__.py          # Main application
├── tests/
│   ├── test_reconcile.py    # Unit tests
│   ├── test_integration.py  # Integration tests
│   └── conftest.py          # Test configuration
├── .github/workflows/
│   └── ci.yml               # GitHub Actions CI
├── pyproject.toml           # Package configuration
├── reconcile.yaml           # Example configuration
└── README.md               # This file
```

---

## 📊 Performance & Costs

### Batch Processing Benefits

| Conflicts | Individual Calls | Batch Calls | Time Saved | Cost Saved |
|-----------|------------------|-------------|------------|------------|
| 5         | 5 calls          | 1 call      | ~80%       | ~60%       |
| 10        | 10 calls         | 2 calls     | ~80%       | ~60%       |
| 20        | 20 calls         | 4 calls     | ~80%       | ~60%       |

### Token Usage Optimization

- **Smart Prompting**: Minimal context with maximum clarity
- **Conflict Grouping**: Related conflicts processed together
- **Model Selection**: Automatic model selection based on complexity
- **Caching**: Avoid re-processing identical conflicts

---

## ❓ FAQ

### **Q: Is my code sent to OpenAI?**
A: Yes, conflict sections are sent to OpenAI's API for resolution. Review their [data usage policy](https://openai.com/policies/privacy-policy). Use `--dry-run` to see conflicts without sending data.

### **Q: What happens if the AI resolution is wrong?**
A: Always review resolved conflicts before committing. Reconcile stages files but doesn't commit automatically. Use `git diff --cached` to review changes.

### **Q: Can I use other AI models besides OpenAI?**
A: Currently, only OpenAI models are supported. Support for other providers (Anthropic, local models) is planned for future releases.

### **Q: Does this work with large files?**
A: Yes, but very large conflicts may hit API token limits. Use smaller `max_batch_size` for complex conflicts.

### **Q: How do I uninstall hooks safely?**
A: Use `reconcile uninstall --hook <type>`. It will show available backups and offer to restore your previous hooks.

### **Q: Can I customize the AI prompts?**
A: Yes! Use the `custom_prompt` field in `reconcile.yaml` for file-type specific prompts.

---

## 📄 License

This project is licensed under the Apache-2.0 License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **OpenAI** for providing the GPT models that power conflict resolution
- **GitPython** for Git repository interaction
- **PyYAML** for configuration file support
- The open-source community for inspiration and contributions

---

## 🔗 Links

- **Documentation**: [Full Documentation](https://github.com/kailashchanel/reconcile-ai/wiki)
- **Issues**: [Bug Reports & Feature Requests](https://github.com/kailashchanel/reconcile-ai/issues)
- **Discussions**: [Community Discussion](https://github.com/kailashchanel/reconcile-ai/discussions)
- **PyPI Package**: [reconcile-ai](https://pypi.org/project/reconcile-ai/)

---

<div align="center">

**Made with ❤️ for developers who hate merge conflicts**

[⭐ Star this project](https://github.com/kailashchanel/reconcile-ai) | [🐛 Report Issues](https://github.com/kailashchanel/reconcile-ai/issues) | [💬 Join Discussion](https://github.com/kailashchanel/reconcile-ai/discussions)

</div> 