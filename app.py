from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
from supabase import create_client, Client
from supabase_config import SUPABASE_URL, SUPABASE_KEY
from serpapi import GoogleSearch
import os
from dotenv import load_dotenv

app = FastAPI()

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StoreSearchRequest(BaseModel):
    topic: str
    phone: str

class SearchRequest(BaseModel):
    topic: str

def load_api_key():
    """Load API key from environment variables"""
    load_dotenv()
    serpapi_key = os.getenv('SERPAPI_KEY')
    if not serpapi_key:
        raise ValueError("SERPAPI_KEY not found in environment variables")
    return serpapi_key

def search_news(topic, api_key):
    """Search news using SerpAPI"""
    params = {
        "engine": "google",
        "q": f"{topic} news",
        "api_key": api_key,
        "tbm": "nws"  # Search in news
    }
    
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        return results.get("news_results", [])
    except Exception as e:
        print(f"Error during search: {str(e)}")
        return []

@app.get("/")
async def root():
    """Serve the index.html page"""
    return FileResponse("static/index.html")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/api/store-search")
async def store_search(request: StoreSearchRequest):
    """API endpoint for storing search data in Supabase"""
    try:
        # Validate input
        if not request.topic or not request.phone:
            raise HTTPException(status_code=400, detail="Topic and phone number are required")
        
        # Store in Supabase
        data = {
            "topic": request.topic,
            "phone": request.phone
        }
        
        result = supabase.table("newsroom").insert(data).execute()
        
        return {"status": "success", "data": result.data}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search")
async def api_search(request: SearchRequest):
    """API endpoint for news search"""
    try:
        topic = request.topic.strip()
        if not topic:
            raise HTTPException(status_code=400, detail="Topic cannot be empty")
        
        # Load API key
        serpapi_key = load_api_key()
        
        # Search news
        results = search_news(topic, serpapi_key)
        
        # Format results
        formatted_results = []
        for idx, result in enumerate(results, 1):
            formatted_result = {
                "number": idx,
                "title": result.get('title', 'No title'),
                "source": result.get('source', 'Unknown source'),
                "date": result.get('date', 'No date'),
                "link": result.get('link', 'No link'),
                "snippet": result.get('snippet', 'No snippet')
            }
            formatted_results.append(formatted_result)
        
        # Prepare response
        response = {
            "topic": topic,
            "summary": "News search completed successfully",  # Simplified for now
            "detailed_results": formatted_results
        }
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 