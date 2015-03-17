#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2015 Dr. Ralf Schlatterbeck Open Source Consulting.
# Reichergasse 131, A-3411 Weidling.
# Web: http://www.runtux.com Email: office@runtux.com
# All rights reserved
# ****************************************************************************
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Library General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
# ****************************************************************************

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import

import xmlrpclib
import json
from   rsclib.autosuper import autosuper
from   rsclib.pycompat  import ustr

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

    def __init__ (self, record, sync_attributes = {}) :
        self.record     = record
        self.attributes = sync_attributes
    # end def __init__

    def __getattr__ (self, name) :
        try :
            return self.record [name]
        except KeyError as exc :
            raise AttributeError (exc)
    # end def __getattr__

    def __getitem__ (self, name) :
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

    def as_json (self) :
        return json.dumps (self.record)
    # end def as_json

    def get (self, name, default = None) :
        return self.record.get (name, default)
    # end def get

# end class Remote_Issue

class Sync_Attribute (autosuper) :

    def __init__ (self, roundup_name, remote_name = None) :
        self.name        = roundup_name
        self.remote_name = remote_name
    # end def __init__

    def sync (self, syncer, id, remote_issue) :
        raise NotImplementedError ("Needs to be implemented in child class")
    # end def sync

# end class Sync_Attribute

class Attr_RO (Sync_Attribute) :
    """ A Sync attribute that is read-only in the remote tracker.
        We simply take the value in the remote tracker and update
        roundup's attribute if the value has changed.
    """

    def sync (self, syncer, id, remote_issue) :
        v = remote_issue.get (self.remote_name, None)
        if syncer.get (self, id) != v :
            syncer.set (self, id, v)
    # end def sync

# end class Attr_RO

class Attr_Default (Sync_Attribute) :
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

# end class Attr_Default

class Attr_Msg (Sync_Attribute) :
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

# end class Attr_Msg

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
    # end def __init__

    def create (self, cls, ** kw) :
        return self.srv.create \
            (cls, * (self.format (cls, k, v) for k, v in kw.items ()))
    # end def create

    def format (self, cls, key, value) :
        t = self.schema [cls][key]
        if t.startswith ('<roundup.hyperdb.Multilink') :
            return '%s=%s' % (key, ','.join (value))
        else :
            return '%s=%s' % (key, value)
    # end def format

    def get (self, attr, id) :
        if attr.name in self.newvalues [id] :
            return self.newvalues [id][attr.name]
        if attr.name not in self.oldvalues [id] :
            if int (id) > 0 :
                self.oldvalues [id][attr.name] = self.srv.display \
                    ('issue%s' % id, attr.name) [attr.name]
            else :
                t = self.schema ['issue'][attr.name]
                if t.startswith ('<roundup.hyperdb.Multilink') :
                    v = []
                else :
                    v = None
                self.oldvalues [id][attr.name] = v
        return self.oldvalues [id][attr.name]
    # end def get

    def getitem (self, cls, id) :
        """ Get all attributes of an item of the given cls.
            This must not be used for attributes of the issue which we
            are currently syncing. The sync framework keeps a cache of
            to-be-updated attributes, this would bypass the cache.
        """
        return self.srv.display ('%s%s' % (cls, id))
    # end def getitem

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
        for i in issues :
            di = self.srv.display ('issue%s' % i, 'ext_id', 'ext_attributes')
            if di ['ext_id'] != remote_id :
                continue
            if di ['ext_attributes'] :
                m = self.getitem ('msg', di ['ext_attributes'])
                if m ['content'] != remote_issue.as_json () :
                    do_sync = True
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
        if 'ext_attributes' not in self.newvalues [id] and do_sync :
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
            self.srv.set \
                ( 'issue%s' % id
                , * ( self.format ('issue', k, v)
                      for k, v in self.newvalues [id].items ()
                    )
                )
    # end def sync

# end class Syncer
