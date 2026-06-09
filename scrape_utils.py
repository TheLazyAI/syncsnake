import os
import re
import json
import urllib.request

import google.genai as genai
import google.genai.types as types


def get_api_key() -> str:
    """Retrieves the Gemini API key from environment or .env file."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key:
        return api_key
    for env_path in [".env", os.path.join(os.path.dirname(__file__), ".env")]:
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if line.startswith("GOOGLE_API_KEY=") or line.startswith("GEMINI_API_KEY="):
                        return line.strip().split("=", 1)[1]
    return ""


def make_client() -> genai.Client:
    """Returns a configured Gemini client."""
    return genai.Client(api_key=get_api_key())


def google_search_grounding(query: str, model: str = "gemini-2.5-flash", client: genai.Client = None) -> dict:
    """Uses Gemini SDK with Google Search grounding. Auto-instrumented by OpenInference."""
    if client is None:
        client = make_client()
    try:
        response = client.models.generate_content(
            model=model,
            contents=query,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.2,
            ),
        )
        text = response.text or ""
        links = []
        if response.candidates and response.candidates[0].grounding_metadata:
            for chunk in response.candidates[0].grounding_metadata.grounding_chunks or []:
                if chunk.web:
                    links.append({"title": chunk.web.title or "", "uri": chunk.web.uri or ""})
        return {"text": text, "links": links, "usage": _usage(response)}
    except Exception as e:
        return {"text": f"Error during search grounding: {e}", "links": [], "usage": {}}


def _usage(response) -> dict:
    """Extracts token usage from a Gemini response."""
    meta = getattr(response, "usage_metadata", None)
    if not meta:
        return {}
    return {
        "input_tokens": getattr(meta, "prompt_token_count", 0) or 0,
        "output_tokens": getattr(meta, "candidates_token_count", 0) or 0,
        "total_tokens": getattr(meta, "total_token_count", 0) or 0,
    }


def clean_html(html: str) -> str:
    """Cleans raw HTML into compact readable text for the LLM."""
    html = re.sub(r'<(script|style)\b[^>]*>([\s\S]*?)<\/\1>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<!--[\s\S]*?-->', '', html)
    html = re.sub(r'<(nav|footer|header)\b[^>]*>([\s\S]*?)<\/\1>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'\s+', ' ', html)
    html = re.sub(r'<h[1-6]\b[^>]*>(.*?)<\/h[1-6]>', r'\n# \1\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<a\b[^>]*href="([^"]*)"[^>]*>(.*?)<\/a>', r'[\2](\1)', html, flags=re.IGNORECASE)
    html = re.sub(r'<p\b[^>]*>', '\n\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<br\b[^>]*>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<li>', '\n- ', html, flags=re.IGNORECASE)
    html = re.sub(r'<[^>]+>', '', html)
    lines = [line.strip() for line in html.split('\n')]
    return '\n'.join([l for l in lines if l])


def fetch_url(url: str) -> str:
    """Fetches a URL and returns cleaned text content."""
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return clean_html(response.read().decode("utf-8", errors="ignore"))
    except Exception as e:
        return f"Error fetching {url}: {e}"


if __name__ == "__main__":
    print("Testing search grounding via google-genai SDK...")
    res = google_search_grounding("music sync licensing agencies Montreal")
    print("Text snippet:", res["text"][:300])
    print("Links found:", len(res["links"]))
    print("Tokens used:", res["usage"])
