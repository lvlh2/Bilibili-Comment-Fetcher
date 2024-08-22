#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File: fetch_bilibili_comments.py
@Time: 2024/08/21 14:15:06
@Author: lvlh2
"""


import hashlib
import os
import re
import time
import urllib.parse

import pandas as pd
import requests
from lxml import etree

# NOTE: Please configure your Cookie here.
HEADERS = {
    # 'cookie': 'Your Cookie',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0',
}


class BilibiliCommentFetcher:
    """Fetches and stores Bilibili comments using the Bilibili API."""

    search_url = 'https://search.bilibili.com/all'
    comment_api = 'https://api.bilibili.com/x/v2/reply/wbi/main'
    a = 'ea1db124af3c7062474693fa704f4ff8'

    def __init__(self, title: str) -> None:
        """Initializes a new BilibiliCommentFetcher instance.

        Args:
            title (str): The title of the video.
        """
        self.title = title

    def get_video_url(self) -> str:
        """Gets the URL of the video.

        Returns:
            str: The URL of the video.
        """
        response = requests.get(
            self.search_url, params={'keyword': self.title}, headers=HEADERS
        )

        tree = etree.HTML(response.text)
        xpath = '//div[@class="bili-video-card__wrap __scale-wrap"]//a[@class=""]/@href'
        href = 'https:' + tree.xpath(xpath)[0]
        return href

    def get_oid(self, video_url: str) -> str:
        """Gets the oid of the video.

        Args:
            video_url (str): The URL of the video.

        Returns:
            str: The oid of the video.
        """
        response = requests.get(video_url, headers=HEADERS)

        pat = re.compile(r'&oid=(\d+)')
        oid = pat.search(response.text).group(1)
        return oid

    def get_w_rid(self, oid: str, pagination_str: str = '{"offset":""}') -> str:
        """Gets the w_rid of the video.

        Args:
            oid (str): The oid of the video.
            pagination_str (str, optional): The pagination string. Defaults to '{"offset":""}' for page 1.

        Returns:
            str: The w_rid of the video.
        """
        if pagination_str == '{"offset":""}':
            # NOTE: Only for page 1.
            pagination_str = urllib.parse.quote(pagination_str)
            l = [
                'mode=3',
                f'oid={oid}',
                f'pagination_str={pagination_str}',
                'plat=1',
                'seek_rpid=',
                'type=1',
                'web_location=1315875',
                f'wts={time.time():.0f}',
            ]
        else:
            pagination_str = urllib.parse.quote(pagination_str)
            l = [
                'mode=3',
                f'oid={oid}',
                f'pagination_str={pagination_str}',
                'plat=1',
                'type=1',
                'web_location=1315875',
                f'wts={time.time():.0f}',
            ]

        y = '&'.join(l)
        data = y + self.a

        md5 = hashlib.md5()
        md5.update(data.encode('utf-8'))
        w_rid = md5.hexdigest()
        return w_rid

    def get_next_offset_and_comments_in_page_1(
        self, oid: str, w_rid: str
    ) -> tuple[str, list[dict[str, list[str]]]]:
        """Gets the next offset and comments in page 1.

        Args:
            oid (str): The oid of the video.
            w_rid (str): The w_rid of the video.

        Returns:
            tuple: The next offset and comments in page 1.
        """
        # NOTE: Only for page 1.
        params = {
            'oid': f'{oid}',
            'type': '1',
            'mode': '3',
            'pagination_str': '{"offset":""}',
            'plat': '1',
            'seek_rpid': '',
            'web_location': '1315875',
            'w_rid': f'{w_rid}',
            'wts': f'{time.time():.0f}',
        }
        response = requests.get(self.comment_api, params=params, headers=HEADERS)

        data = response.json()
        next_offset = data['data']['cursor']['pagination_reply']['next_offset']

        comments = [
            {
                (
                    data['data']['replies'][i]['member']['uname'],
                    data['data']['replies'][i]['member']['sex'],
                    data['data']['replies'][i]['content']['message'],
                    data['data']['replies'][i]['like'],
                ): [
                    data['data']['replies'][i]['replies'][j]['content']['message']
                    for j in range(len(data['data']['replies'][i]['replies']))
                ]
            }
            for i in range(len(data['data']['replies']))
        ]

        return next_offset, comments

    def fetch_comments(
        self, oid: str, w_rid: str, pagination_str: str
    ) -> list[dict[str, list[str]]]:
        """Fetches comments of the page(for pages after page 1).

        Args:
            oid (str): The oid of the video.
            w_rid (str): The w_rid of the video.
            pagination_str (str): The pagination string.

        Returns:
            list: The comments of the page.
        """
        params = {
            'oid': f'{oid}',
            'type': '1',
            'mode': '3',
            'pagination_str': pagination_str,
            'plat': '1',
            'web_location': '1315875',
            'w_rid': f'{w_rid}',
            'wts': f'{time.time():.0f}',
        }
        response = requests.get(self.comment_api, params=params, headers=HEADERS)

        data = response.json()
        comments = [
            {
                (
                    data['data']['replies'][i]['member']['uname'],
                    data['data']['replies'][i]['member']['sex'],
                    data['data']['replies'][i]['content']['message'],
                    data['data']['replies'][i]['like'],
                ): [
                    data['data']['replies'][i]['replies'][j]['content']['message']
                    for j in range(len(data['data']['replies'][i]['replies']))
                ]
            }
            for i in range(len(data['data']['replies']))
        ]
        return comments


def main():
    path = os.path.dirname(__file__)
    os.chdir(path)

    title = input('Please input the title of the video:')
    fetcher = BilibiliCommentFetcher(title=title)

    video_url = fetcher.get_video_url()

    oid = fetcher.get_oid(video_url=video_url)

    # NOTE: Page 1.
    w_rid = fetcher.get_w_rid(oid=oid)

    next_offset, comments_page_1 = fetcher.get_next_offset_and_comments_in_page_1(
        oid=oid, w_rid=w_rid
    )
    total_comments = comments_page_1

    next_offset = next_offset.replace('"', r'\"')
    pagination_str = f'{{"offset":"{next_offset}"}}'

    page = 1
    while True:
        w_rid = fetcher.get_w_rid(oid=oid, pagination_str=pagination_str)
        comments = fetcher.fetch_comments(
            oid=oid, w_rid=w_rid, pagination_str=pagination_str
        )
        if len(comments) == 0:
            break
        else:
            total_comments.extend(comments)
            print(f'Page {page}: {len(comments)} comments fetched.')
            page += 1

        time.sleep(0.1)

    total_comments = pd.concat(map(pd.Series, total_comments), axis=0)
    total_comments.explode().rename_axis(
        ['User Name', 'Sex', 'Comments', 'Likes']
    ).rename('Replies').to_csv(f'{title}_comments.csv')


if __name__ == '__main__':
    main()
