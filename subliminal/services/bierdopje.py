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
from ..cache import cachedmethod
from ..exceptions import ServiceError
from ..subtitles import get_subtitle_path, ResultSubtitle
from ..utils import to_unicode
from ..videos import Episode
from bs4 import BeautifulSoup
from guessit.language import lang_set
import logging
import urllib
try:
    import cPickle as pickle
except ImportError:
    import pickle


logger = logging.getLogger(__name__)


class BierDopje(ServiceBase):
    server_url = 'http://api.bierdopje.com/A2B638AC5D804C2E/'
    api_based = True
    languages = lang_set(['en', 'nl'])
    videos = [Episode]
    require_video = False

    @cachedmethod
    def get_show_id(self, series):
        r = self.session.get('%sGetShowByName/%s' % (self.server_url, urllib.quote(series.lower())))
        if r.status_code != 200:
            logger.error(u'Request %s returned status code %d' % (r.url, r.status_code))
            return None

        soup = BeautifulSoup(r.content, self.config.parser)
        if soup.status.contents[0] == 'false':
            logger.debug(u'Could not find show %s' % series)
            return None

        return int(soup.showid.contents[0])

    def load_cache(self):
        logger.debug(u'Loading showids from cache...')
        with self.lock:
            with open(self.showids_cache, 'r') as f:
                self.showids = pickle.load(f)

    def query(self, filepath, season, episode, languages, tvdbid=None, series=None):
        self.init_cache()
        if series:
            request_id = self.get_show_id(series.lower())
            if request_id is None:
                return []
            request_source = 'showid'
            request_is_tvdbid = 'false'
        elif tvdbid:
            request_id = tvdbid
            request_source = 'tvdbid'
            request_is_tvdbid = 'true'
        else:
            raise ServiceError('One or more parameter missing')
        subtitles = []
        for language in languages:
            logger.debug(u'Getting subtitles for %s %d season %d episode %d with language %s' % (request_source, request_id, season, episode, language.alpha2))
            r = self.session.get('%sGetAllSubsFor/%s/%s/%s/%s/%s' % (self.server_url, request_id, season, episode, language.alpha2, request_is_tvdbid))
            if r.status_code != 200:
                logger.error(u'Request %s returned status code %d' % (r.url, r.status_code))
                return []
            soup = BeautifulSoup(r.content, self.config.parser)
            if soup.status.contents[0] == 'false':
                logger.debug(u'Could not find subtitles for %s %d season %d episode %d with language %s' % (request_source, request_id, season, episode, language.alpha2))
                continue
            path = get_subtitle_path(filepath, language, self.config.multi)
            for result in soup.results('result'):
                subtitle = ResultSubtitle(path, language, service=self.__class__.__name__.lower(), link=result.downloadlink.contents[0],
                                          release=to_unicode(result.filename.contents[0]))
                subtitles.append(subtitle)
        return subtitles

    def list_checked(self, video, languages):
        return self.query(video.path or video.release, video.season, video.episode, languages, video.tvdbid, video.series)


Service = BierDopje
