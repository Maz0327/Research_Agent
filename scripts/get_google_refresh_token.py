import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]


def main():
    secrets_path = os.getenv("GOOGLE_OAUTH_CLIENT_SECRETS_PATH")
    if not secrets_path:
        print(
            "ERROR: Set GOOGLE_OAUTH_CLIENT_SECRETS_PATH to your OAuth client JSON path.",
            file=sys.stderr,
        )
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(
        secrets_path,
        scopes=SCOPES,
    )
    creds = flow.run_local_server(port=0, prompt="consent")
    print("\nGOOGLE_OAUTH_REFRESH_TOKEN=\n", creds.refresh_token)


if __name__ == "__main__":
    main()
