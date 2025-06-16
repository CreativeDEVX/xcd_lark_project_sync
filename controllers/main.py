import json
import logging
from odoo import http, _
from odoo.http import request, Response
import requests
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

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
        
    @http.route('/lark_project_sync/sync', type='http', auth='user', methods=['POST'], csrf=False)
    def sync_tasks(self, **kwargs):
        """
        Handle task synchronization from Lark to Odoo
        
        Returns:
            JSON response with sync results
        """
        try:
            # Get the active Lark API configuration
            lark_api = request.env['lark.api'].sudo().search([], limit=1)
            if not lark_api:
                return Response(
                    json.dumps({
                        'success': False,
                        'message': 'No Lark API configuration found.'
                    }),
                    content_type='application/json',
                    status=400
                )
                
            # Get project ID from request if provided
            project_id = kwargs.get('project_id')
            if project_id:
                try:
                    project_id = int(project_id)
                except (ValueError, TypeError):
                    project_id = None
            
            # Start synchronization
            result = lark_api.sync_lark_tasks(project_id=project_id)
            
            return Response(
                json.dumps({
                    'success': True,
                    'result': result
                }),
                content_type='application/json'
            )
            
        except Exception as e:
            _logger.error("Error during task synchronization: %s", str(e), exc_info=True)
            return Response(
                json.dumps({
                    'success': False,
                    'message': str(e)
                }),
                content_type='application/json',
                status=500
            )
