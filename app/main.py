import time
import uvicorn
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

from app.models import NewsDigestRequest, NewsDigestResponse
from app.graph import graph

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="Agentic-News API",
    description="An API for generating news digests using a multi-agent system.",
    version="1.0.0"
)

@app.post("/generate-digest", response_model=NewsDigestResponse)
async def generate_digest(request: NewsDigestRequest):
    """
    Endpoint to generate a news digest for a given query.
    """
    start_time = time.time()
    
    try:
        # The initial state for the graph
        initial_state = {"query": request.query}
        
        # Invoke the LangGraph workflow
        final_state = graph.invoke(initial_state)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Check if we got a valid result
        if not final_state or not final_state.get('final_digest'):
            raise HTTPException(status_code=500, detail="Failed to generate news digest. The workflow did not complete successfully.")

        response_data = {
            "digest": final_state['final_digest'],
            "metadata": {
                "query": request.query,
                "processing_time_seconds": round(duration, 2),
                "articles_found": len(final_state.get('urls', [])),
                "articles_summarized": len(final_state.get('final_digest', []))
            }
        }
        
        return NewsDigestResponse(**response_data)

    except Exception as e:
        # Generic error handling
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)