import argparse
import subprocess
import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_command(command, cwd=None):
    """Run a shell command and return output."""
    try:
        logging.info(f"Running: {command}")
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.stdout:
            logging.info(result.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {e.stderr.strip()}")
        return False

def git_restore_hard():
    """Reset to HEAD and remove untracked files."""
    logging.warning("Performing HARD restore. All local changes and untracked files will be lost.")
    # git reset --hard HEAD: Resets the index and working tree. Any changes to tracked files are discarded.
    if run_command("git reset --hard HEAD"):
        # git clean -fd: Removes untracked files (-f) and directories (-d).
        return run_command("git clean -fd")
    return False

def git_restore_soft():
    """Restore modified files but keep untracked files."""
    logging.info("Performing SOFT restore. Modified files will be reverted, untracked files preserved.")
    return run_command("git restore .")

def git_checkout(target):
    """Checkout a specific commit or branch."""
    logging.info(f"Checking out: {target}")
    return run_command(f"git checkout {target}")

def main():
    parser = argparse.ArgumentParser(description="Astromech Restoration Utility")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Hard restore
    subparsers.add_parser("hard", help="Reset to HEAD, deleting all changes and untracked files")

    # Soft restore
    subparsers.add_parser("soft", help="Discard local modifications, keep untracked files")

    # Checkout
    checkout_parser = subparsers.add_parser("checkout", help="Checkout a specific commit/branch")
    checkout_parser.add_argument("target", help="Commit hash or branch name")

    args = parser.parse_args()

    success = False
    if args.command == "hard":
        success = git_restore_hard()
    elif args.command == "soft":
        success = git_restore_soft()
    elif args.command == "checkout":
        success = git_checkout(args.target)
    else:
        parser.print_help()
        sys.exit(1)

    if success:
        logging.info("Restoration completed successfully.")
    else:
        logging.error("Restoration failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
