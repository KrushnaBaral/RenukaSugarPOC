import pandas as pd
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.memory import ChatMessageHistory
from langchain_openai import ChatOpenAI
from base import *

from dotenv import load_dotenv
from io import BytesIO, StringIO
from state import session_state
load_dotenv()  # Load environment variables from .env file
from typing import Optional
import logging
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException,Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from tempfile import NamedTemporaryFile
import shutil
from fastapi.responses import JSONResponse
from typing import List
import os, time
import nest_asyncio
from io import BytesIO
import openai
from sqlalchemy.orm import sessionmaker
from prompts import insight_prompt

import chromadb
from llama_index.core import VectorStoreIndex
from llama_index.core import StorageContext
from azure.storage.blob import BlobServiceClient
from llama_parse import LlamaParse
from llama_index.core import Document
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import Settings
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import json
from fastapi import FastAPI, Form, HTTPException, Query, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from fastapi.staticfiles import StaticFiles
import plotly.graph_objects as go
import plotly.express as px
from langchain_openai import ChatOpenAI
import openai, yaml
import base64
from pydantic import BaseModel
from io import BytesIO
import os, csv
import pandas as pd

# Add these imports at the top of your FastAPI file
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from bill_datas import invoice_data, awb_data, packing_data,renuka_data
import os
from io import BytesIO
from werkzeug.utils import secure_filename


from fastapi import FastAPI, HTTPException, Depends, status, Form
import psycopg2
from psycopg2 import sql

from langchain.chains.openai_tools import create_extraction_chain_pydantic
from langchain_core.pydantic_v1 import Field
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from typing import Optional
# Setup environment variables
LLAMA_API_KEY = os.getenv("LLAMA_API_KEY")
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DOCSTORE = os.getenv("DOCSTORE").split(",")
COLLECTION = os.getenv("COLLECTION").split(",")
Chroma_DATABASE = os.getenv("Chroma_DATABASE").split(",")
LLM_MODEL = os.getenv("LLM_MODEL")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
os.environ["LLAMA_CLOUD_API_KEY"] = LLAMA_API_KEY
Settings.llm = OpenAI(model=LLM_MODEL)
Settings.embed_model = OpenAIEmbedding(api_key=OPENAI_API_KEY)
models = os.getenv('models')
databases = os.getenv('databases').split(',')
subject_areas2 = os.getenv('subject_areas2').split(',')
openai_ef = OpenAIEmbeddingFunction(api_key=os.getenv("OPENAI_API_KEY"), model_name=EMBEDDING_MODEL)
AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME")
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up static files and templates
app.mount("/stats", StaticFiles(directory="stats"), name="stats")
templates = Jinja2Templates(directory="templates")

# Initialize OpenAI API key and model

question_dropdown = os.getenv('Question_dropdown')
llm = ChatOpenAI(model=models, temperature=0)  # Adjust model as necessary
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

from table_details import get_table_details  # Importing the function

class Table(BaseModel):
    """Table in SQL database."""
    name: str = Field(description="Name of table in SQL database.")



from urllib.parse import quote

# Initialize the BlobServiceClient
try:
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    print("Blob service client initialized successfully.")
except Exception as e:
    print(f"Error initializing BlobServiceClient: {e}")
    # Handle the error appropriately, possibly exiting the application
    raise  # Re-raise the exception to prevent the app from starting






class ChartRequest(BaseModel):
    """
    Pydantic model for chart generation requests.
    """
    table_name: str
    x_axis: str
    y_axis: str
    chart_type: str

    class Config:  # This ensures compatibility with FastAPI
        json_schema_extra = {
            "example": {
                "table_name": "example_table",
                "x_axis": "column1",
                "y_axis": "column2",
                "chart_type": "Line Chart"
            }
        }
def download_as_excel(data: pd.DataFrame, filename: str = "data.xlsx"):
    """
    Converts a Pandas DataFrame to an Excel file and returns it as a stream.
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        data.to_excel(writer, index=False, sheet_name='Sheet1')
    output.seek(0)
    return output
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=db_host,
            database=db_database,
            user=db_user,
            password=db_password,
            port=db_port
        )
        # Check if the connection is successful
        conn.cursor().execute("SELECT 1")
        print("Database connection established successfully.")
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to the database: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to connect to the database"
        )

get_db_connection()
def escape_single_quotes(input_string):
    return input_string.replace("'","''")
class TemporaryDocumentHandler:
    def init(self):
        self.temp_index = None
        self.uploaded_files = []
        self.parser_choice = "LlamaParse"  # Default parser

    async def handle_upload(self, files: List[UploadFile], parser_choice: str):
        """Handle temporary file uploads and create index."""
        try:
            self.parser_choice = parser_choice
            self.uploaded_files = files

            if files:
                temp_documents = []
                parsed_text = []

                for uploaded_file in files:
                    if parser_choice == "LlamaParse":
                        file_content = await uploaded_file.read()
                        result_text = await self.use_llamaparse(file_content, uploaded_file.filename)
                        parsed_text.append(result_text)
                    else:
                        # Save file temporarily for unstructured parser
                        with NamedTemporaryFile(delete=False) as temp_file:
                            shutil.copyfileobj(uploaded_file.file, temp_file)
                            temp_file_path = temp_file.name

                        result_text = await self.use_unstructured(temp_file_path)
                        parsed_text.append(result_text)
                        os.unlink(temp_file_path)  # Clean up temp file

                # Split text into chunks
                TEMP_CHUNK_SIZE = os.getenv("TEMP_CHUNK_SIZE", 1000)
                chunk_size = int(TEMP_CHUNK_SIZE)
                for text in parsed_text:
                    text_chunks = [
                        text[i:i + chunk_size]
                        for i in range(0, len(text), chunk_size)
                    ]
                    for chunk in text_chunks:
                        document = Document(text=chunk)
                        temp_documents.append(document)

                # Create index
                self.temp_index = VectorStoreIndex.from_documents(
                    temp_documents,
                    embed_model=Settings.embed_model
                )

                return {"status": "success", "message": "Files processed successfully"}

            return {"status": "error", "message": "No files uploaded"}

        except Exception as e:
            return {"status": "error", "message": f"Error processing files: {str(e)}"}

    async def query_index(self, question: str):
        """Query the temporary index with a question."""
        if not self.temp_index:
            return {"status": "error", "message": "No index available - please upload documents first"}

        try:
            # Set up retriever
            retriever = self.temp_index.as_retriever(similarity_top_k=3)

            # Retrieve relevant nodes
            retrieved_nodes = retriever.retrieve(question)
            context_str = "\n\n".join([
                r.get_content().replace("{", "").replace("}", "")[:4000]
                for r in retrieved_nodes
            ])

            # Format QA prompt
            qa_prompt_str = QA_PROMPT_STR  # Define this constant or get from env
            fmt_qa_prompt = qa_prompt_str.format(
                context_str=context_str,
                query_str=question
            )

            # Prepare messages
            chat_text_qa_msgs = [
                ChatMessage(role=MessageRole.SYSTEM, content=LLM_INSTRUCTION),
                ChatMessage(role=MessageRole.USER, content=fmt_qa_prompt),
            ]
            text_qa_template = ChatPromptTemplate(chat_text_qa_msgs)

            # Query the index
            result = self.temp_index.as_query_engine(
                text_qa_template=text_qa_template,
                llm=llm
            ).query(question)

            if result:
                return {
                    "status": "success",
                    "response": result.response,
                    "context": context_str
                }
            else:
                return {"status": "error", "message": "No response generated"}

        except Exception as e:
            return {"status": "error", "message": f"Error querying index: {str(e)}"}

    async def use_llamaparse(self, file_content: bytes, file_name: str):
        """Parse file using LlamaParse."""
        try:
            with open(file_name, "wb") as f:
                f.write(file_content)

            parser = LlamaParse(
                result_type='text',
                verbose=True,
                language="en",
                num_workers=2
            )
            documents = await parser.aload_data([file_name])
            os.remove(file_name)

            return " ".join([doc.text for doc in documents])

        except Exception as e:
            raise Exception(f"LlamaParse error: {str(e)}")

    async def use_unstructured(self, file_path: str):
        """Parse file using Unstructured.io."""
        try:
            # Implement your unstructured.io parsing logic here
            # This is a placeholder - replace with actual implementation
            with open(file_path, "r") as f:
                return f.read()
        except Exception as e:
            raise Exception(f"Unstructured.io error: {str(e)}")

# Initialize the handler
temp_doc_handler = TemporaryDocumentHandler()

# API Endpoints
@app.post("/upload-temp-docs")
async def upload_temp_docs(
    files: List[UploadFile] = File(...),
    parser_choice: str = Form("LlamaParse")
):
    """Endpoint for uploading temporary documents."""
    result = await temp_doc_handler.handle_upload(files, parser_choice)
    return JSONResponse(result)

@app.post("/query-temp-docs")
async def query_temp_docs(
    question: str = Form(...)
):
    """Endpoint for querying temporary documents."""
    result = await temp_doc_handler.query_index(question)

    return JSONResponse(result)

class QueryInput(BaseModel):
    """
    Pydantic model for user query input.
    """
    query: str
@app.post("/clear-temp-docs")
async def clear_temp_docs():
    """Endpoint for clearing temporary documents."""
    temp_doc_handler.temp_index = None
    temp_doc_handler.uploaded_files = []
    return JSONResponse({"status": "success", "message": "Temporary documents cleared"})

from datetime import datetime

# Database connection
def get_connection():
    return psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="Satya@2002",
        host="localhost",
        port="5432"
    )

# def try_multiple_formats(date_str):
#     date_formats = [
#         "%d/%m/%Y",
#         "%d-%m-%Y",
#         "%Y-%m-%d",
#         "%d-%b-%Y",
#         "%d-%b-%y",      # ✅ Supports 6-May-25
#         "%b %d, %Y",
#         "%d %B %Y",
#         "%d.%m.%Y",
#     ]
#     for fmt in date_formats:
#         try:
#             return datetime.strptime(date_str.strip(), fmt).date()
#         except ValueError:
#             continue
#     raise ValueError(f"Unrecognized date format: {date_str}")

app = FastAPI()

FIELD_MAP = {
    "Invoice Number": "invoice_number",
    "Invoice Date": "invoice_date",
    "Vendor Name": "vendor_name",
    "Description": "description",
    "Total Amount (In Ruppees)": "total_amount",
    "GSTIN": "gstin"
}

# @app.post("/insert_invoices")
# async def insert_invoices(request: Request):
#     try:
#         data = await request.json()

#         conn = get_connection()
#         cur = conn.cursor()

#         for entry in data:
#             row = {}
#             for key, value in entry.items():
#                 mapped_key = FIELD_MAP.get(key)
#                 if mapped_key:
#                     row[mapped_key] = value

#             # ✅ Handle flexible date formats
#             invoice_date = None
#             if "invoice_date" in row and row["invoice_date"]:
#                 try:
#                     invoice_date = try_multiple_formats(row["invoice_date"])
#                 except ValueError as e:
#                     raise HTTPException(status_code=400, detail=str(e))

#             # ✅ Insert data
#             cur.execute("""
#                 INSERT INTO Renuka_POC (
#                     invoice_number,
#                     invoice_date,
#                     vendor_name,
#                     description,
#                     total_amount,
#                     gstin
#                 ) VALUES (%s, %s, %s, %s, %s, %s)
#                 ON CONFLICT (invoice_number) DO NOTHING;
#             """, (
#                 row.get("invoice_number"),
#                 invoice_date,
#                 row.get("vendor_name"),
#                 row.get("description"),
#                 float(row.get("total_amount", "0").replace(",", "").strip()) if row.get("total_amount") else None,

#                 row.get("gstin")
#             ))

#         conn.commit()
#         cur.close()
#         conn.close()

#         return {"message": "Invoice data inserted successfully!"}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.post("/add_to_faqs/")
async def add_to_faqs(
    data: QueryInput,
    subject: str = Query(..., description="Subject area as query parameter")
):
    """
    Adds a user query to the FAQ CSV file for the specified subject.
    Subject comes from URL parameter, not request body.
    """
    query = data.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Question cannot be empty!")
    if not subject:
        raise HTTPException(status_code=400, detail="Subject must be specified!")

    blob_name = f"{subject}_questions.csv"

    try:
        blob_client = blob_service_client.get_blob_client(
            container=AZURE_CONTAINER_NAME,
            blob=blob_name
        )

        # Try to download existing content or start with header
        try:
            blob_content = blob_client.download_blob().content_as_text()
        except:
            blob_content = "question\n"  # Default header if file doesn't exist

        # Add new question
        updated_csv_content = blob_content + f"{query}\n"

        # Upload back to Azure
        blob_client.upload_blob(updated_csv_content.encode('utf-8'), overwrite=True)

        return {"message": f"Question added to {subject} FAQs successfully!"}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error saving question: {str(e)}"
        )
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):

    # Extract table names dynamically
    tables = []

    # Pass dynamically populated dropdown options to the template
    return templates.TemplateResponse("index.html", {
        "request": request,
        "models": models,
        "databases": databases,  # Dynamically populated database dropdown
        "section": subject_areas2,
        "tables": tables,        # Table dropdown based on database selection
        "question_dropdown": question_dropdown.split(','),  # Static questions from env
    })
# Login endpoint
@app.post("/login")
async def login(
    email: str = Form(...),
    password: str = Form(...),
    section: str = Form(...),


):
    if not email or not password or not section:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All fields are required"
        )

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Check if the user exists and the password matches
        cur.execute(
            sql.SQL("""
                SELECT u.user_id, u.full_name, r.role_name
                FROM lz_users u
                JOIN lz_user_roles ur ON u.user_id = ur.user_id
                JOIN lz_roles r ON ur.role_id = r.role_id
                WHERE u.email = %s AND u.password_hash = %s
            """),
            (email, password)
        )
        user = cur.fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        user_id, full_name, role_name = user

        # Redirect based on role
        if role_name == "admin":
            encoded_name = quote(full_name)
            encoded_section = quote(section)
            # return RedirectResponse(url=f"/admin?section={encoded_section}", status_code=status.HTTP_303_SEE_OTHER)
            return RedirectResponse(url=f"/role-select?name={encoded_name}&section={encoded_section}", status_code=status.HTTP_303_SEE_OTHER)

        elif role_name == "user":
            # Use urllib.parse.quote to encode full_name and section
            encoded_name = quote(full_name)
            encoded_section = quote(section)
            return RedirectResponse(
                url=f"/user_more?name={encoded_name}&section={encoded_section}",
                status_code=status.HTTP_303_SEE_OTHER
            )
        elif role_name == "viewer":
            # Use urllib.parse.quote to encode full_name and section
            encoded_name = quote(full_name)
            encoded_section = quote(section)
            return RedirectResponse(
                url=f"/customer_landing_page?name={encoded_name}&section={encoded_section}",
                status_code=status.HTTP_303_SEE_OTHER
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized access"
            )

    finally:
        cur.close()
        conn.close()

def generate_chart_figure(data_df: pd.DataFrame, x_axis: str, y_axis: str, chart_type: str):
    """
    Generates a Plotly figure based on the specified chart type.
    """
    fig = None
    if chart_type == "Line Chart":
        fig = px.line(data_df, x=x_axis, y=y_axis)
    elif chart_type == "Bar Chart":
        fig = px.bar(data_df, x=x_axis, y=y_axis)
    elif chart_type == "Scatter Plot":
        fig = px.scatter(data_df, x=x_axis, y=y_axis)
    elif chart_type == "Pie Chart":
        fig = px.pie(data_df, names=x_axis, values=y_axis)
    elif chart_type == "Histogram":
        fig = px.histogram(data_df, x=x_axis, y=y_axis)
    elif chart_type == "Box Plot":
        fig = px.box(data_df, x=x_axis, y=y_axis)
    elif chart_type == "Heatmap":
        fig = px.density_heatmap(data_df, x=x_axis, y=y_axis)
    elif chart_type == "Violin Plot":
        fig = px.violin(data_df, x=x_axis, y=y_axis)
    elif chart_type == "Area Chart":
        fig = px.area(data_df, x=x_axis, y=y_axis)
    elif chart_type == "Funnel Chart":
        fig = px.funnel(data_df, x=x_axis, y=y_axis)
    return fig

# @app.get("/", response_class=HTMLResponse)
# async def user_page(request: Request):
#     return templates.TemplateResponse("index.html", {"request": request})




@app.post("/generate-chart/")
async def generate_chart(request: ChartRequest):
    """
    Generates a chart based on the provided request data.
    """
    try:
        table_name = request.table_name
        x_axis = request.x_axis
        y_axis = request.y_axis
        chart_type = request.chart_type

        if "tables_data" not in globals() or table_name not in globals()["tables_data"]:
            return JSONResponse(
                content={"error": f"No data found for table {table_name}"},
                status_code=404
            )

        data_df = globals()["tables_data"][table_name]
        fig = generate_chart_figure(data_df, x_axis, y_axis, chart_type)

        if fig:
            return JSONResponse(content={"chart": fig.to_json()})
        else:
            return JSONResponse(content={"error": "Unsupported chart type selected."}, status_code=400)

    except Exception as e:
        return JSONResponse(
            content={"error": f"An error occurred while generating the chart: {str(e)}"},
            status_code=500
        )

@app.get("/download-table/")
async def download_table(table_name: str):
    """
    Downloads a table as an Excel file.
    """
    if "tables_data" not in globals() or table_name not in globals()["tables_data"]:
        raise HTTPException(status_code=404, detail=f"Table {table_name} data not found.")

    data = globals()["tables_data"][table_name]
    output = download_as_excel(data, filename=f"{table_name}.xlsx")

    response = StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response.headers["Content-Disposition"] = f"attachment; filename={table_name}.xlsx"
    return response
@app.get("/role-select", response_class=HTMLResponse)
async def user_page(request: Request):
    return templates.TemplateResponse("admin_landing_page.html", {"request": request})

@app.get("/user_client", response_class=HTMLResponse)
async def user_client(request: Request):
    # return templates.TemplateResponse("user_more.html", {"request": request})
    tables = []

    # Pass dynamically populated dropdown options to the template
    return templates.TemplateResponse("user_client.html", {
        "request": request,
        "models": models,
        "databases": databases,  # Dynamically populated database dropdown
        "section": subject_areas2,
        "tables": tables,        # Table dropdown based on database selection
        "question_dropdown": question_dropdown.split(','),  # Static questions from env
    })


@app.get("/customer_landing_page", response_class=HTMLResponse)
async def user_page(request: Request):
    return templates.TemplateResponse("customer_landing_page.html", {"request": request})

@app.get("/authentication", response_class=HTMLResponse)
async def user_page(request: Request):
    return templates.TemplateResponse("authentication.html", {"request": request})


@app.get("/user_more", response_class=HTMLResponse)
async def user_more(request: Request):
    # return templates.TemplateResponse("user_more.html", {"request": request})
    tables = []

    # Pass dynamically populated dropdown options to the template
    return templates.TemplateResponse("user.html", {
        "request": request,
        "models": models,
        "databases": databases,  # Dynamically populated database dropdown
        "section": subject_areas2,
        "tables": tables,        # Table dropdown based on database selection
        "question_dropdown": question_dropdown.split(','),  # Static questions from env
    })



@app.post("/transcribe-audio/")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcribes an audio file using OpenAI's Whisper API.

    Args:
        file (UploadFile): The audio file to transcribe.

    Returns:
        JSONResponse: A JSON response containing the transcription or an error message.
    """
    try:

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="Missing OpenAI API Key.")
        audio_bytes = await file.read()
        audio_bio = BytesIO(audio_bytes)
        audio_bio.name = "audio.webm"

        # Fix: Using OpenAI API correctly
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_bio
        )

        # Fix: Access transcript.text instead of treating it as a dictionary
        return {"transcription": transcript.text}

    except Exception as e:
        return JSONResponse(content={"error": f"Error transcribing audio: {str(e)}"}, status_code=500)
@app.post("/submit_feedback/")
async def submit_feedback(request: Request):
    data = await request.json() # Corrected for FastAPI

    table_name = data.get("table_name")
    feedback_type = data.get("feedback_type")
    user_query = data.get("user_query")
    sql_query = data.get("sql_query")

    if not table_name or not feedback_type:
        return JSONResponse(content={"success": False, "message": "Table name and feedback type are required."}, status_code=400)

    try:
        # Create database connection
        engine = create_engine(
        f'postgresql+psycopg2://{quote_plus(db_user)}:{quote_plus(db_password)}@{db_host}:{db_port}/{db_database}'
        )
        Session = sessionmaker(bind=engine)
        session = Session()

        # Sanitize input (Escape single quotes)
        table_name = escape_single_quotes(table_name)
        user_query = escape_single_quotes(user_query)
        sql_query = escape_single_quotes(sql_query)
        feedback_type = escape_single_quotes(feedback_type)

        # Insert feedback into database
        insert_query = f"""
        INSERT INTO lz_feedbacks (department, user_query, sql_query, table_name, data, feedback_type, feedback)
        VALUES ('unknown', :user_query, :sql_query, :table_name, 'no data', :feedback_type, 'user feedback')
        """

        session.execute(insert_query, {
        "table_name": table_name,
        "user_query": user_query,
        "sql_query": sql_query,
        "feedback_type": feedback_type
        })

        session.commit()
        session.close()

        return JSONResponse(content={"success": True, "message": "Feedback submitted successfully!"})

    except Exception as e:
        session.rollback()
        session.close()
        return JSONResponse(content={"success": False, "message": f"Error submitting feedback: {str(e)}"}, status_code=500)

@app.post("/transcribe-audio/")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcribes an audio file using OpenAI's Whisper API.

    Args:
        file (UploadFile): The audio file to transcribe.

    Returns:
        JSONResponse: A JSON response containing the transcription or an error message.
    """
    try:

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="Missing OpenAI API Key.")
        audio_bytes = await file.read()
        audio_bio = BytesIO(audio_bytes)
        audio_bio.name = "audio.webm"

        # Fix: Using OpenAI API correctly
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_bio
        )

        # Fix: Access transcript.text instead of treating it as a dictionary
        return {"transcription": transcript.text}

    except Exception as e:
        return JSONResponse(content={"error": f"Error transcribing audio: {str(e)}"}, status_code=500)
@app.get("/get_questions")
async def get_questions(subject: str):
    """
    Fetches questions from a CSV file in Azure Blob Storage based on the selected subject.

    Args:
        subject (str): The subject to fetch questions for.

    Returns:
        JSONResponse: A JSON response containing the list of questions or an error message.
    """
    csv_file_name = f"{subject}_questions.csv"
    blob_client = blob_service_client.get_blob_client(container=AZURE_CONTAINER_NAME, blob=csv_file_name)

    try:
        # Check if the blob exists
        if not blob_client.exists():
            print(f"file not found {csv_file_name}")
            return JSONResponse(
                content={"error": f"The file {csv_file_name} does not exist."}, status_code=404
            )

        # Download the blob content
        blob_content = blob_client.download_blob().content_as_text()

        # Read the CSV content
        questions_df = pd.read_csv(StringIO(blob_content))

        if "question" in questions_df.columns:
            questions = questions_df["question"].tolist()
        else:
            questions = questions_df.iloc[:, 0].tolist()

        return {"questions": questions}

    except Exception as e:
        return JSONResponse(
            content={"error": f"An error occurred while reading the file: {str(e)}"}, status_code=500
        )
@app.get("/get-tables/")
async def get_tables(selected_section: str):
    # Fetch table details for the selected section
    print("now starting...")
    table_details = get_table_details(selected_section)
    # Extract table names dynamically
    print("till table details")
    tables = [line.split("Table Name:")[1].strip() for line in table_details.split("\n") if "Table Name:" in line]
    # Return tables as JSON
    return {"tables": tables}

def display_table_with_styles(data, table_name):

    page_data = data # Get whole table data

    styled_table = page_data.style.set_table_attributes('style="border: 2px solid black; border-collapse: collapse;"') \
        .set_table_styles(
            [{
                'selector': 'th',
                'props': [('background-color', '#333'), ('color', 'white'), ('font-weight', 'bold'), ('font-size', '16px')]
            },
            {
                'selector': 'td',
                'props': [('border', '2px solid black'), ('padding', '5px')]
            }]
        ).to_html(escape=False)
    print(styled_table)
    return styled_table


# Invocation Function
def invoke_chain(question, messages, selected_model, selected_subject, selected_tools):
    try:
        print(selected_tools)
        history = ChatMessageHistory()
        for message in messages:
            if message["role"] == "user":
                history.add_user_message(message["content"])
            else:
                history.add_ai_message(message["content"])

        runner = graph.compile()
        result = runner.invoke({
            'question': question,
            'messages': history.messages,
            'selected_model': selected_model,
            'selected_subject': selected_subject,
            'selected_tools': selected_tools
        })

        print(f"Result from runner.invoke:", result)

        # Initialize response with common fields
        response = {
            "messages": result.get("messages", []),
            "follow_up_questions": {}
        }

        # Extract follow-up questions from all messages
        for message in result.get("messages", []):
            if hasattr(message, 'content'):
                content = message.content
                # Try to extract JSON from code block
                json_match = re.search(r'json\n({.*?})\n', content, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group(1))
                        for key, value in data.items():
                            if key.startswith('follow_up_') and value:
                                response["follow_up_questions"][key] = value
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON from message: {e}")

        # Handle different intents
        if result.get("SQL_Statement"):
            print("Intent Classification: db_query")
            response.update({
                "intent": "db_query",
                "SQL_Statement": result.get("SQL_Statement"),
                "chosen_tables": result.get("chosen_tables", []),
                "tables_data": result.get("tables_data", {}),
                "db": result.get("db")
            })
        elif result.get("messages") and len(result["messages"]) > 0:
            last_message = result["messages"][-1]
            if hasattr(last_message, 'name'):
                print(f"Intent Classification: {last_message.name}")
                response.update({
                    "intent": last_message.name,
                    "search_results": last_message.content
                })
            else:
                print("Intent Classification: Unknown (no message name)")
                response.update({
                    "intent": "unknown",
                    "message": "This intent is not yet implemented."
                })

        print("Final response with follow-ups:", response)
        return response

    except Exception as e:
        print("Error:", e)
        return {
            "error": str(e),
            "message": "Insufficient information to generate SQL Query."
        }

@app.post("/submit")
async def submit_query(
    section: str = Form(...),
    example_question: str = Form(...),
    user_query: str = Form(...),
    tool_selected: List[str] = Form(default=[]),
    page: Optional[int] = Query(1),
    records_per_page: Optional[int] = Query(5),
):
    selected_subject = section
    session_state['user_query'] = user_query

    prompt = user_query if user_query else example_question
    if 'messages' not in session_state:
        session_state['messages'] = []

    session_state['messages'].append({"role": "user", "content": prompt})

    try:
        result = invoke_chain(
            prompt, session_state['messages'], "gpt-4o-mini", selected_subject, tool_selected
        )

        response_data = {
            "user_query": session_state['user_query'],
            "follow_up_questions": {}  # Initialize as empty
        }

        # Extract follow-up questions from all messages
        if "messages" in result:
            for message in result["messages"]:
                if hasattr(message, 'content'):
                    content = message.content
                    print(f"Message content for follow-up extraction: {content}")  # Debug
                    follow_ups = extract_follow_ups(content)
                    print(f"Extracted follow-ups: {follow_ups}")  # Debug
                    if follow_ups:
                        response_data["follow_up_questions"].update(follow_ups)

        # Handle different intents
        if result["intent"] == "db_query":
            session_state['generated_query'] = result.get("SQL_Statement", "")
            session_state['chosen_tables'] = result.get("chosen_tables", [])
            session_state['tables_data'] = result.get("tables_data", {})

            tables_html = []
            for table_name, data in session_state['tables_data'].items():
                html_table = display_table_with_styles(data, table_name)
                tables_html.append({
                    "table_name": table_name,
                    "table_html": html_table,
                })
            chat_insight = None
            if result["chosen_tables"]:

                insights_prompt = insight_prompt.format(
                    sql_query=result["SQL_Statement"],
                    table_data=result["tables_data"]
                )

                chat_insight = llm.invoke(insights_prompt).content


            response_data.update({
                "query": session_state['generated_query'],
                "tables": tables_html,
                "chat_insight":chat_insight
            })

        elif result["intent"] == "researcher":
            response_data["search_results"] = result.get("search_results", "No results found.")

        elif result["intent"] == "intellidoc":
            response_data["search_results"] = result.get("search_results", "No results found.")

        print(f"Final response data with follow-ups: {response_data}")  # Debug
        return JSONResponse(content=response_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing the prompt: {str(e)}")

@app.get("/get_table_data/")
async def get_table_data(
    table_name: str = Query(...),
    page_number: int = Query(1),
    records_per_page: int = Query(10),
):
    """Fetch paginated and styled table data."""
    try:
        # Check if the requested table exists in session state
        if "tables_data" not in session_state or table_name not in session_state["tables_data"]:
            raise HTTPException(status_code=404, detail=f"Table {table_name} data not found.")

        # Retrieve the data for the specified table
        data = session_state["tables_data"][table_name]
        total_records = len(data)
        total_pages = (total_records + records_per_page - 1) // records_per_page

        # Ensure valid page number
        if page_number < 1 or page_number > total_pages:
            raise HTTPException(status_code=400, detail="Invalid page number.")

        # Slice data for the requested page
        start_index = (page_number - 1) * records_per_page
        end_index = start_index + records_per_page
        page_data = data.iloc[start_index:end_index]

        # Style the table as HTML
        styled_table = (
            page_data.style.set_table_attributes('style="border: 2px solid black; border-collapse: collapse;"')
            .set_table_styles([
                {'selector': 'th', 'props': [('background-color', '#333'), ('color', 'white'), ('font-weight', 'bold'), ('font-size', '16px')]},
                {'selector': 'td', 'props': [('border', '2px solid black'), ('padding', '5px')]},
            ])
            .to_html(escape=False)  # Render as HTML
        )

        return {
            "table_html": styled_table,
            "page_number": page_number,
            "total_pages": total_pages,
            "total_records": total_records,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating table data: {str(e)}")


class Session:
    def init(self):
        self.data = {}

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value

    def pop(self, key, default=None):
        return self.data.pop(key, default)

    def contains(self, item):
        return item in self.data

    def items(self):
        return self.data.items()

    def keys(self):
        return self.data.keys()

    def values(self):
        return self.data.values()

    def iter(self):
        return iter(self.data)
session = Session()

def hybrid_retrieve(query, docstore, vector_index, bm25_retriever, alpha=0.5):
    """Perform hybrid retrieval using BM25 and vector-based retrieval."""
    # Get results from BM25
    try:
        bm25_results = bm25_retriever.retrieve(query)
        # Get results from the vector store
        vector_results = vector_index.as_retriever(similarity_top_k=2).retrieve(query)
    except Exception as e:
        logging.error(e)
        return JSONResponse("Error with retriever")
    # Combine results with weighting
    combined_results = {}
    # Weight BM25 results
    for result in bm25_results:
        combined_results[result.id_] = combined_results.get(result.id_, 0) + (1 - alpha)
    # Weight vector results
    for result in vector_results:
        combined_results[result.id_] = combined_results.get(result.id_, 0) + alpha

    # Sort results based on the combined score
    sorted_results = sorted(combined_results.items(), key=lambda x: x[1], reverse=True)
    # Return the top N results
    return [docstore.get_document(doc_id) for doc_id, _ in sorted_results[:4]]

@app.route("/admin", methods=["GET", "POST"])
async def admin_page(request: Request):
    """Admin page to manage documents."""
    try:
        if request.method == "POST":
            form_data = await request.form()  # Parse the form data
            selected_section = form_data.get("section")

            # Ensure selected_section is valid
            if selected_section not in subject_areas2:
                raise ValueError("Invalid section selected.")

            collection_name = COLLECTION[subject_areas2.index(selected_section)]
            db_path = Chroma_DATABASE[subject_areas2.index(selected_section)]

            logging.info(f"Selected section: {selected_section}, Collection: {collection_name}, DB Path: {db_path}")

            return templates.TemplateResponse(
                'admin.html',
                {
                    "request": request,
                    "section": selected_section,
                    "collection": collection_name,
                    "db_path": db_path
                }
            )

        logging.info('Rendering admin page')
        return templates.TemplateResponse(
            'admin.html',
            {
                "request": request,
                "sections":subject_areas2
            }
        )
    except Exception as e:
        logging.error(f"Error rendering admin page: {e}")
        return JSONResponse(
            {"status": "error", "message": f"Error rendering admin page: {str(e)}"},
            status_code=500
        )

def upload_to_blob_storage(
                    connect_str: str, container_name: str,collection_name, file_content, file_name
                ):
                    blob_service_client = BlobServiceClient.from_connection_string(connect_str)

                    # Ensure the container exists and create if necessary
                    container_client = blob_service_client.get_container_client(container_name)
                    blob_name = f"{collection_name}/{file_name}"
                    blob_client = container_client.get_blob_client(blob_name)

                    print(f"Uploading {file_name} to {blob_name}...")
                    blob_client.upload_blob(file_content, overwrite=True)

@app.post("/upload")
async def upload_files(
    request: Request,
    files: List[UploadFile] = File(...),
    section : str = Form(...)
):
    """Handle file uploads for documents."""
    try:

        selected_section = section
        print(selected_section)
        # Ensure selected_section is valid
        if selected_section not in subject_areas2:
            raise ValueError("Invalid section selected.")

        collection_name = COLLECTION[subject_areas2.index(selected_section)]
        print("collection name",collection_name)
        db_path = Chroma_DATABASE[subject_areas2.index(selected_section)]

        print(f"Selected section: {selected_section}, Collection: {collection_name}, DB Path: {db_path}")

        if files:
            # logging.info(f"Handling upload for collection: {collection}, DB Path: {db_path}")

            for file in files:
                file_content = await file.read()
                file_name = file.filename

                upload_to_blob_storage(
                    AZURE_STORAGE_CONNECTION_STRING,
                    AZURE_CONTAINER_NAME,
                    collection_name,
                    file_content,
                    file_name,
                )

                try:
                    # Parse the uploaded file using LlamaParse
                    parsed_text =   await use_llamaparse(file_content, file_name)

                    # Split the parsed document into chunks
                    base_splitter = SentenceSplitter(chunk_size=512, chunk_overlap=100)
                    nodes = base_splitter.get_nodes_from_documents([Document(text=parsed_text)])

                    # Initialize storage context (defaults to in-memory)
                    storage_context = StorageContext.from_defaults()

                    # Prepare for storing document chunks
                    base_file_name = os.path.basename(file_name)
                    chunk_ids = []
                    metadatas = []

                    for i, node in enumerate(nodes):
                        chunk_id = f"{base_file_name}_{i + 1}"
                        chunk_ids.append(chunk_id)

                        metadata = {"type": base_file_name, "source": file_name}
                        metadatas.append(metadata)

                        document = Document(text=node.text, metadata=metadata, id_=chunk_id)
                        storage_context.docstore.add_documents([document])

                    # Load existing documents from the .json file if it exists
                    for i in range(len(DOCSTORE)):
                        if collection_name in DOCSTORE[i]:
                            coll = DOCSTORE[i]
                            print("collection name",coll)
                            break
                    existing_documents = {}
                    if os.path.exists(coll):
                        with open(coll, "r") as f:
                            existing_documents = json.load(f)

                        # Persist the storage context (if necessary)
                        storage_context.docstore.persist(coll)

                        # Load new data from the same file (or another source)
                        with open(coll, "r") as f:
                            st_data = json.load(f)

                        # Update existing_documents with st_data
                        for key, value in st_data.items():
                            if key in existing_documents:
                                # Ensure the existing value is a list before extending
                                if isinstance(existing_documents[key], list):
                                    existing_documents[key].extend(
                                        value
                                    )  # Merge lists if key exists
                                else:
                                    # If it's not a list, you can choose to replace it or handle it differently
                                    existing_documents[key] = (
                                        [existing_documents[key]] + value
                                        if isinstance(value, list)
                                        else [existing_documents[key], value]
                                    )
                            else:
                                existing_documents[key] = value  # Add new key-value pair

                        merged_dict = {}
                        for d in existing_documents["docstore/data"]:
                            merged_dict.update(d)
                        final_dict = {}
                        final_dict["docstore/data"] = merged_dict

                        # Write the updated documents back to the JSON file
                        with open(coll, "w") as f:
                            json.dump(final_dict, f, indent=4)

                    else:
                        # Persist the storage context if the file does not exist
                        storage_context.docstore.persist(coll)


                    collection_instance = init_chroma_collection(db_path, collection_name)

                    embed_model = OpenAIEmbedding()
                    VectorStoreIndex(nodes, storage_context=storage_context, embed_model=embed_model)
                    batch_size = 500
                    for i in range(0, len(nodes), batch_size):
                        batch_nodes = nodes[i : i + batch_size]
                        try:
                            collection_instance.add(
                                documents=[node.text for node in batch_nodes],
                                metadatas=metadatas[i : i + batch_size],
                                ids=chunk_ids[i : i + batch_size],
                            )
                            time.sleep(5)  # Add a retry with a delay
                            logging.info(f"Files uploaded and processed successfully for collection: {collection_name}")
                            return JSONResponse({"status": "success", "message": "Documents uploaded successfully."})


                        except:
                            # Handle rate limit by adding a delay or retry mechanism
                            print("Rate limit error has occurred at this moment")
                            return JSONResponse({"status": "error", "message": f"Error processing file {file_name}."})



                except Exception as e:
                    logging.error(f"Error processing file {file_name}: {e}")
                    return JSONResponse({"status": "error", "message": f"Error processing file {file_name}."})

        logging.warning("No files uploaded.")
        return JSONResponse({"status": "error", "message": "No files uploaded."})
    except Exception as e:
        logging.error(f"Error in upload_files: {e}")
        return JSONResponse({"status": "error", "message": "Error during file upload."})

import json
import re


def extract_follow_ups(message_content):
    """Extract follow-up questions from the message content, including:
    1. JSON-formatted follow-up questions
    2. Related queries listed in the text
    3. "Related Query:" sections in the response"""

    follow_ups = {}

    try:
        # First try to extract JSON-formatted follow-ups (original logic)
        # Try to find JSON in code block first
        json_match = re.search(r'json\n({.*?})\n', message_content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(1))
            follow_ups.update({
                k: v for k, v in data.items()
                if k.startswith('follow_up_') and v and isinstance(v, str)
            })

        # If no code block, try parsing the whole content as JSON
        try:
            data = json.loads(message_content)
            follow_ups.update({
                k: v for k, v in data.items()
                if k.startswith('follow_up_') and v and isinstance(v, str)
            })
        except json.JSONDecodeError:
            pass

        # Now extract Related Queries from text - multiple patterns
        # Pattern 1: "Related Queries:" section
        related_queries_section = re.search(
            r'(Related Queries|Related Query):\s*(.*?)(?=\n\n|\Z)',
            message_content,
            re.DOTALL | re.IGNORECASE
        )

        if related_queries_section:
            queries_text = related_queries_section.group(2)
            # Extract numbered questions or bullet points
            numbered_questions = re.findall(
                r'(?:\d+\.|\-)\s*(.*?)(?=\n(?:\d+\.|\-)|\n*\Z)',
                queries_text,
                re.DOTALL
            )

            # Add to follow_ups with follow_up_N keys
            for i, question in enumerate(numbered_questions, len(follow_ups) + 1):
                key = f'follow_up_{i}'
                follow_ups[key] = question.strip()

        # Pattern 2: Questions embedded in the text after "Related Query:"
        embedded_queries = re.findall(
            r'Related Query:\s*\n*(.*?)(?=\n\n|\Z)',
            message_content,
            re.DOTALL | re.IGNORECASE
        )

        if embedded_queries:
            for i, query in enumerate(embedded_queries, len(follow_ups) + 1):
                # Clean up the query (remove leading/trailing whitespace, quotes, etc.)
                clean_query = query.strip().strip('"').strip("'").strip('-').strip()
                if clean_query:
                    key = f'follow_up_{i}'
                    follow_ups[key] = clean_query

    except Exception as e:
        print(f"Error extracting follow-ups: {e}")

    return follow_ups

async def use_llamaparse(file_content, file_name):
    try:
        with open(file_name, "wb") as f:
            f.write(file_content)

        # Ensure the result_type is 'text', 'markdown', or 'json'
        parser = LlamaParse(result_type='text', verbose=True, language="en", num_workers=2)
        documents =  await parser.aload_data([file_name])

        os.remove(file_name)

        res = ''
        for i in documents:
            res += i.text + " "
        return res
    except Exception as e:
        logging.error(f"Error parsing file: {e}")
        raise

def init_chroma_collection(db_path, collection_name):
    try:
        db = chromadb.PersistentClient(path=db_path)
        collection = db.get_or_create_collection(collection_name, embedding_function=openai_ef)
        logging.info(f"Initialized Chroma collection: {collection_name} at {db_path}")
        return collection
    except Exception as e:
        logging.error(f"Error initializing Chroma collection: {e}")
        raise


@app.post("/show_documents")
async def show_documents(request: Request,
                          section: str = Form(...)):
    """Show available documents."""
    try:

        selected_section = section
        # Ensure selected_section is valid
        if selected_section not in subject_areas2:
            raise ValueError("Invalid section selected.")

        collection_name = COLLECTION[subject_areas2.index(selected_section)]
        db_path = Chroma_DATABASE[subject_areas2.index(selected_section)]

        logging.info(f"Selected section: {selected_section}, Collection: {collection_name}, DB Path: {db_path}")

        if not collection_name or not db_path:
            raise ValueError("Missing 'collection' or 'db_path' query parameters.")

        # Initialize the collection
        collection = init_chroma_collection(db_path, collection_name)

        # Retrieve metadata and IDs from the collection
        docs = collection.get()['metadatas']
        ids = collection.get()['ids']

        # Create a dictionary mapping document names to IDs
        doc_name_to_id = {}
        for doc_id, meta in zip(ids, docs):
            if 'source' in meta:
                doc_name = meta['source'].split('\\')[-1]
                if doc_name not in doc_name_to_id:
                    doc_name_to_id[doc_name] = []
                doc_name_to_id[doc_name].append(doc_id)

        # Get the unique document names
        doc_list = list(doc_name_to_id.keys())
        logging.info(f"Documents retrieved successfully for collection: {collection_name}")
        return doc_list



    except Exception as e:
        logging.error(f"Error showing documents: {e}")
        return JSONResponse({"status": "error", "message": "Error showing documents."})

@app.post("/delete_document")
async def delete_document(request: Request,
                         section: str = Form(...),
                          doc_name: str = Form(...)):
    """Handle document deletion."""
    try:
        selected_section = section
    # Ensure selected_section is valid
        if selected_section not in subject_areas2:
            raise ValueError("Invalid section selected.")

        collection_name = COLLECTION[subject_areas2.index(selected_section)]
        db_path = Chroma_DATABASE[subject_areas2.index(selected_section)]

        logging.info(f"Selected section: {selected_section}, Collection: {collection_name}, DB Path: {db_path}")
        # Initialize the collection
        collection = init_chroma_collection(db_path, collection_name)
        print("document to be deleted",doc_name)

        if doc_name:
              def delete_from_blob_storage(connect_str: str, container_name: str, file_name: str,collection_name):
                    # Create a BlobServiceClient to interact with the Azure Blob Storage
                    blob_service_client = BlobServiceClient.from_connection_string(connect_str)

                    # Get the container client
                    container_client = blob_service_client.get_container_client(container_name)

                    # Create the blob name with the collection prefix
                    blob_name = f"{collection_name}/{file_name}"

                    # Get the blob client for the specific file (blob)
                    blob_client = container_client.get_blob_client(blob_name)

                    # Delete the specified blob (file)
                    try:
                        print(f"Deleting {blob_name} from blob storage...")
                        blob_client.delete_blob()
                        print(
                            f"Blob '{blob_name}' deleted successfully from container '{container_name}'."
                        )
                    except Exception as e:
                        print(f"Failed to delete blob: {e}")
        # Retrieve metadata and IDs from the collection
        docs = collection.get()['metadatas']
        ids = collection.get()['ids']

        # Create a dictionary mapping document names to IDs
        doc_name_to_id = {}
        for doc_id, meta in zip(ids, docs):
            if 'source' in meta:
                name = meta['source'].split('\\')[-1]
                if name not in doc_name_to_id:
                    doc_name_to_id[name] = []
                doc_name_to_id[name].append(doc_id)

        # Get the unique document names
        ids_to_delete = doc_name_to_id.get(doc_name, [])

        print("Document name: ", doc_name)
        print("IDs to delete: ", ids_to_delete)

        delete_from_blob_storage(
                        AZURE_STORAGE_CONNECTION_STRING,
                        AZURE_CONTAINER_NAME,
                        doc_name,
                        collection_name )



        if ids_to_delete:

            # Attempt deletio
            collection.delete(ids=ids_to_delete)

             # Step 1: Read the JSON file
            for i in range(len(DOCSTORE)):
                if collection_name in DOCSTORE[i]:
                    coll = DOCSTORE[i]
                    break
            with open(coll, 'r') as file:
                data = json.load(file)["docstore/data"]

            for i in ids_to_delete:
                del data[i]

            final_dict = {}
            final_dict["docstore/data"] = data


            with open(coll, 'w') as file:
                json.dump(final_dict, file, indent=4)

            logging.info(f"Document '{doc_name}' deleted successfully.")
            return JSONResponse({"status": "success", "message": f"Document '{doc_name}' deleted successfully."})
        else:
            logging.warning(f"Document '{doc_name}' not found for deletion.")
            return JSONResponse({"status": "error", "message": "Document not found."})
    except Exception as e:
        logging.error(f"Error deleting document '{doc_name}': {e}")
        print(f"Error deleting document: {e}")  # Print exception for debugging
        return JSONResponse({"status": "error", "message": "Error deleting document."})


# Add this configuration near your other app configurations
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Initialize Azure Form Recognizer client
endpoint = os.environ.get('endpoint')
key = os.environ.get('key')
document_analysis_client = DocumentAnalysisClient(
    endpoint=endpoint, credential=AzureKeyCredential(key)
)


# # Add this route to your FastAPI app
# @app.post("/process-document", response_class=HTMLResponse)
# async def process_document(
#     request: Request,
#     service: str = Form(...),
#     input_method: str = Form(...),
#     file: UploadFile = File(None),
#     bill_url: str = Form(None)
# ):
#     try:
#         # Determine the poller method based on service
#         if service == 'Invoices':
#             poller_method = 'prebuilt-invoice'
#         elif service == 'Renuka POC':
#             poller_method = 'Renuka'
#         elif service == 'Receipts':
#             poller_method = 'prebuilt-receipt'
#         elif service == 'AWB':
#             poller_method = 'finance_insight'
#         elif service == 'Packing Slip':
#             poller_method = 'packing_slip'
#         elif service == 'COMPOSED':
#             poller_method = 'composed_model'
#         else:
#             raise HTTPException(status_code=400, detail="Invalid service type")

#         # Process based on input method
#         if input_method == 'file' and file:
#             filename = secure_filename(file.filename)
#             file_path = os.path.join(UPLOAD_FOLDER, filename)

#             # Save the file temporarily
#             with open(file_path, "wb") as f:
#                 f.write(await file.read())
#             with open(file_path, "rb") as fh:
#                 file_buf = BytesIO(fh.read())

#             poller = document_analysis_client.begin_analyze_document(poller_method, file_buf)
#             os.remove(file_path)  # Clean up the temporary file

#         elif input_method == 'url' and bill_url:
#             poller = document_analysis_client.begin_analyze_document_from_url(poller_method, bill_url)
#         else:
#             raise HTTPException(status_code=400, detail="Invalid input method or missing data")

#         # Get results
#         bill_data = poller.result()
#         results = []

#         # Process results based on document type
#         if poller_method == 'prebuilt-invoice':
#             results = invoice_data(results, bill_data)
#         elif poller_method == 'Renuka':
#             results = renuka_data(results, bill_data)
#         elif poller_method == 'prebuilt-receipt':
#             results = reciept_data(results, bill_data)
#         elif poller_method == 'finance_insight':
#             results = awb_data(results, bill_data)
#         elif poller_method == 'packing_slip':
#             results = packing_data(results, bill_data)
#         elif poller_method == 'composed_model':
#             for idx, doc in enumerate(bill_data.documents):
#                 doc_type = doc.doc_type
#                 if doc_type == "composed_model:finance_insight":
#                     results = awb_data(results, bill_data)
#                 elif doc_type == "composed_model:packing_slip":
#                     results = packing_data(results, bill_data)

#         print("Results:", results)
#         return JSONResponse(content=results)


#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")
@app.post("/process-document", response_class=HTMLResponse)
async def process_document(
    request: Request,
    service: str = Form(...),
    input_method: str = Form(...),
    files: List[UploadFile] = File(None),  # Changed from single file to list
    bill_url: str = Form(None)
):
    try:
        # Determine the poller method based on service
        if service == 'Invoices':
            poller_method = 'prebuilt-invoice'
        elif service == 'Renuka POC':
            poller_method = 'Renuka'
        elif service == 'Receipts':
            poller_method = 'prebuilt-receipt'
        elif service == 'AWB':
            poller_method = 'finance_insight'
        elif service == 'Packing Slip':
            poller_method = 'packing_slip'
        elif service == 'COMPOSED':
            poller_method = 'composed_model'
        else:
            raise HTTPException(status_code=400, detail="Invalid service type")

        all_results = []  # To store results from all files

        # Process based on input method
        if input_method == 'file' and files:
            for file in files:
                filename = secure_filename(file.filename)
                file_path = os.path.join(UPLOAD_FOLDER, filename)

                # Save the file temporarily
                with open(file_path, "wb") as f:
                    f.write(await file.read())
                with open(file_path, "rb") as fh:
                    file_buf = BytesIO(fh.read())

                poller = document_analysis_client.begin_analyze_document(poller_method, file_buf)
                os.remove(file_path)  # Clean up the temporary file

                # Get results for this file
                bill_data = poller.result()
                results = []

                # Process results based on document type
                if poller_method == 'prebuilt-invoice':
                    results = invoice_data(results, bill_data)
                elif poller_method == 'Renuka':
                    results = renuka_data(results, bill_data)
                elif poller_method == 'prebuilt-receipt':
                    results = reciept_data(results, bill_data)
                elif poller_method == 'finance_insight':
                    results = awb_data(results, bill_data)
                elif poller_method == 'packing_slip':
                    results = packing_data(results, bill_data)
                elif poller_method == 'composed_model':
                    for idx, doc in enumerate(bill_data.documents):
                        doc_type = doc.doc_type
                        if doc_type == "composed_model:finance_insight":
                            results = awb_data(results, bill_data)
                        elif doc_type == "composed_model:packing_slip":
                            results = packing_data(results, bill_data)

                all_results.append({
                    "filename": filename,
                    "results": results
                })

        elif input_method == 'url' and bill_url:
            poller = document_analysis_client.begin_analyze_document_from_url(poller_method, bill_url)
            bill_data = poller.result()
            results = []

            # Process results based on document type (same as above)
            if poller_method == 'prebuilt-invoice':
                results = invoice_data(results, bill_data)
            elif poller_method == 'Renuka':
                results = renuka_data(results, bill_data)
            elif poller_method == 'prebuilt-receipt':
                results = reciept_data(results, bill_data)
            elif poller_method == 'finance_insight':
                results = awb_data(results, bill_data)
            elif poller_method == 'packing_slip':
                results = packing_data(results, bill_data)
            elif poller_method == 'composed_model':
                for idx, doc in enumerate(bill_data.documents):
                    doc_type = doc.doc_type
                    if doc_type == "composed_model:finance_insight":
                        results = awb_data(results, bill_data)
                    elif doc_type == "composed_model:packing_slip":
                        results = packing_data(results, bill_data)

            all_results.append({
                "url": bill_url,
                "results": results
            })
        else:
            raise HTTPException(status_code=400, detail="Invalid input method or missing data")

        # print("All Results:", all_results)
        return JSONResponse(content=all_results)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

# FIELD_MAP = {
#     "Invoice Number": "invoice_number",
#     "Invoice Date": "invoice_date",
#     "Vendor Name": "vendor_name",
#     "Description": "description",
#     "Total Amount (In Ruppees)": "total_amount",
#     "GSTIN": "gstin"
# }

# @app.post("/insert_invoices")
# async def insert_invoices(request: Request):
#     try:
#         data = await request.json()

#         def extract_numeric(value):
#             """Extracts the first float-like number from a string like '4 Nos' or '3.5 hrs'."""
#             if not value or not value.strip():
#                 return 0.0
#             match = re.search(r"\d+(\.\d+)?", value.replace(",", ""))
#             return float(match.group()) if match else 0.0

#         def safe_cast(value):
#             if not value or not str(value).strip():
#                 return 0.0
#             # Remove anything that is not a digit or decimal point
#             cleaned = re.sub(r"[^\d.]+", "", value)
#             try:
#                 return float(cleaned)
#             except ValueError:
#                 return 0.0


#         def safe_number_extract(value):
#             if not value or not str(value).strip():
#                 return 0
#             # Remove commas, slashes, hyphens, and non-numeric symbols
#             cleaned = re.sub(r"[^\d.]+", "", value)
#             return float(cleaned) if cleaned else 0

#         def preprocess_item(item):
#             """Preprocess item according to requirements:
#             - Remove if description is null/empty
#             - Fill 0 for null values in other columns
#             """
#             if not item.get("description"):
#                 return None

#             processed = {
#                 "description": item.get("description"),
#                 "qty": safe_number_extract(item.get("qty")),
#                 "weight": safe_number_extract(item.get("weight")),
#                 "rate": safe_cast(item.get("rate")),
#                 "amount": safe_cast(item.get("amount")),
#                 "total_amount": safe_cast(row.get("total_amount"))

#             }
#             return processed

#         conn = get_connection()
#         cur = conn.cursor()

#         for entry in data:
#             row = {}
#             raw_items = entry.get("items", [])

#             # ✅ Preprocess items - filter and fill nulls
#             items = []
#             for item in raw_items:
#                 processed = preprocess_item(item)
#                 if processed:
#                     items.append(processed)

#             for key, value in entry.items():
#                 if key == "items":
#                     continue
#                 mapped_key = FIELD_MAP.get(key)
#                 if mapped_key:
#                     row[mapped_key] = value

#             # ✅ Date conversion
#             invoice_date = None
#             if "invoice_date" in row and row["invoice_date"]:
#                 try:
#                     raw_date = row["invoice_date"].replace(" ", "")  # 🧹 Clean extra spaces

#                     invoice_date = try_multiple_formats(raw_date)
#                 except ValueError as e:
#                     raise HTTPException(status_code=400, detail=str(e))

#             # ✅ Insert into invoices (master)
#             cur.execute("""
#                 INSERT INTO invoices (
#                     invoice_number,
#                     invoice_date,
#                     vendor_name,
#                     gstin,
#                     total_amount
#                 ) VALUES (%s, %s, %s, %s, %s)
#                 ON CONFLICT (invoice_number) DO NOTHING
#                 RETURNING id;
#             """, (
#                 row.get("invoice_number"),
#                 invoice_date,
#                 row.get("vendor_name"),
#                 row.get("gstin"),
#                 float(row.get("total_amount", "0").replace(",", "").strip()) if row.get("total_amount") else None
#             ))

#             result = cur.fetchone()
#             if result:
#                 invoice_id = result[0]
#             else:
#                 cur.execute("SELECT id FROM invoices WHERE invoice_number = %s", (row.get("invoice_number"),))
#                 invoice_id = cur.fetchone()[0]

#             # ✅ Insert into invoice_items (child table)
#             for item in items:
#                 cur.execute("""
#                     INSERT INTO invoice_items (
#                         invoice_id,
#                         description_of_goods,
#                         quantity,
#                         weight,
#                         rate,
#                         amount
#                     ) VALUES (%s, %s, %s, %s, %s, %s);
#                 """, (
#                     invoice_id,
#                     item["description"],  # Guaranteed to exist due to preprocessing
#                     item["qty"],         # Guaranteed to be 0 if null
#                     item["weight"],      # Guaranteed to be 0 if null
#                     item["rate"],        # Guaranteed to be 0 if null
#                     item["amount"]       # Guaranteed to be 0 if null
#                 ))

#         conn.commit()
#         cur.close()
#         conn.close()

#         return {"message": "Invoice data and items inserted successfully!"}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

def clean_date_string(date_str):
    """Clean date string by removing spaces around separators"""
    if not date_str:
        return ""
    date_str = str(date_str).strip()
    # Remove spaces around date separators
    date_str = re.sub(r'\s*([/.-])\s*', r'\1', date_str)

    # Remove any trailing non-digit characters (like hyphens, slashes, etc.)
    date_str = re.sub(r'[^0-9]+$', '', date_str)
    
    return date_str

# def parse_date(date_str):
#     """Robust date parser that handles messy formats including spaces"""
#     if not date_str:
#         return None


#     cleaned_date = clean_date_string(date_str)

#     # List of possible date formats to try (order matters!)
#     formats = [
#         "%d/%m/%Y",    # 06/05/2025
#         "%d-%m-%Y",    # 06-05-2025
#         "%d.%m.%Y",    # 06.05.2025
#         "%Y-%m-%d",    # 2025-05-06 (ISO)
#         "%d/%m/%y",    # 06/05/25
#         "%d-%b-%y",    # 06-May-25
#         "%b %d, %Y",   # May 06, 2025
#     ]

#     for fmt in formats:
#         try:
#             return datetime.strptime(cleaned_date, fmt).date()
#         except ValueError:
#             continue

#     raise ValueError(f"Unrecognized date format: '{date_str}'. Cleaned: {date_str}")
def parse_date(date_str):
    try:
        # Handle date format like '6-May-25'
        return datetime.strptime(date_str, "%d-%b-%y")
    except ValueError as e:
        logger.error(f"Date parsing error for '{date_str}': {e}")
        raise ValueError(f"Unsupported date format: {date_str} - {str(e)}")

def safe_text(value):
    """Returns 'NA' if value is None or empty string"""
    if value is None or (isinstance(value, str) and not value.strip()):
        return "NA"
    return value

@app.post("/insert_invoices")
async def insert_invoices(request: Request):
    conn = None
    cur = None

    # Define field mappings
    FIELD_MAP = {
        "Invoice ID": "invoice_id",
        "Invoice Number": "invoice_number",
        "Invoice Date": "invoice_date",
        "Vendor Name": "vendor_name",
        "Invoice Total": "invoice_total",
        "Vendor Address": "vendor_address",
        "Vendor Address Recipient": "vendor_address_recipient",
        "Customer Name": "customer_name",
        "Purchase Order": "purchase_order",
        "Billing Address": "billing_address",
        "Billing Address Recipient": "billing_address_recipient",
        "Subtotal": "subtotal",
        "Total Tax": "total_tax",
        "Customer Address": "customer_address",
        "Customer Address Recipient": "customer_address_recipient",
        "Shipping Address": "shipping_address",
        "Shipping Address Recipient": "shipping_address_recipient",
        "Due Date": "due_date",
        "Amount Due": "amount_due",
        "Service Start Date": "service_start_date",
        "Service End Date": "service_end_date",
        "Customer ID": "customer_id"
    }

    def safe_text(value):
        """Convert None to 'NA' for text fields"""
        return "NA" if value is None else str(value).strip()

    def parse_date_safe(date_value):
        """Safely parse date from string or return None"""
        if date_value is None:
            return None
        if isinstance(date_value, datetime):
            return date_value.date()
        try:
            # Handle string dates
            if isinstance(date_value, str):
                return parse_date(date_value).date()
            return None
        except:
            return None

    try:
        data = await request.json()
        logger.info(f"Data received for insertion: {data}")

        def clean_numeric(value):
            """Robust cleaning of numeric values"""
            if value is None:
                return 0.0
            if isinstance(value, (int, float)):
                return float(value)

            str_value = str(value).strip()
            if not str_value:
                return 0.0

            # Handle currency symbols and thousand separators
            cleaned = re.sub(r"[^\d.]", "", str_value.replace('₹', '').strip())
            if "/" in str_value:
                cleaned = cleaned.split("/")[0]

            try:
                return float(cleaned) if cleaned else 0.0
            except ValueError as e:
                logger.warning(f"Could not convert '{value}' to float: {e}")
                return 0.0

        def preprocess_item(item):
            """Process invoice items with proper field mapping"""
            if not item.get("description"):
                logger.warning("Item missing description")
                return None

            return {
                "item_name": item.get("item_name", ""),
                "description": item["description"],
                "product_code": item.get("product_code", ""),
                "quantity": clean_numeric(item.get("quantity")),
                "unit_price": clean_numeric(item.get("unit_price")),
                "amount": clean_numeric(item.get("amount"))
            }

        conn = get_db_connection()
        cur = conn.cursor()

        for entry in data:
            try:
                # Map fields using FIELD_MAP
                row = {}
                items = [preprocess_item(i) for i in entry.get("items", []) if preprocess_item(i)]

                for key, value in entry.items():
                    if key == "items":
                        continue
                    if mapped_key := FIELD_MAP.get(key):
                        if mapped_key in ["invoice_total", "subtotal", "total_tax", "amount_due"]:
                            row[mapped_key] = clean_numeric(value)
                        elif mapped_key.endswith("_date"):
                            row[mapped_key] = parse_date_safe(value)
                        else:
                            row[mapped_key] = safe_text(value)

                # Determine invoice ID (fallback to invoice number if needed)
                invoice_id = row.get("invoice_id") or row.get("invoice_number")
                if not invoice_id:
                    raise HTTPException(
                        status_code=400,
                        detail="Missing both Invoice ID and Invoice Number"
                    )

                # Insert invoice
                cur.execute("""
                    INSERT INTO invoice(
                        invoice_id,
                        invoice_date,
                        vendor_name,
                        invoice_total,
                        vendor_address,
                        vendor_address_recipient,
                        customer_name,
                        purchase_order,
                        billing_address,
                        billing_address_recipient,
                        subtotal,
                        total_tax,
                        customer_address,
                        customer_address_recipient,
                        shipping_address,
                        shipping_address_recipient,
                        due_date,
                        amount_due,
                        service_start_date,
                        service_end_date,
                        customer_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (invoice_id) DO NOTHING
                    RETURNING invoice_id;
                """, (
                    invoice_id,
                    row.get("invoice_date"),
                    safe_text(row.get("vendor_name")),
                    row.get("invoice_total", 0.0),
                    safe_text(row.get("vendor_address")),
                    safe_text(row.get("vendor_address_recipient")),
                    safe_text(row.get("customer_name")),
                    safe_text(row.get("purchase_order")),
                    safe_text(row.get("billing_address")),
                    safe_text(row.get("billing_address_recipient")),
                    row.get("subtotal", 0.0),
                    row.get("total_tax", 0.0),
                    safe_text(row.get("customer_address")),
                    safe_text(row.get("customer_address_recipient")),
                    safe_text(row.get("shipping_address")),
                    safe_text(row.get("shipping_address_recipient")),
                    row.get("due_date"),
                    row.get("amount_due", 0.0),
                    row.get("service_start_date"),
                    row.get("service_end_date"),
                    safe_text(row.get("customer_id"))
                ))

                # If no rows were inserted (due to conflict), fetch existing ID
                if not cur.fetchone():
                    cur.execute("SELECT invoice_id FROM invoice WHERE invoice_id = %s", (invoice_id,))
                    if not (result := cur.fetchone()):
                        raise HTTPException(
                            status_code=400,
                            detail=f"Failed to insert or retrieve invoice {invoice_id}"
                        )

                # Insert items
                for item in items:
                    cur.execute("""
                        INSERT INTO invoice_item_list (
                            invoice_id,
                            item_name,
                            description,
                            product_code,
                            quantity,
                            unit_price,
                            amount
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """, (
                        invoice_id,
                        item["item_name"],
                        item["description"],
                        item["product_code"],
                        item["quantity"],
                        item["unit_price"],
                        item["amount"]
                    ))

                logger.info(f"Successfully processed invoice {invoice_id}")

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error processing invoice: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error processing invoice: {str(e)}"
                )

        conn.commit()
        return {"message": f"Successfully processed {len(data)} invoices"}

    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
