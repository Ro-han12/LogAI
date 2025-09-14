"""
Simple test workflow server to receive webhook events.
Run this to test the complete webhook flow.
"""

from fastapi import FastAPI, Request
import uvicorn
from datetime import datetime

app = FastAPI(title="Test Workflow Server")

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/api/workflows/trigger")
async def trigger_workflow(request: Request):
    """Receive webhook events from LogAI webhook server."""
    try:
        data = await request.json()
        
        print("🎉 WORKFLOW TRIGGERED!")
        print(f"📊 Event Type: {data.get('event_type')}")
        print(f"🔗 Repository: {data.get('repository')}")
        print(f"🌿 Branch: {data.get('branch')}")
        print(f"📝 PR #{data.get('pr_number')}: {data.get('pr_title')}")
        print(f"👤 Author: {data.get('author')}")
        print(f"⚡ Risk Level: {data.get('risk_level')}")
        print(f"📈 Changes: +{data.get('additions')} -{data.get('deletions')} ({data.get('changed_files_count')} files)")
        print(f"🕐 Processed: {data.get('processed_at')}")
        print("-" * 50)
        
        return {
            "status": "success",
            "message": "Workflow triggered successfully",
            "event_id": data.get("event_id"),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Error processing workflow: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    print("🚀 Starting Test Workflow Server...")
    print("📡 Listening on: http://localhost:3000")
    print("🔗 Webhook endpoint: http://localhost:3000/api/workflows/trigger")
    print("💡 This will receive events from your LogAI webhook server")
    print("-" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=3000)
