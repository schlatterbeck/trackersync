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

import xmlrpclib
import json
from   rsclib.autosuper import autosuper

class Remote_Attributes (autosuper) :

    def __init__ (self, record) :
        self.record = record
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

# end class Remote_Attributes

class Sync_Attribute (autosuper) :

    def __init__ (self, roundup_name, remote_name) :
        self.name        = roundup_name
        self.remote_name = remote_name
    # end def __init__

    def sync (self, syncer, id, remote_attrs) :
        raise NotImplementedError ("Needs to be implemented in child class")
    # end def sync

# end class Sync_Attribute

class Attr_RO (Sync_Attribute) :
    """ A Sync attribute that is read-only in the remote tracker.
        We simply take the value in the remote tracker and update
        roundup's attribute if the value has changed.
    """

    def sync (self, syncer, id, remote_attrs) :
        v = remote_attrs.get (self.remote_name, None)
        if syncer.get (self, id) != v :
            syncer.set (self, id, v)
    # end def sync

# end class Attr_RO

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

    def sync (self, syncer, id, remote_attrs) :
        v = remote_attrs.get (self.remote_name, None)
        if not v :
            return
        msgs = syncer.get (self, id)
        for m in sorted (-int (x) for x in msgs) :
            msg = syncer.getitem (self, 'msg', m)
            cnt = msg ['content']
            if len (cnt) < self.hlen + 1 :
                continue
            if cnt.startswith (self.headline) and cnt [self.hlen] == '\n' :
                if cnt [hlen + 1:] == v :
                    return
        id = syncer.create ('msg', content = v)
        msgs.append (id)
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

    def __init__ (self, url, remote_name, attributes, verbose = 0) :
        self.srv = xmlrpclib.ServerProxy (url, allow_none = True)
        self.attributes  = attributes
        self.newvalues   = {}
        self.newcount    = 0
        self.remote_name = remote_name
        self.schema      = dict (self.srv.schema () ['issue'])
        self.tracker     = self.srv.lookup ('ext_tracker', remote_name)
        self.verbose     = verbose
    # end def __init__

    def create (self, cls, ** kw) :
        return self.srv.create (cls, * ("%s=%s" % (k, repr (v)) for k, v in kw))
    # end def create

    def get (self, attr, id) :
        if attr.name not in self.newvalues [id] :
            if int (id) > 0 :
                self.newvalues [id][attr.name] = self.srv.display \
                    ('issue%s' % id, attr.name) [attr.name]
            else :
                t = self.schema [attr.name]
                if t == '<roundup.hyperdb.Multilink>' :
                    v = []
                else :
                    v = None
                self.newvalues [id][attr.name] = v
        return self.newvalues [id][attr.name]
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

    def sync (self, remote_id, remote_attrs) :
        """ We try to find issue with the given remote_id and then call
            the sync framework. If no issue with the given remote_id is
            found, a new issue will be created after all attributes have
            been synced.
        """
        issues = self.srv.filter \
            ( 'issue'
            , []
            , dict (ext_id = remote_id, ext_tracker = self.tracker)
            )
        id = None
        do_sync = False
        for i in issues :
            di = self.srv.display ('issue%s' % i, 'ext_id', 'ext_tracker')
            if di [ext_id] != remote_id :
                continue
            if di.ext_attributes != remote_attrs.as_json () :
                do_sync = True
            id = int (i)
            self.newvalues [id] = di
            break
        else :
            self.newcount += 1
            id = -self.newcount
            self.newvalues [id] = {}
            do_sync = True
        if not do_sync :
            return
        for a in self.attributes :
            a.sync (self, id, remote_attrs)
        if 'ext_id' not in self.newvalues [id] :
            self.newvalues [id]['ext_id'] = remote_id
        self.newvalues [id]['ext_attributes'] = remote_attrs.as_json ()
        if id < 0 :
            if self.verbose :
                print ("create issue: %s" % self.newvalues [id])
            #self.create ('issue', self.newvalues [id])
        else :
            if self.verbose :
                print ("set issue: %s" % self.newvalues [id])
            #self.srv.set \
            #    ( 'issue%s' % id
            #    , * ('%s=%s' % (k, repr (v)) for k, v in self.newvalues [id])
            #    )
    # end def sync

# end class Syncer
