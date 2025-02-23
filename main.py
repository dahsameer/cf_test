from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from jinja2 import Environment, FileSystemLoader
from google import genai
import re
import os

# Initialize FastAPI
app = FastAPI()

# Setup database
DATABASE_URL = "sqlite:///./data.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Setup Jinja2
env = Environment(loader=FileSystemLoader("templates"))

def render_template(template_name, **context):
    template = env.get_template(template_name)
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
    
    Provide only the SQL query, without markdown formatting
    """

    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    sql_query = response.text.strip()
    sql_query = re.sub(r"```sql\n|```", "", sql_query).strip()
    forbidden_keywords = {"DELETE", "UPDATE", "DROP", "TRUNCATE", "ALTER", "INSERT"}
    if any(word in sql_query.upper() for word in forbidden_keywords):
        raise Exception("Forbidden keywords found in SQL")
    return sql_query

# Routes
@app.get("/", response_class=HTMLResponse)
def home():
    return render_template("index.html")

@app.post("/query")
def query(nl_query: str = Form(...), db=Depends(get_db)):
    try:
        sql_query = convert_nl_to_sql(nl_query)
        result = db.execute(text(sql_query))
        rows = result.fetchall()
        columns = result.keys()
        results = [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        return render_template("results.html", query=sql_query, error=str(e), results=None)
    return render_template("results.html", query=sql_query, results=results)