import logging
import urllib.parse
from typing import Optional
from aiohttp import web
from src.core.models import GameConfig
from src.core.utils import format_phone_number, calculate_parameter_hash

logger = logging.getLogger(__name__)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Scavenger Hunt - Location Verification</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --primary: #6366f1;
            --primary-hover: #4f46e5;
            --text-color: #f8fafc;
            --text-muted: #94a3b8;
            --border-color: rgba(255, 255, 255, 0.1);
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-color);
            background-image: radial-gradient(circle at top right, rgba(99, 102, 241, 0.15), transparent 40%),
                              radial-gradient(circle at bottom left, rgba(168, 85, 247, 0.15), transparent 40%);
            color: var(--text-color);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .card {{
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 24px;
            padding: 40px 30px;
            width: 100%;
            max-width: 420px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
            text-align: center;
            animation: fadeIn 0.6s ease-out;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        h1 {{
            font-size: 28px;
            font-weight: 800;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #a855f7, #6366f1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .location-badge {{
            display: inline-block;
            padding: 6px 12px;
            background: rgba(99, 102, 241, 0.1);
            border: 1px solid rgba(99, 102, 241, 0.2);
            color: #818cf8;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 20px;
        }}
        p {{
            font-size: 15px;
            color: var(--text-muted);
            margin-bottom: 30px;
            line-height: 1.5;
        }}
        .form-group {{
            margin-bottom: 24px;
            text-align: left;
        }}
        label {{
            display: block;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 8px;
            color: var(--text-color);
        }}
        input {{
            width: 100%;
            padding: 14px 16px;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            background: rgba(15, 23, 42, 0.6);
            color: var(--text-color);
            font-family: inherit;
            font-size: 16px;
            transition: all 0.3s ease;
        }}
        input:focus {{
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
            background: rgba(15, 23, 42, 0.8);
        }}
        button {{
            width: 100%;
            padding: 16px;
            border-radius: 12px;
            border: none;
            background: linear-gradient(135deg, #6366f1, #a855f7);
            color: white;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        }}
        button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
        }}
        button:active {{
            transform: translateY(0);
        }}
        .footer {{
            margin-top: 24px;
            font-size: 12px;
            color: rgba(148, 163, 184, 0.6);
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="location-badge">📍 Scanned Location: {loc_name}</div>
        <h1>Unlock Clue</h1>
        <p>To verify you are at this location, enter your Player ID (Phone Number or Telegram ID) below. We will open your chat app with a secure pre-filled verification code.</p>
        <form method="POST">
            <div class="form-group">
                <label for="playerId">Player ID</label>
                <input type="text" id="playerId" name="playerId" placeholder="e.g. +15551234567 or username" required autocomplete="off">
            </div>
            <button type="submit">Open Chat App</button>
        </form>
        <div class="footer">
            Powered by ScavengerHunt Core
        </div>
    </div>
</body>
</html>
"""

class RedirectServer:
    def __init__(self, config: GameConfig, platform: str):
        self.config = config
        self.platform = platform.lower()
        self._runner: Optional[web.AppRunner] = None

    async def start(self) -> None:
        """Starts the aiohttp redirection web server."""
        app = web.Application()
        app.router.add_get("/scan/{location_id}", self._handle_get)
        app.router.add_post("/scan/{location_id}", self._handle_post)

        self._runner = web.AppRunner(app)
        await self._runner.setup()

        site = web.TCPSite(
            self._runner,
            self.config.twilio_webhook_host,  # Reuses host bind interface (e.g. 0.0.0.0)
            self.config.redirect_port
        )
        await site.start()
        logger.info(f"Redirection Server running on http://{self.config.twilio_webhook_host}:{self.config.redirect_port}")

    async def stop(self) -> None:
        """Stops the redirection web server."""
        if self._runner:
            await self._runner.cleanup()
            logger.info("Redirection Server stopped.")

    def _get_location_name(self, location_id: str) -> str:
        for loc in self.config.locations:
            if loc.id == location_id:
                return loc.name
        return "Unknown Location"

    async def _handle_get(self, request: web.Request) -> web.Response:
        location_id = request.match_info.get("location_id", "")
        loc_name = self._get_location_name(location_id)
        
        html_content = HTML_TEMPLATE.format(loc_name=loc_name)
        return web.Response(text=html_content, content_type="text/html")

    async def _handle_post(self, request: web.Request) -> web.Response:
        location_id = request.match_info.get("location_id", "")
        
        # Parse form data
        data = await request.post()
        raw_player_id = data.get("playerId", "").strip()

        # Standardize phone number if it is digit-like
        player_id = raw_player_id
        if player_id.startswith("+") or player_id.isdigit() or ("-" in player_id) or ("(" in player_id):
            try:
                player_id = format_phone_number(player_id)
            except Exception:
                pass  # Use raw input on failure

        # Compute hash
        token = calculate_parameter_hash(self.config.salt, location_id, player_id)
        logger.info(f"Redirection Server: Generated token '{token}' for player '{player_id}' at location '{location_id}'")

        # Determine target deep link
        if self.platform == "telegram":
            # Redirect to Telegram deep link
            redirect_url = f"https://t.me/{self.config.telegram_bot_username}?start={token}"
        else:
            # Redirect to Twilio SMS deep link
            encoded_body = urllib.parse.quote(token)
            redirect_url = f"sms:{self.config.twilio_phone_number}?body={encoded_body}"

        logger.info(f"Redirecting player to: {redirect_url}")
        
        # Perform 302 redirect
        raise web.HTTPFound(redirect_url)
