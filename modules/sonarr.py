#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cherrypy
import htpc
from cherrypy.lib.auth2 import require
import requests
import urllib
import logging
from json import loads, dumps
import datetime as DT
from htpc.helpers import fix_basepath, get_image, striphttp


class Sonarr(object):
    def __init__(self):
        self.logger = logging.getLogger('modules.sonarr')
        htpc.MODULES.append({
            'name': 'Sonarr',
            'id': 'sonarr',
            'test': htpc.WEBDIR + 'sonarr/Version',
            'fields': [
                {'type': 'bool', 'label': 'Enable', 'name': 'sonarr_enable'},
                {'type': 'text', 'label': 'Menu name', 'name': 'sonarr_name'},
                {'type': 'text', 'label': 'IP / Host', 'placeholder': 'localhost', 'name': 'sonarr_host'},
                {'type': 'text', 'label': 'Port', 'placeholder': '8989', 'name': 'sonarr_port'},
                {'type': 'text', 'label': 'Basepath', 'placeholder': '/sonarr', 'name': 'sonarr_basepath'},
                {'type': 'text', 'label': 'API', 'name': 'sonarr_apikey'},
                {'type': 'bool', 'label': 'Use SSL', 'name': 'sonarr_ssl'},
                {'type': 'text', 'label': 'Reverse proxy link', 'placeholder': '', 'desc': 'Reverse proxy link, e.g. https://sonarr.domain.com', 'name': 'sonarr_reverse_proxy_link'},

            ]
        })

    @cherrypy.expose()
    @require()
    def index(self):
        return htpc.LOOKUP.get_template('sonarr.html').render(scriptname='sonarr', webinterface=self.webinterface())

    def webinterface(self):
        host = striphttp(htpc.settings.get('sonarr_host', ''))
        port = str(htpc.settings.get('sonarr_port', ''))
        sonarr_basepath = htpc.settings.get('sonarr_basepath', '/')
        ssl = 's' if htpc.settings.get('sonarr_ssl', True) else ''

        # Makes sure that the basepath is /whatever/
        sonarr_basepath = fix_basepath(sonarr_basepath)

        url = 'http%s://%s:%s%s' % (ssl, host, port, sonarr_basepath)

        if htpc.settings.get('sonarr_reverse_proxy_link'):
            url = htpc.settings.get('sonarr_reverse_proxy_link')

        return url

    def fetch(self, path, banner=None, type=None, data=None):
        try:
            host = striphttp(htpc.settings.get('sonarr_host', ''))
            port = str(htpc.settings.get('sonarr_port', ''))
            sonarr_basepath = htpc.settings.get('sonarr_basepath', '/')
            ssl = 's' if htpc.settings.get('sonarr_ssl', True) else ''

            # Makes sure that the basepath is /whatever/
            sonarr_basepath = fix_basepath(sonarr_basepath)

            headers = {'X-Api-Key': htpc.settings.get('sonarr_apikey', '')}

            url = 'http%s://%s:%s%sapi/%s' % (ssl, host, port, sonarr_basepath, path)

            if banner:
                #  the path includes the basepath automaticly
                url = 'http%s://%s:%s%s' % (ssl, host, port, path)
                # Cache the image in HTPC Manager aswell.
                return get_image(url, headers=headers)

            if type == 'post':
                r = requests.post(url, data=dumps(data), headers=headers, verify=False)
                return r.content

            elif type == 'put':
                r = requests.put(url, data=dumps(data), headers=headers, verify=False)
                return r.content

            elif type == 'delete':
                r = requests.delete(url, data=dumps(data), headers=headers, verify=False)
                return r.content

            else:
                r = requests.get(url, headers=headers, verify=False)
                return loads(r.text)

        except Exception as e:
            self.logger.error('Failed to fetch url=%s path=%s error %s' % (url, path, e))

    @cherrypy.expose()
    @require()
    def Version(self, sonarr_host, sonarr_port, sonarr_basepath, sonarr_apikey, sonarr_ssl = False, **kwargs):
        try:
            ssl = 's' if sonarr_ssl else ''

            if not sonarr_basepath:
                sonarr_basepath = fix_basepath(sonarr_basepath)

            headers = {'X-Api-Key': str(sonarr_apikey)}

            url = 'http%s://%s:%s%sapi/system/status' % (ssl, striphttp(sonarr_host), sonarr_port, sonarr_basepath)

            result = requests.get(url, headers=headers, verify=False)
            return result.json()
        except:
            return

    @cherrypy.expose()
    @require()
    @cherrypy.tools.json_out()
    def Rootfolder(self):
        return [folder["path"] for folder in self.fetch('Rootfolder')]

    #Returns all shows
    @cherrypy.expose()
    @require()
    @cherrypy.tools.json_out()
    def Series(self):
        return self.fetch('Series')

    #Return one show
    @cherrypy.expose()
    @require()
    @cherrypy.tools.json_out()
    def Show(self, id, tvdbid=None):
        return self.fetch('Series/%s' % id)

    @cherrypy.expose()
    @require()
    @cherrypy.tools.json_out()
    def Delete_Show(self, id, title, delete_date=None):
        self.logger.debug('Deleted tvshow %s' % title)
        return self.fetch('Series/%s' % id, type='delete')

    @cherrypy.expose()
    @require()
    @cherrypy.tools.json_out()
    def History(self):
        return self.fetch('History?page=1&pageSize=100&sortKey=date&sortDir=desc')

    @cherrypy.expose()
    @require()
    @cherrypy.tools.json_out()
    def Calendar(self, param=None):
        return self.fetch('Calendar?end=%s' % (DT.date.today() + DT.timedelta(days=7)))

    @cherrypy.expose()
    @require()
    def View(self, tvdbid, id):
        if not (tvdbid.isdigit()):
            raise cherrypy.HTTPError("500 Error", "Invalid show ID.")
            self.logger.error("Invalid show ID was supplied: " + str(id))
            return False

        return htpc.LOOKUP.get_template('sonarr_view.html').render(scriptname='sonarr_view', tvdbid=tvdbid, id=id)

    @cherrypy.expose()
    @require()
    @cherrypy.tools.json_out()
    def Episodes(self, id):
        return self.fetch('episode?seriesId=%s' % id)

    @cherrypy.expose()
    @require()
    def GetBanner(self, url=None):
        self.logger.debug("Fetching Banner")
        cherrypy.response.headers['Content-Type'] = 'image/jpeg'
        return self.fetch(url, banner=True)

    @cherrypy.expose()
    @require()
    @cherrypy.tools.json_out()
    def Episode(self, id):
        self.logger.debug("Fetching Episode info")
        return self.fetch('episode/%s' % id)

    #Returns all the episodes from a show, with file info
    @cherrypy.expose()
    @require()
    @cherrypy.tools.json_out()
    def Episodesqly(self, id):
        self.logger.debug('Fetching fileinfo for all episodes in a show')
        return self.fetch('episodefile?seriesId=%s' % id)

    #Return one episode with file info
    @cherrypy.expose()
    @require()
    @cherrypy.tools.json_out()
    def Episodeqly(self, id):
        return self.fetch('episodefile/%s' % id)

    #Return the download profiles, used to match a id to  get the name
    @cherrypy.expose()
    @require()
    @cherrypy.tools.json_out()
    def Profile(self):
        return self.fetch('profile')

    @cherrypy.expose()
    @require()
    def Command(self, **kwargs):
        k = kwargs
        cherrypy.response.headers['Content-Type'] = "application/json"
        try:
            data = {}
            data["name"] = k["method"]
            if k["par"] == "episodeIds":
                k["id"] = [int(k["id"])]
            data[k["par"]] = k["id"]
        except KeyError:
            pass

        return self.fetch(path='command', data=data, type='post')

    #Search for a serie
    @cherrypy.expose()
    @require()
    @cherrypy.tools.json_out()
    def Lookup(self, q):
        return self.fetch('Series/lookup?term=%s' % urllib.quote(q))

    @cherrypy.expose()
    @require()
    def AddShow(self, tvdbid, quality, rootfolder='', seasonfolder='on', specials='off'):
        d = {}
        try:
            tvshow = self.fetch('Series/lookup?term=tvdbid:%s' % tvdbid)
            seasoncount = 1
            season = []
            for i in tvshow:
                seasoncount += i['seasonCount']

                d["title"] = i['title']
                d["tvdbId"] = int(i['tvdbId'])
                d["qualityProfileId"] = int(quality)
                d["titleSlug"] = i['titleSlug']
                d["RootFolderPath"] = rootfolder
                d["monitored"] = True

                if seasonfolder == 'on':
                    d["seasonFolder"] = True
                if specials == 'on':
                    start_on_season = 0
                else:
                    start_on_season = 1

                for x in xrange(start_on_season, int(seasoncount)):
                    s = {"seasonNumber": x, "monitored": True}
                    season.append(s)

                d["seasons"] = season

            # Manually add correct headers since @cherrypy.tools.json_out() renders it wrong
            cherrypy.response.headers['Content-Type'] = "application/json"
            return self.fetch('Series', data=d, type='post')

        except Exception, e:
            self.logger.error('Failed to add tvshow %s %s' % (tvdbid, e))
