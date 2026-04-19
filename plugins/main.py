import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
import yt_dlp
import uvicorn

app = FastAPI()

TARGET_SITE = "https://shrutibots.site"

# --- KIRU-MUSIC SEARCH ENGINE ---
def search_youtube(query):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'extract_flat': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # YouTube par search karega
        info = ydl.extract_info(f"ytsearch5:{query}", download=False)
        return [{"title": x['title'], "url": f"https://www.youtube.com/watch?v={x['id']}", "id": x['id']} for x in info['entries']]

# --- API ENDPOINT ---
@app.get("/api/search")
async def api_search(q: str):
    try:
        results = search_youtube(q)
        return {"status": "success", "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- UI INJECTION (KIRU-MUSIC UI) ---
KIRU_UI = """
<div id="kiru-music-bar" style="position:fixed; bottom:0; left:0; width:100%; background:rgba(0,0,0,0.9); color:white; z-index:10000; padding:10px; border-top: 2px solid #ff0055; font-family: sans-serif;">
    <div style="max-width: 800px; margin: auto; display: flex; gap: 10px; align-items: center;">
        <b style="color:#ff0055; font-size:18px;">KIRU-MUSIC</b>
        <input type="text" id="searchQuery" placeholder="Search song..." style="flex:1; padding:8px; border-radius:5px; border:none; color:#000;">
        <button onclick="kiruSearch()" style="background:#ff0055; color:white; border:none; padding:8px 15px; border-radius:5px; cursor:pointer;">Search</button>
    </div>
    <div id="results" style="max-height:200px; overflow-y:auto; margin-top:10px;"></div>
</div>

<script>
async def kiruSearch() {
    const q = document.getElementById('searchQuery').value;
    const resBox = document.getElementById('results');
    resBox.innerHTML = "Searching...";
    
    const response = await fetch(`/api/search?q=${q}`);
    const data = await response.json();
    
    resBox.innerHTML = "";
    data.results.forEach(song => {
        const div = document.createElement('div');
        div.style = "padding:8px; border-bottom:1px solid #333; display:flex; justify-content:space-between;";
        div.innerHTML = `<span>${song.title}</span> 
                        <button onclick="window.open('${song.url}')" style="background:green; color:white; border:none; border-radius:3px; padding:3px 8px;">Play</button>`;
        resBox.appendChild(div);
    });
}
</script>
"""

@app.api_route("/{path_name:path}", methods=["GET", "POST"])
async def proxy_engine(request: Request, path_name: str):
    url = f"{TARGET_SITE}/{path_name}"
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        headers = dict(request.headers)
        headers["host"] = "shrutibots.site"
        
        try:
            resp = await client.request(request.method, url, headers=headers, params=request.query_params)
        except:
            return HTMLResponse("Site Error")

    if "text/html" in resp.headers.get("content-type", ""):
        html = resp.text.replace(TARGET_SITE, "")
        # Injecting KIRU-MUSIC UI
        final_html = html.replace("</body>", f"{KIRU_UI}</body>")
        return HTMLResponse(content=final_html)
    
    return Response(content=resp.content, headers=dict(resp.headers), status_code=resp.status_code)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
