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
import numbers
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

    def create (self) :
        """ Create new remote issue from data here. This is called by
            the sync framework *after* all attributes have been set by
            the sync. Similar to update_remote but creating a new remote
            issue.
        """
        raise NotImplementedError ("Needs to be implemented in child class")
    # end def create

    def get (self, name, default = None) :
        try :
            return self [name]
        except KeyError :
            return default
    # end def get

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
        """ Needs to be implemented in child class.
            Note that a sync method may return a value != None in which
            case the sync for this Issue is not done. Useful for checks
            if a sync for a particular issue should happen.
        """
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
        if syncer.get (id, self.name) != v :
            syncer.set (id, self.name, v)
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
        if syncer.get (id, self.name) is None :
            syncer.set (id, self.name, v)
    # end def sync

# end class Sync_Attribute_Default

class Sync_Attribute_To_Remote (Sync_Attribute) :
    """ Unconditionally synchronize a local attribute to the remote
        tracker. Typical use-case is to set the local tracker issue
        number in the remote tracker if the remote tracker also supports
        keeping numbers of another tracker or there is a dedicated
        custom attribute for this.
        An optional map can map local and remote values via a
        dictionary. The keys in the map are local values. These map to
        the remote values. Internally an inverse map is computed.
        Optionally we can define a local default l_default. This is set
        if the local value is None *and* the remote value is None.
    """

    def __init__ \
        ( self
        , roundup_name
        , remote_name = None
        , l_default   = None
        , map         = None
        ) :
        self.__super.__init__ (roundup_name, remote_name)
        self.l_default = l_default
        self.map       = map
        self.imap      = None
        if self.map :
            self.imap = dict ((v, k) for k, v in map.iteritems ())
    # end def __init__

    def _sync (self, syncer, id, remote_issue) :
        # Never sync something to remote if local issue not yet created.
        # Default values of local issue are assigned during creation, so
        # we can't sync these to the remote site during this sync (they
        # would get empty values).
        if id < 0 :
            return None, None, True
        rv = remote_issue.get (self.remote_name, None)
        lv = syncer.get (id, self.name)
        if self.map :
            # Both maps need to disagree for non-equal -- this prevents
            # ping-pong updates in case the mappings are not fully
            # consistent
            equal = \
                (  self.map.get (lv, self.l_default) == rv
                or self.imap.get (rv, None) == lv
                )
        else :
            equal = lv == rv
        if self.imap :
            rv = self.imap.get (rv, None)
        if self.map :
            lv = self.map.get (lv, self.l_default)
        if lv is None and rv is None and self.l_default is not None :
            lv = self.l_default
        return lv, rv, equal
    # end def _sync

    def sync (self, syncer, id, remote_issue) :
        lv, rv, equal = self._sync (syncer, id, remote_issue)
        if not equal :
            remote_issue.set (self.remote_name, lv)
    # end def sync

# end class Sync_Attribute_To_Remote

class Sync_Attribute_To_Remote_Default (Sync_Attribute_To_Remote) :
    """ A default, only set if the current value is not set.
        Very useful for required attributes on creation.
        This is set from the local attribute and in case this is also
        not set, a default can be specified in the constructor.
        Very similar to Sync_Attribute_To_Remote but only synced if the
        remote attribute is empty.
    """

    def sync (self, syncer, id, remote_issue) :
        lv, rv, equal = self._sync (syncer, id, remote_issue)
        # Note that rv != remote_issue.get in case we do have self.imap
        # in that case we need to check if the *original* attribute
        # is set if it doesn't reverse map to a known value.
        if  (   not equal
            and not rv
            and not remote_issue.get (self.remote_name, None)
            and lv
            ) :
            remote_issue.set (self.remote_name, lv)
    # end def sync

# end class Sync_Attribute_To_Remote_Default

class Sync_Attribute_Two_Way (Sync_Attribute) :
    """ Two-way sync: We first check if the remote changed since last
        sync. If it did, we update the local tracker -- even if it might
        have changed too. If the remote has not changed we check if we
        need to update the local tracker.
        An optional map can map local and remote values via a
        dictionary. The keys in the map are local values. These map to
        the remote values. Internally an inverse map is computed unless
        imap is specified.
        We can specify defaults for both, the local tracker (l_default)
        *and* the remote tracker (r_default). These apply only if both,
        the local *and* the remote value are empty. In that case the
        local default (l_default) is set locally and the remote default
        (r_default) is set on the remote side.
        Note that in case we have both, a remote and a local default and
        both sides have empty values, the result is undefined if both
        values do not match (or a map maps them to equal values).
    """

    def __init__ \
        ( self
        , roundup_name
        , remote_name = None
        , r_default   = None
        , l_default   = None
        , map         = None
        , imap        = None
        ) :
        self.__super.__init__ (roundup_name, remote_name)
        self.r_default = r_default
        self.l_default = l_default
        self.map       = map
        self.imap      = imap
        if self.map and not self.imap :
            self.imap = dict ((v, k) for k, v in map.iteritems ())
        if self.imap and not self.map :
            self.map = dict ((v, k) for k, v in imap.iteritems ())
    # end def __init__

    def sync (self, syncer, id, remote_issue) :
        rv = remote_issue.get (self.remote_name, None)
        lv = syncer.get (id, self.name)
        if self.map :
            # Both maps need to disagree for non-equal -- this prevents
            # ping-pong updates in case the mappings are not fully
            # consistent
            equal = \
                (  self.map.get (lv, self.l_default) == rv
                or self.imap.get (rv, None) == lv
                )
        else :
            equal = lv == rv
        #if not equal :
        #    import pdb; pdb.set_trace ()
        if self.map :
            lv = self.map.get (lv, self.l_default)
        if self.imap :
            rv = self.imap.get (rv, self.r_default)
        if rv is None and lv is None :
            if self.l_default is not None :
                lv = self.l_default # this is synced *to* remote
            if self.r_default is not None :
                rv = self.r_default # this is synced *to* local
        if equal :
            return
        changed = False
        old = syncer.oldremote.get (self.remote_name, None)
        changed = old != rv
        # check if remote changed since last sync;
        # Update remote issue if we have r_default and rv is not set
        if changed and (rv or not self.r_default) :
            syncer.set (id, self.name, rv)
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

    def __init__ (self, headline, remote_name) :
        self.headline = headline
        self.hlen     = len (headline)
        self.__super.__init__ ('messages', remote_name)
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
    def __init__ (self, message) :
        self.message = message
        self.__super.__init__ ('messages', None)
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

    def __init__ (self, prefix = None) :
        self.prefix = prefix
        self.__super.__init__ ('files', remote_name = None)
    # end def __init__

    def sync (self, syncer, id, remote_issue) :
        fids   = syncer.get (id, self.name)
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
            syncer.set (id, self.name, fids)
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

    ext_names = dict.fromkeys \
        (('ext_attributes', 'ext_id', 'ext_status', 'ext_tracker'))

    def __init__ \
        ( self
        , url
        , remote_name
        , attributes
        , verbose = 0
        , debug   = 0
        , dry_run = 0
        ) :
        self.srv = xmlrpclib.ServerProxy (url, allow_none = True)
        self.attributes   = attributes
        self.oldvalues    = {}
        self.newvalues    = {}
        self.newcount     = 0
        self.remote_name  = remote_name
        schema            = self.srv.schema ()
        self.tracker      = self.srv.lookup ('ext_tracker', remote_name)
        self.verbose      = verbose
        self.debug        = debug
        self.dry_run      = dry_run
        self.oldremote    = {}
        self.update_state = False
        self.schema       = dict ((k, dict (schema [k])) for k in schema)
        # Update schema with auto attributes
        for cls in self.schema :
            for k in 'creation', 'activity' :
                self.schema [cls][k] = '<roundup.hyperdb.Date>'
            self.schema [cls]['id']  = '<roundup.hyperdb.String>'
    # end def __init__

    def create (self, cls, ** kw) :
        if self.debug :
            if cls == 'file' :
                print ("srv.create %s %s" % (cls, kw.get('name', '?')))
            else :
                print ("srv.create %s %s" % (cls, kw))
        if self.dry_run :
            return "9999999"
        return self.srv.create \
            (cls, * [self.format (cls, k, v) for k, v in kw.items ()])
    # end def create

    def setitem (self, cls, id, ** kw) :
        """ Set attributes of an item of the given cls,
            attributes are 'key = value' pairs.
        """
        if self.debug :
            print ("srv.set %s%s %s" % (cls, id, kw))
        if not self.dry_run :
            self.srv.set \
                ( '%s%s' % (cls, id)
                , * [self.format (cls, k, v) for k, v in kw.items ()]
                )
    # end def setitem

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
        t = self.schema [cls][key]
        if value is None :
            import pdb; pdb.set_trace ()
        if t.startswith ('<roundup.hyperdb.Multilink') :
            return '%s=%s' % (key, ','.join (value))
        elif isinstance (value, numbers.Number) :
            return '%s=%s' % (key, value)
        elif not isinstance (value, text_type) :
            return xmlrpclib.Binary \
                (key.encode ('ascii') + '='.encode ('ascii') + value)
        else :
            return '%s=%s' % (key, value)
    # end def format

    def get (self, id, name) :
        if name is None :
            return None
        if name in self.newvalues [id] :
            return self.newvalues [id][name]
        if name not in self.oldvalues [id] :
            if name.startswith ('/') :
                classname, path = name.strip ('/').split ('/', 1)
            else :
                classname = 'issue'
                path = name
            sid = None
            if int (id) > 0 :
                sid = id
            if name.startswith ('/') and sid :
                d = dict (issue = id)
                if 'ext_tracker' in self.schema [classname] :
                    d ['ext_tracker'] = self.tracker
                itms = self.srv.filter (classname, None, d)
                assert len (itms) <= 1
                if itms :
                    sid = itms [0]
                else :
                    sid = None
            self.oldvalues [id][name] = self.get_path (classname, path, sid)
        return self.oldvalues [id][name]
    # end def get

    def get_classname (self, classname, name) :
        """ Get the classname of a Link or Multilink property """
        assert self.schema [classname][name].endswith ('">')
        return self.schema [classname][name].strip ('"').rsplit ('"', 2) [-2]
    # end def get_classname

    def get_default (self, classname, name) :
        """ Get default value for a property of the given class """
        t = self.schema [classname][name]
        if t.startswith ('<roundup.hyperdb.Multilink') :
            v = []
        else :
            v = None
        return v
    # end def get_default

    def get_path (self, classname, path, id) :
        path = path.split ('.')
        for p in path [:-1] :
            assert self.get_type (classname, p) == 'Link'
            if id :
                id = self.srv.display ('%s%s' % (classname, id), p) [p]
            classname = self.get_classname (classname, p)
        p = path [-1]
        if id :
            return self.srv.display ('%s%s' % (classname, id), p) [p]
        return self.get_default (classname, p)
    # end def get_path

    def get_type (self, classname, name) :
        """ Get type of link value, either Link or Multilink """
        t = self.schema [classname][name]
        t = t.split () [0]
        t = t.rsplit ('.', 1) [-1]
        assert t in ('Link', 'Multilink')
        return t
    # end def get_type

    def getitem (self, cls, id, *attr) :
        """ Get all or given list of attributes of an item of the given cls.
            This must not be used for attributes of the issue which we
            are currently syncing. The sync framework keeps a cache of
            to-be-updated attributes, this would bypass the cache.
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

    def set (self, id, attrname, value) :
        self.newvalues [id][attrname] = value
    # end def set

    def split_newvalues (self, id) :
        """ Split self.newvalues into attributes belonging to issue and
            attributes belonging to ext_tracker_state. This is only
            needed for new-style roundup sync schema.
        """
        classes = dict (issue = {})
        if 'ext_tracker_state' in self.schema :
            classes ['ext_tracker_state'] = {}
        for k in self.newvalues [id] :
            if k.startswith ('/') :
                # FIXME: Check if rest is composite
                classname, rest = k.strip ('/').split ('/', 1)
                if classname not in classes :
                    classes [classname] = {}
                classes [classname][rest] = self.newvalues [id][k]
            elif k in self.ext_names :
                classes ['ext_tracker_state'][k] = self.newvalues [id][k]
            else :
                # FIXME: Check if k is composite
                classes ['issue'][k] = self.newvalues [id][k]
        return classes
    # end def split_newvalues

    def sync (self, remote_id, remote_issue) :
        """ We try to find issue with the given remote_id and then call
            the sync framework. If no issue with the given remote_id is
            found, a new issue will be created after all attributes have
            been synced.
        """
        assert \
            (  'ext_tracker_state' in self.schema
            or 'ext_tracker' in self.schema ['issue']
            )
        ext_state      = None
        id             = None
        do_sync        = False
        self.oldremote = {}

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

        if id :
            if di ['ext_attributes'] :
                m = self.getitem ('msg', di ['ext_attributes'])
                if m ['content'] != remote_issue.as_json () :
                    do_sync = True
                self.oldremote = json.loads (m ['content'])
            else :
                do_sync = True
            self.newvalues [id] = {}
            self.oldvalues [id] = di
        else :
            self.newcount += 1
            id = -self.newcount
            self.oldvalues [id] = {}
            # create new issue only if the remote issue has all required
            # attributes and doesn't restrict them to a subset:
            do_sync = not remote_issue.attributes
            self.newvalues [id] = {}
            self.newvalues [id]['ext_tracker'] = self.tracker
        # If the following is non-empty, sync only an explicit subset of
        # attributes.
        attr = remote_issue.attributes
        for a in self.attributes :
            if not attr or a.remote_name in attr :
                if self.debug :
                    print \
                        ( "sa: %s %s %s"
                        % (a.__class__.__name__, a.name, a.remote_name)
                        )
                if a.sync (self, id, remote_issue) :
                    if self.verbose :
                        print ("Not syncing: %s" % id)
                    break
        if 'ext_id' not in self.newvalues [id] :
            if  (  self.oldvalues [id].get ('ext_id') != remote_id
                or self.update_state
                ) :
                self.newvalues [id]['ext_id'] = remote_id
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
        if id < 0 :
            if not remote_issue.attributes :
                if self.verbose :
                    print ("create issue: %s" % self.newvalues [id])
                classdict = self.split_newvalues (id)
                attr = self.fix_attributes ('issue', classdict ['issue'])
                iid = self.create ('issue', ** attr)
                del classdict ['issue']
                self.update_aux_classes (iid, classdict)
        elif self.newvalues [id] :
            if self.verbose :
                print ("set issue %s: %s" % (id, self.newvalues [id]))
            classdict = self.split_newvalues (id)
            attr = self.fix_attributes ('issue', classdict ['issue'])
            if attr :
                self.setitem ('issue', id, ** attr)
            del classdict ['issue']
            self.update_aux_classes (id, classdict)
        if remote_issue.newvalues and not self.dry_run :
            if self.verbose :
                print ("Update remote:", remote_issue.newvalues)
            remote_issue.update_remote (self)
    # end def sync

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
            , dict (ext_tracker = self.tracker, ext_attributes = -1)
            )
        for id in ext :
            assert self.get (id, 'ext_id') == None
            remote_issue = self.new_remote_issue ({})
            for a in self.attributes :
                if a.sync (self, id, remote_issue) :
                    if self.verbose :
                        "Not syncing: %s" % id
                    break
            rid = remote_issue.create ()
            self.set (id, 'ext_id', rid)
            newmsg = self.create ('msg', content = remote_issue.as_json ())
            self.set (id, 'ext_attributes', newmsg)
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

# end class Syncer
