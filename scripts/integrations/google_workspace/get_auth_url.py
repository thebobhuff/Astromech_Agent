from google_auth_oauthlib.flow import InstalledAppFlow
from pathlib import Path

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.metadata.readonly'
]

REPO_ROOT = Path(__file__).resolve().parents[3]
CREDENTIALS_PATH = REPO_ROOT / "credentials.json"


def get_auth_url():
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    flow.redirect_uri = 'http://localhost:8080/'
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
    print(f"AUTH_URL: {auth_url}")

if __name__ == '__main__':
    get_auth_url()
