#!/usr/bin/env python3
"""Capture one authenticated TotalCorner schedule response without logging credentials.

The request is a data-source diagnostic only. The exact body is written to the
private local recovery workspace; this repository stores only code and later
sanitized metadata/digests, never the API token or raw licensed response body.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import sys

import requests

QUANT_ROOT = pathlib.Path('/Users/mac/QuantAsiaDesk')
OUTPUT = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/full_history_backfill_20261121/totalcorner_schedule_diagnostics')


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z')


def get_token() -> str:
    token = os.environ.get('TOTALCORNER_TOKEN')
    if token:
        return token.strip()
    sys.path.insert(0, str(QUANT_ROOT))
    try:
        from mac_keychain import get
        token = get('QuantAsiaDesk.TOTALCORNER_TOKEN', os.environ.get('USER', 'mac'))
    except Exception as exc:
        raise RuntimeError(f'KEYCHAIN_READ_FAILED:{type(exc).__name__}') from None
    if not token:
        raise RuntimeError('KEYCHAIN_TOKEN_UNAVAILABLE')
    return token


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--league-id', default='57')
    parser.add_argument('--page', type=int, default=1)
    args = parser.parse_args()
    if not args.league_id.isdigit() or args.page < 1:
        parser.error('league-id must be numeric and page must be positive')

    token = get_token()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    endpoint = f'https://api.totalcorner.com/v1/league/schedule/{args.league_id}'
    started = utc_now()
    try:
        response = requests.get(
            endpoint,
            params={
                'token': token,
                'page': args.page,
                'columns': 'events,attacks,dangerousAttacks,shotOn,shotOff,possession,asian,goalLine',
            },
            headers={'Accept': 'application/json', 'User-Agent': 'QuantAsiaDesk-history-recovery/1'},
            timeout=(15, 60),
        )
        received = utc_now()
        body = response.content
        raw_sha = hashlib.sha256(body).hexdigest()
        # Keep a true raw response locally unless the provider echoed the secret.
        # In that exceptional case persist a redacted copy and preserve the raw digest.
        contains_token = bool(token) and token.encode('utf-8') in body
        stored_body = body.replace(token.encode('utf-8'), b'[REDACTED]') if contains_token else body
        raw_path = OUTPUT / f'league-{args.league_id}-page-{args.page}-{raw_sha}.json'
        tmp_path = raw_path.with_suffix(raw_path.suffix + '.tmp')
        tmp_path.write_bytes(stored_body)
        tmp_path.replace(raw_path)

        parsed = None
        try:
            parsed = response.json()
        except Exception:
            pass
        payload = parsed if isinstance(parsed, dict) else {}
        err = payload.get('error') if isinstance(payload.get('error'), dict) else {}
        message = str(err.get('message') or payload.get('error_message') or '')
        message = message.replace(token, '[REDACTED]') if token else message
        data = payload.get('data')
        matches = data if isinstance(data, list) else data.get('matches', []) if isinstance(data, dict) else []
        pagination = payload.get('pagination') if isinstance(payload.get('pagination'), dict) else {}
        summary = {
            'diagnostic': 'totalcorner_league_schedule_single_response',
            'request': {'league_id': args.league_id, 'page': args.page, 'endpoint_path': f'/v1/league/schedule/{args.league_id}'},
            'request_started_at_utc': started,
            'response_received_at_utc': received,
            'http_status': response.status_code,
            'provider_success': payload.get('success', payload.get('status')),
            'provider_error_code': err.get('code') or payload.get('error_code'),
            'provider_error_message_sanitized': message[:500],
            'response_content_type': response.headers.get('Content-Type'),
            'response_content_length': len(body),
            'response_sha256': raw_sha,
            'private_response_path': str(raw_path),
            'secret_echo_detected_and_redacted_in_saved_copy': contains_token,
            'rate_limit_headers': {
                key: response.headers.get(key)
                for key in ('X-Rate-Limit-Limit', 'X-Rate-Limit-Remaining', 'X-Rate-Limit-Reset', 'Retry-After')
                if response.headers.get(key) is not None
            },
            'data_type': type(data).__name__ if data is not None else None,
            'data_keys': sorted(data.keys()) if isinstance(data, dict) else None,
            'match_count': len(matches) if isinstance(matches, list) else None,
            'pagination': {key: pagination.get(key) for key in ('page', 'pages', 'next', 'per_page', 'total') if key in pagination},
            'first_match_id': str(matches[0].get('id')) if matches and isinstance(matches[0], dict) else None,
            'last_match_id': str(matches[-1].get('id')) if matches and isinstance(matches[-1], dict) else None,
        }
        meta_path = OUTPUT / f'league-{args.league_id}-page-{args.page}-{raw_sha}.meta.json'
        meta_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(summary, ensure_ascii=False))
        return 0
    except Exception as exc:
        # requests exceptions may include the full URL (and token); never print them.
        print(json.dumps({
            'diagnostic': 'totalcorner_league_schedule_single_response',
            'request': {'league_id': args.league_id, 'page': args.page},
            'request_started_at_utc': started,
            'error_type': type(exc).__name__,
            'error_message': 'request failed; inspect only sanitized metadata locally',
        }, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
