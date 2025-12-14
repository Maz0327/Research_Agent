from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]

def main():
    flow = InstalledAppFlow.from_client_secrets_file(
        "/Users/maz/Secrets/research-agent/google-oauth-client/google-oauth-client.json",
        scopes=SCOPES,
    )
    creds = flow.run_local_server(port=0, prompt="consent")
    print("\nGOOGLE_OAUTH_REFRESH_TOKEN=\n", creds.refresh_token)

if __name__ == "__main__":
    main()
