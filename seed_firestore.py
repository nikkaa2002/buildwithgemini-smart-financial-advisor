import subprocess
import google.auth
from google.oauth2.credentials import Credentials
from google.cloud import firestore

# Hardcode project ID as string for Firestore client (do not use GOOGLE_CLOUD_PROJECT or google.auth.default project derivation)
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-01-6acb3664856b"

SAMPLE_EXPENSES = [
    {
        "id": "exp-001",
        "description": "Monthly Apartment Rent",
        "amount": 1500.00,
        "category": "Housing",
        "is_discretionary": False,
        "date": "2026-10-01"
    },
    {
        "id": "exp-002",
        "description": "Whole Foods Market",
        "amount": 125.50,
        "category": "Groceries",
        "is_discretionary": False,
        "date": "2026-10-02"
    },
    {
        "id": "exp-003",
        "description": "City Power Utility",
        "amount": 85.20,
        "category": "Utilities",
        "is_discretionary": False,
        "date": "2026-10-01"
    },
    {
        "id": "exp-004",
        "description": "Italian Restaurant Dinner",
        "amount": 68.40,
        "category": "Dining",
        "is_discretionary": True,
        "date": "2026-10-02"
    },
    {
        "id": "exp-005",
        "description": "Netflix Subscription",
        "amount": 19.99,
        "category": "Entertainment",
        "is_discretionary": True,
        "date": "2026-10-01"
    },
    {
        "id": "exp-006",
        "description": "Artisan Coffee Roasters",
        "amount": 15.50,
        "category": "Dining",
        "is_discretionary": True,
        "date": "2026-10-02"
    },
    {
        "id": "exp-007",
        "description": "Live Music Event",
        "amount": 95.00,
        "category": "Entertainment",
        "is_discretionary": True,
        "date": "2026-10-02"
    },
    {
        "id": "exp-008",
        "description": "Apparel & Accessories",
        "amount": 110.00,
        "category": "Shopping",
        "is_discretionary": True,
        "date": "2026-10-02"
    }
]

def get_firestore_client() -> firestore.Client:
    try:
        credentials, _ = google.auth.default()
        client = firestore.Client(project=FIRESTORE_PROJECT_ID, credentials=credentials)
        list(client.collection("expenses").limit(1).stream())
        return client
    except Exception:
        token = subprocess.check_output(["gcloud", "auth", "print-access-token"]).decode().strip()
        creds = Credentials(token)
        return firestore.Client(project=FIRESTORE_PROJECT_ID, credentials=creds)

def seed_database():
    print(f"Connecting to Firestore for project: {FIRESTORE_PROJECT_ID}...")
    db = get_firestore_client()
    collection_ref = db.collection("expenses")

    for expense in SAMPLE_EXPENSES:
        doc_ref = collection_ref.document(expense["id"])
        doc_ref.set(expense)
        print(f"Seeded document: {expense['id']} - {expense['description']} (${expense['amount']})")

    print(f"Successfully seeded {len(SAMPLE_EXPENSES)} expenses into 'expenses' collection!")

if __name__ == "__main__":
    seed_database()
