#!/usr/bin/python
# Copyright (C) 2019 Dr. Ralf Schlatterbeck Open Source Consulting.
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
from __future__ import absolute_import

""" Example configuration for Pfiff Sync with Jira """

from trackersync import jira_sync
from trackersync import pfiffsync

LOCAL_URL      = 'https://jira.example.com/rest/api/2'
LOCAL_USERNAME = 'localuser'
LOCAL_PASSWORD = 'localsecret'
LOCAL_TRACKER  = 'jira'
COMPANY        = 'TestPrj Zulieferer'
COMPANY_SHORT  = 'TPZ'

oftp_pfx       = 'oftp-server.example.com:/home/oftp/oftp2_1.1b39/messages/'
OFTP_INCOMING  = oftp_pfx + 'Supplier/inbox/RemotePartnerO00XXXXXXXXXXXXXXX'
OFTP_TMP_OUT   = oftp_pfx + 'tmp'
OFTP_OUTGOING  = oftp_pfx + 'RemotePartnerO00XXXXXXXXXXXXXXX/outbox'
LOCAL_TMP      = '.../trackersync/tmp'
LOCAL_OUT_TMP  = '.../trackersync/out'

SSH_KEY        = '/home/syncuser/.ssh/oftp'
SSH_PASSPHRASE = 'GEHEIM'
SSH_USER       = 'syncuser'

ENGDAT_PEER_ID      = 'O00XXXXXXXXXXXXXXX'
ENGDAT_PEER_ROUTING = 'ROUTING-Code-PEER'
ENGDAT_PEER_NAME    = 'OEM Name'
ENGDAT_PEER_ADR1    = 'OEM ADDR1'
ENGDAT_PEER_ADR2    = 'OEM ADDR1'
ENGDAT_PEER_ADR3    = 'GERMANY (Federal Republic of)'
ENGDAT_PEER_COUNTRY = 'DE'
ENGDAT_PEER_DEPT    = 'OEM Department'
ENGDAT_PEER_EMAIL   = 'oem@example.com'

ENGDAT_OWN_ID       = 'O0YYYYYYYYYYYYY'
ENGDAT_OWN_ROUTING  = 'ROUTING-Code-Supplier'
ENGDAT_OWN_NAME     = 'Supplier Name'
ENGDAT_OWN_ADR1     = 'Supplier ADDR1'
ENGDAT_OWN_ADR2     = 'Supplier ADDR2'
ENGDAT_OWN_ADR3     = 'Supplier ADDR3'
ENGDAT_OWN_ADR4     = 'GERMANY (Federal Republic of)'
ENGDAT_OWN_COUNTRY  = 'DE'
ENGDAT_OWN_DEPT     = 'Supplier Department'
ENGDAT_OWN_EMAIL    = 'supplier@example.com'

PFIFF_ATTRIBUTES = \
    ( jira_sync.Sync_Attribute_Check
        ( local_name   = 'status.name'
        , remote_name  = None
        , invert       = True
        , update       = False
        , value        = 'Closed'
        )
    , jira_sync.Sync_Attribute_To_Local_Default
        ( local_name   = 'project.key'
        , remote_name  = None
        , r_default    = 'project-key-in-jira'
        )
    , jira_sync.Sync_Attribute_To_Local_Default
        ( local_name   = 'issuetype.name'
        , remote_name  = None
        , r_default    = 'Defect'
        )
    , jira_sync.Sync_Attribute_To_Local_Default
        ( local_name   = 'security.name'
        , remote_name  = None
        , r_default    = 'Project Insider'
        )
    ## "External Ticket" field in Jira
    #, jira_sync.Sync_Attribute_To_Local
    #    ( local_name   = 'customfield_13000'
    #    , remote_name  = 'problem_number'
    #    , local_prefix = 'PFIFF-'
    #    )
    # "External Issue Reference" field in Jira
    , jira_sync.Sync_Attribute_To_Local
        ( local_name   = 'customfield_12600'
        , remote_name  = 'problem_number'
        , local_prefix = 'PFIFF-'
        )
    , jira_sync.Sync_Attribute_To_Local
        ( local_name   = 'summary'
        , remote_name  = 'problem_synopsis'
        , r_default    = '?'
        )
    , jira_sync.Sync_Attribute_To_Local_Multistring
        ( local_name    = 'labels'
        , remote_name   = 'crstatus'
        , prefix        = 'PFIFF-Status-'
        , l_only_update = True
        )
    , jira_sync.Sync_Attribute_To_Local_Multilink_Default
        ( local_name    = 'versions.id'
        , remote_name   = 'component_sw_version'
        , r_default     = 'Default-Release'
        , use_r_default = True
        )
    , jira_sync.Sync_Attribute_To_Local_Concatenate
        ( local_name    = 'description'
        , remote_names  =
          [ 'problem_description'
          , 'in_analyse_comments'
          , 'action_points'
          , 'ee_top_topic'
          , 'owner_fp'
          , 'component_sw_version'
          , 'component_hw_version'
          , 'release_wanted'
          , 'reproducibility'
          , 'test_case'
          , 'trial_units'
          , 'function_group'
          , 'function_component'
          , 'vehicle_project'
          , 'vehicle'
          , 'var_product_name'
          , 'bug_classification'
          , 'crstatus'
          , 'ets'
          , 'ets_status'
          ]
        , delimiter     = '\n\n'
        , field_prefix  = '*'
        , field_postfix = ':*\n'
        )
    , jira_sync.Sync_Attribute_To_Local_Multistring
        ( local_name    = 'labels'
        , remote_name   = 'release_wanted'
        , prefix        = 'PFIFF-Release-Wanted-'
        , l_only_update = True
        )
    # "Release Note" field in Jira
    , jira_sync.Sync_Attribute_To_Local_Default
        ( local_name    = 'customfield_12009'
        , remote_name   = 'supplier_comments'
        , r_default     = 'Under Investigation'
        , l_only_update = True
        )
    # "Release Note" field in Jira
    , jira_sync.Sync_Attribute_To_Remote
        ( local_name   = 'customfield_12009'
        , remote_name  = 'supplier_comments'
        )
    # priority can currently only be set during creation
    , jira_sync.Sync_Attribute_To_Local_Default
        ( local_name   = 'priority.name'
        , remote_name  = 'priority'
        , r_default    = 'Minor'
        , l_default    = 'MEDIUM'
        , only_update  = True
        , imap = dict
            ( TOP     = 'Showstopper'
            , HIGH    = 'Major'
            , MEDIUM  = 'Minor'
            , LOW     = 'Minor'
            )
        )
    , jira_sync.Sync_Attribute_To_Local_Multistring
        ( local_name    = 'labels'
        , remote_name   = 'priority'
        , prefix        = 'PFIFF-Priority-'
        , l_only_update = True
        )
    , jira_sync.Sync_Attribute_Multi_To_Remote
        ( local_names  = ('status.name', 'resolution.name')
        , remote_name  = 'supplier_status'
        , map =
            ( (('Analyzing',                  None),   'RECEIVED')
            , (('Suspended',                  None),   'RECEIVED')
            , (('Open',                       None),   'RECEIVED')
            , (('Implementation Pending',     None),   'ESTIMATED')
            , (('Implementation in Progress', None),   'ESTIMATED')
            , (('Verification Pending',       None),   'DELIVERED')
            , (('Verification in Progress',   None),   'DELIVERED')
            , (('Closed',                     'Done'), 'CLOSED')
            , (('Closed',                     None),   'REJECTED')
            , (('Deciding',                   None),   'RECEIVED')
            , (('To Do',                      None),   'RECEIVED')
            , (('Implementation Approval',    None),   'ESTIMATED')
            , (('In Progress',                None),   'ESTIMATED')
            , (('Calibration due',            None),   'ESTIMATED')
            , (('Calibration in progress',    None),   'ESTIMATED')
            , (('Active',                     None),   'ESTIMATED')
            , (('Suspension Approval',        None),   'RECEIVED')
            , (('Obsolete',                   None),   'REJECTED')
            , (('Calibrated',                 None),   'DELIVERED')
            , (('Exempt from Calibration',    None),   'DELIVERED')
            )
        )
    , jira_sync.Sync_Attribute_To_Remote
        ( local_name   = 'key'
        , remote_name  = 'supplier_company_id'
        )
    , jira_sync.Sync_Attribute_To_Remote
        ( local_name     = 'fixVersions.name'
        , remote_name    = 'resolved_in_release'
        , join_multilink = True
        )
    , jira_sync.Sync_Attribute_To_Remote
        ( local_name     = 'fixVersions.name'
        , remote_name    = 'resolve_until_release'
        , join_multilink = True
        )
    , jira_sync.Sync_Attribute_Files ()
    , pfiffsync.Sync_Attribute_Pfiff_Messages (prefix = '[TO OEM]')
    , jira_sync.Sync_Attribute_To_Remote_If_Dirty
        ( local_name     = 'updated'
        , remote_name    = 'updated'
        )
    , jira_sync.Sync_Attribute_To_Remote_If_Dirty
        ( local_name     = 'assignee.key'
        , remote_name    = 'assignee_key'
        )
    , jira_sync.Sync_Attribute_To_Remote_If_Dirty
        ( local_name     = 'assignee.displayName'
        , remote_name    = 'assignee_name'
        )
    )

