from google_auth_oauthlib.flow import InstalledAppFlow
import sys
from pathlib import Path

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.metadata.readonly'
]

REPO_ROOT = Path(__file__).resolve().parents[3]
CREDENTIALS_PATH = REPO_ROOT / "credentials.json"
TOKEN_PATH = REPO_ROOT / "token.json"


def generate_token(auth_code):
    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
        flow.redirect_uri = 'http://localhost:8080/'
        flow.fetch_token(code=auth_code)
        creds = flow.credentials

        with open(TOKEN_PATH, 'w') as token_file:
            token_file.write(creds.to_json())
        print(f"SUCCESS: token generated at {TOKEN_PATH}.")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        generate_token(sys.argv[1])
    else:
        print("Usage: python scripts/integrations/google_workspace/gen_token.py <AUTH_CODE>")
