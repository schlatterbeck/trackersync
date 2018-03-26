#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2018 Dr. Ralf Schlatterbeck Open Source Consulting.
# Reichergasse 131, A-3411 Weidling.
# Web: http://www.runtux.com Email: office@runtux.com
# All rights reserved
# ****************************************************************************
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA
# ****************************************************************************

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import

import requests
import json
import numbers
from   time                 import sleep
from   rsclib.autosuper     import autosuper
from   rsclib.pycompat      import ustr, text_type
from   trackersync          import tracker_sync
from   trackersync.jirasync import jira_utctime

Sync_Attribute                   = tracker_sync.Sync_Attribute
Sync_Attribute_Check             = tracker_sync.Sync_Attribute_Check
Sync_Attribute_Check_Remote      = tracker_sync.Sync_Attribute_Check_Remote
Sync_Attribute_To_Local          = tracker_sync.Sync_Attribute_To_Local
Sync_Attribute_To_Local_Default  = tracker_sync.Sync_Attribute_To_Local_Default
Sync_Attribute_To_Remote         = tracker_sync.Sync_Attribute_To_Remote
Sync_Attribute_To_Remote_Default = tracker_sync.Sync_Attribute_To_Remote_Default
Sync_Attribute_Two_Way           = tracker_sync.Sync_Attribute_Two_Way
Sync_Attribute_To_Local_Concatenate = \
    tracker_sync.Sync_Attribute_To_Local_Concatenate
Sync_Attribute_To_Local_Multilink = \
    tracker_sync.Sync_Attribute_To_Local_Multilink
Sync_Attribute_To_Local_Multilink_Default = \
    tracker_sync.Sync_Attribute_To_Local_Multilink_Default
Sync_Attribute_To_Local_Multistring = \
    tracker_sync.Sync_Attribute_To_Local_Multistring

class Syncer (tracker_sync.Syncer) :
    """ Synchronisation Framework
        We get the mapping of remote attributes to jira attributes.
        The type of attribute indicates the action to perform.
    """
    json_header = { 'content-type' : 'application/json' }
    schema_classes = \
        ( 'priority'
        , 'status'
        , 'project'
        , 'issuetype'
        , 'securitylevel'
        , 'version'
        )

    def __init__ (self, remote_name, attributes, opt) :
        self.url          = opt.url
        self.session      = requests.Session ()
        self.session.auth = (opt.local_username, opt.local_password)
        # This initializes schema and already needs the session
        self.__super.__init__ (remote_name, attributes, opt)
    # end def __init__

    def compute_schema (self) :
        u = self.url + '/' + 'field'
        r = self.session.get (u)
        j = r.json ()
        self.schema = {}
        self.schema ['issue'] = {}
        self.schema_namemap = {}
        s = self.schema ['issue']
        for k in j :
            name = k ['id']
            if 'name' in k :
                self.schema_namemap [k ['name']] = name
            if 'schema' not in k :
                type = 'string'
            else :
                type = k ['schema']['type']
            if type == 'array' :
                t = k ['schema']['items']
                if t == 'string' :
                    type = 'stringlist'
                else :
                    type = ('Multilink', t)
            elif type == 'datetime' :
                type = 'date'
            elif type not in ('string', 'number') :
                type = ('Link', type)
            s [name] = type
        # The default class 'issue' contains property 'id' which is not
        # discovered automagically: id and key are not in fields but in
        # the upper-level object
        s ['id']  = 'string'
        s ['key'] = 'string'
        # Some day find out if we can discover the schema via REST
        for k in self.schema_classes :
            self.schema [k] = dict (id = 'string', name = 'string')
        self.schema ['project']['key'] = 'string'
        self.default_class = 'issue'
        # Special hack to get all versions allowed. We query
        # /issue/createmeta?expand=projects.issuetypes.fields
        # and find out all versions. Note that we *should* do this only
        # for the default project we're using but we don't have the
        # project in a sync type. The project could be selected with the
        # additional parameter ?projectKeys=<key> in the request.
        self.versions_by_project = {}
        cm = self.getitem \
            ('issue', 'createmeta?expand=projects.issuetypes.fields')
        for project in cm ['projects'] :
            pkey = project ['key']
            for type in project ['issuetypes'] :
                if 'versions' in type ['fields'] :
                    ver = type ['fields']['versions']
                    if not ver ['allowedValues'] :
                        continue
                    if pkey not in self.versions_by_project :
                        self.versions_by_project [pkey] = {}
                    for av in ver ['allowedValues'] :
                        vn = av ['name']
                        self.versions_by_project [pkey][vn] = av ['id']
    # end def compute_schema

    def _create (self, cls, ** kw) :
        """ Debug and dryrun is handled by base class create. """
        u = self.url + '/' + cls
        d = dict (fields = kw)
        r = self.session.post \
            (u, data = json.dumps (d), headers = self.json_header)
        if not r.ok or not 200 <= r.status_code < 300 :
            raise RuntimeError ("Error %s: %s" % (r.status_code, r.content))
        j = r.json ()
        return j ['key']
    # end def _create

    def filter (self, classname, searchdict) :
        raise NotImplementedError
    # end def filter

    def fix_attributes (self, classname, attrs, create = False) :
        """ Fix transitive attributes.
            In case of links, we can use the name or the id (and
            sometimes a key) in jira. But this has to be passed as a
            dictionary, e.g. the value is something like
            {'name' : 'name-of-entity'}
            We distinguish creation and update (transformation might be
            different) via the create flag.
        """
        new = dict ()
        for k in attrs :
            lst = k.split ('.')
            l   = len (lst)
            assert l <= 2
            if l == 2 :
                # Special case: We may reference link values with the
                # name instead of the id in jira's REST api
                cls, attrname = lst
                if attrname in ('name', 'id', 'key') :
                    if cls == 'versions' :
                        assert len (attrs [k]) == 1
                        new [cls] = [dict (id = attrs [k][0])]
                    else :
                        if cls not in new :
                            new [cls] = {attrname : attrs [k]}
                        else :
                            new [cls][attrname] = attrs [k]
                else :
                    raise AttributeError ("Unknown jira Link: %s" % k)
            else :
                new [k] = attrs [k]
        if not create :
            return dict (fields = new)
        return new
    # end def fix_attributes

    def from_date (self, date) :
        return jira_utctime (date)
    # end def from_date

    def get_name_translation (self, classname, name) :
        """ Map user-given name to jira backend name
        """
        if classname == self.default_class :
            return self.schema_namemap.get (name, name)
        return name
    # end def get_name_translation

    def getitem (self, cls, id, *attr) :
        """ Get all or given list of attributes of an item of the given cls.
            This must not be used for attributes of the issue which we
            are currently syncing. The sync framework keeps a cache of
            to-be-updated attributes, this would bypass the cache.
            This returns a dict with a map from attr name to value.
        """
        u = self.url + '/' + cls + '/' + id
        r = self.session.get (u)
        if not r.ok or not 200 <= r.status_code < 300 :
            raise RuntimeError ("Error %s: %s" % (r.status_code, r.content))
        j = r.json ()
        if 'fields' in j :
            d = {}
            for n in j ['fields'] :
                v = j ['fields'][n]
                if isinstance (v, dict) and ('id' in v or 'key' in v) :
                    if 'id' in v :
                        d [n] = v ['id']
                    else :
                        d [n] = v ['key']
                elif isinstance (v, list) and v and isinstance (v [0], dict) :
                    d [n] = []
                    for item in v :
                        assert 'id' in item or 'key' in item
                        if 'id' in item :
                            d [n].append (item ['id'])
                        else :
                            d [n].append (item ['key'])
                else :
                    d [n] = v
                # id and key are not in fields but in the upper-level object
                if 'id' in j :
                    d ['id'] = j ['id']
                if 'key' in j :
                    d ['key'] = j ['key']
            return d
        return j
    # end def getitem

    def lookup (self, cls, key) :
        """ Should work like getitem in jira
        """
        # Note: This needs the project.key in the current issue
        if cls == 'version' :
            pkey = self.get (self.current_id, 'project.key')
            return self.versions_by_project [pkey][key]
        try :
            j = self.getitem (cls, key)
        except RuntimeError as err :
            raise KeyError (err.message)
        if 'key' in j :
            return j ['key']
        return j ['id']
    # end def lookup

    def _setitem (self, cls, id, ** kw) :
        """ Set attributes of an item of the given cls,
            attributes are 'key = value' pairs.
            Debug and dryrun is handled by base class setitem.
        """
        u = self.url + '/' + cls + '/' + id
        r = self.session.put \
            (u, headers = self.json_header, data = json.dumps (kw))
        if not r.ok or not 200 <= r.status_code < 300 :
            raise RuntimeError ("Error %s: %s" % (r.status_code, r.content))
    # end def _setitem

    def sync_new_local_issues (self, new_remote_issue) :
        """ Determine *local* issues which are not yet synced to the
            remote. Currently we don't sync any new issues from local
            tracker to remote.
        """
        pass
    # end def sync_new_local_issues

# end class Syncer
