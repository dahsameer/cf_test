from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from jinja2 import Environment, FileSystemLoader
from google import genai
import re
import os

# Initialize FastAPI
app = FastAPI()

# Environment Variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Missing GEMINI_API_KEY environment variable")

# Initialize Google AI Client
client = genai.Client(api_key=GEMINI_API_KEY)

# Setup Database
DATABASE_URL = "sqlite:///./data.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Utility Functions
def get_db() -> Session:
    """Dependency to get a new database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Jinja2 Setup
templates_env = Environment(loader=FileSystemLoader("templates"))

def render_template(template_name: str, **context) -> HTMLResponse:
    """Renders an HTML template with the given context."""
    template = templates_env.get_template(template_name)
    return HTMLResponse(content=template.render(context))

# Dummy function for NL to SQL conversion (Replace with AI model later)
def convert_nl_to_sql(nl_query: str) -> str:
    schema_info = """
    Database Schema:
    - Table: airlines
      - IATA_CODE (TEXT)
      - AIRLINE (TEXT)
    - Table: airports
      - IATA_CODE (TEXT)
      - AIRPORT (TEXT)
    - Table: flights
      - YEAR (TEXT)
      - MONTH (TEXT)
      - DAY (TEXT)
      - DAY_OF_WEEK (TEXT)
      - AIRLINE (TEXT)
      - FLIGHT_NUMBER (TEXT)
      - TAIL_NUMBER (TEXT)
      - ORIGIN_AIRPORT (TEXT)
      - DESTINATION_AIRPORT (TEXT)
      - SCHEDULED_DEPARTURE (TEXT)
      - DEPARTURE_TIME (TEXT)
      - DEPARTURE_DELAY (TEXT)
      - TAXI_OUT (TEXT)
      - WHEELS_OFF (TEXT)
      - SCHEDULED_TIME (TEXT)
      - ELAPSED_TIME (TEXT)
      - AIR_TIME (TEXT)
      - DISTANCE (TEXT)
      - WHEELS_ON (TEXT)
      - TAXI_IN (TEXT)
      - SCHEDULED_ARRIVAL (TEXT)
      - ARRIVAL_TIME (TEXT)
      - ARRIVAL_DELAY (TEXT)
      - DIVERTED (TEXT)
      - CANCELLED (TEXT)
      - CANCELLATION_REASON (TEXT)
      - AIR_SYSTEM_DELAY (TEXT)
      - SECURITY_DELAY (TEXT)
      - AIRLINE_DELAY (TEXT)
      - LATE_AIRCRAFT_DELAY (TEXT)
      - WEATHER_DELAY (TEXT)
    """

    prompt = f"""
    Convert the following natural language query into a valid SQL statement for the given schema:
    
    {schema_info}

    Natural Language Query: "{nl_query}"
    
    Provide only the SQL query. if the natural language doesn't specify number of rows, limit the query to 20 rows.
    """

    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    
    sql_query = response.text.strip()
    sql_query = re.sub(r"```sql\n|```", "", sql_query).strip()

    # Prevent destructive SQL commands
    forbidden_keywords = {"DELETE", "UPDATE", "DROP", "TRUNCATE", "ALTER", "INSERT"}
    if any(word in sql_query.upper() for word in forbidden_keywords):
        raise ValueError("Forbidden SQL operation detected")

    return sql_query

# Routes
@app.get("/", response_class=HTMLResponse)
def home():
    """Renders the home page."""
    return render_template("index.html")

@app.post("/query")
def query(nl_query: str = Form(...), db: Session = Depends(get_db)):
    """Handles the natural language query, converts it to SQL, and fetches results."""
    try:
        sql_query = convert_nl_to_sql(nl_query)
        result = db.execute(text(sql_query))
        rows = result.fetchall()
        columns = result.keys()
        results = [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        return render_template("results.html", query=sql_query, error=str(e), results=None)

    return render_template("results.html", query=sql_query, results=results)