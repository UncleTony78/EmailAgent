from cryptography.fernet import Fernet
import logging
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from datetime import datetime
import json
from typing import Optional, Dict, Any

class SecureEmailHandler:
    def __init__(self):
        """Initialize encryption handler with a new key"""
        self.encryption_key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.encryption_key)
    
    def encrypt_sensitive_data(self, data: str) -> bytes:
        """Encrypt sensitive email content
        
        Args:
            data: String data to encrypt
            
        Returns:
            Encrypted bytes
        """
        return self.cipher_suite.encrypt(data.encode())
    
    def decrypt_sensitive_data(self, encrypted_data: bytes) -> str:
        """Decrypt sensitive email content
        
        Args:
            encrypted_data: Encrypted bytes to decrypt
            
        Returns:
            Decrypted string
        """
        return self.cipher_suite.decrypt(encrypted_data).decode()
    
    def secure_store_credentials(self, credentials: Dict[str, Any]) -> bytes:
        """Securely store OAuth credentials
        
        Args:
            credentials: Dictionary containing OAuth credentials
            
        Returns:
            Encrypted credentials
        """
        return self.encrypt_sensitive_data(json.dumps(credentials))

class EmailWorkflowOrchestrator:
    def __init__(self, agents, vector_store):
        """Initialize workflow orchestrator
        
        Args:
            agents: CrewAI agents for email processing
            vector_store: Vector store for semantic search
        """
        self.agents = agents
        self.vector_store = vector_store
        self.telemetry = EmailAgentTelemetry()
    
    async def process_incoming_email(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming email through multilayered workflow
        
        Args:
            email: Dictionary containing email data
            
        Returns:
            Processing results and response
        """
        with self.telemetry.tracer.start_as_current_span("process_incoming_email") as span:
            try:
                # Analyze priority
                priority = await self.analyze_priority(email)
                span.set_attribute("email.priority", priority)
                
                # Retrieve context
                context = await self.vector_store.retrieve_context(email["content"])
                
                # Generate response based on priority
                if priority == "urgent":
                    response = await self.generate_immediate_response(email, context)
                    span.set_attribute("response.type", "immediate")
                elif priority == "followup":
                    response = await self.schedule_followup(email, context)
                    span.set_attribute("response.type", "followup")
                else:
                    response = await self.handle_normal_priority(email, context)
                    span.set_attribute("response.type", "normal")
                
                span.set_status(Status(StatusCode.OK))
                return {
                    "status": "success",
                    "priority": priority,
                    "response": response
                }
                
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR), str(e))
                self.telemetry.log_error("Email processing failed", str(e))
                raise
    
    async def analyze_priority(self, email: Dict[str, Any]) -> str:
        """Analyze email priority using CrewAI agents
        
        Args:
            email: Email data dictionary
            
        Returns:
            Priority level string
        """
        with self.telemetry.tracer.start_as_current_span("analyze_priority"):
            return await self.agents.priority_sorter.analyze(email)
    
    async def generate_immediate_response(self, email: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate immediate response for urgent emails
        
        Args:
            email: Email data
            context: Retrieved context
            
        Returns:
            Response data
        """
        with self.telemetry.tracer.start_as_current_span("generate_immediate_response"):
            return await self.agents.response_drafter.generate_immediate_response(email, context)
    
    async def schedule_followup(self, email: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule followup for non-urgent emails
        
        Args:
            email: Email data
            context: Retrieved context
            
        Returns:
            Scheduled followup data
        """
        with self.telemetry.tracer.start_as_current_span("schedule_followup"):
            return await self.agents.response_drafter.schedule_followup(email, context)
    
    async def handle_normal_priority(self, email: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle normal priority emails
        
        Args:
            email: Email data
            context: Retrieved context
            
        Returns:
            Response data
        """
        with self.telemetry.tracer.start_as_current_span("handle_normal_priority"):
            return await self.agents.response_drafter.generate_response(email, context)

class EmailAgentTelemetry:
    def __init__(self):
        """Initialize telemetry with logging and tracing"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        self.tracer = trace.get_tracer(__name__)
    
    def log_email_interaction(self, interaction_type: str, details: Dict[str, Any]) -> None:
        """Log email interaction with tracing
        
        Args:
            interaction_type: Type of interaction
            details: Interaction details
        """
        with self.tracer.start_as_current_span(interaction_type) as span:
            span.set_attribute("interaction.type", interaction_type)
            span.set_attribute("interaction.timestamp", datetime.now().isoformat())
            
            self.logger.info(f"Email Interaction: {interaction_type}")
            self.logger.debug(f"Details: {json.dumps(details)}")
    
    def log_error(self, message: str, error: str) -> None:
        """Log error with tracing
        
        Args:
            message: Error message
            error: Error details
        """
        with self.tracer.start_as_current_span("error") as span:
            span.set_attribute("error.message", message)
            span.set_attribute("error.details", error)
            span.set_status(Status(StatusCode.ERROR), error)
            
            self.logger.error(f"{message}: {error}")
