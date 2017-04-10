import sys
import re
import time
import dateutil.parser
from itertools import islice
from pyquery import PyQuery as pq

interval = 1
headers = {'user-agent': 'pyquery'};

def normalize_event_url(url):
    if not re.match(r'^https?://.+?\.connpass.com/event/\d', url):
        return None
    else:
        return re.sub(r'^(https?://.+?\.connpass.com/event/\d+).*$', r'\1', url)

def fetch_event_users(event_url):
    d = pq(event_url + '/participation', headers=headers)
    return [
        {
            'id': re.sub(r'^https?://connpass\.com/user/(.+?)/?$', r'\1', d(user).find('.display_name a').attr('href')),
            'name': d(user).find('.display_name').text(),
            'url': d(user).find('.display_name a').attr('href'),
            'type': d(user).find('.label_ptype_name').text(),
            'status': d(user).find('.label_status_tag').text(),
        }
        for user in d('.participation_table_area .user')
    ]

def fetch_user_details(user):
    d = pq(user['url'], headers=headers)
    user['events'] = [
        {
            'title': d(event).find('.event_title').text(),
            'start': dateutil.parser.parse(d(event).find('.dtstart .value-title').attr('title')),
            'end': dateutil.parser.parse(d(event).find('.dtend .value-title').attr('title')),
            'status': d(event).find('.label_status_tag').text(),
            'group': d(event).find('.label_group').text(),
        }
        for event in d('.event_list')
    ]
    return user

def detect_booking_events(events):
    if events[0]['start'].date() != events[1]['start'].date():
        return None
    elif events[0]['group'] == events[1]['group']:
        return None
    else:
        return events

def window(seq, n=2):
    it = iter(seq)
    result = tuple(islice(it, n))
    if len(result) == n:
        yield result    
    for elem in it:
        result = result[1:] + (elem,)
        yield result

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage:\n  conn-cut url" % sys.argv[0])
        sys.exit(1)

    event_url = normalize_event_url(sys.argv[1])
    if not event_url:
        print('Invalid connpass event URL.')
        sys.exit(1)

    for user in fetch_event_users(event_url):
        time.sleep(interval)
        user = fetch_user_details(user)
        cancel_rate = len(list(filter(lambda e:e['status'] == 'キャンセル', user['events']))) / len(user['events'])
        booking_events = [detect_booking_events(event_pair) for event_pair in window(user['events'])]
        booking_events = list(filter(None, booking_events))
        if not booking_events and cancel_rate == 0: continue
        print('(%d%%) %s:' % (cancel_rate * 100, user['id']))
        for event_pair in booking_events:
            print('\t"%s" and "%s" are booking!' % (event_pair[0]['title'], event_pair[1]['title']))
