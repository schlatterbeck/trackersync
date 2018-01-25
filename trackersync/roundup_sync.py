#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2015-18 Dr. Ralf Schlatterbeck Open Source Consulting.
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

import xmlrpclib
import json
import numbers
import ssl
from   time             import sleep
from   rsclib.autosuper import autosuper
from   rsclib.pycompat  import ustr, text_type
from   trackersync      import tracker_sync

Sync_Attribute                   = tracker_sync.Sync_Attribute
Sync_Attribute_Check             = tracker_sync.Sync_Attribute_Check
Sync_Attribute_One_Way           = tracker_sync.Sync_Attribute_One_Way
Sync_Attribute_Default           = tracker_sync.Sync_Attribute_Default
Sync_Attribute_To_Remote         = tracker_sync.Sync_Attribute_To_Remote
Sync_Attribute_To_Remote_Default = tracker_sync.Sync_Attribute_To_Remote_Default
Sync_Attribute_Two_Way           = tracker_sync.Sync_Attribute_Two_Way

def rup_date (datestring) :
    """ String roundup XMLRPC date and extract date/time in the format
        %Y-%m-%d.%H:%M:%S seconds are with 3 decimal places, e.g.
        2015-09-06.13:51:38.840
    """
    assert datestring.startswith ('<Date ')
    ret = datestring [6:-1]
    return ret
# end def rup_date

class Sync_Attribute_Messages (Sync_Attribute) :
    """ Synchronize messages of the remote tracker with the messages in
        roundup. The Remote_Issue descendant class of the remote tracker
        has to implement the 'messages' method to iterate over all
        messages of the remote tracker.
        Two-way sync is used if a keyword is given. In that case the
        msg class in roundup needs to have a ``keywords`` attribute
        which is a Multilink to ``msg_keyword``. If a message has the
        given keyword it is considered for synchronisation to the remote
        tracker.
    """

    def __init__ (self, keyword = None, ** kw) :
        self.__super.__init__ ('messages', remote_name = None, ** kw)
        self.keyword = keyword
    # end def __init__

    def sync (self, syncer, id, remote_issue) :
        rup_msgs = []
        msgs   = syncer.get (id, self.name)
        nosync = {}
        for m in sorted (msgs, key = lambda x: -int (x)) :
            msg = syncer.getitem ('msg', m)
            msg ['id'] = m
            rup_msgs.append (msg)
            nosync [m] = msg
        appended = False
        for m in remote_issue.messages () :
            emk = None
            mid = None
            if 'id' in m :
                mid = m ['id']
                del m ['id']
            matchmsg = False
            if mid :
                try :
                    emk = syncer.lookup \
                        ('ext_msg', ':'.join ((syncer.tracker, mid)))
                except KeyError :
                    pass
                if emk :
                    mk = syncer.getitem ('ext_msg', emk, 'msg') ['msg']
                    if mk in nosync :
                        ct = nosync [mk]['content'].strip ()
                        # Only if content matches, some remote trackers
                        # allow message modification
                        if ct == m ['content'].strip () :
                            del nosync [mk]
                            matchmsg = True
            else :
                for mrup in rup_msgs :
                    # compare content last
                    for k in sorted (m, key = lambda x: x == 'content') :
                        rupm = mrup [k]
                        mm = m [k]
                        if k == 'date' :
                            rupm = rup_date (rupm)
                            if  (   mm [-5] == '+' or mm [-5] == '-'
                                and isdigit (mm [-4:])
                                ) :
                                mm = mm [:-5]
                        if rupm.rstrip () != mm.rstrip () :
                            break
                    else : # match
                        del nosync [mrup ['id']]
                        matchmsg = True
                        break
            if not matchmsg :
                msgs.append (syncer.create ('msg', **m))
                if mid :
                    if emk :
                        syncer.setitem ('ext_msg', emk, msg = msgs [-1])
                    else :
                        syncer.create \
                            ( 'ext_msg'
                            , ext_tracker = syncer.tracker
                            , msg         = msgs [-1]
                            , ext_id      = mid
                            , key         = ''
                            )
                appended  = True
        if appended :
            syncer.set (id, self.name, msgs)
        if self.keyword is not None :
            k = syncer.lookup ('msg_keyword', self.keyword)
            for mrup in nosync.itervalues () :
                if k in mrup ['keywords'] :
                    mid = remote_issue.add_message (mrup)
                    if syncer.verbose :
                        print ("New remote message from msg%s" % mrup ['id'])
                    if mid is not None :
                        syncer.create \
                            ( 'ext_msg'
                            , ext_tracker = syncer.tracker
                            , msg         = mrup ['id']
                            , ext_id      = mid
                            , key         = ''
                            )
    # end def sync

# end class Sync_Attribute_Messages

class Sync_Attribute_Message (Sync_Attribute) :
    """ A Sync attribute that sync the contents of a field of the remote
        tracker to a message in roundup. The message in roundup gets a
        unique headline. We search for the *last* message with that
        headline. If it matches we don't update. If no message is found
        or a non-matching message is found we create a new message in
        roundup and link it to the messages of the issue.
    """

    def __init__ (self, headline, remote_name, ** kw) :
        self.headline = headline
        self.hlen     = len (headline)
        self.__super.__init__ ('messages', remote_name, ** kw)
    # end def __init__

    def sync (self, syncer, id, remote_issue) :
        v = remote_issue.get (self.remote_name, None)
        if not v :
            return
        msgs = syncer.get (id, self.name)
        for m in sorted (msgs, key = lambda x: -int (x)) :
            msg = syncer.getitem ('msg', m)
            cnt = msg ['content']
            if len (cnt) < self.hlen + 1 :
                continue
            if cnt.startswith (self.headline) and cnt [self.hlen] == '\n' :
                if cnt [self.hlen + 1:] == v :
                    return
        content = '\n'.join ((self.headline, v))
        newmsg  = syncer.create ('msg', content = content)
        if not syncer.dry_run :
            msgs.append (newmsg)
        syncer.set (id, self.name, msgs)
    # end def sync

# end class Sync_Attribute_Message

class Sync_Attribute_Default_Message (Sync_Attribute) :
    """ A default message added as the *only* message whenever the
        remote tracker doesn't have any message generated.
        This is used to add at least one message to a new issue in
        roundup because at least one message is required.
    """
    def __init__ (self, message, ** kw) :
        self.message = message
        self.__super.__init__ ('messages', None, ** kw)
    # end def __init__

    def sync (self, syncer, id, remote_issue) :
        msgs = syncer.get (id, self.name)
        if not msgs :
            newmsg  = syncer.create ('msg', content = self.message)
            msgs.append (newmsg)
            syncer.set (id, self.name, msgs)
    # end def sync
# end class Sync_Attribute_Default_Message

class Sync_Attribute_Files (Sync_Attribute) :
    """ A Sync attribute that sync the files attached to a remote issue
        to the local issue. See the documentation of
        remote_issue.document_ids for details of how the documents are
        checked against local documents.
        If the optional prefix is given, files with a name starting with
        the given prefix are synchronized *to* the remote system. In
        case the prefix is empty (zero-length string), *all* files not
        coming from the remote tracker are created in the remote
        tracker. Note that with such a setup (with empty prefix) it is
        almost impossible to delete a file in both trackers -- the file
        would have to be deleted in both systems by hand before starting
        the next sync.
        Note that files synchronized *to* the remote system are renamed
        to the naming convention enforced by the remote system. This is
        done to ensure that they are not created again in roundup on next
        sync. The user used for synchronisation must have write
        permission on the file.name attribute in roundup.
    """

    def __init__ (self, prefix = None, ** kw) :
        self.prefix = prefix
        self.__super.__init__ ('files', remote_name = None, ** kw)
    # end def __init__

    def sync (self, syncer, id, remote_issue) :
        fids    = syncer.get (id, self.name)
        filids  = dict.fromkeys (fids)
        fields  = ('id', 'name', 'type')
        files   = [syncer.getitem ('file', i, *fields) for i in fids]
        attrs   = dict ((f ['id'], f) for f in files)
        by_name = dict ((f ['name'], f ['id']) for f in files)
        by_name = remote_issue.document_fixer (by_name)
        created = False
        for docid in remote_issue.document_ids () :
            # content needs to be fetched because some backends get
            # their document_attributes with the content.
            content    = remote_issue.document_content (docid)
            attributes = remote_issue.document_attributes (docid)
            if docid in by_name :
                did = by_name [docid]
                d  = {}
                for k in attributes :
                    if k in attrs [did] and attributes [k] != attrs [did][k] :
                        d [k] = attributes [k]
                if d :
                    syncer.setitem ('file', did, ** d)
                del filids [did]
            else :
                if 'name' not in attributes :
                    attributes ['name'] = docid
                newfile = syncer.create \
                    ( 'file'
                    , content = content
                    , ** attributes
                    )
                fids.append (newfile)
                created = True
        if created :
            syncer.set (id, self.name, fids)
        if self.prefix is not None and not self.remote_dry_run :
            files = [syncer.getitem ('file', i, 'name', 'id', 'type')
                     for i in filids
                    ]
            for f in files :
                name = f ['name']
                if name.startswith (self.prefix) :
                    fid     = f ['id']
                    name    = name [len (self.prefix):] or 'File'
                    content = syncer.getitem ('file', fid, 'content')['content']
                    n = remote_issue.attach_file (name, f ['type'], content)
                    syncer.setitem ('file', fid, name = n)
                    if syncer.verbose :
                        k = remote_issue ['key']
                        print ("Remote Attach (%s): %s" % (k, n))
    # end def sync

# end class Sync_Attribute_Files

class Retry_Server_Proxy (autosuper) :

    def __init__ (self, retries, sleeptime, *args, **kw) :
        self.retries   = retries
        self.sleeptime = sleeptime
        self.proxy     = xmlrpclib.ServerProxy (*args, **kw)
    # end def __init__

    def retry (self, function) :
        def f_retry (*args, **kw) :
            for retry in range (self.retries) :
                try :
                    return function (*args, **kw)
                except xmlrpclib.ProtocolError :
                    if self.sleeptime :
                        sleep (self.sleeptime)
            raise
        # end def f_retry
        return f_retry
    # end def retry

    def __getattr__ (self, name) :
        obj = getattr (self.proxy, name)
        if (callable (obj)) :
            obj = self.retry (obj)
            setattr (self, name, obj)
        else :
            setattr (self, name, obj)
        return obj
    # end def __getattr__

# end class Retry_Server_Proxy

class Syncer (tracker_sync.Syncer) :
    """ Synchronisation Framework
        We get the mapping of remote attributes to roundup attributes.
        The type of attribute indicates the action to perform.
        We need at least an attribute that maps the ext_id attribute to
        the name of the external id attribute in the remote.
        Note that the parameter 'unverified' denotes an unverified SSL
        connection if applicable.
    """

    ext_names = dict.fromkeys \
        (('ext_attributes', 'ext_id', 'ext_status', 'ext_tracker'))

    def __init__ (self, url, remote_name, attributes, opt) :
        srvargs = dict (allow_none = True)
        if getattr (opt, 'unverified', None) :
            context = ssl._create_unverified_context ()
            srvargs ['context'] = context
        self.srv = Retry_Server_Proxy (3, 0, url, **srvargs)
        self.tracker         = self.srv.lookup ('ext_tracker', remote_name)
        # This initializes schema and already need server connection
        self.__super.__init__ (remote_name, attributes, opt)
    # end def __init__

    def compute_schema (self) :
        s       = self.srv.schema ()
        schema  = {}
        schema  = dict ((k, dict (s [k])) for k in s)
        for cls in schema :
            for k in schema [cls] :
                v = schema [cls][k]
                t = v.split () [0]
                t = t.rsplit ('.', 1) [-1]
                if t.endswith ('>') :
                    t = t [:-1]
                if t in ('Link', 'Multilink') :
                    assert v.endswith ('">')
                    schema [cls][k] = (t, v.strip ('"').rsplit ('"', 2) [-2])
                else :
                    schema [cls][k] = t.lower ()
                    if t == 'boolean' :
                        t = 'bool'
        self.schema = schema
        # Update schema with auto attributes
        for cls in self.schema :
            for k in 'creation', 'activity' :
                self.schema [cls][k] = 'date'
            self.schema [cls]['id']  = 'string'
        self.default_class = 'issue'
    # end def compute_schema

    def create (self, cls, ** kw) :
        """ Debug and dryrun is handled by base class. """
        return self.srv.create \
            (cls, * [self.format (cls, k, v) for k, v in kw.items ()])
    # end def create

    def filter (self, classname, searchdict) :
        return self.srv.filter (classname, None, searchdict)
    # end def filter

    def fix_attributes (self, classname, attrs) :
        """ Fix transitive attributes. Two possibilities:
            - a Link to a remote class and the attribute after the dot
              is the key
            - The attribute is named 'content' and is the content of a
              message attribute
            In the first case we simply perform a lookup, in the second
            case we create the message and store the id.
        """
        new = dict ()
        for k in attrs :
            lst = k.split ('.')
            l   = len (lst)
            assert l <= 2
            if l == 2 :
                cls, name = lst
                if name == 'content' :
                    assert self.get_classname (classname, cls) == 'msg'
                    msg = self.create ('msg', content = attrs [k])
                    new [cls] = msg
                else :
                    assert self.get_type (classname, cls) == 'Link'
                    id = self.lookup (cls, attrs [k])
                    new [cls] = id
            else :
                new [k] = attrs [k]
        return new
    # end def fix_attributes

    def format (self, cls, key, value) :
        """ Format value for xmlrpc """
        t = self.schema [cls][key]
        if self.get_type (cls, key) == 'Multilink' :
            return '%s=%s' % (key, ','.join (value))
        elif isinstance (value, numbers.Number) :
            return '%s=%s' % (key, value)
        elif key == 'content' :
            # Message content in roundup is stored as \r\n line-endings
            # So we make sure to add \r.
            if cls == 'msg' :
                value = value.replace ('\n', '\r\n')
            # Send message content (or file content) as binary to
            # preserve newline semantics across xmlrpc interface
            # even if not really binary.
            if isinstance (value, unicode) :
                value = value.encode ('utf-8')
            return xmlrpclib.Binary \
                (key.encode ('ascii') + '='.encode ('ascii') + value)
        elif not isinstance (value, text_type) :
            return xmlrpclib.Binary \
                (key.encode ('ascii') + '='.encode ('ascii') + value)
        else :
            return '%s=%s' % (key, value)
    # end def format

    def from_date (self, date) :
        return rup_date (date)
    # end def from_date

    def getitem (self, cls, id, *attr) :
        """ Get all or given list of attributes of an item of the given cls.
            This must not be used for attributes of the issue which we
            are currently syncing. The sync framework keeps a cache of
            to-be-updated attributes, this would bypass the cache.
            This returns a dict with a map from attr name to value.
        """
        return self.srv.display ('%s%s' % (cls, id), *attr)
    # end def getitem

    def lookup (self, cls, key) :
        try :
            return self.srv.lookup (cls, key)
        except xmlrpclib.Fault as fault :
            fs = fault.faultString
            if 'exceptions.KeyError' in fs :
                msg = fs.split (':') [1]
                msg = msg.rstrip ("'")
                msg = msg.strip ('\\')
                msg = msg.lstrip ("'")
                raise KeyError (msg)
            else :
                raise
    # end def lookup

    def setitem (self, cls, id, ** kw) :
        """ Set attributes of an item of the given cls,
            attributes are 'key = value' pairs.
            Debug and dryrun is handled by base class.
        """
        self.srv.set \
            ( '%s%s' % (cls, id)
            , * [self.format (cls, k, v) for k, v in kw.items ()]
            )
    # end def setitem

    def sync_status (self, remote_id, remote_issue) :
        """ Get the sync status (e.g., old properties of last sync of 
            remote issue)
        """ 
        assert \
            (  'ext_tracker_state' in self.schema
            or 'ext_tracker' in self.schema ['issue']
            )
        self.oldremote = {}
        ext_state      = None
        id             = None
        if 'ext_tracker_state' in self.schema :
            ext_state = self.srv.filter \
                ( 'ext_tracker_state'
                , None
                , dict (ext_id = remote_id, ext_tracker = self.tracker)
                )
            if ext_state :
                for i in ext_state :
                    di = self.srv.display \
                        ( 'ext_tracker_state%s' % i
                        , 'ext_id', 'ext_attributes', 'issue'
                        )
                    if di ['ext_id'] == remote_id :
                        id = int (di ['issue'])
                        break
        # Either old schema or old *and* new schema and never synced
        # with new schema:
        if not ext_state and 'ext_tracker' in self.schema ['issue'] :
            issues = self.srv.filter \
                ( 'issue'
                , None
                , dict (ext_id = remote_id, ext_tracker = self.tracker)
                )
            for i in issues :
                di = self.srv.display \
                    ('issue%s' % i, 'ext_id', 'ext_attributes')
                if di ['ext_id'] == remote_id :
                    id = int (i)
                    # Update local schema in any case if we have
                    # new-style schema in database but got data from
                    # old-style schema.
                    if 'ext_tracker_state' in self.schema :
                        self.update_state = True
                    break
        self.old_as_json = None
        if id :
            if di ['ext_attributes'] :
                m = self.getitem ('msg', di ['ext_attributes'])
                self.old_as_json = m ['content']
            self.oldvalues [id] = di
	return id
    # end def sync_status

    def sync_new_local_issues (self, new_remote_issue) :
        """ Determine *local* issues which are not yet synced to the
            remote. We search for issues with a remote issue tracker set
            (ext_tracker) but without ext_attributes.
        """
        # Method for generating new remote issue, typically gets an
        # empty dictionary as parameter (but in special cases the dict
        # may contain values in the future)
        self.new_remote_issue = new_remote_issue
        ext = self.srv.filter \
            ( 'ext_tracker_state'
            , None
            , dict (ext_tracker = self.tracker, ext_attributes = '-1')
            )
        for id in ext :
            et = self.getitem ('ext_tracker_state', id)
            assert et ['ext_id'] == None
            iid = et ['issue']
            self.sync_new_local_issue (iid)
    # end def sync_new_local_issues

    def update_aux_classes (self, id, classdict) :
        """ Auxiliary classes, e.g. for KPM an item that links to issue
            and holds additional attributes. We also see
            ext_tracker_status as such an aux class.
            All of those have a Link named 'issue' to the current issue.
        """
        for cls in classdict :
            attr = self.fix_attributes (cls, classdict [cls])
            # Check if we already have an item
            d = dict (issue = str (id))
            if cls == 'ext_tracker_state' :
                d ['ext_tracker'] = self.tracker
            it = self.srv.filter (cls, None, d)
            if it :
                assert len (it) == 1
                if attr :
                    self.setitem (cls, it [0], ** attr)
            else :
                attr ['issue'] = str (id)
                if cls == 'ext_tracker_state' :
                    attr ['ext_tracker'] = self.tracker
                self.create (cls, ** attr)
    # end def update_aux_classes

    def update_sync_db (self, id, rid, remote_issue) :
        """ Note that update_state is only used for old roundup schema
            migration
        """
        if  (self.get (id, '/ext_tracker_state/ext_tracker') != self.tracker) :
            self.newvalues [id]['ext_tracker'] = self.tracker
        if 'ext_id' not in self.newvalues [id] :
            if  (  self.oldvalues [id].get ('ext_id') != rid
                or self.update_state
                ) :
                self.newvalues [id]['ext_id'] = rid
        if  (   'ext_attributes' not in self.newvalues [id]
            and    json.dumps (self.oldremote, sort_keys = True, indent = 4)
                != remote_issue.as_json ()
            ) :
            newmsg = self.create ('msg', content = remote_issue.as_json ())
            self.newvalues [id]['ext_attributes'] = newmsg
        if self.update_state :
            for attr in 'ext_attributes', 'ext_status' :
                # get will return newvalues if existing so this is
                # idempotent if already set
                self.newvalues [id][attr] = self.get (id, attr)
            self.newvalues [id]['ext_tracker'] = self.tracker
    # end def update_sync_db

# end class Syncer
