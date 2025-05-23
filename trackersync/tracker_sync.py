#!/usr/bin/python3
# Copyright (C) 2018-25 Dr. Ralf Schlatterbeck Open Source Consulting.
# Reichergasse 131, A-3411 Weidling.
# Web: http://www.runtux.com Email: office@runtux.com
# All rights reserved
# ****************************************************************************
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# ****************************************************************************

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import

import sys
import os
import json
from   copy             import deepcopy
from   rsclib.autosuper import autosuper
from   rsclib.pycompat  import string_types
from   rsclib.execute   import Log
from   rsclib.pycompat  import string_types

PY2 = sys.version_info [0] == 2

class File_Attachment (autosuper):
    """ Model a local or remote file attachment.
        This has to be subclassed in both, the local and the remote
        backend. The constructor isn't called by the framework code but
        there is a method that gets all file attachments as a list which
        is called by the framework for both, the local and the remote
        backends, so the backend is free to change the signature of the
        constructor. Note that evaluation (especially for the content
        property) may be lazy, therefore some attributes are not
        required in the constructor.
        The issue is the remote or local issue to which this file
        belongs. The name is the remote file name without any '/' in it.
        The id is the id in the local/remote system, it can be a
        path-name with '/' in it (e.g. for the PFIFF backend where we
        get file attachments in a .zip file) and might therefore not be
        useable for a local/remote file name. The type is the MIME
        content-type.
        Note that some backends may create dummy files that are attached
        to the remote issue but are not transmitted for each sync. These
        are expected to already exist at the local issue. We issue a
        warning if such a file is missing from the local issue but do
        not try to attach it.
    """

    def __init__ (self, issue, **kw):
        self.issue   = issue
        self.log     = self.issue.log
        self.id      = kw.get ('id', None)
        self.dummy   = False
        # Some attributes may be @property and unsettable
        for k in 'name', 'type', 'content':
            try:
                setattr (self, k, kw.get (k, None))
            except AttributeError:
                pass
    # end def __init__

    def create (self):
        """ Create this file in the backend.
            Note that self.id may be created on creation.
        """
        raise NotImplementedError ("Needs to be implemented in backend")
    # end def create

# end class File_Attachment

class Message (autosuper):
    """ Model a local or remote message or comment.
        This has to be subclassed in both, the local and the remote
        backend. The constructor isn't called by the framework code but
        there is a method that gets all messages as a list which
        is called by the framework for both, the local and the remote
        backends, so the backend is free to change the signature of the
        constructor. Note that evaluation (especially for the content
        property) may be lazy, therefore some attributes are not
        required in the constructor.
        The issue is the remote or local issue to which this file
        belongs. The id is the id in the local/remote system.
        In addition to the 'content' attribute, the attributes
        'author_id', 'author_name', 'date' are supported. The 'date'
        should be the date of last change. It should be a datetime
        instance.
    """

    properties = ('id', 'author_id', 'author_name', 'date', 'content')

    def __init__ (self, issue, **kw):
        self.issue   = issue
        self.id      = kw.get ('id', None)
        # Some attributes may be @property and unsettable
        for k in self.properties:
            if k in kw:
                try:
                    setattr (self, k, kw.get (k, None))
                except AttributeError:
                    pass
        if getattr (self, 'date', None):
            # Don't store dates with microseconds for comparison
            # This is not supported by most backend formats
            if self.date.microsecond:
                self.date = self.date.replace (microsecond = 0)
    # end def __init__

    def copy (self):
        props = dict ((p, getattr (self, p)) for p in self.properties)
        return self.__class__ (self.issue, ** props)
    # end def copy

# end class Message

class Backend_Common (Log):
    """ Common methods of Syncer and Remote_Issue
    """

    # Needs to be overridden in child. Note that if the signature of
    # File_Attachment constructor changes, the attach_file method below
    # must be reimplemented in child.
    File_Attachment_Class = File_Attachment
    Message_Class         = Message

    def __init__ (self, *args, **kw):
        self.attachments    = None
        self.issue_comments = None
        self.__super.__init__ (*args, **kw)
        # Use syncer.log if available
        if getattr (self, 'syncer', None):
            self.log = self.syncer.log
    # end def __init__

    def _attach_file (self, cls, other_file, name = None):
        """ Attach file to this issue from other_file
            Note that caller of this method must deal with it returning
            None which happens whenever the file is not available for
            sync (e.g. when we're dealing with an imported .zip file
            that contains only the most recent file attachments).
            The given name is the name of the local attribute in the
            local database.
        """
        if other_file.dummy:
            self.log.error \
                ( "Re-attach dummy file %s: deleted in local tracker?"
                % other_file.name
                )
            return None
        f = cls \
            ( self
            , name    = other_file.name
            , type    = other_file.type
            , content = other_file.content
            )
        return f
    # end def _attach_file

    def attach_file (self, other_file, name = None):
        """ Create new file from other side file.
            The name is the name of the attribute in the issue.
            Note that depending on the backend we might not be able to
            use the default constructor.
            The file is *not* persisted yet, this is done by the create
            method of the generated file.
            Note that some backend my need additionale attributes of a
            file and will therefore re-implement this method and the
            corresponding File_Attachment class.
            Also persisting this is left to the backend.
            Note that backend implementation must honor self.dry_run.

            This usually calls _attach_file above and if the returned
            file is not None calls the create method on the file object
            returned by _attach_file.
        """
        raise NotImplementedError ("Needs to be implemented in child class")
    # end def attach_file

    def file_attachments (self, name = None):
        """ Returns a list of File_Attachment_Class objects that belong
            to this issue. The name is the name of the attribute in the
            issue. The name may be hardcoded for many backends.
            Note that for a non-existing issue the special case of an
            empty attachment list is taken care of in the Syncer.
        """
        raise NotImplementedError ("Needs to be implemented in child class")
    # end def file_attachments

    def file_exists (self, other_name):
        """ Sometimes name mangling must happen. This allows the
            derived class to check if the file with the given
            other_name already exists. Called by Sync_Attribute_Files.
            Default is no mangling.
        """
        if getattr (self, 'file_by_name', None):
            return other_name in self.file_by_name
        elif not self.file_attachments ():
            return False
        else:
            self.file_by_name = dict \
                ((x.name, x) for x in self.file_attachments ())
        return other_name in self.file_by_name
    # end def file_exists

    def get_messages (self):
        """ Returns the dictionary of messages/comments for this issue
            Messages are in a dict by message ID. This allows easier
            deletion of messages.
        """
        raise NotImplementedError ("Needs to be implemented in child class")
    # end def

    def append_message (self, m):
        """ Append given message m to local messages.
            Note that the message m is a remote message and will
            probably have no local ID.
        """
        raise NotImplementedError ("Needs to be implemented in child class")
    # end def append_message

    def delete_message (self, id):
        """ Delete the message with the given ID
        """
        raise NotImplementedError ("Needs to be implemented in child class")
    # end def delete_message

# end def Backend_Common

class Remote_Issue (Backend_Common):
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

    multilevel  = None
    # Some backends can decide if an issue is assigned to the supplier
    # e.g. in KPM the issue may be in our mailbox or not.
    is_assigned = True

    def __init__ (self, record, sync_attributes = {}):
        self.record     = record
        self.newvalues  = {}
        self.dirty      = False
        self.attributes = sync_attributes
        self.__super.__init__ ()
    # end def __init__

    def __getattr__ (self, name):
        try:
            return self [name]
        except KeyError as exc:
            raise AttributeError (exc)
    # end def __getattr__

    def __getitem__ (self, name):
        if name is None:
            raise KeyError (name)
        if self.multilevel:
            names = name.split ('.')
            nitem = self.newvalues
            item  = self.record
            for n in names:
                if nitem is not None:
                    if n in nitem:
                        nitem = nitem [n]
                    else:
                        nitem = None
                if item is not None:
                    if n in item:
                        item = item [n]
                    else:
                        item = None
                if item is None and nitem is None:
                    raise KeyError ("Not found: %s" % name)
            if nitem is not None:
                return nitem
            return item
        if name in self.newvalues:
            return self.newvalues [name]
        return self.record [name]
    # end def __getitem__

    def __unicode__ (self):
        r = []
        for k in sorted (self.record):
            v = self.record [k]
            r.append ("%(k)s: >%(v)s<" % locals ())
        return '\n'.join (r)
    # end def __unicode__
    if PY2:
        def __str__ (self):
            return unicode (self).encode ('utf-8')
        # end def __str__
    else:
        __str__ = __unicode__
    __repr__ = __str__

    def add_message (self, msg):
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

    def as_json (self, ** kw):
        """ Only return non-empty values in json dump.
            Optionally update the dumped data with some settings in kw.
        """
        d = {}
        for k in self.record:
            v = self.record [k]
            if v:
                d [k] = v
        d.update (self.newvalues)
        d.update (kw)
        return json.dumps (d, sort_keys = True, indent = 4)
    # end def as_json

    def check_sync_callback (self, syncer, id):
        """ Override a no-sync decision. If this returns False, a sync
            for this issue is performed, even if other no-sync checks of
            a Sync_Attribute_Check fail.
        """
        return True
    # end def check_sync_callback

    def document_fixer (self, namedict):
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

    def create (self):
        """ Create new remote issue from data here. This is called by
            the sync framework *after* all attributes have been set by
            the sync. Similar to update but creating a new remote issue.
        """
        raise NotImplementedError ("Needs to be implemented in child class")
    # end def create

    def equal (self, lv, rv):
        """ Comparison method for remote and local value.
            By default we only make newlines equivalent for both issues
            (if they're both of string type). But some backends need to
            take encoding issues (utf-8 vs latin-1) into account.
        """
        if isinstance (lv, string_types) and isinstance (rv, string_types):
            lv = lv.replace ('\r\n', '\n')
            rv = rv.replace ('\r\n', '\n')
        return lv == rv
    # end def equal

    def get (self, name, default = None):
        try:
            return self [name]
        except KeyError:
            return default
    # end def get

    def set (self, name, value, type):
        """ Set the given attribute to value
            Note that type is one of 'string', 'date', 'number', 'bool'
            We call conversion methods accordingly if existing.
        """
        conv = None
        if type:
            conv = getattr (self, 'convert_%s' % type, None)
        if conv:
            value = conv (value)
        if self.multilevel:
            names = name.split ('.')
            item  = self.newvalues
            # Copy over the current value to ease later update
            if self.record.get (names [0]) and names [0] not in item:
                item [names [0]] = deepcopy (self [names [0]])
            for n in names [:-1]:
                if n not in item:
                    self.dirty = True
                    item [n] = {}
                item = item [n]
            if item.get (names [-1], None) != value:
                self.dirty = True
            item [names [-1]] = value
        else:
            if self.newvalues.get (name, None) != value:
                self.dirty = True
            self.newvalues [name] = value
    # end def set
    __setitem__ = set

    def strip_prefix (self, propname, prefix):
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
        if self.multilevel:
            raise NotImplementedError \
                ("Multilevel not implemented for strip_prefix")
        if  (   propname in self.record
            and propname not in self.newvalues
            and v.startswith (prefix) 
            ):
            l = len (prefix)
            v = v [l:]
            self.record [propname] = v
    # end def strip_prefix

    def update (self, syncer):
        """ Update remote issue tracker with self.newvalues.
            This is expected to *not* update the syncdb anymore!
        """
        raise NotImplementedError ("Needs to be implemented in child class")
    # end def update

# end class Remote_Issue

class Sync_Attribute (autosuper):
    """ Sync a property from/to a remote tracker.
        If only_update is specified, the sync is run only in the update
        phase (when the remote issue is already existing).
        If only_create is specified, the sync is run only for creation
        of the remote issue (when it doesn't exist yet).
        The l_only_update flag indicates that for To_Local sync variants
        the sync should only be run if the local issue exists.
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

        Note that local_prefix is used only in To_Local variants not in
        Two_Way (due to resulting roundtrip problems).

        The allowed_chars are the characters allowed in the local
        variant. The sync automagically replaces the non-allowed
        characters with '_'. Note that currently this transformation is
        only done for the To_Local variants of Sync_Attributes.
    """
    # If to_local is True no sync is done if the issue originates
    # locally (i.e. it is not yet created on the remote side)
    to_local = False

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
        , local_prefix   = None
        , l_only_update  = False
        , allowed_chars  = None
        , local_unset    = None
        , r_unreadable   = None
        , only_assigned  = False
        , after_create   = False
        ):
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
        self.local_prefix   = local_prefix
        self.l_only_update  = l_only_update
        self.allowed_chars  = allowed_chars
        # This is used in the variants that read something from the
        # remote side: We can specify here a value that should be used
        # if the remote issue is unreadable (e.g. due to permissions)
        self.r_unreadable   = r_unreadable
        # only used for Sync_Attribute_To_Local_Default:
        self.local_unset    = local_unset
        # Only run this sync attribute if the remote issue is assigned to us
        self.only_assigned  = only_assigned
        self.after_create   = after_create
        if not self.imap and self.map:
            self.imap = dict ((v, k) for k, v in  map.items ())
        if not self.map and self.imap:
            self.map  = dict ((v, k) for k, v in imap.items ())
    # end def __init__

    def no_sync_necessary (self, lv, rv, remote_issue):
        l_def = getattr (self, 'l_default', None)
        r_def = getattr (self, 'r_default', None)
        if self.map:
            # Both maps need to disagree for non-equal -- this prevents
            # ping-pong updates in case the mappings are not fully
            # consistent
            # For multistring properties we need to map each item in the
            # list, the items are already prefix-mapped, so we don't
            # need to compare both mappings.
            if isinstance (lv, list):
                assert isinstance (rv, list)
                tmplv = lv
                tmprv = rv
                if self.prefix:
                    tmplv = [l for l in lv if l.startswith (self.prefix)]
                    tmprv = [r for r in rv if r.startswith (self.prefix)]
                equal = tmplv == tmprv
            else:
                equal = \
                    (  self.map.get  (lv, l_def) == rv
                    or self.imap.get (rv, None)  == lv
                    )
        else:
            equal = remote_issue.equal (lv, rv)
        return  (   equal
                and (   not (lv is None and rv is None)
                    or  not (l_def or r_def)
                    )
                )
    # end def no_sync_necessary

    def sync (self, syncer, id, remote_issue):
        """ Needs to be implemented in child class.
            Note that a sync method may return a value != None in which
            case the sync for this Issue is not done. Useful for checks
            if a sync for a particular issue should happen.
        """
        pass
    # end def sync

    def type (self, syncer):
        if self.name is None:
            return None
        return syncer.get_transitive_schema (self.name)
    # end def type

# end class Sync_Attribute

class Sync_Attribute_Check (Sync_Attribute):
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
        ):
        self.invert    = invert
        self.update    = update
        self.value     = value
        self.__super.__init__ (local_name, remote_name, ** kw)
    # end def __init__

    def sync (self, syncer, id, remote_issue):
        synccheck = remote_issue.check_sync_callback (syncer, id)
        lv = syncer.get (id, self.name)
        if self.value:
            stop = lv != self.value
        else:
            stop = not lv
        if self.invert:
            stop = not stop
        # Stop sync if following condition is true:
        if stop and (isinstance (id, type ('')) or id > 0) and synccheck:
            return True
        if self.update and lv is None:
            rv = remote_issue.get (self.remote_name, self.r_default)
            syncer.set (id, self.name, rv)
    # end def sync

# end class Sync_Attribute_Check

class Sync_Attribute_Check_Remote (Sync_Attribute):
    """ A boolean remote attribute used to check if the issue should
        be synced. Note that no sync is done, only the check of this
        attribute is performed. The local_name should be None.

        If 'invert' is set, the logic is inverted, it is checked that
        the attribute does *not* exist. Consequently if 'update' is set
        it should update the property to False (or a python equivalent
        that evaluates to a boolean False).
        If an optional value is given, it is checked if the remote value
        matches the given value. If yes and invert is not set, the sync
        is performed. If yes and invert is set, the sync is *not*
        performed.
        Note that we don't currently support a map / imap.
    """
    to_local = True

    def __init__ \
        ( self
        , local_name
        , remote_name = None
        , invert      = False
        , value       = None
        , ** kw
        ):
        self.invert    = invert
        self.value     = value
        self.__super.__init__ (local_name, remote_name, ** kw)
        assert self.remote_name is not None
    # end def __init__

    def sync (self, syncer, id, remote_issue):
        rv = remote_issue.get (self.remote_name, None)

        if self.value:
            stop = rv != self.value
        else:
            stop = not rv
        if self.invert:
            stop = not stop
        if stop:
            return True
    # end def sync

# end class Sync_Attribute_Check_Remote

class Sync_Attribute_Files (Sync_Attribute):
    """ A Sync attribute that sync the files attached to a remote issue
        to the local issue.
        If the optional prefix is given, files with a name starting with
        the given prefix are synchronized *to* the remote system. In
        case the prefix is empty (zero-length string), *all* files not
        coming from the remote tracker are created in the remote
        tracker. Note that such a setup is risky if remote files are not
        identified correctly another file could be created during each
        sync. In addition collisions of filenames may happen where a
        file with the same name is created on both sides and never
        synced.
    """

    def __init__ (self, prefix = None, local_name = 'files', ** kw):
        self.prefix = prefix
        self.__super.__init__ (local_name = local_name, ** kw)
    # end def __init__

    def sync (self, syncer, id, remote_issue):
        if self.only_assigned and not remote_issue.is_assigned:
            return
        if self.l_only_update and syncer.get_existing_id (id) is None:
            return
        lfiles = syncer.file_attachments (id, self.name)
        rfiles = remote_issue.file_attachments (self.remote_name)
        lnames = dict ((x.name, x) for x in lfiles)
        rnames = dict ((x.name, x) for x in rfiles)

        for n in rnames:
            if not syncer.file_exists (id, n):
                syncer.attach_file (id, rnames [n], self.name)

        if self.prefix is not None and not syncer.remote_dry_run:
            exists = remote_issue.file_exists
            for n in lnames:
                if n.startswith (self.prefix) and not exists (n):
                    remote_issue.attach_file (lnames [n], self.remote_name)
    # end def sync

# end class Sync_Attribute_Files

class Sync_Attribute_To_Local (Sync_Attribute):
    """ A Sync attribute that is read-only in the remote tracker.
        We simply take the value in the remote tracker and update
        the local attribute if the value has changed.
        Things get more complicated if we have defaults, if both values
        are None and we have an r_default, it is applied.
    """
    to_local = True

    def sync (self, syncer, id, remote_issue):
        if self.only_assigned and not remote_issue.is_assigned:
            return
        if self.l_only_update and syncer.get_existing_id (id) is None:
            return
        rv = remote_issue.get (self.remote_name, None)
        # Check if there is a configured value we should use when remote
        # issue is unreadable, determine if remote issue has an
        # attribute __readable__ which is set to a False boolean value.
        if  (   self.r_unreadable is not None
            and not remote_issue.get ('__readable__', True)
            ):
            rv = self.r_unreadable
        if isinstance (rv, string_types):
            if self.allowed_chars:
                new_rv = []
                for c in rv:
                    if c in self.allowed_chars:
                        new_rv.append (c)
                    else:
                        new_rv.append ('_')
                rv = ''.join (new_rv)
            if self.local_prefix:
                rv = self.local_prefix + rv
        lv = syncer.get (id, self.name)
        if self.no_sync_necessary (lv, rv, remote_issue):
            return
        if self.imap:
            rv = self.imap.get (rv, self.r_default)
        elif rv is None and self.r_default:
            rv = self.r_default
        syncer.set (id, self.name, rv)
    # end def sync

# end class Sync_Attribute_To_Local

class Sync_Attribute_To_Local_Default (Sync_Attribute):
    """ A default, only set if the current value is not set.
        Very useful for required attributes on creation.
        This is set from the remote attribute and in case this is also
        not set, a default can be specified in the constructor.
    """
    to_local = True

    def sync (self, syncer, id, remote_issue):
        if self.only_assigned and not remote_issue.is_assigned:
            return
        if self.l_only_update and syncer.get_existing_id (id) is None:
            return
        v = remote_issue.get (self.remote_name)
        if self.imap:
            v = self.imap.get (v, self.r_default)
        elif v is None and self.r_default:
            v = self.r_default
        if isinstance (v, string_types) and self.local_prefix:
            v = local_prefix + v
        rv = syncer.get (id, self.name)
        if rv is None or self.local_unset and rv == self.local_unset:
            syncer.set (id, self.name, v)
    # end def sync

# end class Sync_Attribute_To_Local_Default

class Sync_Attribute_To_Local_Concatenate (Sync_Attribute):
    """ A Sync attribute consisting of several read-only attributes in
        the remote tracker.
        We simply take the values in the remote tracker and update
        the local attribute if the value has changed. The remote
        attributes are concatenated (with a separator that defaults to
        '\n'). We don't have default values and no maps. By default the
        name of the fields are prepended to each section, this can be
        turned off by setting add_prefix to False.
    """
    to_local = True

    def __init__ \
        ( self
        , local_name
        , remote_names    = None
        , delimiter       = '\n'
        , short_delimiter = ' '
        , field_prefix    = ''
        , field_postfix   = ':\n'
        , add_prefix      = True
        , l_only_update   = False
        , name_map        = {}
        , content_map     = {}
        , only_assigned   = False
        , after_create    = False
        ):
        self.name            = local_name
        self.remote_names    = remote_names
        self.remote_name     = ', '.join (remote_names) # for debug messages
        self.only_update     = False # only relevant for to remote sync
        self.only_create     = False # only relevant for to remote sync
        self.delimiter       = delimiter
        self.short_delimiter = short_delimiter
        self.field_prefix    = field_prefix
        self.field_postfix   = field_postfix
        self.add_prefix      = add_prefix
        self.strip_prefix    = False
        self.l_only_update   = l_only_update
        self.map = self.imap = None
        self.name_map        = name_map
        self.content_map     = content_map
        self.only_assigned   = only_assigned
        self.after_create    = after_create
    # end def __init__

    def sync (self, syncer, id, remote_issue):
        if self.only_assigned and not remote_issue.is_assigned:
            return
        if self.l_only_update and syncer.get_existing_id (id) is None:
            return
        v = []
        for n, k in enumerate (self.remote_names):
            val = remote_issue.get (k, None)
            if not val:
                continue
            name = self.name_map.get (k, k)
            if name is None:
                v.append (self.short_delimiter)
            else:
                if n:
                    v.append (self.delimiter)
                if self.add_prefix:
                    if self.field_prefix:
                        v.append (self.field_prefix)
                    v.append (name)
                    if self.field_postfix:
                        v.append (self.field_postfix)
            if k in self.content_map:
                val = self.content_map [k].get (val, val)
            v.append (str (val))
        rv = ''.join (v)
        lv = syncer.get (id, self.name)
        if self.no_sync_necessary (lv, rv, remote_issue):
            return
        syncer.set (id, self.name, rv)
    # end def sync

# end class Sync_Attribute_To_Local_Concatenate

class Sync_Attribute_To_Local_Multilink (Sync_Attribute):
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
    to_local = True

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
        , l_only_update = False
        , l_only_create = False
        , only_assigned = False
        , after_create  = False
        ):
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
            , l_only_update = l_only_update
            , only_assigned = only_assigned
            , after_create  = after_create
            )
        self.l_only_create   = l_only_create
        self.use_r_default   = use_r_default
        self.do_only_default = False
    # end def __init__

    def sync (self, syncer, id, remote_issue):
        if self.only_assigned and not remote_issue.is_assigned:
            return
        if syncer.get_existing_id (id) is None:
            if self.l_only_update:
                return
        else:
            if self.l_only_create:
                return
        rv = remote_issue.get (self.remote_name, None)
        if rv is None and self.r_default:
            rv = self.r_default
        lnk, attr = self.name.split ('.', 1)
        cl = syncer.get_classname (syncer.default_class, lnk)
        try:
            rv = [syncer.lookup (cl, rv)]
        except KeyError:
            if not self.use_r_default or self.r_default is None:
                raise
            rv = [syncer.lookup (cl, self.r_default)]
        lv = syncer.get (id, self.name)
        if self.do_only_default and lv is not None:
            return
        if not isinstance (lv, list):
            lv = [lv]
        if self.no_sync_necessary (lv, rv, remote_issue):
            return
        syncer.set (id, self.name, rv)
    # end def sync

# end class Sync_Attribute_To_Local_Multilink

class Sync_Attribute_To_Local_Multilink_Default \
    (Sync_Attribute_To_Local_Multilink):

    def __init__ (self, local_name, ** kw):
        self.__super.__init__ (local_name, ** kw)
        self.do_only_default = True
    # end def __init__

# end class Sync_Attribute_To_Local_Multilink_Default

class Sync_Attribute_To_Local_Multistring (Sync_Attribute_To_Local):
    """ A variant that synchronizes a single attribute at the remote
        side to a Multi-String value locally. It uses a prefix and
        removes all local strings with this prefix before it stores the
        new values. Equality is determined by sorting the strings before
        comparing.
        Note that not all backends know of Multistring values. An
        example backend that supports it is Jira.
    """

    def __init__ \
        ( self
        , local_name
        , remote_name   = None
        , l_default     = None
        , r_default     = None
        , map           = None
        , imap          = None
        , prefix        = None
        , l_only_update = False
        , allowed_chars = None
        , r_unreadable  = None
        , only_assigned = False
        , after_create  = False
        ):
        self.__super.__init__ \
            ( local_name
            , remote_name
            , False # only_update only relevant for to remote sync
            , False # only_create only relevant for to remote sync
            , l_default
            , r_default
            , map
            , imap
            , strip_prefix  = None
            , l_only_update = l_only_update
            , allowed_chars = allowed_chars
            , r_unreadable  = r_unreadable
            , only_assigned = only_assigned
            , after_create  = after_create
            )
        self.prefix = prefix
        if not prefix:
            raise ValueError ("The prefix is required")
        self.do_only_default = False
    # end def __init__

    def _replace (self, s):
        new_rv = []
        for c in s:
            if c in self.allowed_chars:
                new_rv.append (c)
            else:
                new_rv.append ('_')
        return ''.join (new_rv)
    # end def _replace

    def sync (self, syncer, id, remote_issue):
        if self.only_assigned and not remote_issue.is_assigned:
            return
        if self.l_only_update and syncer.get_existing_id (id) is None:
            return
        rval = remote_issue.get (self.remote_name, None)
        # Check if there is a configured value we should use when remote
        # issue is unreadable, determine if remote issue has an
        # attribute __readable__ which is set to a False boolean value.
        if  (   self.r_unreadable is not None
            and not remote_issue.get ('__readable__', True)
            ):
            rval = self.r_unreadable
        if isinstance (rval, list):
            if self.imap:
                rval = [self.imap.get (r, r) for r in rval]
            if self.allowed_chars:
                rval = [self._replace (r) for r in rval]
        else:
            if self.imap:
                rval = self.imap.get (rval, self.r_default)
            elif rval is None and self.r_default:
                rval = self.r_default
        # Can't sync None values to local
        if rval is None:
            return
        if isinstance (rval, string_types) and self.allowed_chars:
            rval = self._replace (rval)
        lv = syncer.get (id, self.name)
        if isinstance (lv, list):
            lv = list (sorted (lv))
            # Keep values without our prefix
            rv = [k for k in lv if not k.startswith (self.prefix)]
        else:
            assert not rv
            rv = []
        if self.prefix:
            if isinstance (rval, list):
                rval = [self.prefix + r for r in rval]
            else:
                rval = [self.prefix + str (rval)]
        rv.extend (rval)
        rv = list (sorted (rv))
        if self.no_sync_necessary (lv, rv, remote_issue):
            return
        if self.do_only_default and lv is not None:
            return
        syncer.set (id, self.name, rv)
    # end def sync

# end class Sync_Attribute_To_Local_Multistring

class Sync_Attribute_To_Local_Multistring_Default \
    (Sync_Attribute_To_Local_Multistring):

    def __init__ (self, local_name, ** kw):
        self.__super.__init__ (local_name, ** kw)
        self.do_only_default = True
    # end def __init__

# end class Sync_Attribute_To_Local_Multistring_Default

class Sync_Attribute_To_Remote (Sync_Attribute):
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

    def _sync (self, syncer, id, remote_issue):
        # Never sync something to remote if local issue not yet created.
        # Default values of local issue are assigned during creation, so
        # we can't sync these to the remote site during this sync (they
        # would get empty values).
        if syncer.get_existing_id (id) is None:
            return None, None, True
        rv = remote_issue.get (self.remote_name, None)
        lv = syncer.get (id, self.name)
        nosync = self.no_sync_necessary (lv, rv, remote_issue)
        if self.imap:
            if self.join_multilink and isinstance (rv, list):
                rv = [self.imap.get (x, None) for x in rv]
            else:
                rv = self.imap.get (rv, None)
        if self.join_multilink and isinstance (rv, list):
            rv = self.separator.join (rv)
        if self.map:
            lv = self.map.get (lv, self.l_default)
        if lv is None and rv is None and self.l_default is not None:
            lv = self.l_default
        return lv, rv, nosync
    # end def _sync

    def sync (self, syncer, id, remote_issue):
        if self.only_assigned and not remote_issue.is_assigned:
            return
        lv, rv, nosync = self._sync (syncer, id, remote_issue)
        if not nosync:
            remote_issue.set (self.remote_name, lv, self.type (syncer))
    # end def sync

# end class Sync_Attribute_To_Remote

class Sync_Attribute_Multi_To_Remote (Sync_Attribute):
    """ Unconditionally synchronize a set of local attribute to the
        remote tracker. Similar to Sync_Attribute_To_Remote but with
        multiple local attributes. A map *has* to be specified, it is
        not a dictionary but a (order matters! see below) table. It
        takes a tuple for the local attributes and a single value for
        the remote attribute.  The value None can be used as a wildcard.
        The *first* match wins.
        Note that if l_default is given it must be an already-mapped
        value from the value-space of remote values!
    """

    def __init__ (self, local_names, map, **kw):
        self.local_names = local_names
        self.__super.__init__ (local_names [0], **kw)
        # 'map' is initialized to None by super call
        self.map         = map
    # end def __init__

    def _check_pattern (self, lv, lvpattern):
        """ Match local value (tuple) against pattern, pattern may
            contain the value None for wildcard. Return True if
            matching, False otherwise
        """
        assert len (lv) == len (lvpattern)
        for v, p in zip (lv, lvpattern):
            if p is not None and v != p:
                return False
        return True
    # end def _check_pattern

    def _sync (self, syncer, id, remote_issue):
        # Never sync something to remote if local issue not yet created.
        # Default values of local issue are assigned during creation, so
        # we can't sync these to the remote site during this sync (they
        # would get empty values).
        if syncer.get_existing_id (id) is None:
            return None, None, True
        rv = remote_issue.get (self.remote_name, None)
        x  = syncer.get (id, 'resolution.name')
        lv = tuple (syncer.get (id, n) for n in self.local_names)
        for lvpattern, rr in self.map:
            if self._check_pattern (lv, lvpattern):
                lv = rr
                break
        else:
            raise ValueError ("Not found: %s" % lv)
        # Note that l_default must be an already-mapped value here, i.e.
        # from the value-space of the remote values.
        if lv is None and rv is None and self.l_default is not None:
            lv = self.l_default
        nosync = (lv == rv)
        return lv, rv, nosync
    # end def _sync

    def sync (self, syncer, id, remote_issue):
        if self.only_assigned and not remote_issue.is_assigned:
            return
        lv, rv, nosync = self._sync (syncer, id, remote_issue)
        if not nosync:
            remote_issue.set (self.remote_name, lv, self.type (syncer))
    # end def sync

# end class Sync_Attribute_Multi_To_Remote

class Sync_Attribute_To_Remote_If_Dirty (Sync_Attribute_To_Remote):
    """ Like Sync_Attribute_To_Remote but only if the remote issue has
        already changes. Used for timestamps or current owner attributes
        that must be synced to the remote site but only if something
        relevant changed.
    """

    def sync (self, syncer, id, remote_issue):
        if self.only_assigned and not remote_issue.is_assigned:
            return
        if remote_issue.dirty:
            self.__super.sync (syncer, id, remote_issue)
    # end def sync

# end class Sync_Attribute_To_Remote_If_Dirty

class Sync_Attribute_To_Remote_Default (Sync_Attribute_To_Remote):
    """ A default, only set if the current value is not set.
        Very useful for required attributes on creation.
        This is set from the local attribute and in case this is also
        not set, a default can be specified in the constructor.
        Very similar to Sync_Attribute_To_Remote but only synced if the
        remote attribute is empty.
    """

    def sync (self, syncer, id, remote_issue):
        if self.only_assigned and not remote_issue.is_assigned:
            return
        lv, rv, nosync = self._sync (syncer, id, remote_issue)
        # Note that rv != remote_issue.get in case we do have self.imap
        # in that case we need to check if the *original* attribute
        # is set if it doesn't reverse map to a known value.
        if  (   not nosync
            and not rv
            and not remote_issue.get (self.remote_name, None)
            and lv
            ):
            type = None
            if self.name:
                type = self.type (syncer)
            remote_issue.set (self.remote_name, lv, type)
    # end def sync

# end class Sync_Attribute_To_Remote_Default

class Sync_Attribute_Two_Way (Sync_Attribute):
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

    def sync (self, syncer, id, remote_issue):
        if self.only_assigned and not remote_issue.is_assigned:
            return
        rv      = remote_issue.get (self.remote_name, None)
        # Check if there is a configured value we should use when remote
        # issue is unreadable, determine if remote issue has an
        # attribute __readable__ which is set to a False boolean value.
        if  (   self.r_unreadable is not None
            and not remote_issue.get ('__readable__', True)
            ):
            rv = self.r_unreadable
        lv      = syncer.get (id, self.name)
        nosync  = self.no_sync_necessary (lv, rv, remote_issue)
        old     = syncer.oldremote.get (self.remote_name, None)
        changed = old != rv
        if self.map:
            lv = self.map.get (lv, self.l_default)
        if self.imap:
            rv = self.imap.get (rv, self.r_default)
        if nosync:
            return
        if rv is None and lv is None:
            if self.l_default is not None:
                lv = self.l_default # this is synced *to* remote
            if self.r_default is not None:
                rv = self.r_default # this is synced *to* local
        # check if remote changed since last sync;
        # Update remote issue if we have r_default and rv is not set
        if  (  (changed and (rv or not self.r_default))
            or (syncer.remote_change and rv is not None)
            ):
            if rv is None:
                print ("WARN: Would set issue%s %s to None" % (id, self.name))
                syncer.log.warn \
                    ("Would set issue%s %s to None" % (id, self.name))
            else:
                syncer.set (id, self.name, rv)
        else:
            remote_issue.set (self.remote_name, lv, self.type (syncer))
    # end def sync

# end class Sync_Attribute_Two_Way

class Local_Issue (Backend_Common, autosuper):

    def __init__ (self, syncer, id, opt, **kw):
        self.syncer        = syncer
        self.newvalues     = {}
        self.oldvalues     = {}
        self.id            = id
        self.opt           = opt
        self.dirty         = False
        self.default_class = syncer.default_class
        self.__super.__init__ (**kw)
    # end def __init__

    def __getattr__ (self, name):
        return getattr (self.syncer, name)
    # end def __getattr__

    def get (self, name):
        name = self.syncer.get_name_translation (self.default_class, name)
        if name is None:
            return None
        if name in self.newvalues:
            return self.newvalues [name]
        if name not in self.oldvalues:
            classname, path = self.split_name (name)
            sid = self.syncer.get_existing_id (self.id)
            if name.startswith ('/') and sid:
                d = {self.default_class: self.id}
                # Probably only relevant for roundup:
                if 'ext_tracker' in self.schema [classname]:
                    d ['ext_tracker'] = self.tracker
                itms = self.filter (classname, d)
                assert len (itms) <= 1
                if itms:
                    sid = itms [0]
                else:
                    sid = None
            self.oldvalues [name] = self.get_transitive_item \
                (classname, path, sid)
        return self.oldvalues [name]
    # end def get

    def set (self, attrname, value):
        name = self.syncer.get_name_translation (self.default_class, attrname)
        self.newvalues [name] = value
        self.dirty = True
    # end def set

    def split_newvalues (self):
        """ Split self.newvalues into attributes belonging to issue and
            attributes belonging to ext_tracker_state. After this
            transformation we have all attributes that are in the
            default_class schema under default_class hierarchy in the
            dictionary.
        """
        classes = { self.default_class: {} }
        if 'ext_tracker_state' in self.schema:
            classes ['ext_tracker_state'] = {}
        for k in self.newvalues:
            if k.startswith ('/'):
                # FIXME: Check if rest is composite
                classname, rest = k.strip ('/').split ('/', 1)
                if classname not in classes:
                    classes [classname] = {}
                classes [classname][rest] = self.newvalues [k]
            elif k in self.ext_names:
                classes ['ext_tracker_state'][k] = self.newvalues [k]
            else:
                # FIXME: Check if k is composite
                classes [self.default_class][k] = self.newvalues [k]
        return classes
    # end def split_newvalues

# end class Local_Issue

class Trackersync_Syncer (Log):
    """ Synchronisation Framework
        We get the mapping of remote attributes to local attributes.
        The type of attribute indicates the action to perform.
        We need at least an attribute that maps the ext_id attribute to
        the name of the external id attribute in the remote.
    """

    ext_names = {}

    # Change in derived class if necessary
    Local_Issue_Class = Local_Issue

    def __init__ (self, remote_name, attributes, opt, cfg, **kw):
        self.remote_name     = remote_name
        self.attributes      = attributes
        self.opt             = opt
        self.cfg             = cfg
        self.localissues     = {} # By id
        self.newcount        = 0
        self.oldremote       = {}
        self.update_state    = False # for migration of old roundup schema
        self.__super.__init__ (**kw)
        # Override log and do not use the inherited one.
        if 'log' in kw:
            self.log = kw ['log']
        self.log.info         ('Starting sync')
        self.compute_schema   ()
        self.reinit           ()
    # end def __init__

    def reinit (self):
        self.localissues     = {}
        self.newcount        = 0
        self.oldremote       = {}
        self.attachments     = None
        self.remote_change   = self.opt.remote_change
        self.verbose         = self.opt.verbose
        self.debug           = self.opt.debug
        self.dry_run         = self.opt.dry_run
        self.remote_dry_run  = self.opt.remote_dry_run
    # end def reinit

    # Don't override in derived class, see Local_Issue
    def attach_file (self, id, file, name):
        return self.localissues [id].attach_file (file, name)
    # end def attach_file
    
    def compute_schema (self):
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

    def create (self, cls, ** kw):
        """ Create local item with given attributes,
            attributes are 'key = value' pairs.
        """
        if cls == 'file':
            self.log_debug ("srv.create %s %s" % (cls, kw.get('name', '?')))
        else:
            self.log_debug ("srv.create %s %s" % (cls, kw))
        if self.dry_run:
            return "9999999"
        return self._create (cls, ** kw)
    # end def create

    def dump_schema (self):
        for cls in self.schema:
            print (cls)
            props = self.schema [cls]
            for pn in props:
                v = props [pn]
                print ("    %s: %s" % (pn, v))
    # end def dump_schema

    def check_method (self, endpoint):
        """ Check an API method, for REST this is equivalent to a call
            of the HTTP Option method on the given endpoint
        """
        raise NotImplementedError ('Needs to be implemented in derived class')
    # end def check_method

    # Don't override in derived class, see Local_Issue
    def file_attachments (self, id, name):
        if self.get_existing_id (id) is None:
            return []
        return self.localissues [id].file_attachments (name)
    # end def file_attachments

    # Don't override in derived class, see Local_Issue
    def file_exists (self, id, name):
        return self.localissues [id].file_exists (name)
    # end def file_exists

    # Don't override in derived class, see Local_Issue
    def get_messages (self, id):
        if self.get_existing_id (id) is None:
            return {}
        return self.localissues [id].get_messages ()
    # end def get_messages

    def filter (self, classname, searchdict):
        """ Search for all properties in searchdict and return ids of
            found objects.
        """
        raise NotImplementedError
    # end def filter

    def fix_attributes (self, classname, attrs, create=False):
        """ Fix transitive attributes. Take care of special cases like
            e.g. roundup's 'content' property
            We distinguish creation and update (transformation might be
            different) via the create flag.
        """
        return attrs
    # end def fix_attributes

    def from_date (self, date):
        """ Note that we convert date values to a string representation
            of the form %Y-%m-%d.%H:%M:%S where seconds are with 3
            decimal places, e.g.  2015-09-06.13:51:38.840
            The default implementation asumes dates are already in that
            format.
        """
        return date
    # end def from_date

    def get (self, id, name):
        return self.localissues [id].get (name)
    # end def get

    def get_classname (self, classname, name):
        """ Get the classname of a Link or Multilink property """
        se = self.get_schema_entry (classname, name)
        assert isinstance (se, tuple)
        return se [1]
    # end def get_classname

    def get_default (self, classname, name):
        """ Get default value for a property 'name' of the given class """
        t = self.get_schema_entry (classname, name)
        if isinstance (t, tuple) and t [0] == 'Multilink':
            v = []
        else:
            v = None
        return v
    # end def get_default

    def get_existing_id (self, id):
        """ An existing id is either a non-empty string that cannot be
            converted to an integer or a positive integer. Non-existing
            ids are negative integers. Note that ids currently must
            evaluate to True in a boolean context (no empty strings or
            None allowed and a 0 for an id is also not allowed).
        """
        assert bool (id)
        try:
            if int (id) < 0:
                return None
        except ValueError:
            return id
        return id
    # end def get_existing_id

    def get_name_translation (self, classname, name):
        """ We may have user-defined names for properties that need to
            be translated.
        """
        return name
    # end def get_name_translation

    def get_schema_entry (self, classname, name):
        """ In some backends, e.g., Jira, we can have symbolic names,
            too.
        """
        name = self.get_name_translation (classname, name)
        return self.schema [classname][name]
    # end def get_schema_entry

    def get_sync_filename (self, remoteid):
        return os.path.join (self.opt.syncdir, str (remoteid))
    # end def get_sync_filename

    def get_transitive_item (self, classname, path, id):
        """ Return the value of the given transitive item.
            The path is a dot-separated transitive property.
            We return the value of the property or the default value for
            this classname and path.
            
            Note that we convert date values to a string representation
            of the form %Y-%m-%d.%H:%M:%S where seconds are with 3
            decimal places, e.g.  2015-09-06.13:51:38.840
        """
        path = self.get_name_translation (classname, path)
        classname, p, id = self.get_transitive_prop (classname, path, id)
        if id:
            if isinstance (id, list):
                r = [self.getitem (classname, i, p) [p] for i in id]
                r = ','.join (r)
            else:
                r = self.getitem (classname, id, p) [p]
            if r and self.get_schema_entry (classname, p) == 'date':
                return self.from_date (r)
            return r
        return self.get_default (classname, p)
    # end def get_transitive_item

    def get_transitive_prop (self, classname, path, id = None):
        """ We get a transitive property 'path' and return classname and
            property name and optionally the id.
            Note that id may become a list when processing multilinks on
            the way.
        """
        path = self.get_name_translation (classname, path)
        path = path.split ('.')
        for p in path [:-1]:
            assert self.get_type (classname, p) in ('Link', 'Multilink')
            if id:
                if isinstance (id, list):
                    id = [self.getitem (classname, i, p) [p] for i in id]
                    if id and isinstance (id [0], list):
                        id = [item for sublist in id for item in sublist]
                else:
                    item = self.getitem (classname, id, p)
                    if p in item:
                        id = item [p]
                    else:
                        id = None
                        self.log.warning \
                            ( "get_transitive_prop: getitem %s %s %s: empty"
                            % (classname, id, p)
                            )
            classname = self.get_classname (classname, p)
        p = path [-1]
        return classname, p, id
    # end def get_transitive_prop

    def get_transitive_schema (self, name):
        """ Return the schema entry of transitive property 'name'.
        """
        classname, path = self.split_name (name)
        classname, prop, id = self.get_transitive_prop (classname, path)
        return self.get_schema_entry (classname, prop)
    # end def get_transitive_schema

    def get_type (self, classname, name):
        """ Get type of property 'name', either a scalar or Link or
            Multilink
        """
        t = self.get_schema_entry (classname, name)
        if isinstance (t, tuple):
            return t [0]
        return t
    # end def get_type

    def getitem (self, cls, id, *attr):
        """ Get all or given list of attributes of an item of the given cls.
            This must not be used for attributes of the issue which we
            are currently syncing. The sync framework keeps a cache of
            to-be-updated attributes, this would bypass the cache.
            This returns a dict with a map from attr name to value.
        """
        raise NotImplementedError
    # end def getitem

    def log_debug (self, msg, *args):
        if self.debug:
            print (msg, *args)
            self.log.debug (msg)
    # end def log_debug

    def log_info (self, msg, *args):
        """ Always log info message. Print to stdout only when verbose
            logging is enabled.
        """
        if self.verbose:
            print (msg, *args)
        self.log.info (msg)
    # end def log_info

    def log_verbose (self, msg, *args):
        if self.verbose:
            print (msg, *args)
            self.log.info (msg)
    # end def log_verbose

    def lookup (self, cls, key):
        """ Look up an item of the given class by key (e.g. name)
            and return the ID
        """
        raise NotImplementedError
    # end def lookup

    def set (self, id, attrname, value):
        self.localissues [id].set (attrname, value)
    # end def set

    def setitem (self, cls, id, ** kw):
        """ Set attributes of an item of the given cls,
            attributes are 'key = value' pairs.
        """
        self.log_debug ("setitem %s:%s %s" % (cls, id, kw))
        if not self.dry_run:
            items = dict \
                ((self.get_name_translation (cls, k), v)
                 for k, v in kw.items ()
                )
            return self._setitem (cls, id, ** items)
    # end def setitem

    def split_name (self, name):
        if not name:
            return None
        if name.startswith ('/'):
            classname, path = name.strip ('/').split ('/', 1)
        else:
            classname = self.default_class
            path = name
        return classname, path
    # end split_name

    def sync (self, remote_id, remote_issue):
        """ We try to find issue with the given remote_id and then call
            the sync framework. If no issue with the given remote_id is
            found, a new issue will be created after all attributes have
            been synced.
        """
        do_sync = False
        id = self.get_oldvalues (remote_id)

        if id:
            # This used to test for equalness of old.as_json and the
            # json representation of the remote_issue and only then
            # set do_sync -- this is wrong as we might have local
            # changes that need to be synced to the remote side
            # So now we're using oldremote directly.
            do_sync = True
            assert id not in self.localissues
            self.localissues [id] = self.Local_Issue_Class \
                (self, id, opt = self.opt)
        else:
            self.newcount += 1
            id = -self.newcount
            assert id not in self.localissues
            self.localissues [id] = self.Local_Issue_Class \
                (self, id, opt = self.opt)
            # create new issue only if the remote issue has all required
            # attributes and doesn't restrict them to a subset:
            do_sync = not remote_issue.attributes
        self.current_id = id
        # If the following is non-empty, sync only an explicit subset of
        # attributes.
        attr = remote_issue.attributes
        # Don't sync a subset of attributes if local issue doesn't exist
        if self.get_existing_id (id) is None and attr:
            return
        self.id = id
        for a in self.attributes:
            if a.only_create:
                continue
            if a.strip_prefix:
                remote_issue.strip_prefix (a.remote_name, a.strip_prefix)
            # Perform local checks in any case even if attributes are
            # restricted to a set.
            check = Sync_Attribute_Check
            if not attr or a.remote_name in attr or isinstance (a, check):
                self.log_debug \
                    ( "sa: id:%s %s %s %s"
                    % (id, a.__class__.__name__, a.name, a.remote_name)
                    )
                if a.sync (self, id, remote_issue):
                    self.log_info ("Not syncing: %s/%s" % (id, remote_id))
                    return

        # Note: This already updates the syncdb!
        if self.get_existing_id (id) is None:
            if not remote_issue.attributes:
                self.log_verbose \
                    ("create issue: %s" % self.localissues [id].newvalues)
                classdict = self.localissues [id].split_newvalues ()
                attr = self.fix_attributes \
                    (self.default_class, classdict [self.default_class], True)
                self.log_verbose ("Create local (after fixattr):", attr)
                iid = self.create (self.default_class, ** attr)
                self.log_info ("created issue: %s/%s" % (iid, remote_id))
                del classdict [self.default_class]
                self.current_id = iid
                # Need to set up localissues for this new id so
                # that self.get keeps working
                self.localissues [iid] = self.localissues [id]
                self.localissues [id].id = iid
                del self.localissues [id]
                self.update_aux_classes \
                    (iid, remote_id, remote_issue, classdict)
        elif self.localissues [id].dirty or remote_issue.dirty:
            self.update_issue (id, remote_id, remote_issue)
        if remote_issue.dirty:
            # Changes to syncdb are written in finalize_sync_db
            if not self.dry_run and not self.remote_dry_run:
                self.log_verbose ("Update remote:", remote_issue.newvalues)
                remote_issue.update (self)
            else:
                self.log_verbose ("DRYRUN upd remote:", remote_issue.newvalues)
            self.finalize_sync_db (id, remote_id, remote_issue)
    # end def sync

    def oldsync_iter (self):
        """ Iterate over all remote ids from previous syncs (all remote
            ids in the sync database)
        """
        for d in os.listdir (self.opt.syncdir):
            if not d.startswith ('__'):
                yield (d)
    # end def oldsync_iter

    def compute_oldvalues (self, remote_id):
        """ Get the sync status (e.g., old properties of last sync of
            remote issue).
        """
        fn = self.get_sync_filename (remote_id)
        j  = None
        try:
            with open (fn, 'r') as f:
                j = f.read ()
        except EnvironmentError:
            pass
        if not j:
            return None
        d  = json.loads (j)
        return d
    # end def compute_oldvalues

    def get_oldvalues (self, remote_id):
        """ Get the sync status (e.g., old properties of last sync of
            remote issue). Side-effect: Set self.oldremote, this
            contains the dictionary of property values from last sync.
            This method must return the id of the local issue if found.
        """
        self.oldremote = {}
        d = self.compute_oldvalues (remote_id)
        if d is None:
            return None
        self.oldremote = d
        id = d ['__local_id__']
        try:
            self.get_transitive_item (self.default_class, 'id', id)
        except RuntimeError as err:
            m = getattr (err, 'message', None)
            if not m:
                m = err.args [0]
            if m.startswith ('Error 404'):
                id = None
                self.oldremote = {}
        return id
    # end def get_oldvalues

    def sync_new_local_issue (self, iid):
        """ Sync this new local issue (must never have been synced to
            remote side) to the remote side creating it there.
            Never called if sync_new_local_issues (note the 's') below is
            the default method doing nothing.
        """
        remote_issue = self.new_remote_issue ({})
        if iid not in self.localissues:
            self.localissues [iid] = self.Local_Issue_Class \
                (self, iid, opt = self.opt)
        do_sync = True
        for a in self.attributes:
            if a.only_update or a.to_local:
                continue
            self.log_debug \
                ( "sa: id:%s %s %s %s"
                % (iid, a.__class__.__name__, a.name, a.remote_name)
                )
            if a.sync (self, iid, remote_issue):
                self.log_info ("Not syncing: %s" % iid)
                do_sync = False
                break
        if not do_sync:
            return
        self.log_verbose ("remote_issue.create", remote_issue.newvalues)
        rid = remote_issue.create ()
        if not rid:
            raise ValueError ("Didn't receive correct remote issue on creation")
        # Now sync all 'To_Local' variants with 'after_create' set
        for a in self.attributes:
            if not a.after_create or not a.to_local:
                continue
            self.log_debug \
                ( "sa: id:%s %s %s %s"
                % (iid, a.__class__.__name__, a.name, a.remote_name)
                )
            if a.sync (self, iid, remote_issue):
                self.log_info ("Not updating after remote create: %s" % iid)
                do_sync = False
                break
        self.update_issue (iid, rid, remote_issue)
    # end def sync_new_local_issue

    def sync_new_local_issues (self, new_remote_issue):
        """ Loop over all local issues that should be synced to the
            remote side but never were synced so far. This needs some
            marks on local issues to determine which issues to sync (we
            *dont't* want to sync *all* local issues to the remote side
            usually!). This is highly application specific and defaults
            to no creation of remote issues.
        """
        pass
    # end def sync_new_local_issues

    def update_aux_classes (self, id, remote_id, remote_issue, classdict):
        """ Auxiliary classes, e.g. for KPM an item that links to issue
            and holds additional attributes. 
            All of those must have a Link named 'issue' to the current issue.
            update_sync_db must come at the start of update_aux_classes
            because it may update attributes that are written by
            update_aux_classes.
        """
        self.update_sync_db (id, remote_id, remote_issue, classdict)
        self.log_verbose ("updated aux: %s/%s" % (id, remote_id))
    # end def update_aux_classes

    def update_issue (self, id, remote_id, remote_issue):
        self.log_verbose \
            ("set issue %s: %s" % (id, self.localissues [id].newvalues))
        classdict = self.localissues [id].split_newvalues ()
        attr = self.fix_attributes \
            (self.default_class, classdict [self.default_class])
        self.log_verbose ("Update local (after fixattr):", attr)
        if self.localissues [id].dirty:
            if attr:
                self.setitem (self.default_class, id, ** attr)
        del classdict [self.default_class]
        self.update_aux_classes (id, remote_id, remote_issue, classdict)
        self.log_info ("Synced: %s/%s" % (id, remote_id))
    # end def update_issue

    def update_sync_db (self, iid, rid, remote_issue, classdict = None):
        """ This may be called as update_sync_db and as finalize_sync_db
            depending on implementation. The finalize_sync_db can update
            the syncdb with things that were updated in remote_issue
            *after* the remote issue has been written.
        """
        fn = self.get_sync_filename (rid)
        with open (fn, "w") as f:
            f.write (remote_issue.as_json (__local_id__ = iid))
    # end def update_sync_db
    # This may be different in other implementations, it does a last
    # write of the sync db after remote issues have been sent.
    finalize_sync_db = update_sync_db

# end class Trackersync_Syncer
Syncer = Trackersync_Syncer
