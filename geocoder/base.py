#!/usr/bin/python
# coding: utf8

from __future__ import absolute_import
import requests
import sys
import json
import six
from collections import defaultdict
from geocoder.distance import Distance

is_python2 = sys.version_info < (3, 0)


class Base(object):
    _exclude = ['parse', 'json', 'url', 'fieldnames', 'help', 'debug',
                'short_name', 'api', 'content', 'params',
                'street_number', 'api_key', 'key', 'id', 'x', 'y',
                'latlng', 'headers', 'timeout', 'wkt', 'locality',
                'province', 'rate_limited_get', 'osm', 'route', 'schema',
                'properties', 'geojson', 'tree', 'error', 'proxies', 'road',
                'xy', 'northeast', 'northwest', 'southeast', 'southwest',
                'road_long', 'city_long', 'state_long', 'country_long',
                'postal_town_long', 'province_long', 'road_long',
                'street_long', 'interpolated', 'method', 'geometry', 'session']
    fieldnames = []
    error = None
    status_code = None
    session = None
    headers = {}
    params = {}

    # Essential attributes for Quality Control
    lat = ''
    lng = ''
    accuracy = ''
    quality = ''
    confidence = ''

    # Bounding Box attributes
    northeast = []
    northwest = []
    southeast = []
    southwest = []
    bbox = {}

    # Essential attributes for Street Address
    address = ''
    housenumber = ''
    street = ''
    road = ''
    city = ''
    state = ''
    country = ''
    postal = ''

    def __repr__(self):
        if self.address:
            return u'<[{0}] {1} - {2} [{3}]>'.format(
                self.status,
                self.provider.title(),
                self.method.title(),
                six.text_type(self.address)
            )
        else:
            return u'<[{0}] {1} - {2}>'.format(
                self.status,
                self.provider.title(),
                self.method.title()
            )

    def rate_limited_get(self, url, **kwargs):
        return self.session.get(url, **kwargs)

    @staticmethod
    def _get_api_key(base_key, **kwargs):
        key = kwargs.get('key')
        # Retrieves API Key from method argument first
        if key:
            return key
        # Retrieves API Key from Environment variables
        elif base_key:
            return base_key
        raise ValueError('Provide API Key')

    def _connect(self, **kwargs):
        try:
            ret = self.rate_limited_get(
                self.url,
                params=self.params,
                headers=self.headers,
                timeout=self.timeout,
                proxies=self.proxies
            )
        except (KeyboardInterrupt, SystemExit):
            raise
        except requests.exceptions.SSLError:
            self.status_code = 495
            self.error = 'ERROR - SSLError'
        else:
            return ret

    def read_request_response(self, ret):
        # Open JSON content from Request response
        self.status_code = ret.status_code
        self.url = ret.url
        if ret.content:
            self.status_code = 200
        if self.status_code == 200:
            try:
                self.content = ret.json()
            except:
                self.status_code = 400
                self.error = 'ERROR - JSON Corrupted'
                self.content = ret.content

    async def read_request_response_async(self, ret):
        # Open JSON content from Request response
        self.status_code = ret.status
        self.url = ret.url
        if ret.content:
            self.status_code = 200
        if self.status_code == 200:
            try:
                self.content = await ret.json()
            except:
                self.status_code = 400
                self.error = 'ERROR - JSON Corrupted'
                self.content = await ret.content.read()

    def _load_response(self):
        try:
            for result in self.next():  # Convert to iterator in each of the search tools
                self._build_tree(result)
                self._exceptions()
                self._catch_errors()
                self._json()
        except:
            self._build_tree(self.content)
            self._exceptions()
            self._catch_errors()
            self._json()

    def _initialize(self, **kwargs):
        # Remove extra URL from kwargs
        if 'url' in kwargs:
            kwargs.pop('url')
        self.json = {}
        self.parse = self.tree()
        self.content = None
        self.encoding = kwargs.get('encoding', 'utf-8')
        self.session = kwargs.get('session', requests.Session())
        self.status_code = 'Unknown'
        self.timeout = kwargs.get('timeout', 5.0)
        self.proxies = kwargs.get('proxies', None)
        # already load result if session comes from request, if it is synchronous
        if isinstance(self.session, requests.Session):
            result = self._connect(url=self.url, **kwargs)
            if result:
                self.read_request_response(ret=result)
            self._load_response()

    async def _init(self):
        if not self.proxies:
            proxy = None
        elif isinstance(self.proxies, (list, tuple)):
            proxy = self.proxies[0]
        elif isinstance(self.proxies, dict):
            proxy = self.proxies.get('https', self.proxies.get('http', list(self.proxies.values())[0]))
        else:
            proxy = self.proxies
        async with self.session.get(
                self.url,
                params=self.params,
                headers=self.headers,
                timeout=self.timeout,
                proxy=proxy) as result:
            if result:
                await self.read_request_response_async(ret=result)
            self._load_response()

    def _json(self):
        self.fieldnames = []
        for key in dir(self):
            if not key.startswith('_') and key not in self._exclude:
                self.fieldnames.append(key)
                value = getattr(self, key)
                if value:
                    self.json[key] = value
        # Add OK attribute even if value is "False"
        self.json['ok'] = self.ok

    def debug(self):
        print(json.dumps(self.parse, indent=4))
        print(json.dumps(self.json, indent=4))
        print('')
        print('OSM Quality')
        print('-----------')
        count = 0
        for key in self.osm:
            if 'addr:' in key:
                if self.json.get(key.replace('addr:', '')):
                    print('- [x] {0}'.format(key))
                    count += 1
                else:
                    print('- [ ] {0}'.format(key))
        print('({0}/{1})'.format(count, len(self.osm) - 2))
        print('')
        print('Fieldnames')
        print('----------')
        count = 0
        for fieldname in self.fieldnames:
            if self.json.get(fieldname):
                print('- [x] {0}'.format(fieldname))
                count += 1
            else:
                print('- [ ] {0}'.format(fieldname))
        print('({0}/{1})'.format(count, len(self.fieldnames)))
        print('')
        print('URL')
        print('---')
        print(self.url)

    def _exceptions(self):
        pass

    def _catch_errors(self):
        pass

    def tree(self):
        return defaultdict(self.tree)

    def _build_tree(self, content, last=''):
        if content:
            if isinstance(content, dict):
                for key, value in content.items():
                    # Rebuild the tree if value is a dictionary
                    if isinstance(value, dict):
                        self._build_tree(value, last=key)
                    else:
                        if last:
                            self.parse[last][key] = value
                        else:
                            self.parse[key] = value

    @property
    def status(self):
        if self.ok:
            return 'OK'
        elif self.error:
            return self.error

        if self.status_code == 200:
            if not self.address:
                return 'ERROR - No results found'
            elif not (self.lng and self.lat):
                return 'ERROR - No Geometry'
        return 'ERROR - Unhandled Exception'

    def _get_bbox(self, south, west, north, east):
        if all([south, east, north, west]):
            # South Latitude, West Longitude, North Latitude, East Longitude
            self.south = float(south)
            self.west = float(west)
            self.north = float(north)
            self.east = float(east)

            # Bounding Box Corners
            self.northeast = [self.north, self.east]
            self.northwest = [self.north, self.west]
            self.southwest = [self.south, self.west]
            self.southeast = [self.south, self.east]

            # GeoJSON bbox
            self.westsouth = [self.west, self.south]
            self.eastnorth = [self.east, self.north]

            return dict(northeast=self.northeast, southwest=self.southwest)
        return {}

    @property
    def confidence(self):
        if self.bbox:
            # Units are measured in Kilometers
            distance = Distance(self.northeast, self.southwest, units='km')
            for score, maximum in [(10, 0.25),
                                   (9, 0.5),
                                   (8, 1),
                                   (7, 5),
                                   (6, 7.5),
                                   (5, 10),
                                   (4, 15),
                                   (3, 20),
                                   (2, 25)]:
                if distance < maximum:
                    return score
                if distance >= 25:
                    return 1
        # Cannot determine score
        return 0

    @property
    def ok(self):
        return bool(self.lng and self.lat)

    @property
    def geometry(self):
        if self.ok:
            return {
                'type': 'Point',
                'coordinates': [self.x, self.y]}
        return {}

    @property
    def osm(self):
        osm = dict()
        if self.ok:
            osm['x'] = self.x
            osm['y'] = self.y
            if self.housenumber:
                osm['addr:housenumber'] = self.housenumber
            if self.road:
                osm['addr:street'] = self.road
            if self.city:
                osm['addr:city'] = self.city
            if self.state:
                osm['addr:state'] = self.state
            if self.country:
                osm['addr:country'] = self.country
            if self.postal:
                osm['addr:postal'] = self.postal
            if hasattr(self, 'population'):
                if self.population:
                    osm['population'] = self.population
        return osm

    @property
    def geojson(self):
        feature = {
            'type': 'Feature',
            'properties': self.json,
        }
        if self.bbox:
            feature['bbox'] = [self.west, self.south, self.east, self.north]
            feature['properties']['bbox'] = feature['bbox']
        if self.geometry:
            feature['geometry'] = self.geometry
        return feature

    @property
    def wkt(self):
        if self.ok:
            return 'POINT({x} {y})'.format(x=self.x, y=self.y)
        return ''

    @property
    def xy(self):
        if self.ok:
            return [self.lng, self.lat]
        return []

    @property
    def latlng(self):
        if self.ok:
            return [self.lat, self.lng]
        return []

    @property
    def y(self):
        return self.lat

    @property
    def x(self):
        return self.lng

    @property
    def locality(self):
        return self.city

    @property
    def province(self):
        return self.state

    @property
    def street_number(self):
        return self.housenumber

    @property
    def road(self):
        return self.street

    @property
    def route(self):
        return self.street
