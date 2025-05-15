from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import os
import json
from deepseek_logic import DeepSeekClient

# Create a static file directory (if it doesn't exist)
os.makedirs("static", exist_ok=True)

# Initialize the FastAPI application
app = FastAPI(title="邮件智能助手", description="基于DeepSeek AI的邮件智能助手系统")

# Add CORS middleware to allow cross-domain requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all sources
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all heads
)

# Mount the static file directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize the DeepSeek client
deepseek_client = DeepSeekClient()

# Request model
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = None
    action: Optional[str] = None  # Optional operation types: analyze, rewrite, translate, template, follow_up
    parameters: Optional[Dict[str, Any]] = None  # Operate specific parameters
    stream: Optional[bool] = False  # Whether to use stream output

class AnalyzeRequest(BaseModel):
    email_content: str
    stream: Optional[bool] = False

class RewriteRequest(BaseModel):
    email_content: str
    requirements: str
    stream: Optional[bool] = False

class TranslateRequest(BaseModel):
    email_content: str
    target_language: str
    stream: Optional[bool] = False

class TemplateRequest(BaseModel):
    scenario: str
    stream: Optional[bool] = False

class FollowUpRequest(BaseModel):
    previous_email: str
    instruction: str
    stream: Optional[bool] = False

# Response model
class ResponseModel(BaseModel):
    code: int
    data: Optional[Any] = None
    msg: str

# API Routing
@app.post("/chat", response_model=ResponseModel)
async def chat(request: ChatRequest):
    """
    Chat with the email assistant
    
    - **message**: The user's message
    - **history**: Conversation history (optional)
    - **action**: Specific action type (optional)
    - **parameters**: Action-specific parameters (optional)
    - **stream**: Whether to use streaming output (optional; defaults to False)
    """
    try:
        # If a stream output is requested
        if request.stream:
            return await handle_stream_chat(request)
            
        # The following is non-stream output processing 
        # Determine the processing method based on the action parameter
        if request.action:
            if request.action == "analyze" and request.parameters and "email_content" in request.parameters:
                return deepseek_client.analyze_email(request.parameters["email_content"])
            
            elif request.action == "rewrite" and request.parameters and "email_content" in request.parameters and "requirements" in request.parameters:
                return deepseek_client.rewrite_email(
                    request.parameters["email_content"],
                    request.parameters["requirements"]
                )
            
            elif request.action == "translate" and request.parameters and "email_content" in request.parameters and "target_language" in request.parameters:
                return deepseek_client.translate_email(
                    request.parameters["email_content"],
                    request.parameters["target_language"]
                )
            
            elif request.action == "template" and request.parameters and "scenario" in request.parameters:
                return deepseek_client.generate_email_template(request.parameters["scenario"])
            
            elif request.action == "follow_up" and request.parameters and "previous_email" in request.parameters and "instruction" in request.parameters:
                return deepseek_client.generate_follow_up_email(
                    request.parameters["previous_email"],
                    request.parameters["instruction"]
                )
            else:
                # Unknown or invalid operation, roll back to normal chat
                pass
        
        # Default situation: Generate regular responses
        return deepseek_client.generate_response(request.message, request.history)
    
    except Exception as e:
        return {"code": 400, "data": None, "msg": f"Error processing request: {str(e)}"}

async def handle_stream_chat(request: ChatRequest):
    """Handle streaming chat requests"""
    try:
        if request.action:
            if request.action == "analyze" and request.parameters and "email_content" in request.parameters:
                stream = deepseek_client.analyze_email_stream(request.parameters["email_content"])
                
            elif request.action == "rewrite" and request.parameters and "email_content" in request.parameters and "requirements" in request.parameters:
                stream = deepseek_client.rewrite_email_stream(
                    request.parameters["email_content"],
                    request.parameters["requirements"]
                )
                
            elif request.action == "translate" and request.parameters and "email_content" in request.parameters and "target_language" in request.parameters:
                stream = deepseek_client.translate_email_stream(
                    request.parameters["email_content"],
                    request.parameters["target_language"]
                )
                
            elif request.action == "template" and request.parameters and "scenario" in request.parameters:
                stream = deepseek_client.generate_email_template_stream(request.parameters["scenario"])
                
            elif request.action == "follow_up" and request.parameters and "previous_email" in request.parameters and "instruction" in request.parameters:
                stream = deepseek_client.generate_follow_up_email_stream(
                    request.parameters["previous_email"],
                    request.parameters["instruction"]
                )
                
            else:
                # Unknown or invalid operation, roll back to normal chat
                stream = deepseek_client.generate_stream_response(request.message, request.history)
        else:
            # Default: Generate streaming responses
            stream = deepseek_client.generate_stream_response(request.message, request.history)
        
        # Return a streaming response using plain text format instead of an event stream
        return StreamingResponse(
            stream,
            media_type="text/plain"
        )
            
    except Exception as e:
        error_json = json.dumps({"code": 400, "data": None, "msg": f"An error occurred when handling the streaming request: {str(e)}"}) + "\n"
        return StreamingResponse(
            iter([error_json]),
            media_type="text/plain"
        )

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat interface (for backward compatibility)"""
    request.stream = True
    return await handle_stream_chat(request)

@app.post("/analyze", response_model=ResponseModel)
async def analyze_email(request: AnalyzeRequest):
    """Analyze the content of the email, provide summaries and improvement suggestions"""
    try:
        if request.stream:
            return StreamingResponse(
                deepseek_client.analyze_email_stream(request.email_content),
                media_type="text/plain"
            )
        return deepseek_client.analyze_email(request.email_content)
    except Exception as e:
        return {"code": 400, "data": None, "msg": f"An error occurred while processing the request: {str(e)}"}

@app.post("/analyze/stream")
async def analyze_email_stream(request: AnalyzeRequest):
    """Stream analysis of email content (for backward compatibility)"""
    request.stream = True
    return await analyze_email(request)

@app.post("/rewrite", response_model=ResponseModel)
async def rewrite_email(request: RewriteRequest):
    """Rewrite the email according to specific requirements"""
    try:
        if request.stream:
            return StreamingResponse(
                deepseek_client.rewrite_email_stream(request.email_content, request.requirements),
                media_type="text/plain"
            )
        return deepseek_client.rewrite_email(request.email_content, request.requirements)
    except Exception as e:
        return {"code": 400, "data": None, "msg": f"An error occurred while processing the request: {str(e)}"}

@app.post("/rewrite/stream")
async def rewrite_email_stream(request: RewriteRequest):
    """Stream rewrite the email (for backward compatibility)"""
    request.stream = True
    return await rewrite_email(request)

@app.post("/translate", response_model=ResponseModel)
async def translate_email(request: TranslateRequest):
    """Translate the email into the specified language"""
    try:
        if request.stream:
            return StreamingResponse(
                deepseek_client.translate_email_stream(request.email_content, request.target_language),
                media_type="text/plain"
            )
        return deepseek_client.translate_email(request.email_content, request.target_language)
    except Exception as e:
        return {"code": 400, "data": None, "msg": f"An error occurred while processing the request: {str(e)}"}

@app.post("/translate/stream")
async def translate_email_stream(request: TranslateRequest):
    """Stream translation of emails (for backward compatibility)"""
    request.stream = True
    return await translate_email(request)

@app.post("/template", response_model=ResponseModel)
async def generate_template(request: TemplateRequest):
    """Generate email templates for specific scenarios"""
    try:
        if request.stream:
            return StreamingResponse(
                deepseek_client.generate_email_template_stream(request.scenario),
                media_type="text/plain"
            )
        return deepseek_client.generate_email_template(request.scenario)
    except Exception as e:
        return {"code": 400, "data": None, "msg": f"An error occurred while processing the request: {str(e)}"}

@app.post("/template/stream")
async def generate_template_stream(request: TemplateRequest):
    """Stream generate email templates (for backward compatibility)"""
    request.stream = True
    return await generate_template(request)

@app.post("/follow_up", response_model=ResponseModel)
async def generate_follow_up(request: FollowUpRequest):
    """Generate follow-up emails based on previous emails and instructions"""
    try:
        if request.stream:
            return StreamingResponse(
                deepseek_client.generate_follow_up_email_stream(request.previous_email, request.instruction),
                media_type="text/plain"
            )
        return deepseek_client.generate_follow_up_email(request.previous_email, request.instruction)
    except Exception as e:
        return {"code": 400, "data": None, "msg": f"An error occurred while processing the request: {str(e)}"}

@app.post("/follow_up/stream")
async def generate_follow_up_stream(request: FollowUpRequest):
    """Stream the subsequent emails (for backward compatibility)"""
    request.stream = True
    return await generate_follow_up(request)

@app.get("/")
async def root():
    """Redirect to the static HTML page"""
    return {"message": "The API of the email intelligent assistant has been launched. Please visit /static/index.html to use the Web interface"}

# When running as the main program
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 