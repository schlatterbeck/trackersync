#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2018-19 Dr. Ralf Schlatterbeck Open Source Consulting.
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
from   datetime             import datetime, timedelta
from   rsclib.autosuper     import autosuper
from   rsclib.pycompat      import ustr, text_type
from   trackersync          import tracker_sync

Sync_Attribute                    = tracker_sync.Sync_Attribute
Sync_Attribute_Check              = tracker_sync.Sync_Attribute_Check
Sync_Attribute_Check_Remote       = tracker_sync.Sync_Attribute_Check_Remote
Sync_Attribute_Files              = tracker_sync.Sync_Attribute_Files
Sync_Attribute_To_Local           = tracker_sync.Sync_Attribute_To_Local
Sync_Attribute_To_Local_Default   = tracker_sync.Sync_Attribute_To_Local_Default
Sync_Attribute_To_Remote          = tracker_sync.Sync_Attribute_To_Remote
Sync_Attribute_Multi_To_Remote    = tracker_sync.Sync_Attribute_Multi_To_Remote
Sync_Attribute_Two_Way            = tracker_sync.Sync_Attribute_Two_Way
Sync_Attribute_To_Remote_Default  = \
    tracker_sync.Sync_Attribute_To_Remote_Default
Sync_Attribute_To_Remote_If_Dirty = \
    tracker_sync.Sync_Attribute_To_Remote_If_Dirty
Sync_Attribute_To_Local_Concatenate = \
    tracker_sync.Sync_Attribute_To_Local_Concatenate
Sync_Attribute_To_Local_Multilink = \
    tracker_sync.Sync_Attribute_To_Local_Multilink
Sync_Attribute_To_Local_Multilink_Default = \
    tracker_sync.Sync_Attribute_To_Local_Multilink_Default
Sync_Attribute_To_Local_Multistring = \
    tracker_sync.Sync_Attribute_To_Local_Multistring

def jira_utctime (jiratime) :
    """ Time with numeric timestamp converted to UTC.
        Note that roundup strips trailing decimal places to 0.
    >>> jira_utctime ('2014-10-28T13:29:22.585+0100')
    '2014-10-28.12:29:22.000+0000'
    >>> jira_utctime ('2014-10-28T13:29:22.385+0100')
    '2014-10-28.12:29:22.000+0000'
    >>> jira_utctime ('2014-10-28T13:29:59.385+0100')
    '2014-10-28.12:29:59.000+0000'
    >>> jira_utctime ('2014-10-28T13:29:59.585+0100')
    '2014-10-28.12:29:59.000+0000'
    >>> jira_utctime ('2014-10-28T13:29:59.0+0100')
    '2014-10-28.12:29:59.000+0000'
    >>> jira_utctime ('2014-10-28T13:29:59+0100')
    '2014-10-28.12:29:59.000+0000'
    >>> jira_utctime ('2015-04-21T08:27:46+0200')
    '2015-04-21.06:27:46.000+0000'
    """
    fmt = fmts = "%Y-%m-%dT%H:%M:%S.%f"
    fmtnos     = "%Y-%m-%dT%H:%M:%S"
    d, tz = jiratime.split ('+')
    tz = int (tz)
    h  = tz / 100
    m  = tz % 100
    if '.' not in d :
        fmt = fmtnos
    d  = datetime.strptime (d, fmt)
    d  = d + timedelta (hours = -h, minutes = -m)
    return d
# end def jira_utctime

class Jira_File_Attachment (tracker_sync.File_Attachment) :

    def __init__ (self, issue, url = None, **kw) :
        """ Either the url or the content must be given
        """
        self.url      = url
        self.dirty    = False
        self._content = None
        if 'content' in kw :
            self._content = kw ['content']
            del kw ['content']
        self.__super.__init__ (issue, **kw)
    # end def __init__

    @property
    def content (self) :
        if self._content is None :
            r = self.session.get (self.url)
            if not r.ok :
                self.issue.raise_error (r)
            self._content = r.content
        return self._content
    # end def content

    def create (self) :
        assert self._content is not None
        u = self.issue.url + '/issue/' + self.issue.id + '/attachments'
        h = {'X-Atlassian-Token': 'nocheck'}
        f = dict (file = (self.name, self.content, self.type))
        r = self.issue.session.post (u, files = f, headers = h)
        self.issue.log.debug \
            ("Create attachment: %s %s" % (self.name, self.type))
        if not r.ok :
            self.issue.raise_error (r, 'Create attachment')
        j = r.json ()
        if len (j) != 1 :
            raise ValueError ("Invalid json on file creation: %s" % self.name)
        self.id = j [0]['id']
    # end def create

# end class Jira_File_Attachment

class Jira_Backend (autosuper) :
    """ Mixin for common function for Jira used when Jira is the
        local tracker as well as when Jira is the remote tracker
    """

    def _attachment_iter (self) :
        u = self.url + '/issue/' + self.id + '?fields=attachment'
        r = self.session.get (u)
        if not r.ok :
            self.raise_error (r)
        j = r.json ()
        for a in j ['fields']['attachment'] :
            yield a
    # end def _attachment_iter

    def _message_iter (self) :
        u = self.url + '/issue/' + self.id + '/comment'
        r = self.session.get (u)
        if not r.ok :
            self.raise_error (r)
        j = r.json ()
        if not j ['comments'] :
            assert j ['startAt'] == 0 and j ['total'] == 0
        for a in j ['comments'] :
            yield a
    # end def _message_iter

    def file_attachments (self, name = None) :
        if self.attachments is None :
            self.attachments = []
            for a in self._attachment_iter () :
                f = Jira_File_Attachment \
                    ( self
                    , id   = a ['id']
                    , type = a ['mimeType']
                    , url  = a ['content']
                    , name = a ['filename']
                    )
                self.attachments.append (f)
        return self.attachments
    # end def file_attachments

    def attach_file (self, other_file, name = None) :
        cls = Jira_File_Attachment
        f   = self._attach_file (cls, other_file, name)
        if f is None :
            return
        f.dirty = True
        if self.attachments is None :
            self.attachments = []
        self.attachments.append (f)
        self.dirty = True
    # end def attach_file

    def get_messages (self) :
        if self.issue_comments is None :
            self.issue_comments = {}
            for m in self._message_iter () :
                msg = self.Message_Class \
                    ( self
                    , id          = m ['id']
                    , author_id   = m ['updateAuthor']['key']
                    , author_name = m ['updateAuthor']['displayName']
                    , date        = jira_utctime (m ['updated'])
                    , content     = m ['body']
                    )
                self.issue_comments [msg.id] = msg
        return self.issue_comments
    # end def get_messages

    @classmethod
    def raise_error (cls, r, *args) :
        """ Used for errors whenever r (the result of a http method) has
            an error. With args we can specifiy additional things to be
            logged.
        """
        msg = []
        for k in 'X-Seraph-LoginReason', 'X-Authentication-Denied-Reason' :
            if k in r.headers and r.headers [k] != 'OK' :
                msg.append (r.headers [k])
        msg = ' '.join (msg)
        if msg :
            msg = ': ' + msg
        a = ''
        if args :
            a = ' ' + ' '.join (str (x) for x in args)
        raise RuntimeError ("HTTP Error %s%s%s" % (r.status_code, msg, a))
    # end def raise_error

# end class Jira_Backend

class Jira_Local_Issue (Jira_Backend, tracker_sync.Local_Issue) :
    pass
# end class Jira_Local_Issue

class Jira_Syncer (tracker_sync.Syncer) :
    """ Synchronisation Framework
        We get the mapping of remote attributes to jira attributes.
        The type of attribute indicates the action to perform.
    """
    Local_Issue_Class = Jira_Local_Issue
    File_Attachment_Class = Jira_File_Attachment
    raise_error = Local_Issue_Class.raise_error
    json_header = { 'content-type' : 'application/json' }
    schema_classes = \
        ( 'priority'
        , 'status'
        , 'project'
        , 'issuetype'
        , 'securitylevel'
        , 'version'
        , 'user'
        , 'resolution'
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
        if not r.ok or not 200 <= r.status_code < 300 :
            self.raise_error (r)
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
        self.schema ['user']['key'] = 'string'
        self.schema ['user']['displayName'] = 'string'
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
            self.raise_error (r)
        j = r.json ()
        return j ['key']
    # end def _create

    def dump_schema (self) :
        self.__super.dump_schema ()
        print ('NAMES:')
        for n in self.schema_namemap :
            print ("%s: %s" % (n, self.schema_namemap [n]))
    # end def dump_schema

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
        d = jira_utctime (date)
        return ustr (d.strftime ("%Y-%m-%d.%H:%M:%S") + '.000+0000')
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
        if cls == 'user' :
            u = self.url + '/' + cls + '?key=' + id
        r = self.session.get (u)
        if not r.ok or not 200 <= r.status_code < 300 :
            self.raise_error (r)
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
            self.raise_error (r, 'setitem', 'id=%s' % id, kw)
    # end def _setitem

    def sync_new_local_issues (self, new_remote_issue) :
        """ Determine *local* issues which are not yet synced to the
            remote. Currently we don't sync any new issues from local
            tracker to remote.
        """
        pass
    # end def sync_new_local_issues

    def update_aux_classes (self, id, r_id, r_issue, classdict) :
        self.__super.update_aux_classes (id, r_id, r_issue, classdict)
        if self.dry_run :
            return
        # May be None
        if self.localissues [id].attachments :
            for f in self.localissues [id].attachments :
                if f.dirty :
                    f.create ()
    # end def update_aux_classes

# end class Jira_Syncer

Syncer = Jira_Syncer
