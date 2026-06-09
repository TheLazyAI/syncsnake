import os
import re
import json
import urllib.request
import urllib.parse

# Setup optional OpenTelemetry tracing
try:
    from opentelemetry import trace
    HAS_OTEL = True
    tracer = trace.get_tracer("sync_licensing_agent")
except ImportError:
    HAS_OTEL = False
    class DummySpan:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def set_attribute(self, key, value): pass
        def set_status(self, status): pass
    class DummyTracer:
        def start_as_current_span(self, name, *args, **kwargs):
            return DummySpan()
    tracer = DummyTracer()

def get_api_key():
    """Retrieves the API key from the local environment or the .env file."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        # Check current workspace directory first
        local_env = ".env"
        if os.path.exists(local_env):
            with open(local_env, "r") as f:
                for line in f:
                    if line.startswith("GOOGLE_API_KEY=") or line.startswith("GEMINI_API_KEY="):
                        api_key = line.strip().split("=", 1)[1]
                        return api_key
        # Fallback to absolute sonic env path
        env_path = "/Users/maryann/sonic/.env"
        if os.path.exists(env_path):
            try:
                with open(env_path, "r") as f:
                    for line in f:
                        if line.startswith("GOOGLE_API_KEY=") or line.startswith("GEMINI_API_KEY="):
                            api_key = line.strip().split("=", 1)[1]
                            break
            except Exception:
                pass
    return api_key

def google_search_grounding(query: str, model: str = "gemini-2.5-flash") -> dict:
    """Uses Gemini API with Google Search grounding to find information via REST API."""
    with tracer.start_as_current_span("google_search_grounding") as span:
        span.set_attribute("openinference.span.kind", "TOOL")
        span.set_attribute("input.value", query)
        span.set_attribute("model", model)
        
        api_key = get_api_key()
        if not api_key:
            err_msg = "Error: GEMINI_API_KEY or GOOGLE_API_KEY not found."
            span.set_attribute("output.value", err_msg)
            return {"text": err_msg, "links": []}
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        req_data = {
            "contents": [{
                "parts": [{"text": query}]
            }],
            "tools": [{"googleSearch": {}}]
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(req_data).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                
                # Extract text
                text = ""
                candidates = res_data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        text = parts[0].get("text", "")
                
                # Extract links
                links = []
                if candidates and "groundingMetadata" in candidates[0]:
                    metadata = candidates[0]["groundingMetadata"]
                    chunks = metadata.get("groundingChunks", [])
                    for chunk in chunks:
                        if "web" in chunk:
                            links.append({
                                "title": chunk["web"].get("title", ""),
                                "uri": chunk["web"].get("uri", "")
                            })
                
                span.set_attribute("output.value", text)
                span.set_attribute("links_count", len(links))
                return {"text": text, "links": links}
        except Exception as e:
            err_msg = f"Error during search grounding: {e}"
            span.set_attribute("output.value", err_msg)
            if HAS_OTEL:
                from opentelemetry.trace import Status, StatusCode
                span.set_status(Status(StatusCode.ERROR, description=str(e)))
            return {"text": err_msg, "links": []}

def clean_html(html: str) -> str:
    """Cleans up raw HTML to make it compact and readable for the LLM."""
    # Remove script and style elements
    html = re.sub(r'<(script|style)\b[^>]*>([\s\S]*?)<\/\1>', '', html, flags=re.IGNORECASE)
    # Remove HTML comments
    html = re.sub(r'<!--[\s\S]*?-->', '', html)
    # Remove navigation, header, footer if possible
    html = re.sub(r'<(nav|footer|header)\b[^>]*>([\s\S]*?)<\/\1>', '', html, flags=re.IGNORECASE)
    # Replace multiple spaces/newlines with single space/newline
    html = re.sub(r'\s+', ' ', html)
    # Convert some common tags to markdown-ish equivalents
    html = re.sub(r'<h[1-6]\b[^>]*>(.*?)<\/h[1-6]>', r'\n# \1\n', html, flags=re.IGNORECASE)
    # Replace links with markdown link
    html = re.sub(r'<a\b[^>]*href="([^"]*)"[^>]*>(.*?)<\/a>', r'[\2](\1)', html, flags=re.IGNORECASE)
    html = re.sub(r'<p\b[^>]*>', '\n\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<br\b[^>]*>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<li>', '\n- ', html, flags=re.IGNORECASE)
    # Remove all other tags
    html = re.sub(r'<[^>]+>', '', html)
    # Final cleanup of spacing
    lines = [line.strip() for line in html.split('\n')]
    return '\n'.join([l for l in lines if l])

def fetch_url(url: str) -> str:
    """Fetches a URL and returns cleaned text content."""
    # Ensure scheme
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
        
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
            return clean_html(html)
    except Exception as e:
        return f"Error fetching {url}: {e}"

if __name__ == "__main__":
    # Small test
    print("Testing search grounding REST API...")
    res = google_search_grounding("music sync licensing agencies Montreal")
    print("Text snippet:", res["text"][:300])
    print("Discovered links:", len(res["links"]))
