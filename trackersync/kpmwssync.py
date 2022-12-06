#!/usr/bin/python3
# Copyright (C) 2020-22 Dr. Ralf Schlatterbeck Open Source Consulting.
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
import logging
try:
    from urllib.parse   import urlencode, parse_qs
except ImportError:
    from urllib         import urlencode
    from urlparse       import parse_qs
from argparse           import ArgumentParser
from datetime           import datetime, date
from lxml.etree         import Element, ElementTree, tostring, _Element
from traceback          import print_exc
from rsclib.autosuper   import autosuper
from rsclib.execute     import Lock_Mixin, Log
from rsclib.Config_File import Config_File
from rsclib.pycompat    import string_types
from uuid               import uuid4
from collections        import deque

from zeep               import Client
from zeep.transports    import Transport
from zeep.helpers       import serialize_object

from trackersync        import tracker_sync
from trackersync        import jira_sync

class Sync_Attribute_KPM_Message (tracker_sync.Sync_Attribute):

    def __init__ (self, prefix = None, ** kw):
        self.__super.__init__ (local_name = None, ** kw)
        self.prefix = prefix
    # end def __init__

    def sync (self, syncer, id, remote_issue):
        """ Note that like for all Sync_Attribute classes the remote
            issue is the KPM issue.
        """
        if self.l_only_update and syncer.get_existing_id (id) is None:
            return
        lmsg = syncer.get_messages (id)
        # Get previously synced keys
        remote_issue.get_old_message_keys (syncer)
        local_issue = syncer.localissues [id]
        aussagen = []
        try:
            aussagen = remote_issue.Aussagen
        except AttributeError:
            pass
        for k in aussagen:
            a = remote_issue.Aussagen [k]
            if a.get ('foreign_id'):
                continue
            message = local_issue.Message_Class \
                ( local_issue
                , id      = k
                , date    = datetime.strptime
                    (a ['date'], '%Y-%m-%d-%H.%M.%S.%f')
                , content = a ['content']
                )
            # There may be a problem if later during sync of the same
            # issue an error occurs and we cannot write the sync db.
            a ['foreign_id'] = local_issue.add_message (message)
            assert a ['foreign_id']
            remote_issue.dirty = True
        if self.prefix:
            for id in lmsg:
                if id in remote_issue.msg_by_foreign_id:
                    continue
                if not lmsg [id].content.startswith (self.prefix):
                    continue
                msg = self._mangle_rec (lmsg [id])
                remote_issue.add_message (msg)
    # end def sync

    def _mangle_rec (self, oldrec):
        rec = oldrec.copy ()
        if rec.content.startswith (self.prefix):
            rec.content = rec.content [len (self.prefix):].lstrip ()
        return rec
    # end def _mangle_rec

# end class Sync_Attribute_KPM_Message

class Config (Config_File):

    config = 'kpm_ws_config'
    path   = '/etc/trackersync'

    def __init__ (self, path = path, config = config):
        self.__super.__init__ \
            ( path, config
            , LOCAL_TRACKER = 'jira'
            , KPM_CERTPATH  = '/etc/trackersync/kpm_certificate.pem'
            , KPM_KEYPATH   = '/etc/trackersync/kpm_certificate.key'
            , KPM_STAGE     = 'Production'
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
        { 'zeep.transports': dict
            ( level     = 'INFO'
            , propagate = True
            , handlers  = ['syslog']
            )
        }
    )
logging.config.dictConfig (logging_cfg)

class KPM_File_Attachment (tracker_sync.File_Attachment):

    def __init__ (self, issue, **kw):
        self.description = self.permission = None
        self._content = self._name = self._type = None
        for k in 'content', 'name', 'type':
            setattr (self, '_' + k, kw.get (k, None))
            if k in kw:
                del kw [k]
        for k in 'permission', 'description':
            if k in kw:
                setattr (self, k, kw.get (k))
                del kw [k]
        self.__super.__init__ (issue, **kw)
    # end def __init__

    @property
    def content (self):
        if self._content is None:
            self._get_file ()
        return self._content
    # end def content

    @property
    def name (self):
        if self._name is None:
            self._get_file ()
        return self._name
    # end def name

    @property
    def type (self):
        return self._type
    # end def type

    def _get_file (self):
        f = self.issue.kpm.get_file (self)
        if f is not None:
            self._content = f ['Data']
            if not self._name:
                if f ['Suffix']:
                    self._name = '.'.join ((f ['Name'], f ['Suffix']))
                else:
                    self._name = f ['Name']
            if not self.permission:
                self.permission = f ['AccessRight']
            if not self.description:
                self.description = f ['Description']
    # end def _get_file

# end class KPM_File_Attachment

class Problem (tracker_sync.Remote_Issue):

    # Allow to access deep datastructures with multilevel keys delimited
    # with '.'
    multilevel = True

    File_Attachment_Class = KPM_File_Attachment

    def __init__ (self, kpm, id, rec, canceled = False, raw = False):
        self.kpm         = kpm
        self.debug       = self.kpm.debug
        self.canceled    = canceled
        self.raw         = raw
        # We can restrict the attributes to be synced to an explicit
        # subset. The default is no restriction with attributes = {}
        attributes = {}
        if self.canceled:
            attributes ['Status'] = True
        self.__super.__init__ (rec, attributes)
        self.id = self.record ['ProblemNumber']
        self.messages = []
    # end def __init__

    def add_message (self, msg):
        self.dirty = True
        msgid = self.kpm.add_message (self, msg)
        return msgid
    # end def add_message

    def convert_date (self, value):
        """ Convert date from roundup value to KPM WS date
            representation. Used only for KPM 'Datum'. Currently we
            don't care about timezone, KPM document doesn't specify the
            timezone used. Roundup XMLRPC dates come as UTC if not
            otherwise configured.
            This is automagically called by framework for each roundup
            date property.
        """
        if not value:
            return value
        dt = datetime.strptime (value, "%Y-%m-%d.%H:%M:%S.%f")
        return dt.strftime ('%Y-%m-%d-%H.%M.%S.%f')
    # end def convert_date

    def file_attachments (self, name = None):
        if self.attachments is None:
            self.attachments = []
            for d in self.kpm.document_list (self):
                if d ['Suffix']:
                    name = '.'.join ((d ['Name'], d ['Suffix']))
                else:
                    name = d ['Name']
                f = KPM_File_Attachment \
                    ( self
                    , id          = d ['DocumentId']
                    , name        = name
                    , permission  = d ['AccessRight']
                    , description = d ['Description']
                    )
                self.attachments.append (f)
        return self.attachments
    # end def file_attachments

    def create (self):
        """ Create new remote issue
        """
        raise NotImplementedError ("Creation in KPM not yet implemented")
    # end def create

    def get_old_message_keys (self, syncer):
        aussagen = syncer.oldremote.get ('Aussagen', {})
        for k in aussagen:
            d = aussagen [k]
            if 'foreign_id' in d:
                self ['Aussagen'][k]['foreign_id'] = d ['foreign_id']
        self.msg_by_foreign_id = {}
        mlist = []
        try:
            mlist = self ['Aussagen']
        except KeyError:
            pass
        for k in mlist:
            m = self ['Aussagen'][k]
            fk = m.get ('foreign_id')
            if fk:
                self.msg_by_foreign_id [fk] = k
    # end def get_old_message_keys

    def sync (self, syncer):
        syncer.log.info ('Syncing %s' % self.id)
        try:
            syncer.sync (self.id, self)
        except Exception:
            syncer.log.error ("Error syncing %s" % self.id)
            syncer.log_exception ()
            print ("Error syncing %s" % self.id)
            print_exc ()
    # end def sync

    def update (self, syncer):
        """ Update remote issue tracker with self.newvalues.
        """
        if self.dirty:
            # This check needs update if we ever create issues
            self.kpm.update (self)
    # end def update

# end def Problem

class KPM_Header (autosuper):
    """ Tools to build the header for the webservice request.
        Note that the stage *should* be given in the constructor.
        Possible parameters are 'Test', 'Production' or 'QualityAssurance'
        Brand may be undefined, possible values are 'V' or 'AU'
        The country also is left out, no idea if this is the country of
        the OEM or what is expected there.
    """

    xmldefs = 'http://xmldefs.volkswagenag.com'
    adr_ns  = 'http://www.w3.org/2005/08/addressing'
    vw_ns   = 'http://xmldefs.volkswagenag.com/Technical/Addressing/V1'
    ws      = 'ws://volkswagenag.com'
    wspath  = '/PP/QM/GroupProblemManagementService/V3'
    wsuri   = ws + wspath

    def __init__ (self, stage = 'Production', brand = None):
        self.stage  = stage
        self.brand  = brand
    # end def __init__

    def element (self, ns, name, value):
        e = Element (self.tag (ns, name))
        e.text = str (value)
        return e
    # end def element

    def header (self, rqname):
        h = [ self.element (self.adr_ns, 'To',        self.wsuri)
            , self.element (self.adr_ns, 'Action',    self.rq (rqname))
            , self.element (self.adr_ns, 'MessageID', self.seqno)
            , self.element (self.vw_ns,  'Stage',     self.stage)
            #, self.element (self.vw_ns,  'Country',   'AT')
            ]
        if self.brand:
            h.append (self.element (self.vw_ns, 'Brand', self.brand))
        return h
    # end def header

    @property
    def seqno (self):
        return 'urn:uuid:' + str (uuid4 ())
    # end def seqno

    def rq (self, rqname):
        return self.xmldefs + self.wspath + '/KpmService/' + rqname
    # end def rq

    def tag (self, ns, name):
        return '{%s}%s' % (ns, name)
    # end def tag

    def __str__ (self):
        tree = ElementTree ()
        tree._setroot (Element ('Header'))
        r = tree.getroot ()
        for e in self.header ('HUHU'):
            r.append (e)
        return tostring (tree, pretty_print = True, encoding = 'unicode')
    # end def __str__

# end class KPM_Header

class KPM_WS (Log, Lock_Mixin):
    """ Interactions with the KPM web service interface
    """

    def __init__ \
        ( self
        , cfg
        , timeout = 300
        , verbose = False
        , debug   = False
        , lock    = None
        , ** kw
        ):
        self.cfg      = cfg
        self.cert     = cfg.KPM_CERTPATH
        self.key      = cfg.KPM_KEYPATH
        self.wsdl     = cfg.KPM_WSDL
        self.url      = cfg.KPM_WS
        self.timeout  = timeout
        self.verbose  = verbose
        self.debug    = debug
        self.session  = requests.Session ()
        if timeout:
            self.session.timeout = timeout
        self.session.cert = (self.cert, self.key)
        transport   = Transport \
            (session = self.session, operation_timeout = timeout)
        self.client = Client (self.wsdl, transport = transport)
        self.client.settings.strict = False
        self.fac    = self.client.type_factory ('ns0')
        self.auth   = self.fac.UserAuthentification \
            (UserId = self.cfg.KPM_USERNAME)
        self.adr    = self.fac.Address \
            (OrganisationalUnit = self.cfg.KPM_OU, Plant = self.cfg.KPM_PLANT)
        if lock:
            self.lockfile = lock
        self.header = KPM_Header (stage = self.cfg.KPM_STAGE)
        self.__super.__init__ (** kw)
    # end def __init__

    def __iter__ (self):
        """ Iterate over all relevant 'Problem' records
        """
        self.log.debug ('In __iter__')
        # Note that PassiveOverview will be needed when we're creating
        # remote issues that need update.
        head = self.header.header ('GetMultipleProblemDataRequest')
        info = self.client.service.GetMultipleProblemData \
            ( UserAuthentification = self.auth
            , OverviewAddress      = self.adr
            , ActiveOverview       = True
            , PassiveOverview      = False
            , _soapheaders         = head
            )
        if self.check_error ('GetMultipleProblemData', info):
            return
        for pr in info ['ProblemReference']:
            id = pr ['ProblemNumber']
            head   = self.header.header ('GetProblemActionsRequest')
            rights = self.client.service.GetProblemActions \
                ( UserAuthentification = self.auth
                , ProblemNumber        = id
                , _soapheaders         = head
                )
            if self.check_error ('GetProblemActions', rights):
                continue
            if 'GET_DEVELOPMENT_PROBLEM_DATA' not in rights ['Action']:
                self.log.info ("No right to get problem data for %s" % id)
                continue
            head = self.header.header ('GetDevelopmentProblemDataRequest')
            rec  = self.client.service.GetDevelopmentProblemData \
                ( UserAuthentification = self.auth
                , ProblemNumber        = id
                , _soapheaders         = head
                )
            if self.check_error ('GetDevelopmentProblemData', rec):
                continue
            rec = rec ['DevelopmentProblem']
            rec = serialize_object (rec)
            raw = rec.get ('_raw_elements', None)
            self.make_serializable (rec)
            rec ['Aussagen'] = {}
            pss = self.get_process_steps (id)
            for ps in pss:
                pstype = ps ['ProcessStepTypeDescription']
                if pstype == 'Lieferantenaussage':
                    sr = ps ['SupplierResponse']
                    rec ['SupplierResponse'] = ps ['Text']
                    if sr is not None:
                        rec ['SupplierVersionOk']   = sr ['VersionOk']
                        rec ['SupplierErrorNumber'] = sr ['ErrorNumber']
                if pstype == 'Analyse abgeschlossen':
                    rec ['Analysis'] = ps ['Text']
                if pstype == 'Aussage':
                    psid = ps ['ProcessStepId']
                    rec ['Aussagen'][psid] = dict \
                        ( id      = psid
                        , date    = ps ['CreationDate']
                        , content = ps ['Text']
                        )
            p = Problem (self, id, rec, raw = raw)
            # If raw elements exist, parsing wasn't fully successful
            if p.raw:
                tags = ','.join (x.tag for x in p.raw)
                self.log.warn \
                    ('KPM-%s has raw elements with tags: %s' % (p.id, tags))
            p.allowed_actions = rights ['Action']
            yield (p)
    # end def __iter__

    def check_error (self, rq, msg):
        c = 'Communication: '
        if 'ResponseMessage' not in msg:
            self.log.error ("%s%s: No ResponseMessage found" % (c, rq))
            return 1
        if 'MessageText' not in msg ['ResponseMessage']:
            self.log.error ("%s%s: No MessageText found" % (c, rq))
            return 1
        txt = msg ['ResponseMessage']['MessageText']
        if 'success' not in txt:
            self.log.error ("%s%s: Error: %s" % (c, rq, txt))
            return 1
        return 0
    # end def check_error

    def add_message (self, problem, msg):
        if 'ADD_NOTICE' not in problem.allowed_actions:
            self.log.error \
                ('No permission to add message to %s' % problem.id)
        else:
            head = self.header.header ('AddNoticeRequest')
            r    = self.client.service.AddNotice \
                ( UserAuthentification = self.auth
                , ProblemNumber        = problem.ProblemNumber
                , Notice               = msg.content
                , _soapheaders         = head
                )
            self.check_error ('AddNotice', r)
            id = r ['ProcessStepId']
            # Workaround: Seems the ID is in different date format
            id = self.fix_process_step_date (id)
            problem.Aussagen [id] = dict \
                ( id         = id
                , content    = msg.content
                , date       = msg.date.strftime ('%Y-%m-%d-%H.%M.%S.%f')
                , foreign_id = msg.id
                )
    # end def add_message

    def fix_process_step_date (self, timestamp):
        """ Workaround: Seems the ID is in different date format
            The IDs returned with GetProcessStepList are in a different
            format than the ID returned with AddNotice.
        """
        try:
            dt = datetime.strptime (timestamp, "%Y-%m-%d %H:%M:%S.%f")
            return dt.strftime ("%Y-%m-%d-%H.%M.%S.%f")
        except ValueError:
            pass
        # Make sure it's the right format before returning:
        dt = datetime.strptime (timestamp, "%Y-%m-%d-%H.%M.%S.%f")
        return timestamp
    # end def fix_process_step_date

    def document_list (self, problem):
        if 'GET_DOCUMENT_LIST' not in problem.allowed_actions:
            self.log.error \
                ('No permission to list documents for %s' % problem.id)
            return []
        head = self.header.header ('GetDocumentListRequest')
        pl   = self.client.service.GetDocumentList \
            ( UserAuthentification = self.auth
            , ProblemNumber        = problem.id
            , _soapheaders         = head
            )
        if self.check_error ('GetDocumentList', pl):
            return []
        return pl ['DocumentReference']
    # end def document_list

    def get_file (self, doc):
        issue = doc.issue
        if getattr (doc, 'permission', None) != '0':
            self.log.error \
                ( 'No permission on document %s of issue %s'
                % (doc.id, issue.id)
                )
            return
        if 'GET_DOCUMENT' not in issue.allowed_actions:
            self.log.error \
                ('No permission to retrieve document for %s' % issue.id)
            return
        head = self.header.header ('GetDocumentRequest')
        doc  = self.client.service.GetDocument \
            ( UserAuthentification = self.auth
            , ProblemNumber        = issue.id
            , DocumentId           = doc.id
            , _soapheaders         = head
            )
        if self.check_error ('GetDocument', doc):
            return
        return doc ['Document']
    # end def get_file

    def get_process_steps (self, problem_id):
        """ Get additional information about problem that is carried
            only in process steps.
        """
        head = self.header.header ('GetProcessStepListRequest')
        info = self.client.service.GetProcessStepList \
            ( UserAuthentification = self.auth
            , ProblemNumber        = problem_id
            , _soapheaders         = head
            )
        self.check_error ('GetProcessStepList', info)
        # Loop over steps and decide which to retrieve
        latest    = {}
        steplist  = []
        for ps in info ['ProcessStepItem']:
            assert int (ps ['ProblemNumber']) == int (problem_id)
            pstype = ps ['ProcessStepTypeDescription']
            psid   = ps ['ProcessStepId']
            for relevant in 'Lieferantenaussage', 'Analyse abgeschlossen':
                if pstype == relevant:
                    # Only keep newest
                    if relevant not in latest or latest [relevant] < psid:
                        latest [relevant] = psid
            if pstype == 'Aussage':
                steplist.append (psid)
        head = self.header.header ('GetProcessStepsRequest')
        info = self.client.service.GetProcessSteps \
            ( UserAuthentification = self.auth
            , ProblemNumber        = problem_id
            , ProcessStepId        = steplist + list (latest.values ())
            , _soapheaders         = head
            )
        self.check_error ('GetProcessStepList', info)
        return info ['ProcessStep']
    # end def get_process_steps

    def make_serializable (self, rec):
        """ This makes the returned data structure serializable (e.g.
            convert date to string) and fixes some problems with the
            data, e.g., the ProblemNumber is numeric which needs to be a
            string.
        """
        for k in rec.keys ():
            if k == 'ProblemNumber':
                rec [k] = str (rec [k])
            elif k == 'Rating' and rec [k] is not None:
                rec [k] = rec [k].strip ()
            elif k == '_raw_elements':
                del rec [k]
            elif isinstance (rec [k], type ({})):
                self.make_serializable (rec [k])
            elif isinstance (rec [k], (list, deque)):
                r = dict ((n, item) for n, item in enumerate (rec [k]))
                self.make_serializable (r)
                rec [k] = list (r [i] for i in sorted (r))
            elif isinstance (rec [k], date):
                rec [k] = rec [k].strftime ('%Y-%m-%d')
            elif isinstance (rec [k], _Element):
                rec [k] = str (rec [k])
    # end def make_serializable

    def update (self, problem):
        response_attrs = set \
            (( 'SupplierStatus', 'SupplierErrorNumber'
            ,  'SupplierVersionOk', 'SupplierResponse'
            ))
        nv = set (problem.newvalues.keys ())
        # Only update if at least one of the attributes is in newvalues
        if response_attrs & nv:
            self.update_supplier_response (problem)
    # end def update

    def update_supplier_response (self, problem):
        d = dict \
            ( Status      = problem.SupplierStatus
            , ErrorNumber = problem.SupplierErrorNumber
            )
        if problem.newvalues.get ('SupplierVersionOk', None):
            d ['VersionOk'] = problem.newvalues ['SupplierVersionOk']
        else:
            d ['VersionOk'] = None
        sr = self.fac.SupplierResponse (** d)
        h = self.header.header ('AddSupplierResponseRequest')
        d = dict \
            ( UserAuthentification = self.auth
            , ProblemNumber        = problem.ProblemNumber
            , SupplierResponse     = sr
            , _soapheaders         = h
            )
        d ['ResponseText'] = problem.SupplierResponse
        if 'ADD_SUPPLIER_RESPONSE' not in problem.allowed_actions:
            self.log.error \
                ('No permission to set supplier response for %s' % problem.id)
        else:
            r = self.client.service.AddSupplierResponse (** d)
            self.check_error ('AddSupplierResponse', r)
    # end def update_supplier_response

# end class KPM_WS

local_trackers = dict (jira = jira_sync.Syncer)

def main ():
    cmd = ArgumentParser ()
    cmd.add_argument \
        ( "-c", "--config"
        , help    = "Configuration file"
        , default = '/etc/trackersync/kpm_ws_config.py'
        )
    cmd.add_argument \
        ( "--check-method"
        , help    = "Test available methods on given endpoint"
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
    loglevels = set (('CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'))
    cmd.add_argument \
        ( "--log-level"
        , help    = "Loglevel for logging backend, default=%(default)s"
        , default = 'INFO'
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
        ( "-t", "--timeout"
        , help    = "Timeout for SOAP requests in seconds, default=%(default)s"
        , default = 300
        , type    = int
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
    if opt.log_level.upper () not in loglevels:
        print \
            ( "Error setting log-level, allowed are: %s"
            % ','.join (sorted (loglevels))
            )
        sys.exit (1)
    log_level = getattr (logging, opt.log_level.upper ())
    config    = Config.config
    cfgpath   = Config.path
    if opt.config:
        cfgpath, config = os.path.split (opt.config)
        config = os.path.splitext (config) [0]
    cfg = Config (path = cfgpath, config = config)
    kpm = KPM_WS \
        ( cfg       = cfg
        , verbose   = opt.verbose
        , debug     = opt.debug
        , lock      = opt.lock_name
        , timeout   = opt.timeout
        , log_level = log_level
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
    if url and cfg.get ('KPM_ATTRIBUTES'):
        try:
            syncer = local_trackers [opt.local_tracker] \
                ('KPM', cfg.KPM_ATTRIBUTES, opt, log_level = log_level)
        except:
            kpm.log_exception ()
            kpm.log.error ("Exception before starting sync")
            # Better explicit, twice won't hurt
            kpm.unlock ()
            return 1
    if opt.schema_only:
        syncer.dump_schema ()
        sys.exit (0)
    if opt.check_method:
        syncer.check_method (opt.check_method)
        sys.exit (0)

    nproblems = 0
    try:
        for problem in kpm:
            problem.sync (syncer)
            nproblems += 1
    except:
        kpm.log_exception ()
        kpm.log.error \
            ("Exception while syncing, synced %d KPM issues" % nproblems)
        # Normally unlock is registered as an atexit handler.
        # No idea why this is not called when a zeep exception occurs.
        kpm.unlock ()
    else:
        kpm.log.info ("Synced %d KPM issues" % nproblems)
# end def main

if __name__ == '__main__':
    main ()
