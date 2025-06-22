#!/usr/bin/env python3
# Copyright 2025 Kailash Elumalai
# Licensed under the Apache License, Version 2.0:
#   http://www.apache.org/licenses/LICENSE-2.0

"""
Reconcile: AI-powered headless merge conflict resolver.

Usage:
  reconcile [--dry-run] [--model MODEL] [--repo PATH]
  reconcile install [--hook pre-merge|post-merge|pre-push]

Place this script in your PATH or install via:
  pip install -e .
"""
import os
import re
import argparse
import logging
import json
import time
import hashlib
from pathlib import Path
from git import Repo
from openai import OpenAI

# Try to import yaml, fallback gracefully if not available
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Configuration: OpenAI client will be initialized when needed
client = None

def _get_openai_client():
    """Initialize OpenAI client with proper error handling."""
    global client
    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "❌ OpenAI API key not found!\n\n"
                "To use AI-powered conflict resolution, you need to:\n"
                "1. Get an API key from https://platform.openai.com/api-keys\n"
                "2. Set it as an environment variable:\n"
                "   export OPENAI_API_KEY='your-api-key-here'\n\n"
                "Alternatively, you can use the --dry-run flag to see conflicts without AI resolution."
            )
        
        # Handle test environment - if API key is a dummy test value, create a mock-compatible client
        if api_key in ['test-api-key', 'dummy-key', 'fake-key'] or api_key.startswith('test-'):
            try:
                # Try to create client anyway, but catch authentication errors gracefully
                client = OpenAI(api_key=api_key)
            except Exception:
                # If OpenAI client creation fails with test key, that's expected
                # The actual API calls will be mocked in tests
                client = OpenAI(api_key=api_key)
        else:
            client = OpenAI(api_key=api_key)
    return client


def setup_logging(verbose=False, json_logging=False):
    """Setup logging configuration with optional JSON format."""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Create logs directory if it doesn't exist
    log_dir = Path(".reconcile")
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger('reconcile')
    logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    if json_logging:
        # JSON formatter for structured logging
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    'timestamp': self.formatTime(record),
                    'level': record.levelname,
                    'message': record.getMessage(),
                    'module': record.module,
                    'function': record.funcName,
                    'line': record.lineno
                }
                
                # Add extra fields if they exist
                for key, value in record.__dict__.items():
                    if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                                 'filename', 'module', 'lineno', 'funcName', 'created', 
                                 'msecs', 'relativeCreated', 'thread', 'threadName', 
                                 'processName', 'process', 'stack_info']:
                        log_entry[key] = value
                
                return json.dumps(log_entry)
        
        # File handler for JSON logs
        file_handler = logging.FileHandler(log_dir / "reconcile.jsonl")
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)
    
    # Console handler for human-readable output
    console_handler = logging.StreamHandler()
    if verbose:
        console_format = '%(asctime)s - %(levelname)s - %(message)s'
    else:
        console_format = '%(message)s'
    
    console_handler.setFormatter(logging.Formatter(console_format))
    logger.addHandler(console_handler)
    
    return logger


def load_config(repo_path="."):
    """Load configuration from reconcile.yaml if it exists."""
    config_path = Path(repo_path) / "reconcile.yaml"
    default_config = {
        'model': 'gpt-4',
        'max_batch_size': 5,
        'branch_preference': None,
        'temperature': 0,
        'timeout': 30,
        'preserve_whitespace': True
    }
    
    if not config_path.exists():
        return default_config
    
    if not HAS_YAML:
        logging.getLogger('reconcile').warning(
            f"Found {config_path} but PyYAML not installed. Install with: pip install PyYAML"
        )
        return default_config
    
    try:
        with open(config_path, 'r') as f:
            user_config = yaml.safe_load(f) or {}
        
        # Merge with defaults
        config = {**default_config, **user_config}
        
        logging.getLogger('reconcile').info(
            f"Loaded configuration from {config_path}",
            extra={'config_file': str(config_path), 'config': config}
        )
        
        return config
    
    except Exception as e:
        logging.getLogger('reconcile').error(
            f"Failed to load config from {config_path}: {e}",
            extra={'config_file': str(config_path), 'error': str(e)}
        )
        return default_config


def get_hunk_hash(section):
    """Generate a hash for a conflict section for logging/tracking."""
    return hashlib.md5(section.encode('utf-8')).hexdigest()[:8]


def detect_conflicts(repo_path="."):
    """
    Detects merge conflicts in the given Git repository.
    Returns a dict of file paths to unmerged blob stages or None.
    """
    logger = logging.getLogger('reconcile')
    logger.debug(f"Detecting conflicts in repository: {repo_path}")
    
    repo = Repo(repo_path)
    unmerged = repo.index.unmerged_blobs()
    
    if unmerged:
        logger.info(
            f"Found conflicts in {len(unmerged)} file(s)",
            extra={'conflict_files': list(unmerged.keys()), 'repo_path': repo_path}
        )
    else:
        logger.info("No merge conflicts detected", extra={'repo_path': repo_path})
    
    return unmerged if unmerged else None


def parse_conflicts(conflict_blobs, repo_path="."):
    """
    Parses conflict markers in files and extracts conflict sections.
    Returns a mapping: file_path -> list of conflict section strings.
    """
    logger = logging.getLogger('reconcile')
    conflicts = {}
    
    for path in conflict_blobs:
        full_path = os.path.join(repo_path, path) if not os.path.isabs(path) else path
        try:
            with open(full_path, 'r') as f:
                content = f.read()
            sections = re.findall(
                r"(<<<<<<< HEAD.*?=======.*?>>>>>>> [^\n]*)",
                content,
                flags=re.DOTALL
            )
            if sections:
                conflicts[path] = sections
                logger.debug(
                    f"Parsed {len(sections)} conflict section(s) in {path}",
                    extra={
                        'file_path': path,
                        'conflict_count': len(sections),
                        'section_hashes': [get_hunk_hash(s) for s in sections]
                    }
                )
        except Exception as e:
            logger.error(
                f"Failed to parse conflicts in {path}: {e}",
                extra={'file_path': path, 'error': str(e)}
            )
    
    return conflicts


def resolve_conflict_sections_batch(sections, model="gpt-4", max_batch_size=5):
    """
    Resolves multiple conflict sections efficiently using batching.
    
    Args:
        sections: List of conflict section strings to resolve
        model: LLM model to use for resolution
        max_batch_size: Maximum number of conflicts to resolve in one API call
        
    Returns:
        List of resolved sections in the same order as input
    """
    if not sections:
        return []
    
    logger = logging.getLogger('reconcile')
    all_resolutions = []
    
    # Process in batches
    for i in range(0, len(sections), max_batch_size):
        batch = sections[i:i + max_batch_size]
        batch_num = (i // max_batch_size) + 1
        total_batches = (len(sections) + max_batch_size - 1) // max_batch_size
        
        logger.info(
            f"Processing batch {batch_num}/{total_batches} ({len(batch)} conflicts)",
            extra={
                'batch_number': batch_num,
                'total_batches': total_batches,
                'batch_size': len(batch)
            }
        )
        
        batch_resolutions = _resolve_batch(batch, model)
        all_resolutions.extend(batch_resolutions)
    
    return all_resolutions


def resolve_conflict_section_single(section, model="gpt-4"):
    """
    Resolves a single conflict section using the OpenAI API.
    
    Args:
        section: The conflict section string including <<<<<<< HEAD, =======, >>>>>>> markers
        model: The OpenAI model to use for resolution
        
    Returns:
        The resolved code section without conflict markers
    """
    logger = logging.getLogger('reconcile')
    section_hash = get_hunk_hash(section)
    
    logger.debug(
        f"Resolving individual conflict section {section_hash}",
        extra={'section_hash': section_hash, 'model': model}
    )
    
    try:
        client = _get_openai_client()
        
        prompt = f"""Please resolve this Git merge conflict by providing clean, working code without any conflict markers.

The conflict shows two different versions of the code:
- The HEAD version (current branch)  
- The feature branch version

Please analyze both versions and provide the best merged result that:
1. Preserves the intent of both changes when possible
2. Removes all conflict markers (<<<<<<< HEAD, =======, >>>>>>> branch)
3. Results in syntactically correct, working code
4. Follows the coding style and patterns evident in the code

Conflict to resolve:
```
{section}
```

Please respond with ONLY the resolved code, no explanations or markdown formatting."""

        start_time = time.time()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant specialized in resolving Git merge conflicts."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        
        latency = time.time() - start_time
        resolved = response.choices[0].message.content.strip()
        
        logger.info(
            f"Successfully resolved conflict section {section_hash}",
            extra={
                'section_hash': section_hash,
                'model': model,
                'latency_seconds': round(latency, 2),
                'tokens_used': getattr(response.usage, 'total_tokens', None)
            }
        )
        
        return resolved
        
    except Exception as e:
        logger.error(
            f"Failed to resolve conflict section {section_hash}: {e}",
            extra={'section_hash': section_hash, 'model': model, 'error': str(e)}
        )
        # Return the original section as fallback
        return section


def _resolve_batch(sections, model="gpt-4"):
    """
    Internal function to resolve a batch of conflict sections in a single API call.
    
    Args:
        sections: List of conflict sections to resolve
        model: LLM model to use
        
    Returns:
        List of resolved sections
    """
    logger = logging.getLogger('reconcile')
    section_hashes = [get_hunk_hash(s) for s in sections]
    
    logger.debug(
        f"Resolving batch of {len(sections)} conflicts",
        extra={'batch_size': len(sections), 'section_hashes': section_hashes, 'model': model}
    )
    
    try:
        client = _get_openai_client()
        
        # Create batch prompt with clear separators
        batch_prompt = """Please resolve these Git merge conflicts by providing clean, working code without any conflict markers.

For each conflict, analyze both versions and provide the best merged result that:
1. Preserves the intent of both changes when possible
2. Removes all conflict markers (<<<<<<< HEAD, =======, >>>>>>> branch)
3. Results in syntactically correct, working code
4. Follows the coding style and patterns evident in the code

Please respond with each resolution numbered and clearly separated like this:

RESOLUTION 1:
[resolved code for conflict 1]

RESOLUTION 2:
[resolved code for conflict 2]

And so on...

Here are the conflicts to resolve:

"""
        
        for i, section in enumerate(sections, 1):
            batch_prompt += f"\n=== CONFLICT {i} ===\n{section}\n"
        
        start_time = time.time()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant specialized in resolving Git merge conflicts."},
                {"role": "user", "content": batch_prompt}
            ],
            temperature=0
        )
        
        latency = time.time() - start_time
        response_text = response.choices[0].message.content.strip()
        
        logger.info(
            f"Successfully resolved batch of {len(sections)} conflicts",
            extra={
                'batch_size': len(sections),
                'section_hashes': section_hashes,
                'model': model,
                'latency_seconds': round(latency, 2),
                'tokens_used': getattr(response.usage, 'total_tokens', None)
            }
        )
        
        return _parse_batch_response(response_text, len(sections))
        
    except Exception as e:
        latency = time.time() - start_time
        logger.warning(
            f"Batch resolution failed ({e}), falling back to individual resolution",
            extra={
                'batch_size': len(sections),
                'section_hashes': section_hashes,
                'model': model,
                'latency_seconds': round(latency, 2),
                'error': str(e)
            }
        )
        # Fallback to individual resolution
        return [resolve_conflict_section_single(section, model) for section in sections]


def _parse_batch_response(response_text, expected_count):
    """
    Parses the LLM's numbered response into individual resolutions.
    
    Args:
        response_text: The full LLM response
        expected_count: Number of resolutions expected
    
    Returns:
        List of resolved sections
    
    Raises:
        ValueError: If parsing fails or count doesn't match
    """
    # Pattern to match RESOLUTION N: followed by content
    pattern = r'RESOLUTION\s+(\d+):\s*\n(.*?)(?=\nRESOLUTION\s+\d+:|$)'
    matches = re.findall(pattern, response_text, re.DOTALL | re.IGNORECASE)
    
    if not matches:
        # Try alternative parsing - look for numbered blocks
        pattern = r'(\d+)[:.]\s*\n(.*?)(?=\n\d+[:.]\s*|$)'
        matches = re.findall(pattern, response_text, re.DOTALL)
        
        if not matches:
            raise ValueError(f"Could not parse LLM response into numbered resolutions. Response: {response_text[:200]}...")
    
    # Sort by resolution number and extract content
    resolutions = {}
    for num_str, content in matches:
        num = int(num_str)
        if num < 1 or num > expected_count:
            raise ValueError(f"Resolution number {num} is out of range (expected 1-{expected_count})")
        
        # Clean up the content
        cleaned_content = content.strip()
        # Remove any markdown code block markers if present
        if cleaned_content.startswith('```') and cleaned_content.endswith('```'):
            lines = cleaned_content.split('\n')
            if len(lines) > 2:
                # Remove first and last lines (the ``` markers)
                cleaned_content = '\n'.join(lines[1:-1])
        
        resolutions[num] = cleaned_content
    
    # Verify we have all expected resolutions
    if len(resolutions) != expected_count:
        missing = set(range(1, expected_count + 1)) - set(resolutions.keys())
        raise ValueError(f"Missing resolutions for numbers: {missing}. Got {len(resolutions)}, expected {expected_count}")
    
    # Return in order
    return [resolutions[i] for i in range(1, expected_count + 1)]


# Backward compatibility alias
def resolve_conflict_section(section, model="gpt-4"):
    """
    Legacy function for resolving a single conflict section.
    Maintained for backward compatibility.
    """
    return resolve_conflict_section_single(section, model)


def apply_resolutions(path, original_content, resolved_map):
    """
    Replaces each conflict section in the file with its resolved code,
    writes the updated content back, and stages the file.
    """
    logger = logging.getLogger('reconcile')
    
    updated = original_content
    for section, resolved in resolved_map.items():
        updated = updated.replace(section, resolved)
    
    with open(path, 'w') as f:
        f.write(updated)
    
    logger.info(
        f"Applied {len(resolved_map)} resolution(s) to {path}",
        extra={
            'file_path': path,
            'resolutions_applied': len(resolved_map),
            'section_hashes': [get_hunk_hash(s) for s in resolved_map.keys()]
        }
    )


def install_hook(hook_type, script_path):
    """
    Installs this script as a Git hook of the given type in the current repo.
    Backs up any existing hook before installation.
    """
    logger = logging.getLogger('reconcile')
    
    # Ensure we're in a Git repository
    if not os.path.isdir('.git'):
        error_msg = "❌ Not in a Git repository. Please run this command from the root of a Git repository."
        logger.error(error_msg, extra={'error_type': 'not_git_repo'})
        print(error_msg)
        return False
    
    hook_dir = os.path.join(os.getcwd(), '.git', 'hooks')
    target = os.path.join(hook_dir, hook_type)
    backup_path = f"{target}.bak"
    
    # Create hooks directory if it doesn't exist
    os.makedirs(hook_dir, exist_ok=True)
    
    # Check if hook already exists
    if os.path.exists(target):
        if os.path.islink(target):
            # It's a symlink, check if it's already pointing to reconcile
            current_target = os.readlink(target)
            if 'reconcile' in current_target.lower() or script_path in current_target:
                print(f"✅ Reconcile {hook_type} hook is already installed at {target}")
                logger.info(
                    f"Hook already installed",
                    extra={'hook_type': hook_type, 'target': target, 'existing_target': current_target}
                )
                return True
        
        # Back up existing hook
        backup_counter = 1
        final_backup_path = backup_path
        while os.path.exists(final_backup_path):
            final_backup_path = f"{backup_path}.{backup_counter}"
            backup_counter += 1
        
        try:
            if os.path.islink(target):
                # Copy the symlink target content if it's a symlink
                link_target = os.readlink(target)
                with open(link_target, 'r') as src, open(final_backup_path, 'w') as dst:
                    dst.write(src.read())
                os.chmod(final_backup_path, 0o755)
            else:
                # Copy regular file
                import shutil
                shutil.copy2(target, final_backup_path)
            
            print(f"📁 Backed up existing {hook_type} hook to {final_backup_path}")
            logger.info(
                f"Backed up existing hook",
                extra={'hook_type': hook_type, 'backup_path': final_backup_path, 'original': target}
            )
        except Exception as e:
            error_msg = f"❌ Failed to backup existing hook: {e}"
            logger.error(error_msg, extra={'hook_type': hook_type, 'error': str(e)})
            print(error_msg)
            return False
        
        # Remove existing hook
        try:
            os.remove(target)
        except Exception as e:
            error_msg = f"❌ Failed to remove existing hook: {e}"
            logger.error(error_msg, extra={'hook_type': hook_type, 'error': str(e)})
            print(error_msg)
            return False
    
    # Install new hook
    try:
        os.symlink(script_path, target)
        os.chmod(target, 0o755)
        
        print(f"🎉 Installed Reconcile {hook_type} hook at {target}")
        print(f"🔗 Hook points to: {script_path}")
        
        logger.info(
            f"Successfully installed hook",
            extra={
                'hook_type': hook_type,
                'target': target,
                'script_path': script_path,
                'permissions': '755'
            }
        )
        
        # Provide usage information
        if hook_type == 'post-merge':
            print("💡 This hook will run automatically after 'git merge' operations")
        elif hook_type == 'pre-push':
            print("💡 This hook will run before 'git push' operations")
        elif hook_type == 'pre-commit':
            print("💡 This hook will run before each commit")
        elif hook_type == 'pre-merge':
            print("💡 This hook will run before 'git merge' operations")
        
        return True
        
    except Exception as e:
        error_msg = f"❌ Failed to install {hook_type} hook: {e}"
        logger.error(error_msg, extra={'hook_type': hook_type, 'error': str(e)})
        print(error_msg)
        return False


def uninstall_hook(hook_type):
    """
    Uninstalls the Reconcile Git hook and optionally restores backup.
    """
    logger = logging.getLogger('reconcile')
    
    # Ensure we're in a Git repository
    if not os.path.isdir('.git'):
        error_msg = "❌ Not in a Git repository. Please run this command from the root of a Git repository."
        logger.error(error_msg, extra={'error_type': 'not_git_repo'})
        print(error_msg)
        return False
    
    hook_dir = os.path.join(os.getcwd(), '.git', 'hooks')
    target = os.path.join(hook_dir, hook_type)
    backup_path = f"{target}.bak"
    
    # Check if hook exists
    if not os.path.exists(target):
        print(f"ℹ️  No {hook_type} hook found at {target}")
        logger.info(f"No hook to uninstall", extra={'hook_type': hook_type, 'target': target})
        return True
    
    # Check if it's a Reconcile hook
    is_reconcile_hook = False
    if os.path.islink(target):
        link_target = os.readlink(target)
        if 'reconcile' in link_target.lower():
            is_reconcile_hook = True
    
    if not is_reconcile_hook:
        print(f"⚠️  The {hook_type} hook at {target} doesn't appear to be a Reconcile hook.")
        response = input("Do you want to remove it anyway? [y/N]: ").lower().strip()
        if response not in ['y', 'yes']:
            print("❌ Uninstall cancelled.")
            return False
    
    # Remove the hook
    try:
        os.remove(target)
        print(f"🗑️  Removed {hook_type} hook from {target}")
        logger.info(
            f"Successfully removed hook",
            extra={'hook_type': hook_type, 'target': target, 'was_reconcile_hook': is_reconcile_hook}
        )
    except Exception as e:
        error_msg = f"❌ Failed to remove {hook_type} hook: {e}"
        logger.error(error_msg, extra={'hook_type': hook_type, 'error': str(e)})
        print(error_msg)
        return False
    
    # Check for and offer to restore backup
    available_backups = []
    backup_counter = 0
    potential_backup = backup_path
    
    # Find all backup files
    while os.path.exists(potential_backup):
        available_backups.append(potential_backup)
        backup_counter += 1
        potential_backup = f"{backup_path}.{backup_counter}"
    
    if available_backups:
        print(f"🔍 Found {len(available_backups)} backup(s):")
        for i, backup in enumerate(available_backups):
            backup_time = os.path.getmtime(backup)
            backup_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(backup_time))
            print(f"  {i + 1}. {backup} (created: {backup_date})")
        
        print("Options:")
        print("  0. Don't restore any backup")
        for i, backup in enumerate(available_backups):
            print(f"  {i + 1}. Restore {os.path.basename(backup)}")
        
        while True:
            try:
                choice = input(f"Select an option [0-{len(available_backups)}]: ").strip()
                choice_num = int(choice)
                if choice_num == 0:
                    print("✅ Hook uninstalled successfully. No backup restored.")
                    break
                elif 1 <= choice_num <= len(available_backups):
                    selected_backup = available_backups[choice_num - 1]
                    try:
                        import shutil
                        shutil.copy2(selected_backup, target)
                        os.chmod(target, 0o755)
                        print(f"🔄 Restored backup from {selected_backup} to {target}")
                        logger.info(
                            f"Restored backup",
                            extra={'hook_type': hook_type, 'backup_restored': selected_backup, 'target': target}
                        )
                        break
                    except Exception as e:
                        error_msg = f"❌ Failed to restore backup: {e}"
                        logger.error(error_msg, extra={'backup_path': selected_backup, 'error': str(e)})
                        print(error_msg)
                        return False
                else:
                    print(f"Invalid choice. Please enter a number between 0 and {len(available_backups)}")
            except ValueError:
                print("Please enter a valid number")
            except KeyboardInterrupt:
                print("\n❌ Uninstall cancelled.")
                return False
    else:
        print("✅ Hook uninstalled successfully. No backups found.")
    
    logger.info(f"Hook uninstall completed", extra={'hook_type': hook_type})
    return True


def main():
    parser = argparse.ArgumentParser(
        prog="reconcile",
        description="AI-powered Git merge conflict resolver"
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Run command parser
    run_parser = subparsers.add_parser('run', help='Detect and auto-resolve conflicts')
    run_parser.add_argument('--repo', default='.', help='Path to the Git repo')
    run_parser.add_argument('--model', help='LLM model name (overrides config)')
    run_parser.add_argument('--dry-run', action='store_true', help='Show conflicts without AI resolution')
    run_parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    run_parser.add_argument('--json-logs', action='store_true', help='Enable structured JSON logging')
    run_parser.add_argument('--max-batch-size', type=int, help='Maximum conflicts per batch (overrides config)')

    # Install command parser
    install_parser = subparsers.add_parser('install', help='Install Git hook')
    install_parser.add_argument('--hook', choices=['pre-commit','post-merge','pre-push','pre-merge'], default='post-merge')

    # Uninstall command parser
    uninstall_parser = subparsers.add_parser('uninstall', help='Uninstall Git hook')
    uninstall_parser.add_argument('--hook', choices=['pre-commit','post-merge','pre-push','pre-merge'], default='post-merge')

    args = parser.parse_args()

    # Handle install command
    if args.command == 'install':
        install_hook(args.hook, os.path.realpath(__file__))
        return

    # Handle uninstall command
    if args.command == 'uninstall':
        uninstall_hook(args.hook)
        return

    # Default to 'run' if no command specified
    if args.command is None:
        args.command = 'run'
        args.repo = '.'
        args.model = None
        args.dry_run = False
        args.verbose = False
        args.json_logs = False
        args.max_batch_size = None

    # Setup logging
    logger = setup_logging(
        verbose=getattr(args, 'verbose', False),
        json_logging=getattr(args, 'json_logs', False)
    )

    # Load configuration
    config = load_config(args.repo)
    
    # Override config with command line arguments
    model = args.model if hasattr(args, 'model') and args.model else config['model']
    max_batch_size = (args.max_batch_size if hasattr(args, 'max_batch_size') and args.max_batch_size 
                     else config['max_batch_size'])

    logger.debug(
        f"Starting reconcile with model={model}, batch_size={max_batch_size}",
        extra={
            'model': model,
            'max_batch_size': max_batch_size,
            'repo_path': args.repo,
            'dry_run': getattr(args, 'dry_run', False)
        }
    )

    # Detect conflicts
    blobs = detect_conflicts(args.repo)
    if not blobs:
        logger.info("No merge conflicts detected.")
        return

    # Parse conflicts
    conflicts = parse_conflicts(blobs, args.repo)
    repo = Repo(args.repo)

    total_conflicts = sum(len(sections) for sections in conflicts.values())
    logger.info(
        f"Processing {total_conflicts} conflict(s) across {len(conflicts)} file(s)",
        extra={
            'total_conflicts': total_conflicts,
            'total_files': len(conflicts),
            'files': list(conflicts.keys())
        }
    )

    for path, sections in conflicts.items():
        full_path = os.path.join(args.repo, path) if not os.path.isabs(path) else path
        
        with open(full_path, 'r') as f:
            content = f.read()

        if getattr(args, 'dry_run', False):
            # Show conflicts without AI resolution
            logger.info(f"Found {len(sections)} conflict(s) in {path}")
            for i, sec in enumerate(sections, 1):
                print(f"\n--- Conflict {i} ---")
                print(sec)
        else:
            logger.info(
                f"Resolving {len(sections)} conflict(s) in {path}",
                extra={
                    'file_path': path,
                    'conflict_count': len(sections),
                    'section_hashes': [get_hunk_hash(s) for s in sections]
                }
            )
            
            # Use batched resolution for better efficiency
            try:
                resolved_sections = resolve_conflict_sections_batch(
                    sections, 
                    model=model, 
                    max_batch_size=max_batch_size
                )
                resolved_map = dict(zip(sections, resolved_sections))
            except Exception as e:
                logger.error(
                    f"Batch resolution failed for {path}: {e}",
                    extra={'file_path': path, 'error': str(e)}
                )
                logger.info("Falling back to individual resolution...")
                resolved_map = {}
                for sec in sections:
                    logger.debug(f"Resolving individual conflict...")
                    merged = resolve_conflict_section(sec, model=model)
                    resolved_map[sec] = merged

            apply_resolutions(full_path, content, resolved_map)
            repo.index.add([path])
            
            logger.info(
                f"File {path} staged for commit",
                extra={'file_path': path, 'staged': True}
            )

    if not getattr(args, 'dry_run', False):
        logger.info("All conflicts auto-resolved and staged. Please review and commit.")

if __name__ == '__main__':
    main()
