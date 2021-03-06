# -*- coding: utf-8 -*-
# Copyright 2011-2012 Antoine Bertin <diaoulael@gmail.com>
#
# This file is part of subliminal.
#
# subliminal is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with subliminal.  If not, see <http://www.gnu.org/licenses/>.
from . import ServiceBase
from ..exceptions import ServiceError
from ..subtitles import get_subtitle_path, ResultSubtitle
from ..videos import Episode, Movie
from bs4 import BeautifulSoup
from guessit.language import lang_set
from subliminal.utils import get_keywords, split_keyword
import guessit
import logging
import re
import urllib


logger = logging.getLogger(__name__)


class SubsWiki(ServiceBase):
    server_url = 'http://www.subswiki.com'
    api_based = False
    languages = lang_set([u'English (US)', u'English (UK)', u'English', u'French', u'Brazilian',
                          u'Portuguese', u'Español (Latinoamérica)', u'Español (España)',
                          u'Español', u'Italian', u'Català'], strict=True)
    videos = [Episode, Movie]
    require_video = False
    release_pattern = re.compile('\nVersion (.+), ([0-9]+).([0-9])+ MBs')

    def list_checked(self, video, languages):
        results = []
        if isinstance(video, Episode):
            results = self.query(video.path or video.release, languages, get_keywords(video.guess), series=video.series, season=video.season, episode=video.episode)
        elif isinstance(video, Movie) and video.year:
            results = self.query(video.path or video.release, languages, get_keywords(video.guess), movie=video.title, year=video.year)
        return results

    def query(self, filepath, languages, keywords=None, series=None, season=None, episode=None, movie=None, year=None):
        if series and season and episode:
            request_series = series.lower().replace(' ', '_')
            if isinstance(request_series, unicode):
                request_series = request_series.encode('utf-8')
            logger.debug(u'Getting subtitles for %s season %d episode %d with languages %r' % (series, season, episode, languages))
            r = self.session.get('%s/serie/%s/%s/%s/' % (self.server_url, urllib.quote(request_series), season, episode))
            if r.status_code == 404:
                logger.debug(u'Could not find subtitles for %s season %d episode %d with languages %r' % (series, season, episode, languages))
                return []
        elif movie and year:
            request_movie = movie.title().replace(' ', '_')
            if isinstance(request_movie, unicode):
                request_movie = request_movie.encode('utf-8')
            logger.debug(u'Getting subtitles for %s (%d) with languages %r' % (movie, year, languages))
            r = self.session.get('%s/film/%s_(%d)' % (self.server_url, urllib.quote(request_movie), year))
            if r.status_code == 404:
                logger.debug(u'Could not find subtitles for %s (%d) with languages %r' % (movie, year, languages))
                return []
        else:
            raise ServiceError('One or more parameter missing')
        if r.status_code != 200:
            logger.error(u'Request %s returned status code %d' % (r.url, r.status_code))
            return []
        soup = BeautifulSoup(r.content, self.config.parser)
        subtitles = []
        for sub in soup('td', {'class': 'NewsTitle'}):
            sub_keywords = split_keyword(self.release_pattern.search(sub.contents[1]).group(1).lower())
            if not keywords & sub_keywords:
                logger.debug(u'None of subtitle keywords %r in %r' % (sub_keywords, keywords))
                continue
            for html_language in sub.parent.parent.findAll('td', {'class': 'language'}):
                language = guessit.Language(html_language.string.strip())
                if not language in languages:
                    logger.debug(u'Language %r not in wanted languages %r' % (language, languages))
                    continue
                html_status = html_language.findNextSibling('td')
                status = html_status.find('strong').string.strip()
                if status != 'Completed':
                    logger.debug(u'Wrong subtitle status %s' % status)
                    continue
                path = get_subtitle_path(filepath, language, self.config.multi)
                subtitle = ResultSubtitle(path, language, service=self.__class__.__name__.lower(), link='%s%s' % (self.server_url, html_status.findNext('td').find('a')['href']))
                subtitles.append(subtitle)
        return subtitles


Service = SubsWiki
