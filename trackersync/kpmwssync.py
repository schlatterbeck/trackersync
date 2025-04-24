#!/usr/bin/python3
# Copyright (C) 2020-25 Dr. Ralf Schlatterbeck Open Source Consulting.
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
from zeep.exceptions    import Fault

from trackersync        import tracker_sync
from trackersync        import jira_sync

try:
    from requests_pkcs12 import Pkcs12Adapter
except ImportError:
    Pkcs12Adapter = None

sanitize_dict = dict.fromkeys (range (0x20))
for k in b'\r\n\t':
    del sanitize_dict [k]

def sanitize (s):
    """ Sanitize strings which should be sent via XML: It seems e.g.
        Jira accepts many control characters that are not serializable
        to XML. The one we encountered so far is a vertical tab \0b.
    >>> sanitize ('abcdef\\x00\\x01\\x02\\x0b\\r\\n\\x08\\x09\\x1f\x20huhu')
    'abcdef\\r\\n\\t huhu'
    """
    return s.translate (sanitize_dict) 
# end def sanitize

class Process_Steps:
    """ Additional information about problem that is carried in
        'process steps' data structure in KPM.
    """
    # List of Process steps to fully retrieve
    # Note: there is a 'SupplierResponse' kept in the sync data.
    # The one stored here is with '_' in the name.
    step_map = dict \
        (( ('Aussage',                        'Aussagen')
        ,  ('Antwort auf TV, RF, WK, FK, WA', 'Answer_to_Supplier')
        ,  ('Rückfrage',                      'Supplier_Question')
        ,  ('Information an Lieferanten',     'Supplier_Info')
        ,  ('Lieferantenaussage',             'Supplier_Response')
        ,  ('Analyse abgeschlossen',          'Analysis_All')
        ))
    rev_step_map = dict \
        ((v, k) for k, v in step_map.items ())
    # Flags if we keep only the latest item or the list, or both
    #     Name                 keep latest, keep list
    step_keep = dict \
        ( Aussagen           = dict (latest = False, history = True)
        , Answer_to_Supplier = dict (latest = False, history = True)
        , Supplier_Question  = dict (latest = False, history = True)
        , Supplier_Info      = dict (latest = False, history = True)
        , Supplier_Response  = dict (latest = True,  history = True)
        , Analysis_All       = dict (latest = True,  history = True)
        )

    def __init__ (self, parent, problem_id, actions):
        self.parent       = parent
        self.problem_id   = problem_id
        self.log          = parent.log
        self.steps        = []
        self.latest_steps = latest = {}
        self.history      = {}
        self.latest       = {}
        needed_actions = set (('GET_PROCESS_STEP_LIST', 'GET_PROCESS_STEPS'))
        if not needed_actions.intersection (actions):
            self.log.error ('Cannot get steps / step list for %s' % problem_id)
            return
        head = parent.header.header ('GetProcessStepListRequest')
        info = parent.client.service.GetProcessStepList \
            ( UserAuthentification = parent.auth
            , ProblemNumber        = problem_id
            , _soapheaders         = head
            )
        parent.check_error ('GetProcessStepList', info)
        # Loop over steps and decide which to retrieve
        steplist = set ()
        for ps in info ['ProcessStepItem']:
            assert int (ps ['ProblemNumber']) == int (problem_id)
            pstype = ps ['ProcessStepTypeDescription']
            psid   = ps ['ProcessStepId']
            if pstype not in self.step_map:
                continue
            psname = self.step_map [pstype]
            self.log.debug ("ID %s StepTypeDesc: %s" % (problem_id, pstype))
            if self.step_keep [psname]['latest']:
                # Only keep newest
                if pstype not in latest or latest [pstype] < psid:
                    latest [pstype] = psid
            if pstype in self.step_map:
                steplist.add (psid)
        head = parent.header.header ('GetProcessStepsRequest')
        info = parent.client.service.GetProcessSteps \
            ( UserAuthentification = parent.auth
            , ProblemNumber        = problem_id
            , ProcessStepId        = list (steplist | set (latest.values ()))
            , _soapheaders         = head
            )
        parent.check_error ('GetProcessStepList', info)
        self.steps = info ['ProcessStep']
        self.compute ()
    # end def __init__

    def compute (self):
        for k in self.rev_step_map:
            self.history [k] = []
        for ps in self.steps:
            pstype = ps ['ProcessStepTypeDescription']
            psname = self.step_map [pstype]
            psid   = ps ['ProcessStepId']
            if self.step_keep [psname]['history']:
                self.history [self.step_map [pstype]].append (ps)
            if  (   self.step_keep [psname]['latest']
                and self.latest_steps [pstype] == psid
                ):
                assert pstype not in self.latest
                self.latest [pstype] = ps
        # Sort each history by ProcessStepId
        for k in self.history:
            self.history [k].sort (key = lambda x: x ['ProcessStepId'])
    # end def compute

    def __bool__ (self):
        return bool (self.steps)
    # end def __bool__

# end class Process_Steps

class Sync_Attribute_KPM_Message (tracker_sync.Sync_Attribute):

    def __init__ \
        ( self
        , prefix           = None
        , local_prefix     = None
        , kpm_process_step = 'Aussage'
        , ** kw
        ):
        self.__super.__init__ (local_name = None, ** kw)
        self.prefix           = prefix
        self.local_prefix     = local_prefix
        self.kpm_process_step = kpm_process_step
    # end def __init__

    def sync (self, syncer, id, remote_issue):
        """ Note that like for all Sync_Attribute classes the remote
            issue is the KPM issue.
        """
        if self.only_assigned and not remote_issue.is_assigned:
            return
        if self.l_only_update and syncer.get_existing_id (id) is None:
            return
        kpm = remote_issue.kpm
        kpm_attribute = Process_Steps.step_map [self.kpm_process_step]
        lmsg = syncer.get_messages (id)
        # Get previously synced keys
        remote_issue.get_old_message_keys (syncer)
        local_issue = syncer.localissues [id]
        pssteps = getattr (remote_issue, kpm_attribute, [])
        for k in pssteps:
            a = getattr (remote_issue, kpm_attribute) [k]
            if a.get ('foreign_id'):
                continue
            content = a ['content']
            if self.local_prefix:
                content = self.local_prefix + content
            message = local_issue.Message_Class \
                ( local_issue
                , id      = k
                , date    = datetime.strptime
                    (a ['date'], '%Y-%m-%d-%H.%M.%S.%f')
                , content = content
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
                remote_issue.add_message (msg, typ = self.kpm_process_step)
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
            , LOCAL_TRACKER       = 'jira'
            , KPM_CERTPATH        = '/etc/trackersync/kpm_certificate.pem'
            , KPM_KEYPATH         = '/etc/trackersync/kpm_certificate.key'
            , KPM_STAGE           = 'Production'
            # Override KPM_CERTPATH and KPM_KEYPATH above with a pkcs12
            # certificate if necessary.
            , KPM_PKCS12_PATH     = None
            , KPM_PKCS12_PASSWORD = None
            , LOCAL_PROJECT       = None
            , LOCAL_ISSUETYPE     = None
            # This is used when creating new remote issues for limiting
            # the issues found by the local search, it should contain
            # query parameters for a query URL for the local tracker
            # used (e.g. jira).
            , LOCAL_QUERY         = {}
            # This is a limit *in KPM*, so it should typically *not* be
            # changed unless something in KPM changes. If a file
            # attachment is too large, we only get 'Internal Error' back
            # from KPM, so it makes more sense to check up front the
            # size before trying.
            , KPM_MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024 # 10MB
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
        if f is None:
            self.issue.log.debug ('get_file returns None')
        else:
            self.issue.log.debug ('Got file: %s' % f ['Name'])
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

    def create (self):
        """ Create this file in the backend.
            Note that self.id may be created on creation.
        """
        self.issue.kpm.add_file (self)
    # end def create

# end class KPM_File_Attachment

class Problem (tracker_sync.Remote_Issue):

    # Allow to access deep datastructures with multilevel keys delimited
    # with '.'
    multilevel = True

    File_Attachment_Class = KPM_File_Attachment

    def __init__ (self, kpm, rec, canceled = False, raw = False):
        self.kpm         = kpm
        self.debug       = self.kpm.debug
        self.canceled    = canceled
        self.raw         = raw
        # No actions allowed on new remote issue
        if not rec:
            self.allowed_actions = set ()
            # Initialize some hierarchical data structures for new issue
            rec ['Creator'] = {}
            rec ['Creator']['Address'] = {}
            rec ['Coordinator'] = {}
            rec ['Coordinator']['Contractor'] = {}
            rec ['Coordinator']['Contractor']['Address'] = {}
            rec ['ForemostTestPart'] = {}
            rec ['ForemostTestPart']['PartNumber'] = {}
            rec ['ForemostGroupProject'] = {}
            rec ['Origin'] = {}
            # Some defaults:
            rec ['Workflow']   = '42'
            rec ['Visibility'] = '0'
            rec ['Repeatable'] = 'XH'
            rec ['Frequency']  = 'XG'
            # A new issue is never assigned
            self.is_assigned = False
        # We can restrict the attributes to be synced to an explicit
        # subset. The default is no restriction with attributes = {}
        attributes = {}
        if self.canceled:
            attributes ['Status'] = True
        self.__super.__init__ (rec, attributes)
        try:
            self.id = self.record ['ProblemNumber']
        except (AttributeError, KeyError):
            self.id = None
        self.messages = []
    # end def __init__

    def add_message (self, msg, typ = 'Aussage'):
        self.dirty = True
        msgid = self.kpm.add_message (self, msg, typ = typ)
        return msgid
    # end def add_message

    def apply_old_values (self, old_rec):
        rec = self.record
        for k in old_rec:
            if k not in rec:
                rec [k] = old_rec [k]
            elif k in Process_Steps.rev_step_map:
                # Copy non-existing process steps
                # Should really never happen
                for pk in old_rec [k]:
                    if pk not in rec [k]:
                        rec [k][pk] = old_rec [k][pk].copy ()
                # Special case for Supplier_Response:
                # We need to copy the last sync date *and content*
                # from old_rec
                if k == 'Supplier_Response':
                    # Last key
                    m = max (rec [k])
                    n_r = rec [k][m]
                    if m in old_rec [k] and 'last_sync' in old_rec [k][m]:
                        o_r = old_rec [k][m]
                        n_r ['last_sync'] = o_r ['last_sync']
                        n_r ['content']   = o_r ['content']
                        rec ['SupplierResponse'] = o_r ['content']
                        for k in self.kpm.supp_status_keys:
                            v = o_r.get ('Supplier' + k, None)
                            if v:
                                n_r ['Supplier' + k] = v
    # end def apply_old_values

    def attach_file (self, other, name = None):
        self.kpm.log.debug ('Attaching file "%s" to kpm' % other.name)
        f = self._attach_file (KPM_File_Attachment, other)
        if f is None:
            return
        f.create ()
    # end def attach_file

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

    def create (self):
        """ Create new remote issue
        """
        head  = self.kpm.header.header ('CreateDevelopmentProblemRequest')
        nv    = self.newvalues
        creat = self.kpm.fac.Contractor (** nv ['Creator'])
        coord = self.kpm.fac.Order      (** nv ['Coordinator'])
        tpart = self.kpm.fac.TestPart   (** nv ['ForemostTestPart'])
        gpr   = None
        orig  = None
        if self.get ('ForemostGroupProject'):
            gpr  = self.kpm.fac.GroupProject \
                (** self.get ('ForemostGroupProject'))
        if self.get ('Origin'):
            orig = self.kpm.fac.Origin (** self.get ('Origin'))
        l_id  = nv ['NewSupplierErrorNumber']
        self.kpm.log.debug ('Create remote issue for "%s"' % l_id)
        if self.kpm.dry_run:
            self.kpm.log.debug ('Not creating: Dry run')
            return 'Not-created'
        # This consists of CoreProblem + a sequence
        # The first part of CoreProblem is a ProblemReference
        # We don't have any attributes from ProblemReference
        keys = \
            ( 'Exclaimer'
            , 'ProblemDate', 'ProblemStatus', 'DescriptionNational'
            , 'ActiveRole', 'MasterProblemNumber', 'ProblemLinkList'
            , 'ProblemSlaveList', 'VBV', 'Section'
            , 'AdditionalCriteriaList', 'ForemostTestVehicle', 'EProject'
            , 'AuthorityToClose', 'AuthorityToOutgoingCheck'
            , 'SpecialistCoordinator', 'Function', 'Kefa', 'Country'
            , 'ModuleRelevant', 'Module', 'EngineeringStatus'
            , 'SupplierStatus', 'EstimatedStartDate', 'Keyword'
            , 'Supplier', 'FollowUp', 'TCB', 'CommitteeList'
            , 'RefNrSupplier', 'LaunchPriority', 'TestOrderId'
            , 'TestCaseId', 'VehicleSopId', 'RequirementId'
            , 'TrafficLight', 'BSMRelevant', 'DriveType', 'ForecastDate'
            , 'CyberSecurity', 'VerbundRelease', 'SollVerbundRelease'
            , 'FixVerbundRelease', 'ProblemType'
            )
        kw = dict ((k, self.get (k)) for k in keys)
        # The explicitly listed items are probably required or at least
        # highly recommended.
        prob = self.kpm.fac.DevelopmentProblem \
            ( ExternalProblemNumber = l_id
            , Workflow              = self.get ('Workflow')
            , Rating                = nv ['Rating']
            , Description           = sanitize (nv ['Description'])
            , ShortText             = sanitize (nv ['ShortText'])
            , Origin                = orig
            , Creator               = creat
            , Coordinator           = coord
            # Here ends type CoreProblem
            , Visibility            = self.get ('Visibility')
            , StartOfProductionDate = self.get ('StartOfProductionDate')
            , ForemostGroupProject  = gpr
            , Frequency             = self.get ('Frequency')
            , Repeatable            = self.get ('Repeatable')
            , ForemostTestPart      = tpart
            , **kw
            )
        s = str (prob)
        for line in s.split ('\n'):
            self.kpm.log.debug ('Problem: %s' % line)
        r = self.kpm.client.service.CreateDevelopmentProblem \
            ( UserAuthentification  = self.kpm.auth
            , DevelopmentProblem    = prob
            , _soapheaders          = head
            )
        # If we cannot create the issue, this is a fatal error for now:
        if self.kpm.check_error ('CreateDevelopmentProblem', r):
            raise ValueError ('Got error on creation')
        id = str (r ['ProblemNumber'])
        self.set ('ProblemNumber', id, 'string')
        return id
    # end def create

    def equal (self, lv, rv):
        """ Comparison method for remote and local value.
            KPM seems to remove whitespace at end of line.
            The old KPM also used latin1 encoding, hopefully it is no
            longer necessary to do a lossy conversion to latin1 for
            comparing the results.
        """
        if isinstance (lv, string_types) and isinstance (rv, string_types):
            lv = '\n'.join (x.rstrip () for x in lv.split ('\n') if x.rstrip ())
            rv = '\n'.join (x.rstrip () for x in rv.split ('\n') if x.rstrip ())
            # KPM seems to sometimes convert non-breaking space \xa0 to space
            lv = lv.replace ('\xa0', ' ')
            rv = rv.replace ('\xa0', ' ')
        return self.__super.equal (lv, rv)
    # end def equal

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

    def get (self, name, default = None):
        try:
            return self [name]
        except KeyError:
            pass
        if name is None or not '.' in name:
            return default
        n, r = name.rsplit ('.', 1)
        try:
            v = self [n]
        except KeyError:
            return default
        if isinstance (v, list):
            if not len (v):
                return v
            if isinstance (v [0], dict):
                v = [k [r] for k in v]
                return v
        return default
    # end def get

    def get_old_message_keys (self, syncer):
        for typ in Process_Steps.step_map:
            kpm_attribute = Process_Steps.step_map [typ]
            content = syncer.oldremote.get (kpm_attribute, {})
            if kpm_attribute not in self.record:
                self.record [kpm_attribute] = {}
            for k in content:
                d = content [k]
                if 'foreign_id' in d:
                    if k not in self [kpm_attribute]:
                        self [kpm_attribute][k] = {}
                    self [kpm_attribute][k]['foreign_id'] = d ['foreign_id']
        self.msg_by_foreign_id = {}
        for typ in Process_Steps.step_map:
            kpm_attribute = Process_Steps.step_map [typ]
            try:
                d = self [kpm_attribute]
            except KeyError:
                continue
            for k in d:
                m = d [k]
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

class Process_Step_Formatter:

    def __init__ (self, step_history):
        self.history = step_history
    # end def __init__

    def __str__ (self):
        r = []
        for ps in self.history:
            date = self.convert_date (ps ['CreationDate'])
            txt  = ps ['Text']
            uid  = ''
            name = ''
            n    = ''
            if 'LastChanger' in ps:
                uid  = ps ['LastChanger']['UserId']
                name = ps ['LastChanger']['UserName']
            elif 'Creator' in ps:
                uid  = ps ['Creator']['UserId']
                name = ps ['Creator']['UserName']
            if name:
                n = '%s (%s)' % (name, uid)
            r.append ('%s %s:' % (date, n))
            r.append (txt)
            r.append ('')
        return '\n'.join (r)
    # end def __str__
    __repr__ = __str__

    def convert_date (self, value):
        """ Convert date from Process_Step representation
        """
        if not value:
            return ''
        try:
            dt = datetime.strptime (value, "%Y-%m-%d-%H.%M.%S.%f")
            return dt.strftime ('%Y-%m-%d %H.%M.%S')
        except ValueError:
            pass
        return value
    # end def convert_date

# end class Process_Step_Formatter

class KPM_WS (Log, Lock_Mixin):
    """ Interactions with the KPM web service interface
    """
    # keys in SupplierResponse in ProcessStep of Type 'Lieferantenaussage'
    supp_status_keys = ('Status', 'ErrorNumber', 'VersionOk', 'DueDate')

    def __init__ \
        ( self
        , cfg
        , opt
        , dry_run = False
        , ** kw
        ):
        self.cfg      = cfg
        self.opt      = opt
        self.cert     = cfg.KPM_CERTPATH
        self.key      = cfg.KPM_KEYPATH
        self.wsdl     = cfg.KPM_WSDL
        self.url      = cfg.KPM_WS
        self.timeout  = opt.timeout
        self.verbose  = opt.verbose
        self.debug    = opt.debug
        self.dry_run  = dry_run
        self.session  = requests.Session ()
        if 'log_level' not in kw:
            kw ['log_level'] = getattr (logging, opt.log_level.upper ())
        if self.timeout:
            self.session.timeout = self.timeout
        if cfg.KPM_PKCS12_PATH:
            if not Pkcs12Adapter:
                raise RuntimeError \
                    ("PKCS12 configured but requests_pkcs12 not installed")
            d = dict (pkcs12_filename = cfg.KPM_PKCS12_PATH)
            if cfg.KPM_PKCS12_PASSWORD:
                d.update (pkcs12_password = cfg.KPM_PKCS12_PASSWORD)
            adapter = Pkcs12Adapter (**d)
            prefix = cfg.KPM_SITE
            self.session.mount (prefix, adapter)
        else:
            self.session.cert = (self.cert, self.key)
        transport   = Transport \
            (session = self.session, operation_timeout = self.timeout)
        self.client = Client (self.wsdl, transport = transport)
        self.client.settings.strict = False
        self.fac    = self.client.type_factory ('ns0')
        self.auth   = self.fac.UserAuthentification \
            (UserId = self.cfg.KPM_USERNAME)
        self.adr    = self.fac.Address \
            (OrganisationalUnit = self.cfg.KPM_OU, Plant = self.cfg.KPM_PLANT)
        if opt.lock_name:
            self.lockfile = opt.lock_name
        self.header = KPM_Header (stage = self.cfg.KPM_STAGE)
        self.__super.__init__ (** kw)
        if opt.log_file:
            handler = logging.FileHandler (opt.log_file)
            level   = getattr (logging, opt.file_log_level.upper ())
            handler.setLevel (level)
            self.log.addHandler (handler)
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
            p = self.get_problem (pr ['ProblemNumber'])
            if p is not None:
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
        if 'success' in txt:
            return 0
        if 'Method completed with warnings' in txt:
            self.log.warn ("%s%s: Warning: %s" % (c, rq, txt))
            return 0
        self.log.error ("%s%s: Error: %s" % (c, rq, txt))
        return 1
    # end def check_error

    def add_file (self, doc):
        issue = doc.issue
        self.log.debug ('Adding file "%s" to KPM' % doc.name)
        if 'ADD_DOCUMENT' not in issue.allowed_actions:
            self.log.error \
                ('No permission to add document for %s' % issue.id)
            return
        leng = len (doc.content)
        if leng > self.cfg.KPM_MAX_ATTACHMENT_SIZE:
            self.log.error \
                ( 'Document %s is too large for KPM (%s > %s)'
                % (doc.name, leng, self.cfg.KPM_MAX_ATTACHMENT_SIZE)
                )
            return
        head = self.header.header ('AddDocumentRequest')
        name, suffix = os.path.splitext (doc.name)
        # Max len of suffix is 4 and we don't want leading dots
        suffix = suffix.lstrip ('.')[:4]
        kpmdoc = self.fac.Document \
            ( AccessRight          = "0"
            , Name                 = name
            , Size                 = leng
            , Suffix               = suffix
            , Data                 = doc.content
            )
        ans = self.client.service.AddDocument \
            ( UserAuthentification = self.auth
            , ProblemNumber        = issue.id
            , Document             = kpmdoc
            , _soapheaders         = head
            )
        if self.check_error ('AddDocument', ans):
            return
        doc.id = ans ['DocumentReference']
    # end def add_file

    def add_message (self, problem, msg, typ = 'Aussage'):
        kpm_attribute = Process_Steps.step_map [typ]
        err = 0
        if typ == 'Aussage':
            if 'ADD_NOTICE' not in problem.allowed_actions:
                self.log.error \
                    ('No permission to add message to %s' % problem.id)
                return
            head = self.header.header ('AddNoticeRequest')
            r    = self.client.service.AddNotice \
                ( UserAuthentification = self.auth
                , ProblemNumber        = problem.ProblemNumber
                , Notice               = sanitize (msg.content)
                , _soapheaders         = head
                )
            err = self.check_error ('AddNotice', r)
        elif typ == 'Rückfrage':
            # FIXME: We should check for the action being present in
            # problem.allowed_actions (see above for ADD_NOTICE).
            # The string from the error message when this fails is:
            # Communication: AddSupplierQuestion: Error: The user has no
            # permission to execute action: ADD_SUPPLIER_QUESTION
            # So the string *probably* is 'ADD_SUPPLIER_QUESTION'
            self.log.info \
                ( 'Allowed actions during supplier question: %s'
                % problem.allowed_actions
                )
            head = self.header.header ('AddSupplierQuestionRequest')
            r    = self.client.service.AddSupplierQuestion \
                ( UserAuthentification = self.auth
                , ProblemNumber        = problem.ProblemNumber
                , SupplierQuestion     = sanitize (msg.content)
                , _soapheaders         = head
                )
            err = self.check_error ('AddSupplierQuestion', r)
        else:
            raise NotImplementedError \
                ('ProcessStepTypeDescription "%s" not implemented' % typ)
        if err:
            self.log.error ("add_message failed for %s" % problem.id)
            return
        id = r ['ProcessStepId']
        id = self.fix_process_step_date (id)
        d = getattr (problem, kpm_attribute)
        d [id] = dict \
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
        self.log.debug ('Getting file %s' % doc.id)
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

    def get_problem (self, id, old_rec = None):
        head   = self.header.header ('GetProblemActionsRequest')
        rights = self.client.service.GetProblemActions \
            ( UserAuthentification = self.auth
            , ProblemNumber        = id
            , _soapheaders         = head
            )
        if self.check_error ('GetProblemActions', rights):
            return
        actions = set (rights ['Action'])
        rec = {}
        raw = None
        if 'GET_DEVELOPMENT_PROBLEM_DATA' in actions:
            head = self.header.header ('GetDevelopmentProblemDataRequest')
            rec  = self.client.service.GetDevelopmentProblemData \
                ( UserAuthentification = self.auth
                , ProblemNumber        = id
                , _soapheaders         = head
                )
            if self.check_error ('GetDevelopmentProblemData', rec):
                return
            rec = rec ['DevelopmentProblem']
            rec = serialize_object (rec)
            raw = rec.get ('_raw_elements', None)
            self.make_serializable (rec)
        elif not old_rec:
            self.log.info ("No right to get problem data for %s" % id)
            return
        pss = Process_Steps (self, id, actions)
        if not pss and old_rec:
            old_rec ['__readable__'] = False
            return
        for rl in Process_Steps.step_map:
            recname = Process_Steps.step_map [rl]
            rec [recname] = {}
        if 'Supplier_Response' in pss.latest:
            ps = pss.latest ['Supplier_Response']
            rec ['__readable__'] = True
            sr = ps ['SupplierResponse']
            rec ['SupplierResponse'] = ps ['Text']
            if sr is not None:
                for k in self.supp_status_keys:
                    # The SupplierStatus is natively in data
                    # retrieved via GetDevelopmentProblemData
                    combined_k = 'Supplier' + k
                    if combined_k not in rec:
                        rec [combined_k] = sr [k]
        if 'Analysis_All' in pss.latest:
            rec ['Analysis'] = pss.latest ['Analysis_All']['Text']
        if 'Analysis_All' in pss.history:
            v = Process_Step_Formatter (pss.history ['Analysis_All'])
            rec ['Analysis_History'] = str (v)

        for recname in pss.history:
            for ps in pss.history [recname]:
                pstype = ps ['ProcessStepTypeDescription']
                psid   = ps ['ProcessStepId']
                rec [recname][psid] = ps_rec = dict \
                    ( id      = psid
                    , date    = ps ['CreationDate']
                    , content = ps ['Text']
                    )
                if pstype == 'Lieferantenaussage':
                    sr = ps ['SupplierResponse']
                    if sr is not None:
                        for k in self.supp_status_keys:
                            ps_rec ['Supplier' + k] = sr [k]

        p = Problem (self, rec, raw = raw)
        if p.id and old_rec:
            p.apply_old_values (old_rec)
        # If raw elements exist, parsing wasn't fully successful
        if p.id and p.raw:
            tags = ','.join (x.tag for x in p.raw)
            self.log.warn \
                ('KPM-%s has raw elements with tags: %s' % (p.id, tags))
        p.allowed_actions = actions
        return p
    # end def get_problem

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
        d = dict (ErrorNumber = problem.SupplierErrorNumber)
        try:
            # Special case: KPM will send us '-' to reset to open but will
            # not accept '-' in return, we cannot distinguish the two as
            # both are mapped to the same local status
            if problem.SupplierStatus == '-':
                problem.SupplierStatus = '1'
            d ['Status'] = problem.SupplierStatus
        except AttributeError:
            pass
        d ['VersionOk'] = problem.newvalues.get ('SupplierVersionOk', None)
        sr = self.fac.SupplierResponse (** d)
        h = self.header.header ('AddSupplierResponseRequest')
        d = dict \
            ( UserAuthentification = self.auth
            , ProblemNumber        = problem.ProblemNumber
            , SupplierResponse     = sr
            , _soapheaders         = h
            )
        resp = getattr (problem, 'SupplierResponse', '')
        d ['ResponseText'] = resp
        if 'ADD_SUPPLIER_RESPONSE' not in problem.allowed_actions:
            self.log.error \
                ('No permission to set supplier response for %s' % problem.id)
        else:
            r = self.client.service.AddSupplierResponse (** d)
            if self.check_error ('AddSupplierResponse', r):
                return
            id = r ['ProcessStepId']
            id = self.fix_process_step_date (id)
            d  = getattr (problem, 'Supplier_Response', None)
            if not d:
                problem.Supplier_Response = {}
            ts = datetime.strftime (datetime.utcnow (), '%Y-%m-%d.%H:%M:%S')
            # We deliberately produce a timestamp *now* in a different
            # format than the one from KPM.
            d [id] = dict \
                ( id         = id
                , content    = problem.SupplierResponse
                , date       = id
                , last_sync  = ts
                , SupplierErrorNumber = problem.SupplierErrorNumber
                , SupplierVersionOk   = getattr
                    (problem, 'SupplierVersionOk', None)
                , SupplierStatus      = getattr
                    (problem, 'SupplierStatus', None)
                )
    # end def update_supplier_response

# end class KPM_WS

local_trackers = dict (jira = jira_sync.Syncer)

def wstest ():
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
        , opt     = opt
        , dry_run = True
        )
    head = KPM_Header (stage = 'Production')
    if opt.debug :
        x = kpm.client.create_message \
            ( kpm.client.service
            , 'GetServiceInfo'
            , UserAuthentification = kpm.auth
            , _soapheaders = head.header ('GetServiceInfoRequest')
            )
        print (tostring (x, pretty_print = True, encoding = 'unicode'))
    vv = kpm.client.service.GetServiceInfo \
        ( UserAuthentification = kpm.auth
        , _soapheaders = head.header ('GetServiceInfoRequest')
        )
    print (vv)

    if opt.verbose :
        for problem in kpm :
            print (problem)
# end def wstest

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
        ( "--file-log-level"
        , help    = "Loglevel for logging to file, default=%(default)s,"
                    " this is only relevant with --log-file option"
        , default = 'INFO'
        , choices = ('CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG')
        )
    cmd.add_argument \
        ( "--issue-type"
        , help    = "Issue type of local tracker"
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
        ( "--log-file"
        , help    = "Log to file in addtion to syslog"
        )
    cmd.add_argument \
        ( "--log-level"
        , help    = "Loglevel for logging backend, default=%(default)s"
        , default = 'INFO'
        , choices = ('CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG')
        )
    cmd.add_argument \
        ( "-M", "--no-mangle-filenames"
        , help    = "Allow more than only ascii for file names"
                    " Default=%(default)s"
        , action  = 'store_true'
        , default = False
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
        ( "--project-key"
        , help    = "Project key in local tracker"
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
    opt       = cmd.parse_args ()
    config    = Config.config
    cfgpath   = Config.path
    if opt.config:
        cfgpath, config = os.path.split (opt.config)
        config = os.path.splitext (config) [0]
    cfg = Config (path = cfgpath, config = config)
    kpm = KPM_WS \
        ( cfg       = cfg
        , opt       = opt
        , dry_run   = opt.dry_run or opt.remote_dry_run
        )
    url       = opt.url         or cfg.get ('LOCAL_URL', None)
    lpassword = opt.local_password or cfg.LOCAL_PASSWORD
    lusername = opt.local_username or cfg.LOCAL_USERNAME
    ltracker  = opt.local_tracker  or cfg.LOCAL_TRACKER
    lproject  = opt.project_key    or cfg.LOCAL_PROJECT
    lissue    = opt.issue_type     or cfg.LOCAL_ISSUETYPE
    opt.local_password = lpassword
    opt.local_username = lusername
    opt.url            = url
    opt.local_tracker  = ltracker
    opt.project_key    = lproject
    opt.issue_type     = lissue
    syncer = None
    if url and cfg.get ('KPM_ATTRIBUTES'):
        try:
            syncer = local_trackers [opt.local_tracker] \
                ('KPM', cfg.KPM_ATTRIBUTES, opt, cfg, log = kpm.log)
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

    # First get all *existing* old issues:
    old_issues = dict.fromkeys (syncer.oldsync_iter ())
    nproblems = 0
    try:
        for problem in kpm:
            if problem.id in old_issues:
                # This fixes issues with KPM losing info:
                problem.apply_old_values \
                    (syncer.compute_oldvalues (problem.id))
                del old_issues [problem.id]
            problem.sync (syncer)
            nproblems += 1
        if old_issues:
            syncer.log.warn \
                ('Processing %s issues not found in mailbox' % len (old_issues))
            for id in old_issues:
                oldid = syncer.get_oldvalues (id)
                if not oldid:
                    syncer.log.error \
                        ('Cannot get old KPM issue %s/%s' % (oldid, id))
                else:
                    problem = kpm.get_problem (id, syncer.oldremote)
                    if problem is None or problem.id is None:
                        syncer.log.warn \
                            ('KPM issue "%s" not found/readable' % id)
                        # This attempts to set __readable__ and
                        # associated sync rules
                        rec = syncer.oldremote.copy ()
                        rec ['__readable__'] = False
                        problem = Problem (kpm, rec)
                        problem.allowed_actions = set ()
                        # Sync *only* the __readable__ attribute
                        problem.attributes ['__readable__'] = True
                        problem.sync (syncer)
                    else:
                        problem.is_assigned = False
                        syncer.log.warn ('Processing KPM issue "%s"' % id)
                        problem.sync (syncer)
                        nproblems += 1
        syncer.sync_new_local_issues (lambda x: Problem (kpm, x))
    except Exception as err:
        kpm.log_exception ()
        if isinstance (err, Fault):
            kpm.log.error \
                ( 'Zeep Fault: "%s" code: %s actor: %s'
                % (err.message, err.code, err.actor)
                )
            s = tostring (err.detail, pretty_print = True, encoding = 'unicode')
            for line in s.split ('\n'):
                kpm.log.error (line)
        kpm.log.error \
            ("Exception while syncing, synced %d KPM issues" % nproblems)
        # Normally unlock is registered as an atexit handler.
        # No idea why this is not called when a zeep exception occurs.
        kpm.unlock ()
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
