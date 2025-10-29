#!/usr/bin/env python3
"""
Claude Code - Environment Setup Script
"""

import os
import platform
import subprocess
import urllib.request
import urllib.error
import json
from pathlib import Path
from typing import Tuple, Optional, Dict


def get_shell_rc_file() -> Path:
    """
    Determine the appropriate shell configuration file based on the OS and shell.
    
    Returns:
        Path: Path to the shell configuration file
    """
    system = platform.system().lower()
    shell = os.environ.get("SHELL", "").lower()
    
    if system == "darwin":
        # macOS - default shell is zsh
        if "zsh" in shell:
            return Path.home() / ".zprofile"
        else:
            return Path.home() / ".bash_profile"
    
    elif system == "linux":
        # Linux
        if "zsh" in shell:
            return Path.home() / ".zshrc"
        else:
            return Path.home() / ".bashrc"
    
    elif system == "windows":
        # Windows - uses registry, no rc file
        return None
    
    else:
        raise OSError(f"Unsupported operating system: {system}")


def append_to_file(file_path: Path, line: str) -> bool:
    """
    Append a line to a file only if it's not already present.
    
    Args:
        file_path: Path to the file to append to
        line: Line to append (without newline)
    
    Returns:
        bool: True if line was added, False if it already existed
    """
    try:
        file_path.touch(exist_ok=True)
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if line not in content:
            # Check if we need to add the header comment
            has_header = "# Claude Code Configuration" in content
            
            with open(file_path, "a", encoding="utf-8") as f:
                if not has_header:
                    f.write(f"\n# Claude Code Configuration\n")
                f.write(f"{line}\n")
            return True
        else:
            return False
    except Exception as e:
        print(f"❌ Failed to modify {file_path}: {e}")
        return False


def set_env_var_on_windows(var_name: str, value: str) -> bool:
    """
    Set environment variable permanently on Windows using setx.
    
    Args:
        var_name: Name of the environment variable
        value: Value to set
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        subprocess.run(["setx", var_name, value], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to set {var_name} on Windows: {e}")
        if e.stderr:
            print(f"   Error details: {e.stderr.decode()}")
        return False
    except FileNotFoundError:
        print(f"❌ 'setx' command not found. Please set {var_name} manually.")
        return False


def set_env_var_on_unix(var_name: str, value: str) -> bool:
    """
    Set environment variable permanently on Unix-like systems (macOS, Linux).
    
    Args:
        var_name: Name of the environment variable
        value: Value to set
    
    Returns:
        bool: True if successful, False otherwise
    """
    rc_file = get_shell_rc_file()
    if rc_file is None:
        return False
    
    export_line = f'export {var_name}="{value}"'
    
    was_added = append_to_file(rc_file, export_line)
    
    if was_added:
        print(f"✅ Added {var_name} to {rc_file}")
        return True
    else:
        print(f"ℹ️  {var_name} already configured in {rc_file}")
        return True


def set_env_var_forever(var_name: str, value: str) -> Tuple[bool, str]:
    """
    Set an environment variable permanently across all OS platforms.
    
    Args:
        var_name: Name of the environment variable
        value: Value to set
    
    Returns:
        Tuple[bool, str]: (success, message)
    """
    system = platform.system().lower()
    
    if system == "windows":
        success = set_env_var_on_windows(var_name, value)
        if success:
            return True, "Environment variable set for new terminals"
        else:
            return False, "Failed to set environment variable"
    
    elif system in ["darwin", "linux"]:
        success = set_env_var_on_unix(var_name, value)
        if success:
            shell_name = "zsh" if "zsh" in os.environ.get("SHELL", "") else "bash"
            return True, f"Run 'source ~/.{shell_name}rc' or restart terminal"
        else:
            return False, "Failed to set environment variable"
    
    else:
        return False, f"Unsupported OS: {system}"


def prompt_for_var(var_name: str, description: str, required: bool = True) -> Optional[str]:
    """
    Prompt user for an environment variable value.
    
    Args:
        var_name: Name of the variable
        description: Description to show the user
        required: Whether the variable is required
    
    Returns:
        The value entered by the user, or None if skipped
    """
    prompt = f"\nEnter {description}"
    if not required:
        prompt += " (optional, press Enter to skip)"
    prompt += ": "
    
    value = input(prompt).strip()
    
    if required and not value:
        print(f"❌ {var_name} is required.")
        return None
    
    return value if value else None


def prompt_yes_no(question: str, default: bool = True) -> bool:
    """
    Prompt user for a yes/no question.
    
    Args:
        question: Question to ask
        default: Default value if user just presses Enter
    
    Returns:
        True if yes, False if no
    """
    default_text = "Y/n" if default else "y/N"
    response = input(f"{question} ({default_text}): ").strip().lower()
    
    if not response:
        return default
    
    return response in ["y", "yes"]


def verify_api_key(api_key: str) -> bool:
    """
    Verify the API key by making a request to the /models endpoint.
    
    Args:
        api_key: The API key to verify
    
    Returns:
        True if valid, False otherwise
    """
    if not api_key or len(api_key) == 0:
        print("❌ API key is empty")
        return False
    
    try:
        url = "https://api.getunbound.ai/v1/models"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        request = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                
                # Check if response has data (models)
                if data and isinstance(data, dict) and "data" in data:
                    if isinstance(data["data"], list) and len(data["data"]) > 0:
                        return True
                # Also check if data is a list directly
                elif data and isinstance(data, list) and len(data) > 0:
                    return True
                # Or if it's an object
                elif data and isinstance(data, dict):
                    return True
                
                return False
            else:
                print(f"❌ API key verification failed: {response.status}")
                return False
                
    except urllib.error.HTTPError as e:
        print(f"❌ API key verification failed: {e.code} {e.reason}")
        try:
            error_data = json.loads(e.read().decode())
            if "error" in error_data and "message" in error_data["error"]:
                print(f"   Error: {error_data['error']['message']}")
        except:
            pass
        return False
    except Exception as e:
        print(f"❌ API key verification failed: {e}")
        return False


def prompt_vertex_configuration() -> Dict[str, any]:
    """
    Prompt user for Vertex AI configuration.
    
    Returns:
        Dictionary with useVertex, model, and smallModel keys
    """
    print("\n" + "─" * 60)
    print("🔄 Vertex AI Configuration")
    print("─" * 60)
    
    use_vertex = prompt_yes_no("Do you want to use Vertex AI models?", default=False)
    
    if not use_vertex:
        return {"useVertex": False}
    
    print("\n📝 Vertex AI Model Configuration:")
    print("Default models:")
    print("  • Primary model: claude-sonnet-4-5@20250929")
    print("  • Small/fast model: claude-3-5-haiku@20241022")
    print("")
    
    use_defaults = prompt_yes_no("Would you like to proceed with the default models?", default=True)
    
    primary_model = "anthropic.claude-sonnet-4-5@20250929"
    small_model = "anthropic.claude-3-5-haiku@20241022"
    
    if not use_defaults:
        print("\n📝 Enter custom Vertex AI model IDs:")
        
        custom_primary = input(f"Primary model (default: {primary_model}): ").strip()
        if custom_primary:
            primary_model = custom_primary
        
        custom_small = input(f"Small/fast model (default: {small_model}): ").strip()
        if custom_small:
            small_model = custom_small
    
    return {
        "useVertex": True,
        "model": primary_model,
        "smallModel": small_model
    }


def main():
    """Main setup function."""
    print("=" * 60)
    print("Claude Code - Environment Setup")
    print("=" * 60)
    
    api_key = None
    
    while True:
        api_key = prompt_for_var(
            "UNBOUND_API_KEY",
            "Unbound API Key",
            required=True
        )
        
        if not api_key:
            print("\n❌ API key is required. Exiting.")
            return
        
        # Verify the API key
        print("\nVerifying API key...")
        if verify_api_key(api_key):
            print("✅ API key verified successfully")
            break
        else:
            retry = prompt_yes_no("\nWould you like to try again?", default=True)
            if not retry:
                return
    
    # Set API key environment variable
    print("\n" + "=" * 60)
    print("Setting Environment Variables")
    print("=" * 60)
    
    success, message = set_env_var_forever("UNBOUND_API_KEY", api_key)
    if success:
        print(f"✅ UNBOUND_API_KEY configured successfully")
    else:
        print(f"❌ Failed to configure UNBOUND_API_KEY: {message}")
        return
    
    # Prompt for Vertex configuration
    vertex_config = prompt_vertex_configuration()
    
    # Set additional environment variables based on configuration
    if vertex_config.get("useVertex"):
        # Vertex AI configuration
        print("\nSetting Vertex AI environment variables...")
        
        env_vars = {
            "ANTHROPIC_MODEL": vertex_config.get("model", "anthropic.claude-sonnet-4-5@20250929"),
            "ANTHROPIC_SMALL_FAST_MODEL": vertex_config.get("smallModel", "anthropic.claude-3-5-haiku@20241022")
        }
        
        for var_name, value in env_vars.items():
            success, message = set_env_var_forever(var_name, value)
            if success:
                print(f"✅ {var_name} configured")
            else:
                print(f"⚠️  {var_name}: {message}")
    else:
        # Standard Unbound proxy configuration
        print("\nSetting standard Unbound configuration...")
        
        success, message = set_env_var_forever("ANTHROPIC_BASE_URL", "https://api.getunbound.ai")
        if success:
            print(f"✅ ANTHROPIC_BASE_URL configured")
        else:
            print(f"⚠️  ANTHROPIC_BASE_URL: {message}")
    
    # Final instructions
    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    
    system = platform.system().lower()
    if system in ["darwin", "linux"]:
        shell_name = "zsh" if "zsh" in os.environ.get("SHELL", "") else "bash"
        rc_file = ".zshrc" if shell_name == "zsh" else ".bashrc"
        
        print(f"\nTo apply the changes in your current terminal:")
        print(f"  source ~/{rc_file}")
        print(f"\nOr simply open a new terminal window.")
    else:
        print("\nTo apply the changes:")
        print("  Close and reopen your terminal/command prompt")
    
    print("\n" + "=" * 60)
    print("Next Steps:")
    print("=" * 60)
    print("\n1. Reload your terminal configuration (see above)")
    print("2. Start using Claude Code with: claude")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user.")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        exit(1)

