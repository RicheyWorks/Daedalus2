# SPDX-License-Identifier: MIT
"""Durable, bounded agent handoffs on the existing teamlink broker. No automatic agent ACKs."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import time
import uuid

from .teamlink import Link

MAX_PENDING = 256
PAGE_SIZE = 128
STATES = ('accepted', 'blocked', 'completed')


def message_body(message):
    body = message.get('body')
    return body if isinstance(body, dict) else {'text': str(body or '')}


def transport_receipt(message):
    body = message_body(message)
    return (message.get('type') == 'ack' and type(body.get('id')) is int
            and body['id'] == message.get('reply_to') and set(body) <= {'id', 'type'})


@contextmanager
def locked_state(path, me, start_after=None):
    """OS lock is released on process death; an old lock file alone never blocks recovery."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path) + '.lock', 'a+b') as lock:
        lock.seek(0, 2)
        if lock.tell() == 0:
            lock.write(b'0'); lock.flush()
        lock.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            if path.exists():
                state = json.loads(path.read_text(encoding='utf-8'))
                if state.get('version') != 1 or state.get('me') != me:
                    raise ValueError('State belongs to a different protocol or agent')
            else:
                if start_after is None or start_after < 0:
                    raise ValueError('First run requires explicit --start-after ID (0 replays all history)')
                state = dict(version=1, me=me, cursor=start_after, pending={}, outgoing={})
            yield state
            temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
            with temporary.open('x', encoding='utf-8', newline='\n') as stream:
                json.dump(state, stream, ensure_ascii=False)
                stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.name == 'nt':
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def deliver(link, envelope):
    # Existing v1 UUID deduplication makes retries after an uncertain response safe.
    response = link._call('POST', '/v1/messages', envelope)
    if not response or not response.get('seq'):
        raise ConnectionError('Hub did not confirm delivery; retry the same key/state')
    return response['seq']


def request(state, link, key, to, text, ack_within=30, now=None):
    now = time.time() if now is None else now
    if not key or len(key)>128 or not to or len(to)>80 or to == '*' or not text \
            or len(text.encode('utf-8'))>16000 or not 1 <= ack_within <= 3600:
        raise ValueError('A direct recipient, stable key, text and 1..3600 second deadline are required')
    outgoing = state['outgoing']
    if key not in outgoing:
        if len(outgoing) >= MAX_PENDING:
            raise ValueError('Outgoing capacity reached; archive completed requests first')
        outgoing[key] = dict(to=to, text=text, sent_at=now, ack_by=now + ack_within,
                             uid=str(uuid.uuid4()), state='sending')
    item = outgoing[key]
    if item['to'] != to or item['text'] != text:
        raise ValueError('Key already identifies a different request')
    if not item.get('id'):
        # Persist this envelope before calling deliver (CLI commits it in a separate transaction).
        item['envelope'] = {'v': 1, 'id': item['uid'], 'from': link.me, 'to': to, 'type': 'request',
                            'body': {'text': text, 'ack_by': item['ack_by'], 'key': key}}
    return item


def send_request(item, link):
    if not item.get('id'):
        item['id'] = deliver(link, item['envelope'])
        item['state'] = 'sent'
    return item['id']


def collect(state, link):
    page = link._call('GET', '/log?after=%d&limit=%d' % (state['cursor'], PAGE_SIZE))
    if page is None:
        raise ConnectionError('Hub unavailable; cursor and inbox preserved')
    for message in page['messages']:
        # Topics describe work; they must not silently discard another team's ping.
        # Broker housekeeping is available in the hub log, not the decision inbox.
        broadcast = message['to'] == '*' and message['type'] not in ('lock', 'unlock', 'bot.register')
        relevant = message['from'] != link.me and (message['to'] == link.me or broadcast)
        if relevant:
            reply = message.get('reply_to')
            for item in state['outgoing'].values():
                if item.get('id') == reply and item['to'] == message['from']:
                    kind = message['type']
                    if kind == 'ack' and item['state'] == 'sent':
                        item['state'] = 'received'  # A receipt is not acceptance or completion.
                    elif kind.startswith('request.') and kind[8:] in STATES:
                        incoming = kind[8:]
                        if item['state'] != 'completed':
                            item['state'] = incoming
                            item['reply'] = message
                            if incoming in ('accepted', 'completed'):
                                item.setdefault('acceptance_observed_at', time.time())
            if not transport_receipt(message):
                if len(state['pending']) >= MAX_PENDING:
                    break  # Do not advance past a message we cannot durably retain.
                state['pending'].setdefault(str(message['id']), dict(message=message, state='queued'))
        state['cursor'] = message['id']


def prepare_response(state, link, mid, status, text):
    if status not in STATES or not text or len(text.encode('utf-8'))>16000:
        raise ValueError('Explicit accepted, blocked or completed response and text required')
    item = state['pending'].get(str(mid))
    if not item:
        raise ValueError('Read the message into this agent inbox before responding')
    if item['state'] == 'completed' and status != 'completed':
        raise ValueError('Completed handoff cannot move backwards')
    message = item['message']
    previous = item.get('response_envelope')
    if previous and previous['type'] == 'request.' + status and previous['body']['text'] == text:
        return previous
    envelope = {'v': 1, 'id': str(uuid.uuid4()),
                'from': link.me, 'to': message['from'], 'type': 'request.' + status,
                'reply_to': str(mid), 'body': {'text': text}}
    item['response_envelope'] = envelope
    return envelope


def respond(state, link, mid, status, text):
    envelope = prepare_response(state, link, mid, status, text)
    item = state['pending'][str(mid)]
    # Never ACK just because a listener received bytes. This follows an explicit agent decision.
    seq = deliver(link, envelope)
    item['state'] = status
    item['response'] = seq
    if not link.ack(mid):
        raise ConnectionError('Response delivered; ACK uncertain. Retry the same response state')
    return seq


def summary(state, now=None, limit=12):
    now = time.time() if now is None else now
    pending = [item for item in state['pending'].values() if item['state'] not in ('completed', 'handled')]
    pending.sort(key=lambda item: (item['state'] != 'queued', item['message']['type'] != 'request', item['message']['id']))
    return {'cursor': state['cursor'], 'pending_count': len(pending),
            'queued_count': sum(item['state'] == 'queued' for item in pending),
            'inbox_capacity': MAX_PENDING,
            'messages': [{'id': p['message']['id'], 'from': p['message']['from'],
                          'type': p['message']['type'], 'state': p['state'],
                          'text': str(message_body(p['message']).get('text', ''))[:700]}
                         for p in pending[:limit]],
            'requests': [{'key': key, 'id': item.get('id'), 'to': item['to'], 'state': item['state'],
                          'acceptance_observed_seconds': round(item['acceptance_observed_at'] - item['sent_at'], 3)
                              if 'acceptance_observed_at' in item else None,
                          'acceptance_overdue': now > item['ack_by'] and item['state'] in ('sending', 'sent', 'received')}
                         for key, item in state['outgoing'].items() if item['state'] != 'completed'],
            'meaning': 'Queued/receipt is not agent acceptance. A listener cannot wake an idle model.'}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--me', required=True); p.add_argument('--state', required=True)
    p.add_argument('--port', type=int, default=9890)
    p.add_argument('--start-after', type=int)
    sub = p.add_subparsers(dest='command', required=True)
    poll = sub.add_parser('poll'); poll.add_argument('--wait', type=float, default=0)
    send = sub.add_parser('request'); send.add_argument('--to', required=True)
    send.add_argument('--key', required=True); send.add_argument('--text', required=True)
    send.add_argument('--ack-within', type=int, default=30)
    send.add_argument('--allow-unregistered', action='store_true',
                      help='Explicitly allow a new bot address not yet registered in this hub')
    reply = sub.add_parser('respond'); reply.add_argument('--id', type=int, required=True, action='append',
        help='Request ID; repeat to send a separately correlated response for each request')
    reply.add_argument('--status', choices=STATES, required=True); reply.add_argument('--text', required=True)
    sub.add_parser('status')
    read = sub.add_parser('read', help='Read a full retained message without acknowledging it')
    read.add_argument('--id', type=int, required=True)
    receipt = sub.add_parser('ack'); receipt.add_argument('--id', type=int, required=True)
    replay = sub.add_parser('replay'); replay.add_argument('--after', type=int, required=True)
    sub.add_parser('archive-completed')
    a = p.parse_args(argv)
    link = Link(a.me, a.port)
    if a.command == 'request':
        # Save the UUID before the network call so process death cannot duplicate a request.
        with locked_state(a.state, a.me, a.start_after) as state:
            if a.key not in state['outgoing'] and not a.allow_unregistered:
                bots = link._call('GET', '/bots')
                if not isinstance(bots, dict):
                    raise ConnectionError('Cannot verify recipient registration; no request saved or sent')
                if a.to not in bots:
                    raise ValueError('Unknown recipient %r; check /bots or explicitly use --allow-unregistered' % a.to)
            request(state, link, a.key, a.to, a.text, a.ack_within)
    elif a.command == 'respond':
        with locked_state(a.state, a.me, a.start_after) as state:
            # Validate the entire batch and persist every UUID before sending anything.
            # A retry after partial delivery reuses each envelope independently.
            for mid in dict.fromkeys(a.id):
                prepare_response(state, link, mid, a.status, a.text)
    if a.command == 'poll' and not 0 <= a.wait <= 55:
        p.error('--wait must be between 0 and 55 seconds')
    with locked_state(a.state, a.me, a.start_after) as state:
        if a.command == 'request':
            send_request(state['outgoing'][a.key], link)
        elif a.command == 'respond':
            for mid in dict.fromkeys(a.id):
                respond(state, link, mid, a.status, a.text)
        elif a.command == 'poll':
            collect(state, link)
        elif a.command == 'replay':
            if not 0 <= a.after <= state['cursor']:
                raise ValueError('Replay cursor must be between 0 and the current cursor')
            state['cursor'] = a.after
        elif a.command == 'ack':
            item = state['pending'].get(str(a.id))
            if not item or item['message']['type'] == 'request':
                raise ValueError('Requests need an explicit response; ACK is for notes/status/replies')
            if not link.ack(a.id):
                raise ConnectionError('Receipt uncertain; retry the same ID')
            item['state'] = 'handled'
        elif a.command == 'archive-completed':
            for name in ('pending', 'outgoing'):
                state[name] = {key: item for key, item in state[name].items() if item['state'] not in ('completed', 'handled')}
        if a.command == 'read':
            item = state['pending'].get(str(a.id))
            if not item:
                raise ValueError('Message is not retained; poll or explicitly replay its history first')
            result = item
        else:
            result = summary(state)
    if a.command == 'poll' and a.wait and not result['queued_count']:
        link.wait(result['cursor'], a.wait)
        with locked_state(a.state, a.me) as state:
            collect(state, link); result = summary(state)
    # ASCII JSON also works when Windows launches Python with a non-UTF-8 pipe encoding.
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
