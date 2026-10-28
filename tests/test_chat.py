"""Tests for the Reports-page ride chat (#608): tools, service loop, endpoint.

The Anthropic client is always mocked; no test makes a live API call.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.chat_service import (
    ChatNotConfiguredError,
    ChatRequestError,
    ChatService,
)
from app.services.chat_tools import TOOL_DEFINITIONS, ChatTools, ToolInputError
from src.data_fetcher import Activity

HOME = (41.8781136, -87.6297982)
POLYLINE = 'u{~vFvyys@fS]_secret_polyline_'


def _act(id_, local, distance_mi, *, gear='b1', sport='Ride', name='Morning Ride', elev_ft=500, hours=1.0):
    return Activity(
        id=id_, name=name, type='Ride', sport_type=sport,
        start_date=local + 'Z', start_date_local=local + 'Z',
        distance=distance_mi / 0.000621371, moving_time=int(hours * 3600), elapsed_time=int(hours * 3600),
        total_elevation_gain=elev_ft / 3.28084, average_speed=(distance_mi / 0.000621371) / (hours * 3600),
        start_latlng=HOME, end_latlng=HOME, polyline=POLYLINE, gear_id=gear,
        average_heartrate=140.0, kilojoules=800.0,
    )


ACTIVITIES = [
    _act(1, '2025-09-06T08:00:00', 40.0, name='Saturday long one'),           # Sat
    _act(2, '2025-09-09T07:30:00', 12.0, gear='b2'),                           # Tue
    _act(3, '2026-09-08T07:30:00', 25.5, name='Tuesday stretch'),              # Tue
    _act(4, '2026-09-12T09:00:00', 60.0, sport='GravelRide', elev_ft=2500),    # Sat
    _act(5, '2026-10-01T17:00:00', 8.0, gear=None),                            # Thu
]

GEAR = {'bikes': [
    {'id': 'b1', 'name': 'Road Bike', 'type': 'bike', 'brand_name': 'Trek', 'model_name': 'Domane',
     'primary': True, 'strava_distance_m': 160934.4},
    {'id': 'b2', 'name': 'Commuter', 'type': 'bike', 'brand_name': '', 'model_name': '',
     'primary': False, 'strava_distance_m': 0},
], 'shoes': []}


class _FakeLibrary:
    def get_all_routes(self, route_type='all', sort_by='uses', limit=None):
        return {'status': 'success', 'total_count': 2, 'routes': [
            {'id': 'r1', 'type': 'commute', 'name': 'Lakefront to Work', 'direction': 'home_to_work',
             'distance': 16.09, 'duration': 45.0, 'elevation': 30.0, 'uses': 120,
             'last_ridden': '2026-10-01T07:30:00', 'is_favorite': True,
             'coordinates': [[41.8781136, -87.6297982]]},
            {'id': 'r2', 'type': 'long_ride', 'name': 'North Shore loop', 'distance': 80.47,
             'duration': 240.0, 'elevation': 300.0, 'uses': 4, 'last_ridden': '', 'is_favorite': False},
        ]}


@pytest.fixture
def tools():
    return ChatTools(
        activities_source=lambda: ACTIVITIES,
        gear_source=lambda: GEAR,
        route_library_source=lambda: _FakeLibrary(),
    )


def _run(tools, name, args=None):
    return json.loads(tools.execute(name, args or {}))


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestChatTools:
    def test_definitions_are_well_formed(self):
        names = [t['name'] for t in TOOL_DEFINITIONS]
        assert names == ['get_totals', 'search_activities', 'list_gear', 'list_routes']
        for t in TOOL_DEFINITIONS:
            assert t['input_schema']['type'] == 'object'
            assert t['description']

    def test_totals_summary_with_date_range(self, tools):
        out = _run(tools, 'get_totals', {'start_date': '2026-09-01', 'end_date': '2026-09-30'})
        assert out['summary']['total_rides'] == 2
        assert out['summary']['total_distance_mi'] == pytest.approx(85.5, abs=0.1)
        assert out['first_date'] == '2026-09-08'
        assert out['last_date'] == '2026-09-12'
        assert out['records']['longest_ride']['distance_mi'] == 60.0
        assert 'id' not in out['records']['longest_ride']

    def test_totals_by_month_compares_years(self, tools):
        out = _run(tools, 'get_totals', {'group_by': 'month'})
        by = {g['group']: g for g in out['groups']}
        assert by['2025-09']['total_distance_mi'] == pytest.approx(52.0, abs=0.1)
        assert by['2026-09']['total_distance_mi'] == pytest.approx(85.5, abs=0.1)
        assert list(by) == ['2025-09', '2026-09', '2026-10']

    def test_totals_by_weekday_in_calendar_order(self, tools):
        out = _run(tools, 'get_totals', {'group_by': 'weekday'})
        assert [g['group'] for g in out['groups']] == ['Tuesday', 'Thursday', 'Saturday']

    def test_totals_by_gear_names_gear(self, tools):
        out = _run(tools, 'get_totals', {'group_by': 'gear', 'start_date': '2026-01-01'})
        by = {g['group']: g for g in out['groups']}
        assert by['b1']['gear_name'] == 'Road Bike'
        assert by['b1']['total_rides'] == 2
        assert by['unassigned']['gear_name'] == 'No gear recorded'

    def test_search_weekday_longest(self, tools):
        out = _run(tools, 'search_activities', {
            'weekdays': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
            'sort_by': 'distance_desc', 'limit': 1,
        })
        assert out['total_matches'] == 3
        assert out['returned'] == 1
        row = out['activities'][0]
        assert row['name'] == 'Tuesday stretch'
        assert row['weekday'] == 'Tuesday'
        assert row['start_time'] == '07:30'
        assert row['distance_mi'] == 25.5

    def test_search_filters_distance_sport_and_name(self, tools):
        assert _run(tools, 'search_activities', {'min_distance_mi': 30})['total_matches'] == 2
        assert _run(tools, 'search_activities', {'sport_type': 'GravelRide'})['total_matches'] == 1
        assert _run(tools, 'search_activities', {'name_contains': 'SATURDAY'})['total_matches'] == 1

    def test_search_limit_is_clamped(self, tools):
        out = _run(tools, 'search_activities', {'limit': 10_000})
        assert out['returned'] == len(ACTIVITIES)

    def test_list_gear(self, tools):
        out = _run(tools, 'list_gear')
        road = next(g for g in out['gear'] if g['gear_id'] == 'b1')
        assert road['name'] == 'Road Bike'
        assert road['total_rides'] == 3
        assert road['last_used'] == '2026-09-12'
        assert road['strava_odometer_mi'] == pytest.approx(100.0, abs=0.1)

    def test_list_gear_without_gear_cache(self):
        t = ChatTools(lambda: ACTIVITIES, lambda: None, lambda: None)
        out = _run(t, 'list_gear')
        assert out['gear_cache_available'] is False
        assert {g['gear_id'] for g in out['gear']} == {'b1', 'b2'}

    def test_list_routes_converts_units_and_counts_all(self, tools):
        out = _run(tools, 'list_routes', {'limit': 1})
        assert out['total_routes'] == 2
        assert len(out['routes']) == 1
        r = out['routes'][0]
        assert r['distance_mi'] == pytest.approx(10.0, abs=0.1)
        assert r['times_ridden'] == 120
        assert r['last_ridden'] == '2026-10-01'

    def test_list_routes_without_library(self):
        t = ChatTools(lambda: [], lambda: None, lambda: None)
        assert _run(t, 'list_routes')['routes'] == []

    @pytest.mark.parametrize('name,args', [
        ('get_totals', {'start_date': '09/01/2026'}),
        ('get_totals', {'group_by': 'decade'}),
        ('search_activities', {'weekdays': ['Funday']}),
        ('search_activities', {'sort_by': 'random'}),
        ('search_activities', {'min_distance_mi': 'far'}),
        ('list_routes', {'route_type': 'secret'}),
        ('no_such_tool', {}),
    ])
    def test_bad_input_raises(self, tools, name, args):
        with pytest.raises(ToolInputError):
            tools.execute(name, args)

    def test_no_gps_or_home_location_in_any_tool_output(self, tools):
        """Acceptance criterion: no coordinates or polylines ever leave the app."""
        calls = [
            ('get_totals', {}), ('get_totals', {'group_by': 'month'}), ('get_totals', {'group_by': 'gear'}),
            ('get_totals', {'group_by': 'weekday'}), ('get_totals', {'group_by': 'sport_type'}),
            ('search_activities', {'limit': 50}), ('list_gear', {}), ('list_routes', {}),
        ]
        for name, args in calls:
            text = tools.execute(name, args)
            for forbidden in ('41.87', '-87.62', '41.8781136', '-87.6297982', POLYLINE,
                              'latlng', 'polyline', 'coordinates'):
                assert forbidden not in text, f"{name} leaked {forbidden!r}"

    def test_outbound_text_is_pii_sanitized(self):
        acts = [_act(9, '2026-09-01T08:00:00', 10.0, name='Ride from 123 Main Street at 41.8781136, -87.6297982')]
        t = ChatTools(lambda: acts, lambda: None, lambda: None)
        text = t.execute('search_activities', {})
        assert '123 Main Street' not in text
        assert '41.8781136' not in text


# ---------------------------------------------------------------------------
# Service loop (mocked Anthropic client)
# ---------------------------------------------------------------------------

def _text(t):
    return SimpleNamespace(type='text', text=t)


def _tool_use(id_, name, args):
    return SimpleNamespace(type='tool_use', id=id_, name=name, input=args)


def _resp(stop, *content):
    usage = SimpleNamespace(input_tokens=10, output_tokens=5, cache_read_input_tokens=0,
                            cache_creation_input_tokens=0)
    return SimpleNamespace(stop_reason=stop, content=list(content), usage=usage)


@pytest.fixture
def service(tools, monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-key')
    svc = ChatService(tools)
    svc.initialize()
    svc._client = MagicMock()
    return svc


def _create(svc):
    return svc._client.beta.messages.create


@pytest.mark.unit
class TestChatService:
    def test_not_configured_without_key(self, tools, monkeypatch):
        monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
        svc = ChatService(tools)
        svc.initialize()
        assert svc.is_configured is False
        with pytest.raises(ChatNotConfiguredError):
            svc.chat([{'role': 'user', 'content': 'hi'}])

    def test_configured_with_key(self, tools, monkeypatch):
        monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-key')
        svc = ChatService(tools)
        svc.initialize()
        assert svc.is_configured is True
        assert svc.model == 'claude-sonnet-5-5'

    def test_tool_loop_runs_tool_and_returns_answer(self, service):
        _create(service).side_effect = [
            _resp('tool_use', _tool_use('t1', 'get_totals', {'start_date': '2026-09-01', 'end_date': '2026-09-30'})),
            _resp('end_turn', _text('You rode **85.5 miles** in September.')),
        ]
        out = service.chat([{'role': 'user', 'content': 'Miles in September?'}])
        assert out == {'reply': 'You rode **85.5 miles** in September.', 'tool_calls': 1}

        second = _create(service).call_args_list[1].kwargs
        tool_msg = second['messages'][-1]
        assert tool_msg['role'] == 'user'
        result = tool_msg['content'][0]
        assert result['tool_use_id'] == 't1'
        assert json.loads(result['content'])['summary']['total_rides'] == 2
        # The assistant turn with the tool_use block is passed back unchanged.
        assert second['messages'][-2]['role'] == 'assistant'

    def test_request_shape_caching_fallbacks_effort(self, service):
        _create(service).return_value = _resp('end_turn', _text('ok'))
        service.chat([{'role': 'user', 'content': 'hi'}])
        kw = _create(service).call_args.kwargs
        assert kw['model'] == 'claude-sonnet-5-5'
        assert kw['system'][0]['cache_control'] == {'type': 'ephemeral'}
        assert 'cache_control' not in kw['system'][1]          # volatile date block sits after the breakpoint
        assert "Today's date" in kw['system'][1]['text']
        assert kw['cache_control'] == {'type': 'ephemeral'}
        assert kw['tools'] is TOOL_DEFINITIONS
        assert kw['output_config'] == {'effort': 'low'}
        assert kw['fallbacks'] == 'default'
        assert kw['betas'] == ['server-side-fallback-2026-07-01']
        assert 'tool_choice' not in kw
        assert 'thinking' not in kw

    def test_without_fallbacks_uses_plain_messages_api(self, service):
        service.use_fallbacks = False
        service._client.messages.create.return_value = _resp('end_turn', _text('ok'))
        assert service.chat([{'role': 'user', 'content': 'hi'}])['reply'] == 'ok'
        assert 'fallbacks' not in service._client.messages.create.call_args.kwargs

    def test_iteration_cap_forces_final_answer(self, service):
        service.max_tool_iterations = 2
        _create(service).side_effect = [
            _resp('tool_use', _tool_use('t1', 'list_gear', {})),
            _resp('tool_use', _tool_use('t2', 'list_gear', {})),
            _resp('end_turn', _text('Best I can tell: Road Bike.')),
        ]
        out = service.chat([{'role': 'user', 'content': 'Top bike?'}])
        assert out['reply'] == 'Best I can tell: Road Bike.'
        calls = _create(service).call_args_list
        assert len(calls) == 3
        assert 'tool_choice' not in calls[0].kwargs
        assert calls[2].kwargs['tool_choice'] == {'type': 'none'}
        assert calls[2].kwargs['tools'] is TOOL_DEFINITIONS   # unchanged, keeps the cache prefix

    def test_bad_tool_input_is_reported_to_claude_as_error(self, service):
        _create(service).side_effect = [
            _resp('tool_use', _tool_use('t1', 'get_totals', {'start_date': 'yesterday'})),
            _resp('end_turn', _text('Which dates?')),
        ]
        service.chat([{'role': 'user', 'content': 'q'}])
        result = _create(service).call_args_list[1].kwargs['messages'][-1]['content'][0]
        assert result['is_error'] is True
        assert 'YYYY-MM-DD' in result['content']

    def test_refusal_returns_polite_reply(self, service):
        _create(service).return_value = _resp('refusal')
        out = service.chat([{'role': 'user', 'content': 'q'}])
        assert "can't help" in out['reply']

    def test_max_tokens_marks_cut_off(self, service):
        _create(service).return_value = _resp('max_tokens', _text('Partial'))
        assert 'cut off' in service.chat([{'role': 'user', 'content': 'q'}])['reply']

    def test_history_trimmed_to_newest_starting_with_user(self, service):
        service.max_history_messages = 4
        _create(service).return_value = _resp('end_turn', _text('ok'))
        history = []
        for i in range(5):
            history += [{'role': 'user', 'content': f'q{i}'}, {'role': 'assistant', 'content': f'a{i}'}]
        history.append({'role': 'user', 'content': 'latest'})
        service.chat(history)
        sent = _create(service).call_args.kwargs['messages']
        assert sent[0]['role'] == 'user'
        assert sent[-1]['content'] == 'latest'
        assert len(sent) <= 4

    @pytest.mark.parametrize('messages', [
        None, [], 'hello',
        [{'role': 'system', 'content': 'x'}],
        [{'role': 'user', 'content': ''}],
        [{'role': 'user', 'content': 'x' * 4001}],
        [{'role': 'user', 'content': 'q'}, {'role': 'assistant', 'content': 'a'}],
        [{'role': 'user', 'content': [{'type': 'text', 'text': 'block content'}]}],
    ])
    def test_invalid_transcripts_rejected(self, service, messages):
        with pytest.raises(ChatRequestError):
            service.chat(messages)

    def test_api_timeout_becomes_friendly_error(self, service):
        import anthropic
        from app.services.chat_service import ChatUpstreamError
        _create(service).side_effect = anthropic.APITimeoutError(request=MagicMock())
        with pytest.raises(ChatUpstreamError, match='too long'):
            service.chat([{'role': 'user', 'content': 'q'}])

    def test_nothing_written_to_disk(self, service, tmp_path, monkeypatch):
        """No transcript persistence: a chat turn touches no files."""
        monkeypatch.chdir(tmp_path)
        _create(service).side_effect = [
            _resp('tool_use', _tool_use('t1', 'search_activities', {})),
            _resp('end_turn', _text('done')),
        ]
        service.chat([{'role': 'user', 'content': 'q'}])
        assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@pytest.fixture
def app_client():
    from app.factory import create_app
    app = create_app({'TESTING': True, 'RATELIMIT_ENABLED': False})
    app.container.initialise = lambda: None
    with app.test_client() as c:
        yield c


def _install(client, svc):
    client.application.container.chat_service = svc


@pytest.mark.unit
class TestChatEndpoint:
    def test_status_and_post_when_not_configured(self, app_client, tools, monkeypatch):
        monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
        svc = ChatService(tools)
        svc.initialize()
        _install(app_client, svc)

        assert app_client.get('/api/chat/status').get_json()['configured'] is False
        r = app_client.post('/api/chat', json={'messages': [{'role': 'user', 'content': 'hi'}]})
        assert r.status_code == 503
        assert r.get_json()['code'] == 'not_configured'

    def test_post_returns_reply(self, app_client, service):
        _install(app_client, service)
        _create(service).return_value = _resp('end_turn', _text('42 rides.'))
        r = app_client.post('/api/chat', json={'messages': [{'role': 'user', 'content': 'How many rides?'}]})
        assert r.status_code == 200
        body = r.get_json()
        assert body['status'] == 'success'
        assert body['reply'] == '42 rides.'
        assert app_client.get('/api/chat/status').get_json()['configured'] is True

    def test_post_bad_body_is_400(self, app_client, service):
        _install(app_client, service)
        r = app_client.post('/api/chat', json={'messages': 'nope'})
        assert r.status_code == 400

    def test_upstream_failure_is_502(self, app_client, service):
        import anthropic
        _install(app_client, service)
        _create(service).side_effect = anthropic.APIConnectionError(request=MagicMock())
        r = app_client.post('/api/chat', json={'messages': [{'role': 'user', 'content': 'q'}]})
        assert r.status_code == 502
        assert "Couldn't reach Claude" in r.get_json()['message']
