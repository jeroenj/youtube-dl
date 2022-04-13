# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import int_or_none
from .goplay_auth_aws import AwsIdp


class GoPlayIE(InfoExtractor):
    IE_NAME = 'goplay'
    IE_DESC = 'GoPlay.be'
    _VALID_URL = r'https?://(www\.)?goplay\.be/video/(?P<series>[^/]+)/(?P<season>[^/]+)(/(?P<episode>[^/]+)|)'
    _NETRC_MACHINE = 'goplay'
    _TESTS = [{
        'url': 'https://www.goplay.be/video/de-container-cup/de-container-cup-s3/de-container-cup-s3-aflevering-2#autoplay',
        'info_dict': {
            'id': '9c4214b8-e55d-4e4b-a446-f015f6c6f811',
            'ext': 'mp4',
            'title': 'S3 - Aflevering 2',
            'series': 'De Container Cup',
            'season': 'Season 3',
            'season_number': 3,
            'episode': 'Episode 2',
            'episode_number': 2,
        },
        'skip': 'This video is only available for registered users'
    }]

    def _real_initialize(self):
        self._logged_in = False
        self._id_token = ''

    def _login(self):
        self.report_login()
        username, password = self._get_login_info()
        if username is None or password is None:
            self.raise_login_required()

        aws = AwsIdp(pool_id='eu-west-1_dViSsKM5Y', client_id='6s1h851s8uplco5h6mqh1jac8m')
        self._id_token, _ = aws.authenticate(username=username, password=password)
        self._logged_in = True

    def _real_extract(self, url):
        if not self._logged_in:
            self._login()

        if "#" in url:
            url = url.split("#")[0]

        display_id = url.split('#')[0].split('/')[-1]

        webpage = self._download_webpage(url, display_id)
        video_data = self._html_search_regex(r'<div\s+data-hero="([^"]+)"', webpage, 'video_data')
        playlists = self._parse_json(video_data.replace('&quot;', '"'), display_id)['data']['playlists']
        playlist = [x for x in playlists if x['pageInfo']['url'] in url][0]
        episode = [x for x in playlist['episodes'] if x['pageInfo']['url'] == url][0] or [x for x in playlist['episodes'] if x['pageInfo']['url'] in url][0]
        video_id = episode['videoUuid']

        api = self._download_json(
            'https://api.viervijfzes.be/content/%s' % video_id,
            video_id,
            headers={'authorization': self._id_token},
        )

        formats = self._extract_m3u8_formats(
            api['video']['S'], video_id, ext='mp4', entry_protocol='m3u8_native', m3u8_id='HLS')
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': episode['episodeTitle'],
            'series': episode['program']['title'],
            'season_number': int_or_none(episode['seasonNumber'] ),
            'episode_number': int_or_none(episode['episodeNumber']),
            'formats': formats,
        }
