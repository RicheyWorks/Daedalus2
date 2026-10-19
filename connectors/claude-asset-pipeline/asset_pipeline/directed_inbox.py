"""Inert TeamLink receiver diagnostic: no transport, ACK, cursor write or wake.

Consumes caller-retained raw /wait or /pending JSON. Body @mentions are hints,
never recipient aliases. A broker ID or correlated reply is not worker wake,
semantic acceptance, completed work or a parent-read receipt.
"""
import argparse
import json
import re

BROKER_CONTRACT = {
    'module': 'asset_pipeline.teamlink', 'routing_symbol': 'Broker._for',
    'wait_symbol': 'Broker.wait', 'ack_symbol': 'Broker.ack',
    'pending_symbol': 'Broker.pending',
    'historical_inspection_only': {
        'checkout': 'D2-build', 'relative_path': 'connectors/claude-asset-pipeline/asset_pipeline/teamlink.py',
        'sha256': '2daa496eeb1d45d8401c25161c6c876a9e193f337cdee1fc841a23b53fd0cd9c',
        'routing_lines': [235, 237], 'wait_lines': [239, 250],
        'ack_lines': [252, 261], 'pending_lines': [263, 265],
    },
}


def positive_id(value):
    return type(value) is int and value > 0


def eligible(message, receiver, topics=()):
    """Match the existing broker _for contract without mutating a message."""
    return message['from'] != receiver and (message['to'] == receiver or
        (message['to'] == '*' and (not topics or message.get('topic') in topics)))


def inspect_batch(response, receiver, *, after=0, handled_ids=(),
                  probe_id=None, expected_sender=None, request_id=None, topics=()):
    """Normalize a raw successful observation, preserving all unhandled work.

    None is UNKNOWN, not a healthy empty inbox. Passing a decoded JSON response
    establishes only supplied observation data, not a currently live transport.
    This function never advances a cursor or generates a send/ACK instruction.
    """
    if not isinstance(receiver, str) or not receiver or receiver == '*':
        raise ValueError('an explicit receiver identity is required')
    if type(after) is not int or after < 0:
        raise ValueError('invalid input cursor')
    if probe_id is not None and not positive_id(probe_id):
        raise ValueError('invalid probe ID')
    if request_id is not None and (not isinstance(request_id, str) or not request_id):
        raise ValueError('invalid request correlation ID')
    handled = set(handled_ids)
    if any(not positive_id(mid) for mid in handled):
        raise ValueError('invalid explicitly handled ID')
    result = {'v': 1, 'receiver': receiver, 'observation': 'UNKNOWN',
        'input_after': after, 'retained_after': after, 'reported_broker_last': None,
        'notices': [], 'mention_only': [], 'unhandled_ids': [],
        'correlated_replies': [], 'ack_or_send_performed': False,
        'parent_read': None, 'automatic_wake': None, 'contract': BROKER_CONTRACT}
    if response is None:
        return result
    if not isinstance(response, dict) or not isinstance(response.get('messages'), list):
        raise ValueError('raw response with messages array required; retain raw evidence')
    last = response.get('last')
    if last is not None and (type(last) is not int or last < after):
        raise ValueError('invalid broker last; retain cursor and raw evidence')
    by_id = {}
    for message in response['messages']:
        if (not isinstance(message, dict) or not positive_id(message.get('id')) or
            any(not isinstance(message.get(k), str) or not message[k] for k in ('from', 'to', 'type')) or
            not isinstance(message.get('body'), dict) or
            (message.get('reply_to') is not None and not positive_id(message['reply_to']))):
            raise ValueError('malformed message; retain batch without consuming')
        mid = message['id']
        if mid in by_id and by_id[mid] != message:
            raise ValueError('conflicting duplicate ID; retain batch without consuming')
        by_id[mid] = message
    result['observation'] = 'SUPPLIED_RESPONSE_ONLY'
    result['reported_broker_last'] = last
    mention = re.compile(r'(?<![A-Za-z0-9_-])@' + re.escape(receiver) + r'(?![A-Za-z0-9_-])')
    # A recent directed request must not sit behind a broadcast backlog. Keep
    # broker order within each group, retaining every unhandled message.
    for mid, message in sorted(by_id.items(), key=lambda item: (item[1]['to'] != receiver, item[0])):
        if not eligible(message, receiver, topics):
            text = message['body'].get('text')
            if message['to'] not in (receiver, '*') and isinstance(text, str) and mention.search(text):
                result['mention_only'].append({'id': mid, 'actual_to': message['to'],
                    'status': 'NOT_ROUTED_TO_RECEIVER', 'raw': message})
            continue
        receipt = message['type'] == 'ack'
        result['notices'].append({'id': mid, 'from': message['from'], 'to': message['to'],
            'type': message['type'], 'raw_timestamp': message.get('ts'),
            'reply_to': message.get('reply_to'), 'evidence': 'BROKER_ACK_ONLY' if receipt else 'MESSAGE_ONLY',
            'raw': message})
        if not receipt and mid not in handled:
            result['unhandled_ids'].append(mid)
        if probe_id is not None and message.get('reply_to') == probe_id:
            matches_sender = expected_sender is not None and message['from'] == expected_sender
            ack_id = message['body'].get('id')
            consistent_ack = not receipt or (positive_id(ack_id) and ack_id == probe_id)
            matches_request = None if request_id is None or receipt else message['body'].get('request_id') == request_id
            result['correlated_replies'].append({'id': mid, 'reply_to': probe_id,
                'expected_sender_matches': matches_sender, 'ack_body_consistent': consistent_ack,
                'request_id_matches': matches_request,
                'status': 'CORRELATED_EVIDENCE_ONLY' if matches_sender and consistent_ack and matches_request is not False else 'UNCONFIRMED',
                'kind': 'BROKER_ACK_ONLY' if receipt else 'REPLY_CONTENT_UNVERIFIED'})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', help='caller-retained raw response JSON file; never a URL')
    parser.add_argument('--receiver', required=True)
    parser.add_argument('--after', type=int, default=0)
    parser.add_argument('--probe-id', type=int)
    parser.add_argument('--expected-sender')
    parser.add_argument('--request-id')
    args = parser.parse_args()
    with open(args.input, encoding='utf-8') as source:
        response = json.load(source)
    print(json.dumps(inspect_batch(response, args.receiver, after=args.after,
        probe_id=args.probe_id, expected_sender=args.expected_sender, request_id=args.request_id), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
