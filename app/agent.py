# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
from pathlib import Path
import uuid
import datetime
from zoneinfo import ZoneInfo
import subprocess
import google.auth
from google.oauth2.credentials import Credentials
from google.cloud import firestore

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.memory import VertexAiMemoryBankService
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.genai import types

from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from .a2ui_utils import a2ui_callback





# Hardcoded GCP Project ID for Firestore client
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-01-6acb3664856b"

def get_firestore_client() -> firestore.Client:
    """Returns a Firestore client bound to the hardcoded project ID."""
    try:
        credentials, _ = google.auth.default()
        client = firestore.Client(project=FIRESTORE_PROJECT_ID, credentials=credentials)
        list(client.collection("expenses").limit(1).stream())
        return client
    except Exception:
        token = subprocess.check_output(["gcloud", "auth", "print-access-token"]).decode().strip()
        creds = Credentials(token)
        return firestore.Client(project=FIRESTORE_PROJECT_ID, credentials=creds)

def list_expenses(category: str | None = None) -> str:
    """Lists expenses from the Firestore database, optionally filtered by category.

    Args:
        category: Optional category name to filter expenses (e.g. 'Dining', 'Groceries', 'Housing', 'Entertainment', 'Utilities', 'Shopping').

    Returns:
        A list of expense records as a formatted string representation.
    """
    db = get_firestore_client()
    collection_ref = db.collection("expenses")
    if category:
        docs = collection_ref.where("category", "==", category).stream()
    else:
        docs = collection_ref.stream()

    expenses = [doc.to_dict() for doc in docs]
    return str(expenses)

def add_expense(description: str, amount: float, category: str, is_discretionary: bool = True, date: str | None = None) -> str:
    """Adds a new expense item to the Firestore database.

    Args:
        description: A short description of the expense (e.g., 'Groceries at Trader Joes', 'Movie Tickets').
        amount: Dollar amount of the expense (e.g., 45.50).
        category: Category of expense (e.g., 'Dining', 'Groceries', 'Housing', 'Entertainment', 'Utilities', 'Shopping').
        is_discretionary: Boolean indicating if spending is discretionary (optional expenses) or essential (fixed bills like rent/utilities). Defaults to True.
        date: Date of expense in YYYY-MM-DD format. Defaults to current date if omitted.

    Returns:
        Confirmation message with the created expense ID.
    """
    db = get_firestore_client()
    expense_id = f"exp-{uuid.uuid4().hex[:6]}"
    if not date:
        date = datetime.date.today().isoformat()

    expense_data = {
        "id": expense_id,
        "description": description,
        "amount": float(amount),
        "category": category,
        "is_discretionary": bool(is_discretionary),
        "date": date
    }

    db.collection("expenses").document(expense_id).set(expense_data)
    return f"Successfully recorded expense: {expense_id} - {description} (${amount:.2f}) under category '{category}'."

def calculate_category_breakdown() -> str:
    """Calculates total spending grouped by category and discretionary vs. fixed status.

    Returns:
        A formatted string with category totals, overall spent amount, and discretionary vs. fixed totals.
    """
    db = get_firestore_client()
    docs = db.collection("expenses").stream()
    expenses = [doc.to_dict() for doc in docs]

    category_totals = {}
    discretionary_total = 0.0
    fixed_total = 0.0
    total_spent = 0.0

    for exp in expenses:
        amt = float(exp.get("amount", 0.0))
        cat = exp.get("category", "Uncategorized")
        is_disc = bool(exp.get("is_discretionary", True))

        total_spent += amt
        category_totals[cat] = category_totals.get(cat, 0.0) + amt

        if is_disc:
            discretionary_total += amt
        else:
            fixed_total += amt

    summary = {
        "total_spent": round(total_spent, 2),
        "fixed_expenses_total": round(fixed_total, 2),
        "discretionary_expenses_total": round(discretionary_total, 2),
        "categories": {cat: round(amt, 2) for cat, amt in category_totals.items()}
    }
    return str(summary)

def analyze_savings_plan(target_savings: float, monthly_income: float = 3000.0) -> str:
    """Analyzes income vs expenses to generate spending cut recommendations targeting discretionary expenses to hit savings goal.

    Args:
        target_savings: Target dollar amount to save each month (e.g. 500.0).
        monthly_income: Net monthly income in dollars (e.g. 3000.0). Defaults to 3000.0.

    Returns:
        Structured breakdown showing current savings, savings gap, and discretionary category breakdown.
    """
    db = get_firestore_client()
    docs = db.collection("expenses").stream()
    expenses = [doc.to_dict() for doc in docs]

    total_spent = sum(float(e.get("amount", 0.0)) for e in expenses)
    current_savings = monthly_income - total_spent
    savings_gap = target_savings - current_savings

    discretionary_items = [e for e in expenses if e.get("is_discretionary", True)]
    discretionary_total = sum(float(e.get("amount", 0.0)) for e in discretionary_items)

    cuts_needed = max(0.0, savings_gap)
    feasible = cuts_needed <= discretionary_total

    recommendations = {
        "monthly_income": monthly_income,
        "total_spent": round(total_spent, 2),
        "current_savings": round(current_savings, 2),
        "target_savings": target_savings,
        "savings_gap": round(savings_gap, 2),
        "cuts_needed_from_discretionary": round(cuts_needed, 2),
        "discretionary_total": round(discretionary_total, 2),
        "is_feasible": feasible,
        "discretionary_categories": list(set(e.get("category") for e in discretionary_items))
    }
    return str(recommendations)

def update_expense_category(expense_id: str, new_category: str, is_discretionary: bool = True) -> str:
    """Updates the category and discretionary status of an existing expense transaction in Firestore.

    Args:
        expense_id: The document ID of the expense to update (e.g. 'exp-004').
        new_category: The new category name (e.g. 'Dining', 'Groceries', 'Utilities').
        is_discretionary: Boolean indicating if the new category is discretionary spending. Defaults to True.

    Returns:
        Confirmation string indicating if update succeeded.
    """
    db = get_firestore_client()
    doc_ref = db.collection("expenses").document(expense_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Error: Expense with ID '{expense_id}' was not found."

    doc_ref.update({
        "category": new_category,
        "is_discretionary": bool(is_discretionary)
    })
    return f"Successfully updated expense '{expense_id}' to category '{new_category}' (Discretionary: {is_discretionary})."

def convert_currency(amount: float, from_currency: str = "USD", to_currency: str = "EUR") -> str:
    """Converts a monetary amount between currencies using live foreign exchange rates from a public currency API.

    Args:
        amount: Dollar or monetary amount to convert (e.g., 100.0).
        from_currency: 3-letter currency code to convert from (e.g., 'USD', 'EUR', 'GBP', 'CAD', 'JPY'). Defaults to 'USD'.
        to_currency: 3-letter currency code to convert to (e.g., 'EUR', 'GBP', 'CAD', 'JPY'). Defaults to 'EUR'.

    Returns:
        A string with the converted currency amount, target currency code, and exchange rate.
    """
    import os
    import json
    import urllib.request

    from_curr = from_currency.upper()
    to_curr = to_currency.upper()

    # Optional API key support from environment variable if provided
    api_key = os.getenv("EXCHANGE_RATE_API_KEY") or os.getenv("CURRENCY_API_KEY")

    try:
        url = f"https://api.frankfurter.app/latest?amount={amount}&from={from_curr}&to={to_curr}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            converted_amount = data.get("rates", {}).get(to_curr)
            if converted_amount is not None:
                rate = round(converted_amount / amount, 4) if amount else 0.0
                return f"{amount:.2f} {from_curr} = {converted_amount:.2f} {to_curr} (Exchange rate: 1 {from_curr} = {rate} {to_curr}, Date: {data.get('date')})"
            return f"Error: Currency '{to_curr}' is not supported by the conversion service."
    except Exception as e:
        return f"Failed to fetch live currency conversion rates: {str(e)}"

def geocode_address(address: str) -> str:
    """Converts a street address or city location into latitude and longitude coordinates using the Google Maps Geocoding API.

    Args:
        address: Street address or location name (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA' or 'San Francisco, CA').

    Returns:
        A string containing formatted address, latitude, and longitude.
    """
    import os
    import json
    import urllib.request
    import urllib.parse

    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not set."

    encoded_address = urllib.parse.quote(address)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            if data.get("status") == "OK" and data.get("results"):
                first_result = data["results"][0]
                formatted_address = first_result.get("formatted_address", address)
                location = first_result.get("geometry", {}).get("location", {})
                lat = location.get("lat")
                lng = location.get("lng")
                return f"Address: '{formatted_address}' | Latitude: {lat}, Longitude: {lng}"
            return f"Geocoding failed with status: {data.get('status')} ({data.get('error_message', 'No details')})"
    except Exception as e:
        return f"Error executing Geocoding request: {str(e)}"

def find_nearby_places(latitude: float, longitude: float, place_type: str = "supermarket", radius_meters: float = 2000.0) -> str:
    """Finds nearby places of a given type around latitude and longitude using Google Places API (New) searchNearby REST endpoint.

    Args:
        latitude: Latitude of center point (e.g. 37.7749).
        longitude: Longitude of center point (e.g. -122.4194).
        place_type: Type of place to search for (e.g. 'supermarket', 'restaurant', 'bank', 'cafe', 'store'). Defaults to 'supermarket'.
        radius_meters: Search radius in meters (e.g. 2000.0). Defaults to 2000.0.

    Returns:
        List of matching nearby places with name, formatted address, and location coordinates.
    """
    import os
    import json
    import urllib.request

    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not set."

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location"
    }

    body = {
        "includedTypes": [place_type.lower()],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": float(latitude),
                    "longitude": float(longitude)
                },
                "radius": float(radius_meters)
            }
        }
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            places = data.get("places", [])
            if not places:
                return f"No nearby places of type '{place_type}' found within {radius_meters}m."

            results = []
            for place in places:
                name = place.get("displayName", {}).get("text", "Unknown Name")
                addr = place.get("formattedAddress", "Unknown Address")
                loc = place.get("location", {})
                results.append({
                    "name": name,
                    "address": addr,
                    "location": f"({loc.get('latitude')}, {loc.get('longitude')})"
                })
            return str(results)
    except Exception as e:
        return f"Error executing Places (New) request: {str(e)}"

async def generate_expense_image(
    prompt_description: str,
    tool_context: ToolContext
) -> str:
    """Generates an image for an expense transaction, visual receipt, or financial summary chart using gemini-3.1-flash-lite-image in the global region.
    Saves the image bytes as a session artifact and uploads it to the public Cloud Storage bucket.

    Args:
        prompt_description: Description of the financial item, receipt, or expense chart to visualize (e.g. 'A visual infographic receipt for $45 groceries at Safeway').

    Returns:
        The public HTTPS URL of the uploaded image in Cloud Storage (https://storage.googleapis.com/<bucket>/<object>).
    """
    import uuid
    from google import genai
    from google.genai import types
    from google.cloud import storage

    bucket_name = "smart-financial-advisor-assets-6acb3664856b"
    project_id = "qwiklabs-gcp-01-6acb3664856b"

    try:
        client = genai.Client(
            vertexai=True,
            project=project_id,
            location="global"
        )

        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=f"Generate a clear, high quality visual illustration for a financial advisor app representing: {prompt_description}",
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"]
            )
        )

        image_bytes = None
        mime_type = "image/jpeg"
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                image_bytes = part.inline_data.data
                if part.inline_data.mime_type:
                    mime_type = part.inline_data.mime_type
                break

        if not image_bytes:
            return "Error: Image generation model did not return image data."

        ext = "png" if "png" in mime_type else "jpg"
        filename = f"expense_image_{uuid.uuid4().hex[:6]}.{ext}"

        # 1. Save artifact for ADK Playground
        image_artifact = types.Part.from_bytes(
            data=image_bytes,
            mime_type=mime_type
        )
        await tool_context.save_artifact(
            filename=filename,
            artifact=image_artifact
        )

        # 2. Upload to public Cloud Storage bucket
        gcs_client = storage.Client(project=project_id)
        bucket = gcs_client.bucket(bucket_name)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{bucket_name}/{filename}"
        return f"Successfully generated image! Saved artifact '{filename}' and published to public Cloud Storage: {public_url}"

    except Exception as e:
        return f"Error generating or saving image: {str(e)}"

async def generate_expense_video(
    prompt_description: str,
    tool_context: ToolContext
) -> str:
    """Generates a short animated video for a financial item, savings goal, or expense visualization using Google's Omni model (gemini-omni-flash-preview) in the global region.
    Saves the video bytes as a session artifact for the Playground and uploads it to the public Cloud Storage bucket.

    Args:
        prompt_description: Description of the financial item, receipt, or savings goal to animate (e.g. 'A piggy bank filling up with gold coins for a savings goal').

    Returns:
        The public HTTPS URL of the uploaded video in Cloud Storage (https://storage.googleapis.com/<bucket>/<object>).
    """
    import uuid
    import base64
    from google import genai
    from google.genai import types
    from google.cloud import storage

    bucket_name = "smart-financial-advisor-assets-6acb3664856b"
    project_id = "qwiklabs-gcp-01-6acb3664856b"

    try:
        client = genai.Client(
            vertexai=True,
            project=project_id,
            location="global"
        )

        interaction = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=f"Create a short high quality animated video illustrating: {prompt_description}"
        )

        video_bytes = None
        mime_type = "video/mp4"

        if hasattr(interaction, "output_video") and interaction.output_video:
            if hasattr(interaction.output_video, "data") and interaction.output_video.data:
                raw_data = interaction.output_video.data
                if isinstance(raw_data, str):
                    video_bytes = base64.b64decode(raw_data)
                else:
                    video_bytes = raw_data
            if hasattr(interaction.output_video, "mime_type") and interaction.output_video.mime_type:
                mime_type = interaction.output_video.mime_type
        
        if not video_bytes and hasattr(interaction, "outputs") and interaction.outputs:
            for out in interaction.outputs:
                if hasattr(out, "video") and out.video and hasattr(out.video, "data"):
                    raw_data = out.video.data
                    video_bytes = base64.b64decode(raw_data) if isinstance(raw_data, str) else raw_data
                    if hasattr(out.video, "mime_type") and out.video.mime_type:
                        mime_type = out.video.mime_type
                    break

        if not video_bytes:
            dump = interaction.model_dump() if hasattr(interaction, "model_dump") else {}
            out_vid = dump.get("output_video") or {}
            if out_vid.get("data"):
                raw_data = out_vid["data"]
                video_bytes = base64.b64decode(raw_data) if isinstance(raw_data, str) else raw_data
                if out_vid.get("mime_type"):
                    mime_type = out_vid["mime_type"]

        if not video_bytes:
            return "Error: Video generation model did not return video bytes."

        filename = f"expense_video_{uuid.uuid4().hex[:6]}.mp4"

        # 1. Save artifact for ADK Playground
        video_artifact = types.Part.from_bytes(
            data=video_bytes,
            mime_type=mime_type
        )
        await tool_context.save_artifact(
            filename=filename,
            artifact=video_artifact
        )

        # 2. Upload video bytes to public Cloud Storage bucket
        gcs_client = storage.Client(project=project_id)
        bucket = gcs_client.bucket(bucket_name)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{bucket_name}/{filename}"
        return f"Successfully generated video! Saved artifact '{filename}' and published to public Cloud Storage: {public_url}"

    except Exception as e:
        return f"Error generating or saving video: {str(e)}"

def get_weather(query: str) -> str:
    """Simulates a web search for weather information."""
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."

def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city."""
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"

# Initialize AgentEngineSandboxCodeExecutor from deployment_metadata.json if available
code_executor = None
metadata_path = Path(__file__).parent.parent / "deployment_metadata.json"
if metadata_path.exists():
    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
            agent_engine_id = metadata.get("remote_agent_runtime_id")
            if agent_engine_id:
                code_executor = AgentEngineSandboxCodeExecutor(
                    agent_engine_resource_name=agent_engine_id
                )
    except Exception as e:
        print(f"Warning: Could not initialize AgentEngineSandboxCodeExecutor: {e}")

async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()
    return None

def memory_bank_service_builder():
    return VertexAiMemoryBankService(
        project="qwiklabs-gcp-01-6acb3664856b",
        location="us-east1",
        agent_engine_id="626212553948659712",
    )

a2ui_schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = a2ui_schema_manager.generate_system_prompt(
    role_description="You are a Smart Financial Advisor AI assistant helping users manage expenses, track spending categories, convert currency values, find budget-friendly nearby stores, generate visual financial charts/receipts, generate video animations of financial goals, run code calculations, and analyze discretionary vs. fixed expenses to hit monthly savings targets.",
    workflow_description="Analyze the request, use tools when needed to fetch or compute data, and return structured A2UI UI when appropriate. You actively remember and personalize responses based on user stated spending preferences, budget limits, target savings goals, preferred currency, and favorite stores.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "To render expense category breakdowns or lists, build them as a single Card containing a Column of Rows, where each Row contains two Text components (one for the Category Name, one for the Dollar Amount). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),

    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=code_executor,
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        list_expenses,
        add_expense,
        calculate_category_breakdown,
        analyze_savings_plan,
        update_expense_category,
        convert_currency,
        geocode_address,
        find_nearby_places,
        generate_expense_image,
        generate_expense_video,
        get_weather,
        get_current_time
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)









