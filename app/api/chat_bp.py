"""Ride-data chat API Blueprint (#608).

Routes:
  GET  /api/chat/status
  POST /api/chat

Stateless: the client sends its running transcript each turn and nothing is
stored server-side.
"""

from flask import Blueprint, current_app, jsonify, request

from app.extensions import limiter
from src.secure_logger import SecureLogger

logger = SecureLogger(__name__)

bp = Blueprint('chat', __name__, url_prefix='/api')


@bp.route('/chat/status')
def chat_status():
    """Whether the chat is usable, so the panel can show a disabled state."""
    service = current_app.container.get_chat_service()
    return jsonify({'status': 'success', 'configured': service.is_configured})


@bp.route('/chat', methods=['POST'])
@limiter.limit("10 per minute")
def chat():
    """
    Answer the last user message using tool calls over the rider's data.

    Body: {"messages": [{"role": "user"|"assistant", "content": str}, ...]}
    """
    from app.services.chat_service import (
        ChatNotConfiguredError,
        ChatRequestError,
        ChatUpstreamError,
    )

    container = current_app.container
    service = container.get_chat_service()
    if not service.is_configured:
        return jsonify({'status': 'error', 'code': 'not_configured',
                        'message': "Ride chat isn't set up: add ANTHROPIC_API_KEY to .env"}), 503

    body = request.get_json(silent=True) or {}
    # Gear and route tools read through the analysis/route-library services.
    container.initialise()
    try:
        result = service.chat(body.get('messages'))
    except ChatRequestError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except ChatNotConfiguredError as e:
        return jsonify({'status': 'error', 'code': 'not_configured', 'message': str(e)}), 503
    except ChatUpstreamError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 502

    logger.info("Ride chat answered with %d tool call(s)", result['tool_calls'])
    return jsonify({'status': 'success', **result})
