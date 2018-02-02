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

import os
import json
from   rsclib.autosuper import autosuper

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
        """ Add the given local message msg to this remote issue.
            The local message is a dictionary with the message
            properties as keys and the values of the given message.
            The method should return the id of the message just created
            if available. If no ids are supported by the remote system,
            message matching is performed only by other attributes
            (including content).
        """
        raise NotImplementedError ("Needs to be implemented in child class")
    # end def add_message

    def as_json (self, ** kw) :
        """ Only return non-empty values in json dump.
            Optionally update the dumped data with some settings in kw.
        """
        d = dict ((k, v) for k, v in self.record.iteritems () if v)
        d.update ((k, v) for k, v in self.newvalues.iteritems ())
        d.update (kw)
        return json.dumps (d, sort_keys = True, indent = 4)
    # end def as_json

    def attach_file (self, name, type, content) :
        """ Attach a file with the given filename to this remote issue.
            Return the unique filename of the remote issue. Note that
            care must be taken to return the new document id as returned
            by the document_ids method. The local issue will be
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
            issue. By default the local issue only has the MIME-Type
            here named 'type'. But schemas can be changed (e.g. in
            roundup). This should return a dictionary of all local
            attributes to be set.
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
            because we don't have the remote document id in the local
            tracker and need to preserve it in the filename. So we need
            a way to code both, the docid and the remote filename into
            the local filename.
        """
        return namedict
    # end def document_fixer

    def document_ids (self) :
        """ This returns a list of document ids for this issue. Note
            that the IDs need to be unique for this issue. The IDs are
            used to decide if a file is already attached to the local
            issue, no files are compared for the decision. The filenames
            in the local tracker are the IDs returned by this method.
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
            message properties in the local tracker (so the iterator has
            to convert from the attributes of the remote issue). Only
            the 'content' property is mandatory. Note that the given
            properties are used for comparison. So if, e.g., a 'date'
            property is given, this is compared *first*. If no message
            matches the given date, the message is created in the local
            tracker. The content property is generally compared *last*
            as it is most effort.
        """
        raise NotImplementedError ("Needs to be implemented in child class")
    # end def messages

    def set (self, name, value, type) :
        """ Set the given attribute to value
            Note that type is one of 'string', 'date', 'number', 'bool'
            We call conversion methods accordingly if existing.
        """
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

        We can automagically join local multilinks into a separated
        field in the target tracker. This only works for one-direction
        sync To_Remote variants. For this you specify join_multilink
        as True and optionally change the separator from the default.
    """

    def __init__ \
        ( self
        , local_name
        , remote_name    = None
        , only_update    = False
        , only_create    = False
        , l_default      = None
        , r_default      = None
        , map            = None
        , imap           = None
        , strip_prefix   = None
        , join_multilink = False
        , separator      = ', '
        ) :
        self.name           = local_name
        self.remote_name    = remote_name
        self.only_update    = only_update
        self.only_create    = only_create
        self.l_default      = l_default
        self.r_default      = r_default
        self.map            = map
        self.imap           = imap
        self.strip_prefix   = strip_prefix
        self.join_multilink = join_multilink
        self.separator      = separator
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
        return syncer.get_transitive_schema (self.name)
    # end def type

# end class Sync_Attribute

class Sync_Attribute_Check (Sync_Attribute) :
    """ A boolean local attribute used to check if the issue should
        be synced to the remote side. If a remote_name exists, the value
        of it is used to set the local attribute if 'update' is True.
        Otherwise and if 'update' is on, r_default (usually set to
        True) must exist.
        If 'invert' is set, the logic is inverted, it is checked that
        the attribute does *not* exist. Consequently if 'update' is set
        it should update the property to False (or a python equivalent
        that evaluates to a boolean False).
        If an optional value is given, it is checked if the remote value
        matches the given value. If yes and invert is not set, the sync
        is performed. If yes and invert is set, the sync is *not*
        performed.
        The check_sync_callback routine gets the syncer and id as
        parameters and must return a boolean value indicating if syncing
        should be forced. This routine can override a no-sync
        decision.
        Note that update is only performed for new local issues.
        Note that we don't currently support a map / imap.
    """

    def __init__ \
        ( self
        , local_name
        , remote_name = None
        , invert      = False
        , update      = True
        , value       = None
        , ** kw
        ) :
        self.invert    = invert
        self.update    = update
        self.value     = value
        self.__super.__init__ (local_name, remote_name, ** kw)
    # end def __init__

    def sync (self, syncer, id, remote_issue) :
        synccheck = remote_issue.check_sync_callback (syncer, id)
        lv = syncer.get (id, self.name)
        if self.value :
            stop = lv != self.value
        else :
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

class Sync_Attribute_To_Local (Sync_Attribute) :
    """ A Sync attribute that is read-only in the remote tracker.
        We simply take the value in the remote tracker and update
        the local attribute if the value has changed.
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

# end class Sync_Attribute_To_Local

class Sync_Attribute_To_Local_Default (Sync_Attribute) :
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

# end class Sync_Attribute_To_Local_Default

class Sync_Attribute_To_Local_Concatenate (Sync_Attribute) :
    """ A Sync attribute consisting of several read-only attributes in
        the remote tracker.
        We simply take the values in the remote tracker and update
        the local attribute if the value has changed. The remote
        attributes are concatenated (with a separator that defaults to
        '\n'). We don't have default values and no maps. By default the
        name of the fields are prepended to each section, this can be
        turned off by setting add_prefix to False.
    """

    def __init__ \
        ( self
        , local_name
        , remote_names = None
        , delimiter    = '\n'
        , add_prefix   = True
        ) :
        self.name         = local_name
        self.remote_names = remote_names
        self.remote_name  = ', '.join (remote_names) # for debug messages
        self.only_update  = False # only relevant for to remote sync
        self.only_create  = False # only relevant for to remote sync
        self.delimiter    = delimiter
        self.add_prefix   = add_prefix
        self.strip_prefix = False
        self.map = self.imap = None
    # end def __init__

    def sync (self, syncer, id, remote_issue) :
        v = []
        for k in self.remote_names :
            val = remote_issue.get (k, None)
            if not val :
                continue
            if self.add_prefix :
                v.append ('%s:' % k)
            v.append (val)
        rv = self.delimiter.join (v)
        lv = syncer.get (id, self.name)
        if self.no_sync_necessary (lv, rv) :
            return
        syncer.set (id, self.name, rv)
    # end def sync

# end class Sync_Attribute_To_Local_Concatenate

class Sync_Attribute_To_Local_Multilink (Sync_Attribute) :
    """ A Sync attribute that is read-only in the remote tracker.
        We simply take the value in the remote tracker and update
        the local attribute if the value has changed. The only
        complication is that the local value is a multilink but with
        only one (the remote) value.
        Things get more complicated if we have defaults, if both values
        are None and we have an r_default, it is applied.
        If use_r_default is True, a lookup of the item in the Multilink
        will use the given r_default.
    """

    def __init__ \
        ( self
        , local_name
        , remote_name   = None
        , l_default     = None
        , r_default     = None
        , map           = None
        , imap          = None
        , strip_prefix  = None
        , use_r_default = False
        ) :
        self.__super.__init__ \
            ( local_name
            , remote_name
            , False # only_update only relevant for to remote sync
            , False # only_create only relevant for to remote sync
            , l_default
            , r_default
            , map
            , imap
            , strip_prefix
            )
        self.use_r_default   = use_r_default
        self.do_only_default = False
    # end def __init__

    def sync (self, syncer, id, remote_issue) :
        rv = remote_issue.get (self.remote_name, None)
        if rv is None and self.r_default :
            rv = self.r_default
        lnk, attr = self.name.split ('.', 1)
        cl = syncer.get_classname (syncer.default_class, lnk)
        try :
            rv = [syncer.lookup (cl, rv)]
        except KeyError :
            if not self.use_r_default or self.r_default is None :
                raise
            rv = [syncer.lookup (cl, self.r_default)]
        lv = syncer.get (id, self.name)
        if not isinstance (lv, list) :
            lv = [lv]
        if self.do_only_default and lv is not None :
            return
        if self.no_sync_necessary (lv, rv) :
            return
        syncer.set (id, self.name, rv)
    # end def sync

# end class Sync_Attribute_To_Local_Multilink

class Sync_Attribute_To_Local_Multilink_Default \
    (Sync_Attribute_To_Local_Multilink) :

    def __init__ (self, local_name, ** kw) :
        self.__super.__init__ (local_name, ** kw)
        self.do_only_default = True
    # end def __init__

# end class Sync_Attribute_To_Local_Multilink_Default

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
            if self.join_multilink and isinstance (rv, list) :
                rv = [self.imap.get (x, None) for x in rv]
            else :
                rv = self.imap.get (rv, None)
        if self.join_multilink and isinstance (rv, list) :
            rv = self.separator.join (rv)
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

class Trackersync_Syncer (autosuper) :
    """ Synchronisation Framework
        We get the mapping of remote attributes to local attributes.
        The type of attribute indicates the action to perform.
        We need at least an attribute that maps the ext_id attribute to
        the name of the external id attribute in the remote.
    """

    ext_names = {}

    def __init__ (self, remote_name, attributes, opt) :
        self.remote_name     = remote_name
        self.attributes      = attributes
        self.opt             = opt
        self.oldvalues       = {}
        self.newvalues       = {}
        self.newcount        = 0
        self.remote_change   = opt.remote_change
        self.verbose         = opt.verbose
        self.debug           = opt.debug
        self.dry_run         = opt.dry_run
        self.remote_dry_run  = opt.remote_dry_run
        self.oldremote       = {}
        self.update_state    = False # for migration of old roundup schema
        self.__super.__init__ ()
        self.compute_schema   ()
    # end def __init__
    
    def compute_schema (self) :
	""" Compute the schema. The schema is a dictionary of
            dictionaries. The top-level dictionary is indexed by class
            name. The inner dictionaries map attributes names to types.
            The type is either a 2-tuple consisting of 'Link' or
            'Multilink' as the first item and the name of the class as
            the second item. Otherwise the type is just a type name.
            That type name is one of 'string', 'date', 'number', 'bool'.

            This method must compute also the default_class attribute.
        """
	raise NotImplementedError ("Child must implement schema computation")
    # end def compute_schema

    def create (self, cls, ** kw) :
        """ Create local item with given attributes,
            attributes are 'key = value' pairs.
        """
        if self.debug :
            if cls == 'file' :
                print ("srv.create %s %s" % (cls, kw.get('name', '?')))
            else :
                print ("srv.create %s %s" % (cls, kw))
	if self.dry_run :
	    return "9999999"
	return self._create (cls, ** kw)
    # end def create

    def filter (self, classname, searchdict) :
        """ Search for all properties in searchdict and return ids of
            found objects.
        """
	raise NotImplementedError
    # end def filter

    def fix_attributes (self, classname, attrs, create=False) :
        """ Fix transitive attributes. Take care of special cases like
            e.g. roundup's 'content' property
            We distinguish creation and update (transformation might be
            different) via the create flag.
        """
	return attrs
    # end def fix_attributes

    def from_date (self, date) :
        """ Note that we convert date values to a string representation
            of the form %Y-%m-%d.%H:%M:%S where seconds are with 3
            decimal places, e.g.  2015-09-06.13:51:38.840
            The default implementation asumes dates are already in that
            format.
        """
        return date
    # end def from_date

    def get (self, id, name) :
        if name is None :
            return None
        if name in self.newvalues [id] :
            return self.newvalues [id][name]
        if name not in self.oldvalues [id] :
            classname, path = self.split_name (name)
            sid = self.get_existing_id (id)
            if name.startswith ('/') and sid :
                d = {self.default_class : id}
                # Probably only relevant for roundup:
                if 'ext_tracker' in self.schema [classname] :
                    d ['ext_tracker'] = self.tracker
                itms = self.filter (classname, d)
                assert len (itms) <= 1
                if itms :
                    sid = itms [0]
                else :
                    sid = None
            self.oldvalues [id][name] = self.get_transitive_item \
                (classname, path, sid)
        return self.oldvalues [id][name]
    # end def get

    def get_classname (self, classname, name) :
        """ Get the classname of a Link or Multilink property """
        assert isinstance (self.schema [classname][name], tuple)
        return self.schema [classname][name][1]
    # end def get_classname

    def get_default (self, classname, name) :
        """ Get default value for a property 'name' of the given class """
        t = self.schema [classname][name]
        if isinstance (t, tuple) and t [0] == 'Multilink' :
            v = []
        else :
            v = None
        return v
    # end def get_default

    def get_existing_id (self, id) :
        """ An existing id is either a non-empty string that cannot be
            converted to an integer or a positive integer. Non-existing
            ids are negative integers. Note that ids currently must
            evaluate to True in a boolean context (no empty strings or
            None allowed and a 0 for an id is also not allowed).
        """
        assert bool (id)
        try :
            if int (id) < 0 :
                return None
        except ValueError :
            return id
        return id
    # end def get_existing_id

    def get_sync_filename (self, remoteid) :
        return os.path.join (self.opt.syncdir, remoteid)
    # end def get_sync_filename

    def get_transitive_item (self, classname, path, id) :
        """ Return the value of the given transitive item.
            The path is a dot-separated transitive property.
            We return the value of the property or the default value for
            this classname and path.
            
            Note that we convert date values to a string representation
            of the form %Y-%m-%d.%H:%M:%S where seconds are with 3
            decimal places, e.g.  2015-09-06.13:51:38.840
        """
        classname, p, id = self.get_transitive_prop (classname, path, id)
        if id :
            if isinstance (id, list) :
                r = [self.getitem (classname, i, p) [p] for i in id]
                r = ','.join (r)
            else :
                r = self.getitem (classname, id, p) [p]
            if r and self.schema [classname][p] == 'date' :
                return self.from_date (r)
            return r
        return self.get_default (classname, p)
    # end def get_transitive_item

    def get_transitive_prop (self, classname, path, id = None) :
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
                    id = [self.getitem (classname, i, p) [p] for i in id]
                    if id and isinstance (id [0], list) :
                        id = [item for sublist in id for item in sublist]
                else :
                    id = self.getitem (classname, id, p) [p]
            classname = self.get_classname (classname, p)
        p = path [-1]
        return classname, p, id
    # end def get_transitive_prop

    def get_transitive_schema (self, name) :
        """ Return the schema entry of transitive property 'name'.
        """
        classname, path = self.split_name (name)
        classname, prop, id = self.get_transitive_prop (classname, path)
        return self.schema [classname][prop]
    # end def get_transitive_schema

    def get_type (self, classname, name) :
        """ Get type of property 'name', either a scalar or Link or
            Multilink
        """
        t = self.schema [classname][name]
        if isinstance (t, tuple) :
            return t [0]
        return t
    # end def get_type

    def getitem (self, cls, id, *attr) :
        """ Get all or given list of attributes of an item of the given cls.
            This must not be used for attributes of the issue which we
            are currently syncing. The sync framework keeps a cache of
            to-be-updated attributes, this would bypass the cache.
            This returns a dict with a map from attr name to value.
        """
        raise NotImplementedError
    # end def getitem

    def lookup (self, cls, key) :
        """ Look up an item of the given class by key (e.g. name)
            and return the ID
        """
        raise NotImplementedError
    # end def lookup

    def set (self, id, attrname, value) :
        self.newvalues [id][attrname] = value
    # end def set

    def setitem (self, cls, id, ** kw) :
        """ Set attributes of an item of the given cls,
            attributes are 'key = value' pairs.
        """
        if self.debug :
            print ("setitem %s:%s %s" % (cls, id, kw))
        if not self.dry_run :
            return self._setitem (cls, id, ** kw)
    # end def setitem

    def split_name (self, name) :
        if not name :
            return None
        if name.startswith ('/') :
            classname, path = name.strip ('/').split ('/', 1)
        else :
            classname = self.default_class
            path = name
        return classname, path
    # end split_name

    def split_newvalues (self, id) :
        """ Split self.newvalues into attributes belonging to issue and
            attributes belonging to ext_tracker_state. After this
            transformation we have all attributes that are in the
            default_class schema under default_class hierarchy in the
            dictionary.
        """
        classes = { self.default_class : {} }
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
                classes [self.default_class][k] = self.newvalues [id][k]
        return classes
    # end def split_newvalues

    def sync (self, remote_id, remote_issue) :
        """ We try to find issue with the given remote_id and then call
            the sync framework. If no issue with the given remote_id is
            found, a new issue will be created after all attributes have
            been synced.
        """
        do_sync = False
        id = self.sync_status (remote_id, remote_issue)

        if id :
            if self.old_as_json :
                if self.old_as_json != remote_issue.as_json () :
                    do_sync = True
                self.oldremote = json.loads (self.old_as_json)
            else :
                do_sync = True
            self.newvalues [id] = {}
            if id not in self.oldvalues :
                self.oldvalues [id] = {}
        else :
            self.newcount += 1
            id = -self.newcount
            self.oldvalues [id] = {}
            # create new issue only if the remote issue has all required
            # attributes and doesn't restrict them to a subset:
            do_sync = not remote_issue.attributes
            self.newvalues [id] = {}
        self.current_id = id
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
        if id < 0 :
            if not remote_issue.attributes :
                if self.verbose :
                    print ("create issue: %s" % self.newvalues [id])
                classdict = self.split_newvalues (id)
                attr = self.fix_attributes \
                    (self.default_class, classdict [self.default_class], True)
                iid = self.create (self.default_class, ** attr)
                self.current_id = iid
                # update_sync_db must come before update_aux_classes
                # because update_sync_db may update attributes that are
                # written by update_aux_classes
                self.update_sync_db (iid, remote_id, remote_issue)
                del classdict [self.default_class]
                self.update_aux_classes (iid, classdict)
        elif self.newvalues [id] :
            # update_sync_db must come before update_aux_classes
            # because update_sync_db may update attributes that are
            # written by update_aux_classes
            self.update_sync_db (id, remote_id, remote_issue)
            self.update_issue (id)
        if  (   remote_issue.newvalues
            and not self.dry_run
            and not self.remote_dry_run
            ) :
            if self.verbose :
                print ("Update remote:", remote_issue.newvalues)
            remote_issue.update (self)
    # end def sync

    def sync_status (self, remote_id, remote_issue) :
        """ Get the sync status (e.g., old properties of last sync of
            remote issue)
            This method must return the id of the local issue if found.
        """
        id = None
        self.oldremote = {}
        fn = self.get_sync_filename (remote_id)
        j  = None
        try :
            with open (fn, 'r') as f :
                j = f.read ()
        except EnvironmentError :
            pass
        if j :
            self.old_as_json = j
            d  = json.loads (self.old_as_json)
            id = d ['__local_id__']
            # Check that local issue really exists
            # The id may be bogus if sync didn't work or a dry_run was
            # performed
            try :
                self.get_transitive_item (self.default_class, 'id', id)
            except RuntimeError as err :
                if err.message.startswith ('Error 404') :
                    id = None
        return id
    # end def sync_status

    def sync_new_local_issue (self, iid) :
        """ Sync this new local issue (must never have been synced to
            remote side) to the remote side creating it there.
            Never called if sync_new_local_issues (note the 's') below is
            the default method doing nothing.
        """
        remote_issue = self.new_remote_issue ({})
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
            return
        if self.verbose :
            print ("remote_issue.create", remote_issue.newvalues)
        rid = remote_issue.create ()
        if not rid :
            raise ValueError ("Didn't receive correct remote issue on creation")
        self.update_sync_db (iid, rid, remote_issue)
        # We might keep some sync state in the local issue which was
        # updated by update_sync_db above, does nothing if we didn't
        # update self.newvalues [iid]
        self.update_issue (iid)
    # end def sync_new_local_issue

    def sync_new_local_issues (self, new_remote_issue) :
        """ Loop over all local issues that should be synced to the
            remote side but never were synced so far. This needs some
            marks on local issues to determine which issues to sync (we
            *dont't* want to sync *all* local issues to the remote side
            usually!). This is highly application specific and defaults
            to no creation of remote issues.
        """
        pass
    # end def sync_new_local_issues

    def update_aux_classes (self, id, classdict) :
        """ Auxiliary classes, e.g. for KPM an item that links to issue
            and holds additional attributes. 
            All of those must have a Link named 'issue' to the current issue.
        """
        pass
    # end def update_aux_classes

    def update_issue (self, id) :
        if self.verbose :
            print ("set issue %s: %s" % (id, self.newvalues [id]))
        classdict = self.split_newvalues (id)
        attr = self.fix_attributes \
            (self.default_class, classdict [self.default_class])
        if attr :
            self.setitem (self.default_class, id, ** attr)
        del classdict [self.default_class]
        self.update_aux_classes (id, classdict)
    # end def update_issue

    def update_sync_db (self, iid, rid, remote_issue) :
        fn = self.get_sync_filename (rid)
        with open (fn, "w") as f :
            f.write (remote_issue.as_json (__local_id__ = iid))
    # end def update_sync_db

# end class Trackersync_Syncer
Syncer = Trackersync_Syncer
