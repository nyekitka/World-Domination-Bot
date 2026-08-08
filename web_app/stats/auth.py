import hashlib
import hmac
import json
from urllib.parse import parse_qsl


def verify_telegram_init_data(init_data: str, bot_token: str) -> dict | None:
    try:
        parsed_data = dict(parse_qsl(init_data, keep_blank_values=True))
    except Exception: # noqa: BLE001
        return None

    received_hash = parsed_data.pop('hash', None)
    if not received_hash:
        return None

    data_check_string = '\n'.join(
        f'{k}={v}' for k, v in sorted(parsed_data.items())
    )

    secret_key = hmac.new(
        b'WebAppData', bot_token.encode(), hashlib.sha256
    ).digest()

    calculated_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if hmac.compare_digest(calculated_hash, received_hash):
        if 'user' in parsed_data:
            parsed_data['user'] = json.loads(parsed_data['user'])
        return parsed_data

    return None
