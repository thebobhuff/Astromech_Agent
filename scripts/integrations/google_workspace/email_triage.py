import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
GMAIL_TOOL = REPO_ROOT / "app" / "skills" / "google-workspace" / "scripts" / "gmail_tool.py"


def run_gmail_tool(args: list[str]) -> str | None:
    """Helper to run the gmail_tool.py script."""
    command = ["python", str(GMAIL_TOOL)] + args
    result = subprocess.run(command, capture_output=True, text=True, check=False, cwd=str(REPO_ROOT))
    if result.returncode != 0:
        print(f"Error running gmail_tool: {result.stderr}")
        return None
    return result.stdout


def triage_emails() -> str:
    summary: list[str] = []
    marked_as_read_count = 0
    important_emails_found: list[dict[str, str]] = []

    list_output = run_gmail_tool(["list", "--unread"])
    if list_output is None:
        return "Failed to list unread emails."

    try:
        emails = json.loads(list_output)
    except json.JSONDecodeError:
        return f"Failed to parse email list output: {list_output}"

    if not emails:
        print("No unread emails to triage.")
        return "No unread emails to triage."

    for email in emails:
        message_id = email.get("id")
        sender = email.get("from")
        subject = email.get("subject", "")
        snippet = email.get("snippet", "")

        is_important = any(
            keyword in subject.lower() or keyword in snippet.lower()
            for keyword in ["recruiter", "job", "opportunity", "lead", "business", "interview"]
        )

        if is_important:
            response_subject = f"Re: {subject}"
            sender_name = sender.split("<")[0].strip() if "<" in sender else sender
            response_body = (
                f"Dear {sender_name},\n\n"
                "Thank you for reaching out. I appreciate you considering me for this opportunity.\n"
                "I will review the details and get back to you shortly.\n\n"
                "Best regards,\n"
                "Your Assistant"
            )

            response_body_escaped = response_body.replace("'", "'\\''")
            draft_output = run_gmail_tool(
                ["draft", "--to", sender, "--subject", response_subject, "--body", response_body_escaped]
            )
            if draft_output:
                important_emails_found.append(
                    {
                        "subject": subject,
                        "sender": sender,
                        "draft_response_subject": response_subject,
                        "draft_response_body": response_body,
                    }
                )
            else:
                summary.append(
                    f"Failed to draft response for email from {sender} with subject '{subject}'."
                )
        else:
            mark_read_output = run_gmail_tool(["mark_read", "--id", message_id])
            if mark_read_output:
                marked_as_read_count += 1
            else:
                summary.append(f"Failed to mark email '{subject}' as read.")

    summary_text = "Email Triage Summary:\n\n"
    if important_emails_found:
        summary_text += "Important Emails Found and Responses Drafted:\n"
        for email_info in important_emails_found:
            summary_text += (
                f"- Subject: {email_info['subject']}\n"
                f"  From: {email_info['sender']}\n"
                f"  Drafted Response Subject: {email_info['draft_response_subject']}\n"
                "  Drafted Response Body:\n"
                "'''\n"
                f"{email_info['draft_response_body']}\n"
                "'''\n\n"
            )
    else:
        summary_text += "No important emails (recruiter/lead) found.\n\n"

    summary_text += f"Total non-critical messages marked as read: {marked_as_read_count}\n"

    print(summary_text)
    return summary_text


if __name__ == "__main__":
    triage_emails()
