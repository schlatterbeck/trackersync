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
import ssl
from   time             import sleep
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

    # Map roundup types to names for conversion methods
    typemap = \
        { '<roundup.hyperdb.String>'  : 'string'
        , '<roundup.hyperdb.Date>'    : 'date'
        , '<roundup.hyperdb.Number>'  : 'number'
        , '<roundup.hyperdb.Boolean>' : 'bool'
        }

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

    def check_sync_callback (self, syncer, id) :
        """ Override a no-sync decision. If this returns False, a sync
            for this issue is performed, even if other no-sync checks of
            a Sync_Attribute_Check fail.
        """
        return True
    # end def check_sync_callback

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

    def document_fixer (self, namedict) :
        """ Allow the remote issue to correct document names, i.e.,
            extract only the relevant document id part according the the
            naming convention of the remote issue. This is needed
            because we don't have the remote document id in roundup and
            need to preserve it in the filename. So we need a way to
            code both, the docid and the remote filename into the
            roundup filename.
        """
        return namedict
    # end def document_fixer

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
            the sync. Similar to update but creating a new remote issue.
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

    def set (self, name, value, type) :
        type = self.typemap.get (type, None)
        conv = None
        if type :
            conv = getattr (self, 'convert_%s' % type, None)
        if conv :
            value = conv (value)
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

    def strip_prefix (self, propname, prefix) :
        """ Strip a prefix from a given property.
            This must sometimes be done when the remote system returns a
            prefix where it should not: When setting the remote to "x"
            and it returns "PREFIXx", the result will not roundtrip,
            instead for each update for a two-way sync, the remote will
            grow a new prefix. To prevent this behaviour we strip prefix
            from oldvalue (correcting the behaviour of the remote
            system).
            Note that this is currently not implemented for transitive
            properties (self.multilevel set) of the remote system.
        """
        v = self.get (propname)
        if self.multilevel :
            raise NotImplementedError \
                ("Multilevel not implemented for strip_prefix")
        if  (   propname in self.record
            and propname not in self.newvalues
            and v.startswith (prefix) 
            ) :
            l = len (prefix)
            v = v [l:]
            self.record [propname] = v
    # end def strip_prefix

    def update (self, syncer) :
        """ Update remote issue tracker with self.newvalues.
        """
        raise NotImplementedError ("Needs to be implemented in child class")
    # end def update

# end class Remote_Issue

def rup_date (datestring) :
    """ String roundup XMLRPC date and extract date/time in the format
        %Y-%m-%d.%H:%M:%S seconds are with 3 decimal places, e.g.
        2015-09-06.13:51:38.840
    """
    assert datestring.startswith ('<Date ')
    ret = datestring [6:-1]
    return ret
# end def rup_date

class Sync_Attribute (autosuper) :
    """ Sync a property from/to a remote tracker.
        If only_update is specified, the sync is run only in the update
        phase (when the remote issue is already existing).
        If only_create is specified, the sync is run only for creation
        of the remote issue (when it doesn't exist yet).
        The default is to run a sync during both phases.

        The map attribute is an optional map of local values to remote
        values. The imap is the inverse. Both can be specified if the
        mapping is not 1:1, but be careful as such configurations tend
        not to roundtrip very well. Note that not all Sync_Attribute
        support a map.

        Note that if both, a map/imap and l_default or r_default is
        specified, the default values must be the values *after*
        applying the map (or imap).
    """

    def __init__ \
        ( self
        , roundup_name
        , remote_name  = None
        , only_update  = False
        , only_create  = False
        , l_default    = None
        , r_default    = None
        , map          = None
        , imap         = None
        , strip_prefix = None
        ) :
        self.name         = roundup_name
        self.remote_name  = remote_name
        self.only_update  = only_update
        self.only_create  = only_create
        self.l_default    = l_default
        self.r_default    = r_default
        self.map          = map
        self.imap         = imap
        self.strip_prefix = strip_prefix
        if not self.imap and self.map :
            self.imap = dict ((v, k) for k, v in  map.iteritems ())
        if not self.map and self.imap :
            self.map  = dict ((v, k) for k, v in imap.iteritems ())
    # end def __init__

    def no_sync_necessary (self, lv, rv) :
        l_def = getattr (self, 'l_default', None)
        r_def = getattr (self, 'r_default', None)
        if self.map :
            # Both maps need to disagree for non-equal -- this prevents
            # ping-pong updates in case the mappings are not fully
            # consistent
            equal = \
                (  self.map.get  (lv, l_def) == rv
                or self.imap.get (rv, None)  == lv
                )
        else :
            equal = lv == rv
        return  (   equal
                and (   not (lv is None and rv is None)
                    or  not (l_def or r_def)
                    )
                )
    # end def no_sync_necessary

    def sync (self, syncer, id, remote_issue) :
        """ Needs to be implemented in child class.
            Note that a sync method may return a value != None in which
            case the sync for this Issue is not done. Useful for checks
            if a sync for a particular issue should happen.
        """
        pass
    # end def sync

    def type (self, syncer) :
        if not self.name :
            return None
        if self.name.startswith ('/') :
            classname, path = self.name.strip ('/').split ('/', 1)
        else :
            classname = 'issue'
            path = self.name
        return syncer.get_transitive_schema (classname, path)
    # end def type

# end class Sync_Attribute

class Sync_Attribute_Check (Sync_Attribute) :
    """ A boolean roundup attribute used to check if the issue should
        be synced to the remote side. If a remote_name exists, the value
        of it is used to set the roundup attribute if 'update' is True.
        Otherwise an if 'update' is on, r_default (usually set to
        True) must exist.
        If 'invert' is set, the logic is inverted, it is checked that
        the attribute does *not* exist. Consequently if 'update' is set
        it should update the property to False (or a python equivalent
        that evaluates to a boolean False).
        The check_sync_callback routine gets the syncer and id as
        parameters and must return a boolean value indicating if syncing
        should be forced. This routine can override a no-sync
        decision.
        Note that update is only performed for new local issues.
        Note that we don't currently support a map / imap.
    """

    def __init__ \
        ( self
        , roundup_name
        , remote_name = None
        , invert      = False
        , update      = True
        , ** kw
        ) :
        self.invert    = invert
        self.update    = update
        self.__super.__init__ (roundup_name, remote_name, ** kw)
    # end def __init__

    def sync (self, syncer, id, remote_issue) :
        synccheck = remote_issue.check_sync_callback (syncer, id)
        lv = syncer.get (id, self.name)
        stop = not lv
        if self.invert :
            stop = not stop
        # Stop sync if following condition is true:
        if stop and id > 0 and synccheck :
            return True
        if self.update and lv is None :
            rv = remote_issue.get (self.remote_name, self.r_default)
            syncer.set (id, self.name, rv)
    # end def sync

# end class Sync_Attribute_Check

class Sync_Attribute_One_Way (Sync_Attribute) :
    """ A Sync attribute that is read-only in the remote tracker.
        We simply take the value in the remote tracker and update
        roundup's attribute if the value has changed.
        Things get more complicated if we have defaults, if both values
        are None and we have an r_default, it is applied.
    """

    def sync (self, syncer, id, remote_issue) :
        rv = remote_issue.get (self.remote_name, None)
        lv = syncer.get (id, self.name)
        if self.no_sync_necessary (lv, rv) :
            return
        if self.imap :
            rv = self.imap.get (rv, self.r_default)
        elif rv is None and self.r_default :
            rv = self.r_default
        syncer.set (id, self.name, rv)
    # end def sync

# end class Sync_Attribute_One_Way

class Sync_Attribute_Default (Sync_Attribute) :
    """ A default, only set if the current value is not set.
        Very useful for required attributes on creation.
        This is set from the remote attribute and in case this is also
        not set, a default can be specified in the constructor.
    """

    def sync (self, syncer, id, remote_issue) :
        v = remote_issue.get (self.remote_name)
        if self.imap :
            v = self.imap.get (v, self.r_default)
        elif v is None and self.r_default :
            v = self.r_default
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

    def _sync (self, syncer, id, remote_issue) :
        # Never sync something to remote if local issue not yet created.
        # Default values of local issue are assigned during creation, so
        # we can't sync these to the remote site during this sync (they
        # would get empty values).
        if id < 0 :
            return None, None, True
        rv = remote_issue.get (self.remote_name, None)
        lv = syncer.get (id, self.name)
        nosync = self.no_sync_necessary (lv, rv)
        if self.imap :
            rv = self.imap.get (rv, None)
        if self.map :
            lv = self.map.get (lv, self.l_default)
        if lv is None and rv is None and self.l_default is not None :
            lv = self.l_default
        return lv, rv, nosync
    # end def _sync

    def sync (self, syncer, id, remote_issue) :
        lv, rv, nosync = self._sync (syncer, id, remote_issue)
        if not nosync :
            remote_issue.set (self.remote_name, lv, self.type (syncer))
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
        lv, rv, nosync = self._sync (syncer, id, remote_issue)
        # Note that rv != remote_issue.get in case we do have self.imap
        # in that case we need to check if the *original* attribute
        # is set if it doesn't reverse map to a known value.
        if  (   not nosync
            and not rv
            and not remote_issue.get (self.remote_name, None)
            and lv
            ) :
            remote_issue.set (self.remote_name, lv, self.type (syncer))
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

    def sync (self, syncer, id, remote_issue) :
        rv      = remote_issue.get (self.remote_name, None)
        lv      = syncer.get (id, self.name)
        nosync  = self.no_sync_necessary (lv, rv)
        old     = syncer.oldremote.get (self.remote_name, None)
        changed = old != rv
        if self.map :
            lv = self.map.get (lv, self.l_default)
        if self.imap :
            rv = self.imap.get (rv, self.r_default)
        if nosync :
            return
        if rv is None and lv is None :
            if self.l_default is not None :
                lv = self.l_default # this is synced *to* remote
            if self.r_default is not None :
                rv = self.r_default # this is synced *to* local
        # check if remote changed since last sync;
        # Update remote issue if we have r_default and rv is not set
        if  (  (changed and (rv or not self.r_default))
            or (syncer.remote_change and rv is not None)
            ) :
            if rv is None :
                print ("WARN: Would set issue%s %s to None" % (id, self.name))
            else :
                syncer.set (id, self.name, rv)
        else :
            remote_issue.set (self.remote_name, lv, self.type (syncer))
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
        , verbose         = 0
        , debug           = 0
        , dry_run         = 0
        , remote_dry_run  = 0
        , remote_change   = False
        , unverified      = False
        ) :
        srvargs = dict (allow_none = True)
        if unverified :
            context = ssl._create_unverified_context ()
            srvargs ['context'] = context
        self.srv = Retry_Server_Proxy (3, 0, url, **srvargs)
        self.attributes      = attributes
        self.oldvalues       = {}
        self.newvalues       = {}
        self.newcount        = 0
        self.remote_name     = remote_name
        self.remote_change   = remote_change
        schema               = self.srv.schema ()
        self.tracker         = self.srv.lookup ('ext_tracker', remote_name)
        self.verbose         = verbose
        self.debug           = debug
        self.dry_run         = dry_run
        self.remote_dry_run  = remote_dry_run
        self.oldremote       = {}
        self.update_state    = False
        self.schema          = dict ((k, dict (schema [k])) for k in schema)
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
        if t.startswith ('<roundup.hyperdb.Multilink') :
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

    def get_class_path (self, classname, path, id = None) :
        """ We get a transitive property 'path' and return classname and
            property name and optionally the id.
            Note that id may become a list when processing multilinks on
            the way.
        """
        path = path.split ('.')
        for p in path [:-1] :
            assert self.get_type (classname, p) in ('Link', 'Multilink')
            if id :
                if isinstance (id, list) :
                    id = [self.srv.display ('%s%s' % (classname, i), p) [p]
                          for i in id
                         ]
                    if id and isinstance (id [0], list) :
                        id = [item for sublist in id for item in sublist]
                else :
                    id = self.srv.display ('%s%s' % (classname, id), p) [p]
            classname = self.get_classname (classname, p)
        p = path [-1]
        return classname, p, id
    # end def get_class_path

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
        classname, p, id = self.get_class_path (classname, path, id)
        if id :
            if isinstance (id, list) :
                r = [self.srv.display ('%s%s' % (classname, i), p) [p]
                     for i in id
                    ]
                r = ','.join (r)
            else :
                r = self.srv.display ('%s%s' % (classname, id), p) [p]
            if r and self.schema [classname][p] == '<roundup.hyperdb.Date>' :
                return rup_date (r)
            return r
        return self.get_default (classname, p)
    # end def get_path

    def get_transitive_schema (self, classname, path) :
        classname, prop, id = self.get_class_path (classname, path)
        return self.schema [classname][prop]
    # end def get_transitive_schema

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
        # Don't sync a subset of attributes if local issue doesn't exist
        if id < 0 and attr :
            return
        for a in self.attributes :
            if a.only_create :
                continue
            if a.strip_prefix :
                remote_issue.strip_prefix (a.remote_name, a.strip_prefix)
            if not attr or a.remote_name in attr :
                if self.debug :
                    print \
                        ( "sa: %s %s %s"
                        % (a.__class__.__name__, a.name, a.remote_name)
                        )
                if a.sync (self, id, remote_issue) :
                    if self.verbose :
                        print ("Not syncing: %s" % id)
                    return
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
            self.update_issue (id)
        if  (   remote_issue.newvalues
            and not self.dry_run
            and not self.remote_dry_run
            ) :
            if self.verbose :
                print ("Update remote:", remote_issue.newvalues)
            remote_issue.update (self)
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
            , dict (ext_tracker = self.tracker, ext_attributes = '-1')
            )
        for id in ext :
            et = self.getitem ('ext_tracker_state', id)
            assert et ['ext_id'] == None
            remote_issue = self.new_remote_issue ({})
            iid = et ['issue']
            self.newvalues [iid] = {}
            self.oldvalues [iid] = {}
            do_sync = True
            for a in self.attributes :
                if a.only_update :
                    continue
                if a.sync (self, iid, remote_issue) :
                    if self.verbose :
                        print ("Not syncing: %s" % iid)
                    do_sync = False
                    break
            if not do_sync :
                continue
            if self.verbose :
                print ("remote_issue.create", remote_issue.newvalues)
            rid = remote_issue.create ()
            if not rid :
                raise ValueError \
                    ("Didn't receive correct remote issue on creation")
            self.set (iid, '/ext_tracker_state/ext_id', rid)
            newmsg = self.create ('msg', content = remote_issue.as_json ())
            self.set (iid, '/ext_tracker_state/ext_attributes', newmsg)
            self.update_issue (iid)
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

    def update_issue (self, id) :
        if self.verbose :
            print ("set issue %s: %s" % (id, self.newvalues [id]))
        classdict = self.split_newvalues (id)
        attr = self.fix_attributes ('issue', classdict ['issue'])
        if attr :
            self.setitem ('issue', id, ** attr)
        del classdict ['issue']
        self.update_aux_classes (id, classdict)
    # end def update_issue

# end class Syncer
