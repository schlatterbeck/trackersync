#!/usr/bin/python3
# Copyright (C) 2020 Dr. Ralf Schlatterbeck Open Source Consulting.
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
import sys
import requests
import logging.config
try :
    from urllib.parse   import urlencode, parse_qs
except ImportError :
    from urllib         import urlencode
    from urlparse       import parse_qs
from argparse           import ArgumentParser
from datetime           import datetime, date
from lxml.etree         import Element
from traceback          import print_exc
from rsclib.autosuper   import autosuper
from rsclib.execute     import Lock_Mixin, Log
from rsclib.Config_File import Config_File
from rsclib.pycompat    import string_types

from zeep               import Client
from zeep.transports    import Transport
from zeep.helpers       import serialize_object

from trackersync        import tracker_sync
from trackersync        import jira_sync

class Config (Config_File) :

    config = 'kpm_ws_config'
    path   = '/etc/trackersync'

    def __init__ (self, path = path, config = config) :
        self.__super.__init__ \
            ( path, config
            , LOCAL_TRACKER = 'jira'
            , KPM_CERTPATH  = '/etc/trackersync/kpm_certificate.pem'
            , KPM_KEYPATH   = '/etc/trackersync/kpm_certificate.key'
            )
    # end def __init__

# end class Config

logging_cfg = dict \
    ( version = 1
    , formatters = dict (verbose = dict (format = '%(name)s: %(message)s'))
    , handlers = dict
        ( syslog =
            { 'level'     : 'INFO'
            , 'class'     : 'logging.handlers.SysLogHandler'
            , 'formatter' : 'verbose'
            }
        )
    , loggers = 
        { 'zeep.transports' : dict
            ( level     = 'INFO'
            , propagate = True
            , handlers  = ['syslog']
            )
        }
    )
logging.config.dictConfig (logging_cfg)

class KPM_File_Attachment (tracker_sync.File_Attachment) :

    def __init__ (self, issue, **kw) :
        self._content = self._name = self._type = None
        for k in 'content', 'name', 'type' :
            setattr (self, '_' + k, kw.get (k, None))
            if k in kw :
                del kw [k]
        self.__super.__init__ (issue, **kw)
    # end def __init__

    @property
    def content (self) :
        if self._content is None :
            self._get_file ()
        return self._content
    # end def content

    @property
    def name (self) :
        if self._name is None :
            self._get_file ()
        return self._name
    # end def name

    @property
    def type (self) :
        if self._type is None :
            self._get_file ()
        return self._type
    # end def type

    def _get_file (self) :
        FIXME
        result = self.issue.kpm.get \
            ( 'problem.base.dokument.download.do'
            , actionCommand = 'downloadDokumentAsAttachment'
            , dokTs         = self.id
            )
        h = result.headers
        if 'content-type' in h :
            self._type = h ['content-type'].decode ('latin1')
        else :
            self._type = 'application/octet-stream'
        if 'content-disposition' in h :
            parts = h ['content-disposition'].decode ('latin1').split (';')
            for p in parts :
                if p.startswith ('filename=') :
                    fn = p.split ('=', 1) [-1].strip ('"')
                    self._name = fn
                    break
        if self._name is None :
            self._name = self.id
        # Allow content to be None, we create an empty file in this case
        self._content = result.content or ''
    # end def _get_file

# end class KPM_File_Attachment

class Problem (tracker_sync.Remote_Issue) :

    File_Attachment_Class = KPM_File_Attachment

    def __init__ (self, kpm, id, rec, canceled = False) :
        self.kpm         = kpm
        self.debug       = self.kpm.debug
        self.canceled    = canceled
        # We can restrict the attributes to be synced to an explicit
        # subset. The default is no restriction with attributes = {}
        attributes = {}
        if self.canceled :
            attributes ['Status'] = True
        rec = serialize_object (rec)
        self.make_serializable (rec)
        self.__super.__init__ (rec, attributes)
        self.id = self.record ['ProblemNumber']
    # end def __init__

    def convert_date (self, value) :
        """ Convert date from roundup value to german date
            representation. Used only for KPM 'Datum'. Currently we
            don't care about timezone, KPM document doesn't specify the
            timezone used. Roundup XMLRPC dates come as UTC if not
            otherwise configured.
            This is automagically called by framework for each roundup
            date property.
        """
        if not value :
            return value
        dt = datetime.strptime (value, "%Y-%m-%d.%H:%M:%S.%f")
        return dt.strftime ('%Y-%m-%d %H:%M:%S.%f')
    # end def convert_date

    def file_attachments (self, name = None) :
        # FIXME
        if self.attachments is None :
            self.attachments = []
            docs = self.get ('Dokumente')
            if docs :
                self.kpm.log.info ("docs: %r" % docs)
                for doc in docs.split () :
                    parsed = parse_qs (doc)
                    if 'dokTs' not in parsed :
                        self.kpm.log.error ("Error parsing doc: %r" % parsed)
                    else :
                        f = KPM_File_Attachment (self, id = parsed ['dokTs'][0])
                        self.attachments.append (f)
        return self.attachments
    # end def file_attachments

    def create (self) :
        """ Create new remote issue
        """
        raise NotImplementedError ("Creation in KPM not yet implemented")
    # end def create

    def make_serializable (self, rec) :
        """ This makes the returned data structure serializable (e.g.
            convert date to string) and fixes some problems witht the
            data, e.g., the ProblemNumber is numeric which needs to be a
            string.
        """
        for k in rec.keys () :
            if k == 'ProblemNumber' :
                rec [k] = str (rec [k])
            if k == 'Rating' :
                rec [k] = rec [k].strip ()
            if isinstance (rec [k], type ({})) :
                self.make_serializable (rec [k])
            elif isinstance (rec [k], date) :
                rec [k] = rec [k].strftime ('%Y-%m-%d')
    # end def make_serializable

    def sync (self, syncer) :
        syncer.log.info ('Syncing %s' % self.id)
        try :
            syncer.sync (self.id, self)
        except Exception :
            syncer.log.error ("Error syncing %s" % self.id)
            syncer.log_exception ()
            print ("Error syncing %s" % self.id)
            print_exc ()
    # end def sync

    def update (self, syncer) :
        """ Update remote issue tracker with self.newvalues.
        """
        if self.dirty :
            self.kpm.update (self)
    # end def update

# end def Problem

class KPM_Header (autosuper) :
    """ Tools to build the header for the webservice request.
        FIXME: For now this seems to working without a header
    """

    def __init__ (self) :
        self.adr_ns = 'http://www.w3.org/2005/08/addressing'
        self.vw_ns  = 'http://xmldefs.volkswagenag.com/Technical/Addressing/V1'
        self.ws     = \
            'ws://volkswagenag.com/PP/QM/GroupProblemManagementService/V3'
        self._seqno = 0
    # end def __init__

    def element (self, ns, name, value) :
        e = Element (tag (ns, name))
        e.text = str (value)
        return e
    # end def element

    def header (self, rqname) :
        h = [ self.element (self.adr_ns, 'To',        self.ws)
            , self.element (self.adr_ns, 'Action',    self.rq (rqname))
            , self.element (self.adr_ns, 'MessageID', self.seqno)
            , self.element (self.vw_ns,  'Stage',     'Test')
            , self.element (self.vw_ns,  'Country',   'AT')
            ]
        return h
    # end def header

    def seqno (self) :
        self._seqno += 1
        return str (self._seqno)
    # end def seqno

    def rq (self, rqname) :
        return self.ws + '/KpmService/' + rqname
    # end def rq

    def tag (self, ns, name) :
        return '{%s}%s' % (ns, name)
    # end def tag

# end class KPM_Header

class KPM_WS (Log, Lock_Mixin) :
    """ Interactions with the KPM web service interface
    """

    def __init__ \
        ( self
        , cfg
        , timeout = None
        , verbose = False
        , debug   = False
        , lock    = None
        , ** kw
        ) :
        self.cfg      = cfg
        self.cert     = cfg.KPM_CERTPATH
        self.key      = cfg.KPM_KEYPATH
        self.wsdl     = cfg.KPM_WSDL
        self.url      = cfg.KPM_WS
        self.timeout  = timeout
        self.verbose  = verbose
        self.debug    = debug
        self.session  = requests.Session ()
        if timeout :
            self.session.timeout = timeout
        self.session.cert = (self.cert, self.key)
        transport   = Transport (session = self.session)
        self.client = Client (self.wsdl, transport = transport)
        self.fac    = self.client.type_factory ('ns0')
        self.auth   = self.fac.UserAuthentification \
            (UserId = self.cfg.KPM_USERNAME)
        self.adr    = self.fac.Address \
            (OrganisationalUnit = self.cfg.KPM_OU, Plant = self.cfg.KPM_PLANT)
        if lock :
            self.lockfile = lock
        self.__super.__init__ (** kw)
    # end def __init__

    def check_error (self, rq, msg) :
        c = 'Communication: '
        if 'ResponseMessage' not in msg :
            self.log.error ("%s%s: No ResponseMessage found" % (c, rq))
            return 1
        if 'MessageText' not in msg ['ResponseMessage'] :
            self.log.error ("%s%s: No MessageText found" % (c, rq))
            return 1
        txt = msg ['ResponseMessage']['MessageText']
        if 'success' not in txt :
            self.log.error ("%s%s: Error: %s" % (c, rq, txt))
            return 1
        return 0
    # end def check_error

    def __iter__ (self) :
        """ Iterate over all relevant 'Problem' records
        """
        self.log.debug ('In __iter__')
        info = self.client.service.GetMultipleProblemData \
            ( UserAuthentification = self.auth
            , OverviewAddress      = self.adr
            , ActiveOverview       = True
            , PassiveOverview      = True
            )
        if self.check_error ('GetMultipleProblemData', info) :
            return
        for pr in info ['ProblemReference'] :
            id = pr ['ProblemNumber']
            rights = self.client.service.GetProblemActions \
                (UserAuthentification = self.auth, ProblemNumber = id)
            if self.check_error ('GetProblemActions', rights) :
                continue
            if 'GET_DEVELOPMENT_PROBLEM_DATA' not in rights ['Action'] :
                self.log.info ("No right to get problem data for %s" % id)
                continue
            rec = self.client.service.GetDevelopmentProblemData \
                (UserAuthentification = self.auth, ProblemNumber = id)
            if self.check_error ('GetDevelopmentProblemData', rec) :
                continue
            rec = rec ['DevelopmentProblem']
            p = Problem (self, id, rec)
            yield (p)
    # end def __iter__

    def update (self, problem) :
        d = dict \
            ( Status      = problem.SupplierStatus
            , ErrorNumber = problem.ExternalProblemNumber
            )
        if problem.get ('VersionOK', None) :
            d ['VersionOK'] = problem.VersionOK
        sr = self.fac.SupplierResponse (** d)
        d = dict \
            ( UserAuthentification = self.auth
            , ProblemNumber        = int (problem.ProblemNumber)
            , SupplierResponse     = sr
            )
        d ['ResponseText'] = problem.SupplierResponse
        r = self.client.service.AddSupplierResponse (** d)
        self.check_error ('AddSupplierResponse', r)
    # end def update

# end class KPM_WS

local_trackers = dict (jira = jira_sync.Syncer)

def main () :
    cmd = ArgumentParser ()
    cmd.add_argument \
        ( "-c", "--config"
        , help    = "Configuration file"
        , default = '/etc/trackersync/kpm_ws_config.py'
        )
    cmd.add_argument \
        ( "-D", "--debug"
        , help    = "Debugging"
        , action  = 'store_true'
        , default = False
        )
    cmd.add_argument \
        ( "-l", "--local-username"
        , help    = "Username for local tracker"
        )
    cmd.add_argument \
        ( "-L", "--local-tracker"
        , help    = "Local tracker, one of %s, default: jira"
                  % ', '.join (local_trackers.keys ())
        )
    cmd.add_argument \
        ( "-n", "--no-action"
        , help    = "Dry-run: Don't update any side of sync"
        , action  = 'store_true'
        , default = False
        , dest    = 'dry_run'
        )
    cmd.add_argument \
        ( "-N", "--no-remote-action"
        , help    = "Remote-dry-run: Don't update remote side of sync"
        , action  = 'store_true'
        , default = False
        , dest    = 'remote_dry_run'
        )
    cmd.add_argument \
        ( "-p", "--local-password"
        , help    = "Password for local tracker"
        )
    cmd.add_argument \
        ( "-R", "--remote-change"
        , help    = "Treat remote values as changed if non-empty. "
                    "Set local value to remote value for two-way sync "
                    "attributes, even if the remote doesn't seem to be "
                    "changed. The default in this case would be to "
                    "overwrite the remote with the local value. This is "
                    "useful in case the sync configuration changed and "
                    "some local values are unset or need update. "
                    "Note that this applies only if the remote value is "
                    "non-empty."
        , dest    = 'remote_change'
        , action  = 'store_true'
        , default = False
        )
    cmd.add_argument \
        ( "-s", "--syncdir"
        , help    = "Sync directory, not used by all local trackers, "
                    "default: %(default)s"
        , default = './syncdir'
        )
    cmd.add_argument \
        ( "--schema-only"
        , help    = "Display Jira Schema and stop"
        , action  = 'store_true'
        )
    cmd.add_argument \
        ( "-u", "--url"
        , help    = "Local Tracker URL for XMLRPC/REST"
        )
    cmd.add_argument \
        ( "-v", "--verbose"
        , help    = "Verbose reporting"
        , action  = 'store_true'
        , default = False
        )
    cmd.add_argument \
        ( "--lock-name"
        , help    = "Locking-filename -- note that this is "
                    "dangerous, you should not have two instances of "
                    "kpmsync writing to KPM."
        )
    opt     = cmd.parse_args ()
    config  = Config.config
    cfgpath = Config.path
    if opt.config :
        cfgpath, config = os.path.split (opt.config)
        config = os.path.splitext (config) [0]
    cfg = Config (path = cfgpath, config = config)
    kpm = KPM_WS \
        ( cfg     = cfg
        , verbose = opt.verbose
        , debug   = opt.debug
        , lock    = opt.lock_name
        )
    url       = opt.url         or cfg.get ('LOCAL_URL', None)
    lpassword = opt.local_password or cfg.LOCAL_PASSWORD
    lusername = opt.local_username or cfg.LOCAL_USERNAME
    ltracker  = opt.local_tracker  or cfg.LOCAL_TRACKER
    opt.local_password = lpassword
    opt.local_username = lusername
    opt.url            = url
    opt.local_tracker  = ltracker
    syncer = None
    if url and cfg.get ('KPM_ATTRIBUTES') :
        syncer = local_trackers [opt.local_tracker] \
            ('KPM', cfg.KPM_ATTRIBUTES, opt)
    if opt.schema_only :
        syncer.dump_schema ()
        sys.exit (0)

    for problem in kpm :
        problem.sync (syncer)
# end def main

if __name__ == '__main__' :
    main ()
