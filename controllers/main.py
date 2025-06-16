from odoo import http, _
from odoo.http import request
import requests
from datetime import datetime, timedelta

class LarkOAuthController(http.Controller):
    @http.route('/lark/oauth/callback', type='http', auth='public', csrf=False)
    def lark_oauth_callback(self, **kwargs):
        code = kwargs.get('code')
        state = kwargs.get('state')
        if not code or not state:
            return "Missing code or state."

        # Find the LarkAPI config with this state
        lark_api = request.env['lark.api'].sudo().search([('oauth_state', '=', state)], limit=1)
        if not lark_api:
            return "Invalid state."

        # Exchange code for token
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "app_id": lark_api.app_id,
            "app_secret": lark_api.app_secret,
        }
        response = requests.post("https://accounts.larksuite.com/open-apis/authen/v1/authorize", json=payload)
        data = response.json()
        if data.get("code") != 0:
            return f"Failed to get token: {data.get('msg')}"

        access_token = data["data"]["access_token"]
        refresh_token = data["data"].get("refresh_token")
        expire = data["data"]["expires_in"]  # seconds

        lark_api.sudo().write({
            "user_access_token": access_token,
            "refresh_token": refresh_token,
            "token_expire": datetime.utcnow() + timedelta(seconds=expire),
        })
        return "Lark access token updated! You can close this window."
