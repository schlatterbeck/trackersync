#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2015 Dr. Ralf Schlatterbeck Open Source Consulting.
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
from   rsclib.autosuper import autosuper
from   rsclib.pycompat  import ustr, text_type

class Remote_Issue (autosuper) :
    """ This models a remote issue.
        The default (if sync_attributes is an empty dict) to synchronize
        *all* attributes for which a Sync_Attribute (see below) is
        found. In some cases it is necessary to restrict the
        synchronized attributes, e.g., if the remote tracker doesn't
        have full permissions for certain issues (e.g. cancelled issues
        in KPM) so we only get a subset of the attributes in certain
        situation (e.g. when the remote issue has been closed).
        Note that when sync_attributes is non-empty we do *not* create a
        new issue in the local tracker if the remote issue is not found.
    """

    multilevel = None

    def __init__ (self, record, sync_attributes = {}) :
        self.record     = record
        self.newvalues  = {}
        self.attributes = sync_attributes
    # end def __init__

    def __getattr__ (self, name) :
        try :
            return self [name]
        except KeyError as exc :
            raise AttributeError (exc)
    # end def __getattr__

    def __getitem__ (self, name) :
        if name is None :
            raise KeyError (name)
        if self.multilevel :
            names = name.split ('.')
            nitem = self.newvalues
            item  = self.record
            for n in names :
                if nitem is not None :
                    if n in nitem :
                        nitem = nitem [n]
                    else :
                        nitem = None
                item = item [n]
            if nitem is not None :
                return nitem
            return item
        if name in self.newvalues :
            return self.newvalues [name]
        return self.record [name]
    # end def __getitem__

    def __unicode__ (self) :
        r = []
        for k, v in sorted (self.record.iteritems ()) :
            r.append ("%(k)s: >%(v)s<" % locals ())
        return '\n'.join (r)
    # end def __unicode__

    def __str__ (self) :
        return unicode (self).encode ('utf-8')
    # end def __str__
    __repr__ = __str__

    def add_message (self, msg) :
        """ Add the given roundup message msg to this remote issue.
            The roundup message is a dictionary with the message
            properties as keys and the values of the given message.
            The method should return the id of the message just created
            if available. If no ids are supported by the remote system,
            message matching is performed only by other attributes
            (including content).
        """
        raise NotImplementedError ("Needs to be implemented in child class")
    # end def add_message

    def as_json (self) :
        """ Only return non-empty values in json dump. """
        d = dict ((k, v) for k, v in self.record.iteritems () if v)
        d.update ((k, v) for k, v in self.newvalues.iteritems ())
        return json.dumps (d, sort_keys = True, indent = 4)
    # end def as_json

    def attach_file (self, name, type, content) :
        """ Attach a file with the given filename to this remote issue.
            Return the unique filename of the remote issue. Note that
            care must be taken to return the new document id as returned
            by the document_ids method. The roundup issue will be
            updated with this new name to make sure that no duplicate
            attachments are created.
        """
        raise NotImplementedError ("Needs to be implemented in child class")
    # end def attach_file

    def document_attributes (self, docid) :
        """ Additional attributes for a file (document) attached to an
            issue. By default roundup only has the MIME-Type here named
            'type'. But schemas can be changed in roundup. This should
            return a dictionary of all roundup attributes to be set.
        """
        return dict (type = 'application/octet-stream')
    # end def document_attributes

    def document_content (self, docid) :
        """ This gets a document id (unique for this issue) and
            retrieves and returns the document content.
        """
        raise NotImplementedError ("Needs to be implemented in child class")
    # end def document_content

    def document_ids (self) :
        """ This returns a list of document ids for this issue. Note
            that the IDs need to be unique for this issue. The IDs are
            used to decide if a file is already attached to the local
            issue, no files are compared for the decision. The filenames
            in roundup are the IDs returned by this method.
        """
        raise NotImplementedError ("Needs to be implemented in child class")
    # end def document_ids

    def messages (self) :
        """ Iterator over messages of this remote issue.
            The iterator must return a dictionary, the keys are the
            message properties in roundup (so the iterator has to
            convert from the attributes of the remote issue). Only the
            'content' property is mandatory. Note that the given
            properties are used for comparison. So if, e.g., a 'date'
            property is given, this is compared *first*. If no message
            matches the given date, the message is created in roundup.
            The content property is generally compared *last* as it is
            most effort.
        """
        raise NotImplementedError ("Needs to be implemented in child class")
    # end def messages

    def get (self, name, default = None) :
        try :
            return self [name]
        except KeyError :
            return default
    # end def get

    def set (self, name, value) :
        if self.multilevel :
            names = name.split ('.')
            item  = self.newvalues
            # Copy over the current value to ease later update
            item [names [0]] = self [names [0]]
            for n in names [:-1] :
                if n not in item :
                    item [n] = {}
                item = item [n]
            item [names [-1]] = value
        else :
            self.newvalues [name] = value
    # end def set
    __setitem__ = set

    def update_remote (self, syncer) :
        """ Update remote issue tracker with self.newvalues.
        """
        raise NotImplementedError ("Needs to be implemented in child class")
    # end def update_remote

# end class Remote_Issue

class Sync_Attribute (autosuper) :

    def __init__ (self, roundup_name, remote_name = None) :
        self.name        = roundup_name
        self.remote_name = remote_name
    # end def __init__

    def sync (self, syncer, id, remote_issue) :
        """ Needs to be implemented in child class """
        pass
    # end def sync

# end class Sync_Attribute

class Sync_Attribute_One_Way (Sync_Attribute) :
    """ A Sync attribute that is read-only in the remote tracker.
        We simply take the value in the remote tracker and update
        roundup's attribute if the value has changed.
    """

    def sync (self, syncer, id, remote_issue) :
        v = remote_issue.get (self.remote_name, None)
        if syncer.get (self, id) != v :
            syncer.set (self, id, v)
    # end def sync

# end class Sync_Attribute_One_Way

class Sync_Attribute_Default (Sync_Attribute) :
    """ A default, only set if the current value is not set.
        Very useful for required attributes on creation.
        This is set from the remote attribute and in case this is also
        not set, a default can be specified in the constructor.
    """

    def __init__ (self, roundup_name, remote_name = None, default = None) :
        self.default = default
        self.__super.__init__ (roundup_name, remote_name)
    # end def __init__

    def sync (self, syncer, id, remote_issue) :
        v = remote_issue.get (self.remote_name, self.default)
        if syncer.get (self, id) is None :
            syncer.set (self, id, v)
    # end def sync

# end class Sync_Attribute_Default

class Sync_Attribute_To_Remote (Sync_Attribute) :
    """ Unconditionally synchronize a local attribute to the remote
        tracker. Typical use-case is to set the local tracker issue
        number in the remote tracker if the remote tracker also supports
        keeping numbers of another tracker or there is a dedicated
        custom attribute for this.
    """

    def sync (self, syncer, id, remote_issue) :
        rv = remote_issue.get (self.remote_name, None)
        lv = syncer.get (self, id)
        if lv != rv :
            remote_issue.set (self.remote_name, lv)
    # end def sync

# end class Sync_Attribute_To_Remote

class Sync_Attribute_Two_Way (Sync_Attribute) :
    """ Two-way sync: We first check if the remote changed since last
        sync. If it did, we update the local tracker -- even if it might
        have changed too. If the remote has not changed we check if we
        need to update the local tracker.
    """

    def sync (self, syncer, id, remote_issue) :
        rv = remote_issue.get (self.remote_name, None)
        lv = syncer.get (self, id)
        if rv == lv :
            return
        changed = False
        old = syncer.oldremote.get (self.remote_name, None)
        changed = old != remote_issue.get (self.remote_name)
        # check if remote changed since last sync
        if changed :
            syncer.set (self, id, rv)
        else :
            remote_issue.set (self.remote_name, lv)
    # end def sync

# end class Sync_Attribute_Two_Way

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

    def __init__ (self, keyword = None) :
        self.__super.__init__ ('messages', remote_name = None)
        self.keyword = keyword
    # end def __init__

    def sync (self, syncer, id, remote_issue) :
        rup_msgs = []
        msgs   = syncer.get (self, id)
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
                            assert rupm.startswith ('<Date ')
                            rupm = rupm [6:-1]
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
            syncer.set (self, id, msgs)
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

    def __init__ (self, headline, remote_name) :
        self.headline = headline
        self.hlen     = len (headline)
        self.__super.__init__ ('messages', remote_name)
    # end def __init__

    def sync (self, syncer, id, remote_issue) :
        v = remote_issue.get (self.remote_name, None)
        if not v :
            return
        msgs = syncer.get (self, id)
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
        msgs.append (newmsg)
        syncer.set (self, id, msgs)
    # end def sync

# end class Sync_Attribute_Message

class Sync_Attribute_Default_Message (Sync_Attribute) :
    """ A default message added as the *only* message whenever the
        remote tracker doesn't have any message generated.
        This is used to add at least one message to a new issue in
        roundup because at least one message is required.
    """
    def __init__ (self, message) :
        self.message = message
        self.__super.__init__ ('messages', None)
    # end def __init__

    def sync (self, syncer, id, remote_issue) :
        msgs = syncer.get (self, id)
        if not msgs :
            newmsg  = syncer.create ('msg', content = self.message)
            msgs.append (newmsg)
            syncer.set (self, id, msgs)
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

    def __init__ (self, prefix = None) :
        self.prefix = prefix
        self.__super.__init__ ('files', remote_name = None)
    # end def __init__

    def sync (self, syncer, id, remote_issue) :
        fids   = syncer.get (self, id)
        nosync = dict.fromkeys (fids)
        files  = [syncer.getitem ('file', i, 'name', 'id') for i in fids]
        names  = dict ((f ['name'], f ['id']) for f in files)
        found  = False
        for docid in remote_issue.document_ids () :
            if docid in names :
                del nosync [names [docid]]
            else :
                newfile = syncer.create \
                    ( 'file'
                    , name    = docid
                    , content = remote_issue.document_content (docid)
                    , ** remote_issue.document_attributes (docid)
                    )
                fids.append (newfile)
                found = True
        if found :
            syncer.set (self, id, fids)
        if self.prefix is not None :
            files = [syncer.getitem ('file', i, 'name', 'id', 'type')
                     for i in nosync
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

class Syncer (autosuper) :
    """ Synchronisation Framework
        We get the mapping of remote attributes to roundup attributes.
        The type of attribute indicates the action to perform.
        We need at least an attribute that maps the ext_id attribute to
        the name of the external id attribute in the remote.
    """

    def __init__ (self, url, remote_name, attributes, verbose = 0, debug = 0) :
        self.srv = xmlrpclib.ServerProxy (url, allow_none = True)
        self.attributes  = attributes
        self.oldvalues   = {}
        self.newvalues   = {}
        self.newcount    = 0
        self.remote_name = remote_name
        schema = self.srv.schema ()
        self.schema      = dict ((k, dict (schema [k])) for k in schema)
        self.tracker     = self.srv.lookup ('ext_tracker', remote_name)
        self.verbose     = verbose
        self.debug       = debug
        self.oldremote   = {}
    # end def __init__

    def create (self, cls, ** kw) :
        return self.srv.create \
            (cls, * (self.format (cls, k, v) for k, v in kw.items ()))
    # end def create

    def format (self, cls, key, value) :
        t = self.schema [cls][key]
        if t.startswith ('<roundup.hyperdb.Multilink') :
            return '%s=%s' % (key, ','.join (value))
        elif not isinstance (value, text_type) :
            return xmlrpclib.Binary \
                (key.encode ('ascii') + '='.encode ('ascii') + value)
        else :
            return '%s=%s' % (key, value)
    # end def format

    def get (self, attr, id, name = None) :
        name = name or attr.name
        if name in self.newvalues [id] :
            return self.newvalues [id][name]
        if name not in self.oldvalues [id] :
            if int (id) > 0 :
                self.oldvalues [id][name] = self.srv.display \
                    ('issue%s' % id, name) [name]
            else :
                t = self.schema ['issue'][name]
                if t.startswith ('<roundup.hyperdb.Multilink') :
                    v = []
                else :
                    v = None
                self.oldvalues [id][name] = v
        return self.oldvalues [id][name]
    # end def get

    def getitem (self, cls, id, *attr) :
        """ Get all or given list of attributes of an item of the given cls.
            This must not be used for attributes of the issue which we
            are currently syncing. The sync framework keeps a cache of
            to-be-updated attributes, this would bypass the cache.
        """
        return self.srv.display ('%s%s' % (cls, id), *attr)
    # end def getitem

    def setitem (self, cls, id, **attr) :
        """ Set an attribute of an item of the given cls,
            attributes are 'key = value' pairs.
        """
        p = ("%s=%s" % (k, v) for k, v in attr.iteritems ())
        return self.srv.set ('%s%s' % (cls, id), *p)
    # end def setitem

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

    def set (self, attr, id, value) :
        self.newvalues [id][attr.name] = value
    # end def set

    def sync (self, remote_id, remote_issue) :
        """ We try to find issue with the given remote_id and then call
            the sync framework. If no issue with the given remote_id is
            found, a new issue will be created after all attributes have
            been synced.
        """
        issues = self.srv.filter \
            ( 'issue'
            , None
            , dict (ext_id = remote_id, ext_tracker = self.tracker)
            )
        id = None
        do_sync = False
        self.oldremote = {}
        for i in issues :
            di = self.srv.display ('issue%s' % i, 'ext_id', 'ext_attributes')
            if di ['ext_id'] != remote_id :
                continue
            if di ['ext_attributes'] :
                m = self.getitem ('msg', di ['ext_attributes'])
                if m ['content'] != remote_issue.as_json () :
                    do_sync = True
                self.oldremote = json.loads (m ['content'])
            else :
                do_sync = True
            id = int (i)
            self.newvalues [id] = {}
            self.oldvalues [id] = di
            break
        else :
            self.newcount += 1
            id = -self.newcount
            self.oldvalues [id] = {}
            # create new issue only if the remote issue has all required
            # attributes and doesn't restrict them to a subset:
            do_sync = not remote_issue.attributes
            self.newvalues [id] = {}
            self.newvalues [id]['ext_tracker'] = self.tracker
        attr = remote_issue.attributes
        for a in self.attributes :
            if not attr or a.remote_name in attr :
                a.sync (self, id, remote_issue)
        if 'ext_id' not in self.newvalues [id] :
            if self.oldvalues [id].get ('ext_id') != remote_id :
                self.newvalues [id]['ext_id'] = remote_id
        if  (   'ext_attributes' not in self.newvalues [id]
            and    json.dumps (self.oldremote, sort_keys = True, indent = 4)
                != remote_issue.as_json ()
            ) :
            newmsg = self.create ('msg', content = remote_issue.as_json ())
            self.newvalues [id]['ext_attributes'] = newmsg
        if id < 0 :
            if not remote_issue.attributes :
                if self.verbose :
                    print ("create issue: %s" % self.newvalues [id])
                self.create ('issue', ** self.newvalues [id])
        elif self.newvalues [id] :
            if self.verbose :
                print ("set issue %s: %s" % (id, self.newvalues [id]))
            if self.debug :
                print (self.newvalues [id].items ())
            self.srv.set \
                ( 'issue%s' % id
                , * ( self.format ('issue', k, v)
                      for k, v in self.newvalues [id].items ()
                    )
                )
        if remote_issue.newvalues :
            remote_issue.update_remote (self)
    # end def sync

# end class Syncer
