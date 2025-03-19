import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError

class GoogleAuth:
    """
    Eine zentrale Authentifizierungsklasse für alle Google-Dienste.
    Erstellt ein gemeinsames Token mit allen benötigten Scopes und ermöglicht es,
    Clients für Gmail, YouTube, Calendar und Drive zu erhalten.
    """

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/drive.readonly"
    ]

    # Speicherpfade für Credentials & Token
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
    TOKEN_PATH = os.path.join(BASE_DIR, "global_token.pickle")

    @staticmethod
    def get_credentials():
        """
        Lädt oder erstellt ein OAuth-Token mit allen benötigten Scopes.
        Gibt eine gültige `Credentials`-Instanz zurück.
        """
        creds = None

        # 1) Prüfen, ob ein gespeichertes Token existiert
        if os.path.exists(GoogleAuth.TOKEN_PATH):
            with open(GoogleAuth.TOKEN_PATH, "rb") as token_file:
                creds = pickle.load(token_file)

        # 2) Falls Token abgelaufen oder nicht vorhanden, erneuern/neu erstellen
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    print("Token abgelaufen. Erneuere ...")
                    creds.refresh(Request())
                except RefreshError:
                    print("Fehler bei der Token-Erneuerung. Starte OAuth-Flow ...")
                    creds = None  # Token-Inhalte zurücksetzen für neuen OAuth-Flow
            if not creds:
                print("Kein gültiges Token vorhanden. Starte OAuth-Flow ...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    GoogleAuth.CREDENTIALS_PATH, GoogleAuth.SCOPES
                )
                creds = flow.run_local_server(port=0)

            # 3) Neues Token speichern
            with open(GoogleAuth.TOKEN_PATH, "wb") as token_file:
                pickle.dump(creds, token_file)

        return creds

    @staticmethod
    def get_service(service_name: str, version: str):
        """
        Erstellt und gibt einen Google API-Service-Client zurück.

        :param service_name: Name des Dienstes (z. B. "gmail", "youtube", "calendar", "drive")
        :param version: API-Version (z. B. "v1" für Gmail, "v3" für Drive)
        :return: Google API Service Client
        """
        creds = GoogleAuth.get_credentials()
        return build(service_name, version, credentials=creds)

# Falls dieses Skript direkt ausgeführt wird, einfach mal testen
if __name__ == "__main__":
    gmail_service = GoogleAuth.get_service("gmail", "v1")
    print("Gmail-Service erfolgreich initialisiert!")