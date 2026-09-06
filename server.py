import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(PROJECT_ROOT, "backend")

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.main import app as fastapi_app

try:
    import gradio as gr

    with gr.Blocks(title="AI Data Science & AutoML Platform") as demo:
        gr.Markdown("# 🚀 AI Data Science & AutoML Platform")

    app = gr.mount_gradio_app(fastapi_app, demo, path="/gradio")
except Exception:
    app = fastapi_app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
