"""
Chat Service — plain-language Q&A over the rider's own data (#608).

Wraps the Anthropic Messages API with a tool-use loop over the read-only
tools in chat_tools.py. Stateless by design: the browser sends the running
message list each turn and nothing is persisted here or anywhere else — the
Messages API keeps no conversation history either.

Optional feature: without ANTHROPIC_API_KEY the service reports itself as
not configured and /api/chat returns a clear error, mirroring how the
Explore page degrades without ORS_API_KEY.

Only the text of earlier turns comes back from the browser, so no thinking
blocks are ever replayed across turns. That keeps trimming old turns
(max_history_messages) safe with models that bind thinking blocks to an
unedited conversation prefix. Within one turn the loop appends each
response's full content unchanged.
"""

import os
from datetime import date
from typing import Any, Dict, List, Optional

from src.config_manager import ConfigManager
from src.pii_sanitizer import sanitize_log_message
from src.secure_logger import SecureLogger

from app.services.chat_tools import ChatTools, ToolInputError

logger = SecureLogger(__name__)

_FALLBACK_BETA = 'server-side-fallback-2026-07-01'
_MAX_MESSAGE_CHARS = 4000

# Frozen: any byte change here invalidates the prompt cache. Per-request
# context (today's date) goes in a separate block after the cache breakpoint.
_SYSTEM_PROMPT = """You answer questions about one cyclist's own ride history for the Reports page of their Ride Optimizer app.

Use the tools to look up facts; never guess numbers. Prefer one well-filtered call over many broad ones: get_totals for totals, comparisons and trends, search_activities for specific rides, list_gear for bikes and shoes, list_routes for the route library. For a comparison like "this September vs. last September", call get_totals once per period with explicit start_date and end_date.

Dates are the ride's local calendar date. Units are imperial: miles, feet, hours, mph. If the data can't answer the question (for example, it predates the cached history or a field isn't recorded), say so plainly and say what the data does show.

Keep answers short and direct, lead with the number the rider asked for, and use a small markdown table only when comparing several rows. You have no access to GPS tracks or locations; if asked about where a ride went, say that's outside what you can see."""


class ChatNotConfiguredError(RuntimeError):
    """No Anthropic credential is configured."""


class ChatRequestError(ValueError):
    """The client sent a message list the service can't use."""


class ChatUpstreamError(RuntimeError):
    """The Claude API call failed; the message is safe to show the user."""


class ChatService:

    def __init__(self, tools: ChatTools):
        self.tools = tools
        self._client = None
        self.model = None
        self.max_tokens = None
        self.effort = None
        self.max_tool_iterations = None
        self.max_history_messages = None
        self.use_fallbacks = True

    def initialize(self) -> None:
        config = ConfigManager.get_instance()
        self.model = config.get('chat.model', 'claude-sonnet-5-5')
        self.max_tokens = int(config.get('chat.max_tokens', 16000))
        self.effort = config.get('chat.effort', 'low')
        self.max_tool_iterations = int(config.get('chat.max_tool_iterations', 6))
        self.max_history_messages = int(config.get('chat.max_history_messages', 20))
        self.use_fallbacks = bool(config.get('chat.fallbacks', True))
        timeout = float(config.get('chat.timeout_seconds', 60))

        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            logger.info("Ride chat disabled: ANTHROPIC_API_KEY is not set")
            self._client = None
            return

        import anthropic
        # One retry, not the SDK's default two: each attempt can hold one of
        # gunicorn's four request threads for up to `timeout` seconds.
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout, max_retries=1)
        logger.info("Ride chat enabled (model %s)", self.model)

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chat(self, messages: Any) -> Dict[str, Any]:
        """Answer the last user message in ``messages``.

        ``messages`` is the browser's running transcript:
        ``[{"role": "user"|"assistant", "content": str}, ...]`` ending with
        a user message. Returns ``{"reply": str, "tool_calls": int}``.
        """
        if not self.is_configured:
            raise ChatNotConfiguredError("Ride chat isn't set up: add ANTHROPIC_API_KEY to .env")

        history = self._prepare_history(messages)
        import anthropic

        tool_calls = 0
        response = None
        for iteration in range(self.max_tool_iterations + 1):
            # Last pass: no more tools, so Claude has to answer with what it has.
            final_pass = iteration == self.max_tool_iterations
            try:
                response = self._create(history, allow_tools=not final_pass)
            except anthropic.APITimeoutError:
                raise ChatUpstreamError("Claude took too long to answer. Try again or ask a narrower question.")
            except anthropic.RateLimitError:
                raise ChatUpstreamError("Claude is rate-limiting requests right now. Wait a minute and try again.")
            except anthropic.AuthenticationError:
                logger.error("Ride chat: Anthropic rejected the API key")
                raise ChatUpstreamError("The configured ANTHROPIC_API_KEY was rejected.")
            except anthropic.BadRequestError as e:
                logger.error("Ride chat: bad request to Claude API: %s", sanitize_log_message(e.message))
                raise ChatUpstreamError("Claude couldn't process this conversation. Start a new chat and try again.")
            except anthropic.APIStatusError as e:
                logger.error("Ride chat: Claude API error %s", e.status_code)
                raise ChatUpstreamError("Claude is unavailable right now. Try again shortly.")
            except anthropic.APIConnectionError:
                logger.error("Ride chat: could not reach the Claude API")
                raise ChatUpstreamError("Couldn't reach Claude. Check the server's internet connection.")

            self._log_usage(response, iteration)

            if response.stop_reason == 'refusal':
                return {'reply': "Sorry, I can't help with that one. Try asking about your rides, gear or routes.",
                        'tool_calls': tool_calls}

            if response.stop_reason == 'tool_use':
                history.append({'role': 'assistant', 'content': response.content})
                results = []
                for block in response.content:
                    if block.type != 'tool_use':
                        continue
                    tool_calls += 1
                    results.append(self._run_tool(block))
                history.append({'role': 'user', 'content': results})
                continue

            if response.stop_reason == 'pause_turn':
                history.append({'role': 'assistant', 'content': response.content})
                continue

            break

        reply = self._text_of(response)
        if response is not None and response.stop_reason == 'max_tokens':
            reply = (reply + "\n\n_(Answer cut off — try a narrower question.)_").strip()
        if not reply:
            reply = "I couldn't come up with an answer to that. Try rephrasing or narrowing the question."
        return {'reply': reply, 'tool_calls': tool_calls}

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _prepare_history(self, messages: Any) -> List[Dict[str, Any]]:
        """Validate the client transcript and trim it to the newest turns."""
        if not isinstance(messages, list) or not messages:
            raise ChatRequestError("messages must be a non-empty list")
        clean = []
        for m in messages:
            if not isinstance(m, dict) or m.get('role') not in ('user', 'assistant'):
                raise ChatRequestError("each message needs role 'user' or 'assistant'")
            content = m.get('content')
            if not isinstance(content, str) or not content.strip():
                raise ChatRequestError("each message needs non-empty text content")
            if len(content) > _MAX_MESSAGE_CHARS:
                raise ChatRequestError(f"messages are limited to {_MAX_MESSAGE_CHARS} characters")
            clean.append({'role': m['role'], 'content': content})
        if clean[-1]['role'] != 'user':
            raise ChatRequestError("the last message must be from the user")

        clean = clean[-self.max_history_messages:]
        while clean and clean[0]['role'] != 'user':
            clean.pop(0)
        return clean

    def _create(self, history: List[Dict[str, Any]], allow_tools: bool):
        kwargs: Dict[str, Any] = {
            'model': self.model,
            'max_tokens': self.max_tokens,
            'system': [
                {'type': 'text', 'text': _SYSTEM_PROMPT, 'cache_control': {'type': 'ephemeral'}},
                {'type': 'text', 'text': f"Today's date is {date.today().isoformat()}."},
            ],
            'tools': self.tools.definitions,
            'messages': history,
            'output_config': {'effort': self.effort},
            # Also caches the growing transcript between tool-loop passes.
            'cache_control': {'type': 'ephemeral'},
        }
        if not allow_tools:
            # Keep `tools` identical (it's part of the cached prefix) and
            # forbid calls instead of dropping the list.
            kwargs['tool_choice'] = {'type': 'none'}
        if self.use_fallbacks:
            # On a safety-classifier decline, the API re-runs the request on
            # Anthropic's recommended fallback model instead of refusing.
            return self._client.beta.messages.create(betas=[_FALLBACK_BETA], fallbacks='default', **kwargs)
        return self._client.messages.create(**kwargs)

    def _run_tool(self, block) -> Dict[str, Any]:
        try:
            content = self.tools.execute(block.name, block.input)
            return {'type': 'tool_result', 'tool_use_id': block.id, 'content': content}
        except ToolInputError as e:
            return {'type': 'tool_result', 'tool_use_id': block.id, 'content': f"Error: {e}", 'is_error': True}
        except Exception as e:
            logger.error("Ride chat tool %s failed: %s", block.name, e, exc_info=True)
            return {'type': 'tool_result', 'tool_use_id': block.id,
                    'content': "Error: this tool failed unexpectedly.", 'is_error': True}

    @staticmethod
    def _text_of(response) -> str:
        if response is None:
            return ''
        return '\n\n'.join(b.text for b in response.content if b.type == 'text' and b.text).strip()

    @staticmethod
    def _log_usage(response, iteration: int) -> None:
        usage = getattr(response, 'usage', None)
        if usage is None:
            return
        logger.debug(
            "Ride chat pass %d: stop=%s in=%s out=%s cache_read=%s cache_write=%s",
            iteration, response.stop_reason, usage.input_tokens, usage.output_tokens,
            getattr(usage, 'cache_read_input_tokens', None), getattr(usage, 'cache_creation_input_tokens', None),
        )
