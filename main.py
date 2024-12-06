from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from crewai import Crew, Task
from agents import create_jared_crew
from security import SecureEmailHandler, EmailWorkflowOrchestrator, EmailAgentTelemetry
import uvicorn
import os
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Jared Email Assistant API")
jared_crew = create_jared_crew()
secure_handler = SecureEmailHandler()
telemetry = EmailAgentTelemetry()

# Initialize workflow orchestrator (we'll add vector store integration later)
workflow = EmailWorkflowOrchestrator(jared_crew, None)

# OAuth2 Configuration
CLIENT_SECRETS_FILE = "client_secrets.json"
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly',
          'https://www.googleapis.com/auth/gmail.send']

class EmailRequest(BaseModel):
    to: str
    subject: str
    body: str

class EmailQuery(BaseModel):
    max_results: Optional[int] = 10
    query: Optional[str] = None

@app.post("/read-emails")
async def read_emails(query: EmailQuery):
    """Read and analyze emails"""
    try:
        telemetry.log_email_interaction("read_emails", {"query": query.dict()})
        
        # Create crew and tasks
        crew = Crew(
            agents=[jared_crew['reader'], jared_crew['analyzer']],
            tasks=[
                Task(
                    description=f"Read {query.max_results} emails with query: {query.query}",
                    agent=jared_crew['reader']
                ),
                Task(
                    description="Analyze the emails and provide insights",
                    agent=jared_crew['analyzer']
                )
            ]
        )
        
        result = crew.kickoff()
        
        # Encrypt sensitive data before returning
        if result.get("sensitive_content"):
            result["sensitive_content"] = secure_handler.encrypt_sensitive_data(
                result["sensitive_content"]
            )
        
        return {"result": result}
    except Exception as e:
        telemetry.log_error("Failed to read emails", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send-email")
async def send_email(email: EmailRequest):
    """Compose and send an email"""
    try:
        telemetry.log_email_interaction("send_email", {"to": email.to, "subject": email.subject})
        
        # Process email through workflow
        workflow_result = await workflow.process_incoming_email({
            "to": email.to,
            "subject": email.subject,
            "content": email.body
        })
        
        # Create crew and tasks
        crew = Crew(
            agents=[jared_crew['composer']],
            tasks=[
                Task(
                    description=f"Send email to {email.to} with subject: {email.subject}",
                    agent=jared_crew['composer']
                )
            ]
        )
        
        result = crew.kickoff()
        return {
            "result": result,
            "workflow": workflow_result
        }
    except Exception as e:
        telemetry.log_error("Failed to send email", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-conversation")
async def analyze_conversation(query: EmailQuery):
    """Analyze email conversations"""
    try:
        telemetry.log_email_interaction("analyze_conversation", {"query": query.dict()})
        
        # Create crew and tasks
        crew = Crew(
            agents=[jared_crew['analyzer']],
            tasks=[
                Task(
                    description=f"Analyze conversation with query: {query.query}",
                    agent=jared_crew['analyzer']
                )
            ]
        )
        
        result = crew.kickoff()
        return {"result": result}
    except Exception as e:
        telemetry.log_error("Failed to analyze conversation", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/auth/callback")
async def auth_callback(request: Request):
    """Handle the OAuth2 callback from Google"""
    try:
        # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=f"http://{request.base_url.hostname}:{request.base_url.port}/auth/callback"
        )
        
        # Use the authorization server's response to fetch the OAuth 2.0 tokens
        authorization_response = str(request.url)
        flow.fetch_token(authorization_response=authorization_response)
        
        # Store the credentials
        credentials = flow.credentials
        # Here you should securely store the credentials for the user
        # For now, we'll just return a success message
        return {"message": "Successfully authenticated with Google!"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/auth/login")
async def login():
    """Initiate the OAuth2 login flow"""
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri="http://localhost:8000/auth/callback"
        )
        
        # Generate URL for request to Google's OAuth 2.0 server
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        return RedirectResponse(authorization_url)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
