#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (C) 2018-23 Dr. Ralf Schlatterbeck Open Source Consulting.
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

JSONDecodeError = json.decoder.JSONDecodeError

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

def jira_utctime (jiratime):
    """ Time with numeric timestamp converted to UTC.
        Note that roundup strips trailing decimal places to 0.
        Also note: We've recently added 'date' to the known types when
        parsing the schema, the previous known format was only
        'datetime'. So it may well be that we should anticipate
        additional date formats here.
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
    if '.' not in d:
        fmt = fmtnos
    d  = datetime.strptime (d, fmt)
    d  = d + timedelta (hours = -h, minutes = -m)
    return d
# end def jira_utctime

class Jira_File_Attachment (tracker_sync.File_Attachment):

    def __init__ (self, issue, url = None, **kw):
        """ Either the url or the content must be given
        """
        self.url      = url
        self.dirty    = False
        self._content = None
        if 'content' in kw:
            self._content = kw ['content']
            del kw ['content']
        self.__super.__init__ (issue, **kw)
    # end def __init__

    @property
    def content (self):
        if self._content is None:
            self.log.debug ('Jira send GET: %s' % self.url)
            r = self.session.get (self.url)
            if not r.ok:
                self.issue.raise_error (r, "Content")
            self._content = r.content
        return self._content
    # end def content

    def create (self):
        if self._content is None:
            self.issue.log.error ("Create attachment: %s is empty" % self.name)
            return
        u = self.issue.url + '/issue/' + self.issue.id + '/attachments'
        h = {'X-Atlassian-Token': 'nocheck'}
        f = dict (file = (self.name, self.content, self.type))
        self.log.debug ('Jira send POST (file attachment): %s' % u)
        r = self.issue.session.post (u, files = f, headers = h)
        self.issue.log.debug \
            ("Create attachment: %s %s" % (self.name, self.type))
        if not r.ok:
            self.issue.raise_error (r, 'Create attachment')
        j = r.json ()
        self.log.debug ('Jira receive:')
        for line in r.text.split ('\n'):
            self.log.debug (line)
        if len (j) != 1:
            raise ValueError ("Invalid json on file creation: %s" % self.name)
        self.id = j [0]['id']
    # end def create

# end class Jira_File_Attachment

class Jira_Backend (autosuper):
    """ Mixin for common function for Jira used when Jira is the
        local tracker as well as when Jira is the remote tracker
    """

    def __init__ (self, syncer, id, **kw):
        self.mangle_filenames = True
        self.__super.__init__ (syncer, id, **kw)
        if getattr (self.opt, 'no_mangle_filenames', None):
            self.mangle_filenames = False
    # end def __init__

    def _attachment_iter (self):
        if isinstance (self.id, int) and self.id < 0:
            raise StopIteration ('negative id')
        u = self.url + '/issue/' + str (self.id) + '?fields=attachment'
        self.log.debug ('Jira send GET: %s' % u)
        r = self.session.get (u)
        if not r.ok:
            self.raise_error (r, "Attachment of %s" % self.id)
        j = r.json ()
        self.log.debug ('Jira receive:')
        for line in r.text.split ('\n'):
            self.log.debug (line)
        for a in j ['fields']['attachment']:
            yield a
    # end def _attachment_iter

    def _message_iter (self):
        u = self.url + '/issue/' + self.id + '/comment'
        self.log.debug ('Jira send GET: %s' % u)
        r = self.session.get (u)
        if not r.ok:
            self.raise_error (r, "Message of %s" % self.id)
        j = r.json ()
        self.log.debug ('Jira receive:')
        for line in r.text.split ('\n'):
            self.log.debug (line)
        if not j ['comments']:
            assert j ['startAt'] == 0 and j ['total'] == 0
        for a in j ['comments']:
            yield a
    # end def _message_iter

    def file_attachments (self, name = None):
        if self.attachments is None:
            self.attachments  = []
            self.file_by_name = {}
            for a in self._attachment_iter ():
                f = Jira_File_Attachment \
                    ( self
                    , id   = a ['id']
                    , type = a.get ('mimeType', 'application/octet-stream')
                    , url  = a ['content']
                    , name = a ['filename']
                    )
                self.attachments.append (f)
                self.file_by_name [f.name] = f
        return self.attachments
    # end def file_attachments

    def file_exists (self, other_name):
        """ Take name mangling into account, some Jira instances are set
            up in a way that does not permit non-ascii filenames. So we
            try to find other_name unmangled first, then we try the
            mangled name.
        """
        if not getattr (self, 'file_by_name', None):
            self.file_attachments ()
        if other_name in self.file_by_name:
            return True
        if self.mangle_file_name (other_name) in self.file_by_name:
            return True
    # end def file_exists

    def mangle_file_name (self, fn):
        """ Mangle remote file name to something permissible locally.
            Some Jira instances are configured to only allow ascii
            filenames.
        """
        fnb = fn.encode ('ascii', errors = 'replace')
        return fnb.decode ('ascii')
    # end def mangle_file_name

    def attach_file (self, other_file, name = None):
        cls   = Jira_File_Attachment
        fname = other_file.name
        if self.mangle_filenames:
            fname = self.mangle_file_name (other_file.name)
        fcp = tracker_sync.File_Attachment \
            ( other_file.issue
            , url     = getattr (other_file, 'url', None)
            , id      = getattr (other_file, 'id',  None)
            , name    = fname
            , type    = other_file.type
            , content = other_file.content
            )
        f = self._attach_file (cls, fcp, name)
        if f is None:
            return
        f.dirty = True
        if self.attachments is None:
            self.attachments = []
        self.attachments.append (f)
        self.dirty = True
    # end def attach_file

    def get_messages (self):
        if self.issue_comments is None:
            self.issue_comments = {}
            for m in self._message_iter ():
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

    def add_message (self, msg):
        """ Add a jira notice and return the id
        """
        self.dirty = True # Needed for syncdb update
        return self.syncer.add_comment (self.id, msg)
    # end def add_message

    @classmethod
    def raise_error (cls, r, *args):
        """ Used for errors whenever r (the result of a http method) has
            an error. With args we can specifiy additional things to be
            logged.
        """
        msg = []
        for k in 'X-Seraph-LoginReason', 'X-Authentication-Denied-Reason':
            if k in r.headers and r.headers [k] != 'OK':
                msg.append (r.headers [k])
        try:
            j = r.json ()
            if 'errorMessages' in j:
                msg.extend (j ['errorMessages'])
            if 'errors' in j and 'comment' in j ['errors']:
                msg.append (j ['errors']['comment'])
        except (AttributeError, KeyError, IndexError, JSONDecodeError):
            pass
        msg = ' '.join (msg)
        if msg:
            msg = ': ' + msg + ': '
        a = ''
        if args:
            a = ' ' + ' '.join (str (x) for x in args)
        raise RuntimeError ("HTTP Error %s%s%s" % (r.status_code, msg, a))
    # end def raise_error

# end class Jira_Backend

class Jira_Local_Issue (Jira_Backend, tracker_sync.Local_Issue):
    pass
# end class Jira_Local_Issue

class Jira_Syncer (tracker_sync.Syncer):
    """ Synchronisation Framework
        We get the mapping of remote attributes to jira attributes.
        The type of attribute indicates the action to perform.
    """
    Local_Issue_Class = Jira_Local_Issue
    File_Attachment_Class = Jira_File_Attachment
    raise_error = Local_Issue_Class.raise_error
    json_header = { 'content-type': 'application/json' }

    def __init__ (self, remote_name, attributes, opt, **kw):
        self.url          = opt.url
        self.session      = requests.Session ()
        self.session.auth = (opt.local_username, opt.local_password)
        self.item_cache   = {}
        # This initializes schema and already needs the session
        self.__super.__init__ (remote_name, attributes, opt, **kw)
    # end def __init__

    def compute_schema (self):
        u = self.url + '/' + 'field'
        self.log.debug ('Jira send GET: %s' % u)
        r = self.session.get (u)
        if not r.ok or not 200 <= r.status_code < 300:
            self.raise_error (r, "Compute Schema")
        j = r.json ()
        self.log.debug ('Jira receive:')
        for line in r.text.split ('\n'):
            self.log.debug (line)
        self.schema = {}
        self.schema ['issue'] = {}
        self.schema_namemap = {}
        s = self.schema ['issue']
        schema_classes = set ()
        self.multilinks = set ()
        for k in j:
            name = k ['id']
            if 'name' in k:
                self.schema_namemap [k ['name']] = name
            if 'schema' not in k:
                type = 'string'
            else:
                type = k ['schema']['type']
            if type == 'array':
                # Seems custom fields do not have an 'items' key
                # FIXME: This may still need some investigation if we
                # need such a field in the future
                t = k ['schema'].get ('items')
                if not t:
                    assert 'custom' in k ['schema']
                    type = 'custom'
                elif t == 'string':
                    type = 'stringlist'
                else:
                    type = ('Multilink', t)
                    # The default schema entry, see below for special cases
                    if t not in self.schema:
                        schema_classes.add (t)
                        self.multilinks.add (t)
            elif type == 'datetime':
                type = 'date'
            elif type == 'date':
                type = 'date'
            elif type not in ('string', 'number'):
                t    = type
                type = ('Link', type)
                # The default schema entry, see below for special cases
                if t not in self.schema:
                    schema_classes.add (t)
            s [name] = type
        # The default class 'issue' contains property 'id' which is not
        # discovered automagically: id and key are not in fields but in
        # the upper-level object
        s ['id']  = 'string'
        s ['key'] = 'string'
        # Some day find out if we can discover the schema via REST
        # These are custom schema options
        self.schema ['option'] = dict (id = 'string', value = 'string')
        for name in schema_classes:
            if name not in self.schema:
                self.schema [name] = dict \
                    (id = 'string', name = 'string', key = 'string')
        self.schema ['user']['displayName'] = 'string'
        self.default_class = 'issue'
        # Special hack to get all multilink values allowed.
        # Examples: versions, components
        # We query /issue/createmeta?expand=projects.issuetypes.fields
        # and find out all multilinks. Note that we *should* do this only
        # for the default project we're using but we don't have the
        # project in a sync type. The project could be selected with the
        # additional parameter ?projectKeys=<key> in the request.
        # We build the multilinks_by_project on the fly here.
        self.multilinks_by_project = {}
        self.multilink_keyattr     = {}
        cm = self.getitem \
            ('issue', 'createmeta?expand=projects.issuetypes.fields')
        for project in cm ['projects']:
            pkey = project ['key']
            ml = self.multilinks_by_project [pkey] = {}
            for type in project ['issuetypes']:
                for fieldname in type ['fields']:
                    entry = type ['fields'][fieldname]
                    m = entry ['schema'].get ('items')
                    if m in self.multilinks:
                        if not entry.get ('allowedValues'):
                            continue
                        assert entry ['schema']['type'] == 'array'
                        assert 'set' in entry ['operations']
                        ml [m] = {}
                        for av in entry ['allowedValues']:
                            for k in ('key', 'name', 'value'):
                                if k in av:
                                    break
                            else:
                                raise KeyError ('No key attr found: %s' % av)
                            if m in self.multilink_keyattr:
                                assert self.multilink_keyattr [m] == k
                            else:
                                self.multilink_keyattr [m] = k
                            vn = av [k]
                            ml [m][vn] = dict \
                                ((k, av [k]) for k in av if k != 'self')
    # end def compute_schema

    def _create (self, cls, ** kw):
        """ Debug and dryrun is handled by base class create. """
        u = self.url + '/' + cls
        d = dict (fields = kw)
        self.log.debug ('Jira send POST: %s' % u)
        for line in json.dumps (d, indent = 4).split ('\n'):
            self.log.debug (line)
        r = self.session.post \
            (u, data = json.dumps (d), headers = self.json_header)
        if not r.ok or not 200 <= r.status_code < 300:
            self.raise_error (r, "Create %s" % cls)
        j = r.json ()
        self.log.debug ('Jira receive:')
        for line in r.text.split ('\n'):
            self.log.debug (line)
        return j ['key']
    # end def _create

    def add_comment (self, id, msg):
        u = self.url + '/' + self.default_class + '/' + str (id) + '/comment'
        c = [ dict (type = 'text', text = msg.content) ]
        b = dict (body = msg.content)
        self.log.debug ('Jira send POST (message body): %s' % u)
        r = self.session.post (u, json = b, headers = self.json_header)
        if not r.ok or not 200 <= r.status_code < 300:
            self.raise_error (r, "Add comment for %s" % id)
        j = r.json ()
        self.log.debug ('Jira receive:')
        for line in r.text.split ('\n'):
            self.log.debug (line)
        return j ['id']
    # end def add_comment

    def dump_schema (self):
        self.__super.dump_schema ()
        print ('NAMES:')
        for n in self.schema_namemap:
            print ("%s: %s" % (n, self.schema_namemap [n]))
        for p in self.multilinks_by_project:
            print ("PROJECT: %s" % p)
            for m in self.multilinks_by_project [p]:
                print ("MULTILINK: %s" % m)
                ml = self.multilinks_by_project [p][m]
                for k in ml:
                    print ("    %s: %s" % (k, ml [k]))
    # end def dump_schema

    def check_method (self, endpoint):
        u = self.url + '/' + endpoint
        self.log.debug ('Jira send OPTIONS: %s' % u)
        r = self.session.options (u)
        if not r.ok or not 200 <= r.status_code < 300:
            self.raise_error (r, "Options method failed")
        print ('Allowed: %s' % r.headers ['Allow'])
    # end def check_method

    def filter (self, classname, searchdict):
        raise NotImplementedError
    # end def filter

    def format_multilink (self, attrname, values, fancy = False):
        """ The components property is special, it is of the form:
            {'components':
                [{'set': [{'name': 'somename'}, {'name': 'someothername'}]}]
            }
            and it can take add/remove events like
            {'components':
                [ {'add': {'name': 'somename'}}
                , {'remove':{'name': 'someothername'}]}
                , ...
                ]
            }
            see
            https://developer.atlassian.com/server/jira/platform/jira-rest-api-examples/#editing-an-issue-examples

            But it looks like that description does not work.
            Maybe a version issue of the Jira API.
            So we use the old schema:
        """
        if isinstance (values, str):
            values = [values]
        new = []
        # See above for documented format with fancy set
        if fancy:
            c   = []
            new.append (dict (set = c))
            for v in values:
                c.append ({attrname: v})
        else:
            for v in values:
                new.append ({attrname: v})
        return new

    def fix_attributes (self, classname, attrs, create = False):
        """ Fix transitive attributes.
            In case of links, we can use the name or the id (and
            sometimes a key) in jira. But this has to be passed as a
            dictionary, e.g. the value is something like
            {'name': 'name-of-entity'}
            We distinguish creation and update (transformation might be
            different) via the create flag.
            For Multilinks see format_multilink above.
        """
        pkey       = self.get (self.current_id, 'project.key')
        new        = {}
        transition = {}
        for k in attrs:
            lst = k.split ('.')
            l   = len (lst)
            assert l <= 2
            if l == 2:
                # Special case: We may reference link values with the
                # name instead of the id in jira's REST api
                prop, attrname = lst
                if attrname in ('name', 'id', 'key', 'value'):
                    #if prop == 'components':
                    #    continue
                    if self.schema [classname][prop][0] == 'Multilink':
                        cls = self.schema [classname][prop][1]
                        mbp = self.multilinks_by_project [pkey].get (cls)
                        mlk = self.multilink_keyattr.get (cls)
                        if mbp and mlk:
                            if attrname != mlk:
                                raise ValueError \
                                    ('Configured attribute "%s" of "%s" '
                                     'should be "%s".'
                                    % (attrname, prop, mlk)
                                    )
                            d = {}
                            #if cls == 'component':
                            #    d ['fancy'] = True
                            new [prop] = self.format_multilink \
                                (mlk, attrs [k], **d)
                        else:
                            raise ValueError \
                                ( 'Autodetect for multilink %s.%s failed'
                                % propname, attrname
                                )
                    elif prop == 'status':
                        # Currently only works for status.name or .id
                        assert attrname in ('name', 'id')
                        cls = self.schema [classname][prop][1]
                        assert cls == 'status'
                        transition [prop] = {attrname: attrs [k]}
                    else: # Link
                        if prop not in new:
                            new [prop] = {attrname: attrs [k]}
                        else:
                            new [prop][attrname] = attrs [k]
                else:
                    raise AttributeError ("Unknown jira Link: %s" % k)
            else:
                new [k] = attrs [k]
        if not create:
            d = dict (fields = new)
            if transition:
                d ['transition'] = transition
            return d
        return new
    # end def fix_attributes

    def from_date (self, date):
        d = jira_utctime (date)
        return ustr (d.strftime ("%Y-%m-%d.%H:%M:%S") + '.000+0000')
    # end def from_date

    def get_name_translation (self, classname, name):
        """ Map user-given name to jira backend name
        """
        if classname == self.default_class:
            return self.schema_namemap.get (name, name)
        return name
    # end def get_name_translation

    def getitem (self, cls, id, *attr):
        """ Get all or given list of attributes of an item of the given cls.
            This must not be used for attributes of the issue which we
            are currently syncing. The sync framework keeps a cache of
            to-be-updated attributes, this would bypass the cache.
            This returns a dict with a map from attr name to value.
        """
        if (cls, id) in self.item_cache:
            return self.item_cache [(cls, id)]
        u = self.url + '/' + cls + '/' + id
        if cls == 'user':
            u = self.url + '/' + cls + '?key=' + id
        elif cls == 'option':
            u = self.url + '/' + 'customFieldOption' + '/' + id
        self.log.debug ('Jira send GET: %s' % u)
        r = self.session.get (u)
        if not r.ok or not 200 <= r.status_code < 300:
            self.raise_error (r, "Getitem %s %s" % (cls, id))
        j = r.json ()
        self.log.debug ('Jira receive: (content not logged)')
        if 'fields' in j:
            d = {}
            for n in j ['fields']:
                v = j ['fields'][n]
                if isinstance (v, dict) and ('id' in v or 'key' in v):
                    if 'id' in v:
                        d [n] = v ['id']
                    else:
                        d [n] = v ['key']
                elif isinstance (v, list) and v and isinstance (v [0], dict):
                    d [n] = []
                    for item in v:
                        assert 'id' in item or 'key' in item
                        if 'id' in item:
                            d [n].append (item ['id'])
                        else:
                            d [n].append (item ['key'])
                else:
                    d [n] = v
                # id and key are not in fields but in the upper-level object
                if 'id' in j:
                    d ['id'] = j ['id']
                if 'key' in j:
                    d ['key'] = j ['key']
            self.item_cache [(cls, id)] = d
            return d
        self.item_cache [(cls, id)] = j
        return j
    # end def getitem

    def lookup (self, cls, key):
        """ Should work like getitem in jira
        """
        # Note: This needs the project.key in the current issue
        if cls in self.multilink_keyattr:
            mkey = self.multilink_keyattr [cls]
            if self.current_id == -1:
                for pkey in self.multilinks_by_project:
                    try:
                        return self.multilinks_by_project [pkey][cls][key][mkey]
                    except KeyError:
                        pass
                raise KeyError (key)
            else:
                pkey = self.get (self.current_id, 'project.key')
                return self.multilinks_by_project [pkey][cls][key][mkey]
        try:
            j = self.getitem (cls, key)
        except RuntimeError as err:
            m = getattr (err, 'message', None)
            if m:
                raise KeyError (err.message)
            else:
                raise KeyError (key)
        if 'key' in j:
            return j ['key']
        return j ['id']
    # end def lookup

    def _set_status (self, id, trans):
        """ Handle state changes, these must be done via transitions
            And transitions must be submitted as a post
            trans is of the form { 'status': { 'id/name': val }}
        """
        u = self.url + '/issue/' + id
        assert 'status' in trans
        trans = trans ['status']
        keys  = list (trans)
        assert len (keys) == 1
        key = keys [0]
        val = trans [key]
        assert key in ('id', 'name')
        r = self.session.get (u + '/transitions')
        if not r.ok or not 200 <= r.status_code < 300:
            self.raise_error (r, 'setitem', 'get transitions: %s' % id)
        j = r.json ()
        tid = None
        for t in  j ['transitions']:
            if t ['to'][key] == val:
                tid = t ['id']
                break
        if tid is None:
            print ('Status change to "%s" not allowed by Jira' % val)
            self.log.error \
                ('Status change to "%s" not allowed by Jira' % val)
        else:
            d = dict (transition = dict (id = tid))
            u = u + '/transitions'
            r = self.session.post \
                (u, headers = self.json_header, data = json.dumps (d))
            if not r.ok or not 200 <= r.status_code < 300:
                self.raise_error (r, 'setitem', '%s' % id, d)
    # end def _set_status

    def _setitem (self, cls, id, ** kw):
        """ Set attributes of an item of the given cls,
            attributes are 'key = value' pairs.
            Debug and dryrun is handled by base class setitem.
            Note: This currently handles attribute updates and state
            changes (via transition) seperately. This may make
            transitions fail that need an update of some other field
            together with the state change.
        """
        u = self.url + '/' + cls + '/' + id
        trans = None
        if 'transition' in kw:
            # Status only for issue
            assert (cls == 'issue')
            trans = kw ['transition']
            del kw ['transition']
        self.log.debug ('Jira send PUT: %s' % u)
        for line in json.dumps (kw, indent = 4).split ('\n'):
            self.log.debug (line)
        r = self.session.put \
            (u, headers = self.json_header, data = json.dumps (kw))
        if not r.ok or not 200 <= r.status_code < 300:
            self.raise_error (r, 'setitem', 'id=%s' % id, kw)
        if trans:
            self._set_status (id, trans)
    # end def _setitem

    def sync_new_local_issues (self, new_remote_issue):
        """ Determine *local* issues which are not yet synced to the
            remote. Currently we don't sync any new issues from local
            tracker to remote.
        """
        pass
    # end def sync_new_local_issues

    def update_aux_classes (self, id, r_id, r_issue, classdict):
        self.__super.update_aux_classes (id, r_id, r_issue, classdict)
        if self.dry_run:
            return
        # May be None
        if self.localissues [id].attachments:
            for f in self.localissues [id].attachments:
                if f.dirty:
                    f.create ()
    # end def update_aux_classes

# end class Jira_Syncer

Syncer = Jira_Syncer
