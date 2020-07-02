#!/usr/bin/python
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
from __future__ import absolute_import

""" Example configuration for KPM Sync with Jira """

from trackersync import jira_sync
from trackersync import kpmwssync

KPM_USERNAME   = 'user'
KPM_SITE       = 'https://ws-gateway-cert.volkswagenag.com'
KPM_WS         = KPM_SITE + '/PP/QM/GroupProblemManagementService/V3'
KPM_CERTPATH   = '/etc/trackersync/kpm_certificate.pem'
KPM_KEYPATH    = '/etc/trackersync/kpm_certificate.key'
KPM_WSDL       = '/etc/trackersync/kpm.wsdl'
KPM_OU         = 'KPM-TEST' # OrganisationalUnit
KPM_PLANT      = 'Z$'
LOCAL_URL      = 'https://jira.example.com/rest/api/2'
LOCAL_USERNAME = 'localuser'
LOCAL_PASSWORD = 'localsecret'
LOCAL_TRACKER  = 'jira'

KPM_ATTRIBUTES = \
    ( jira_sync.Sync_Attribute_Check
        ( local_name   = 'status.name'
        , remote_name  = None
        , invert       = True
        , update       = False
        , value        = 'Closed'
        )
    , jira_sync.Sync_Attribute_Check_Remote
        ( local_name   = None
        , remote_name  = 'EngineeringStatus'
        , value        = '2'
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
    # "External Ticket" field in Jira, e.g. customfield_12600
    , jira_sync.Sync_Attribute_To_Local
        ( local_name   = 'customfield_12600'
        , remote_name  = 'ProblemNumber'
        , local_prefix = 'KPM-'
        )
    , jira_sync.Sync_Attribute_To_Local
        ( local_name   = 'summary'
        , remote_name  = 'ShortText'
        , r_default    = '?'
        )
    , jira_sync.Sync_Attribute_To_Local_Multistring
        ( local_name    = 'labels'
        , remote_name   = 'EngineeringStatus'
        , prefix        = 'KPM-FB-Status-'
        , l_only_update = True
        )
    , jira_sync.Sync_Attribute_To_Local_Multilink_Default
        ( local_name    = 'versions.id'
        , remote_name   = 'ForemostTestPart.Software'
        , r_default     = 'defaultversion'
        , use_r_default = True
        )
    , jira_sync.Sync_Attribute_To_Local_Concatenate
        ( local_name    = 'description'
        , remote_names  =
          [ 'Description'
          , 'Analysis'
          , 'Rating'
          , 'ForemostTestPart.Software'
          , 'ForemostTestPart.Hardware'
          , 'Repeatable'
          , 'Frequency'
          , 'Creator.Address.ContactPerson'
          , 'Creator.PersonalContractor.UserName'
          , 'ProblemSolver.Address.ContactPerson'
          , 'ProblemSolver.Contractor.Address.ContactPerson'
          , 'ProblemSolver.Contractor.PersonalContractor.UserName'
          ]
        , delimiter     = '\n\n'
        , field_prefix  = '*'
        , field_postfix = ':*\n'
        )
    # "Release Note" field in Jira, some customfield_12009
    , jira_sync.Sync_Attribute_To_Local_Default
        ( local_name    = 'customfield_12009'
        , remote_name   = None
        , r_default     = 'Under Investigation'
        , l_only_update = True
        )
    # "Release Note" field in Jira, e.g. customfield_12009
    , jira_sync.Sync_Attribute_To_Remote
        ( local_name   = 'customfield_12009'
        , remote_name  = 'SupplierResponse'
        )
    # priority can currently only be set during creation
    # Seems we have no permission, we get 400 with:
    # id=... {'fields': {'priority': {'name': 'Minor'}}}
    # when trying to set Unspecified -> Minor
    , jira_sync.Sync_Attribute_To_Local_Default
        ( local_name   = 'priority.name'
        , remote_name  = 'Rating'
        , r_default    = 'Minor'
        , l_default    = 'DB'
        , only_update  = True
        #, local_unset  = 'Unspecified'
        , imap =
            { '1'  : 'Showstopper' # A
            , '2'  : 'Showstopper' # A
            , '3'  : 'Showstopper' # A
            , '4'  : 'Major'       # B
            , '5'  : 'Major'       # B
            , '6'  : 'Minor'       # C
            , '7'  : 'Minor'       # C
            , '8'  : 'Minor'       # D
            , '9'  : 'Minor'       # D
            , '10' : 'Minor'       # D
            }
        )
    , jira_sync.Sync_Attribute_To_Remote
        ( local_name   = 'status.name'
        , remote_name  = 'SupplierStatus'
        , map =
            { 'Analyzing'                  : '0'
            , 'Deciding'                   : '0'
            , 'Suspended'                  : '0'
            , 'Open'                       : '1'
            , 'To Do'                      : '1'
            , 'Implementation Approval'    : '1'
            , 'Implementation Pending'     : '1'
            , 'Implementation in Progress' : '1'
            , 'In Progress'                : '1'
            , 'Calibration due'            : '1'
            , 'Calibration in progress'    : '1'
            , 'Active'                     : '1'
            , 'Verification Pending'       : '4'
            , 'Verification in Progress'   : '4'
            , 'Suspension Approval'        : '5'
            , 'Closed'                     : '5'
            , 'Obsolete'                   : '5'
            , 'Calibrated'                 : '5'
            , 'Exempt from Calibration'    : '5'
            }
        )
    , jira_sync.Sync_Attribute_To_Local_Multistring
        ( local_name    = 'labels'
        , remote_name   = 'Rating'
        , prefix        = 'KPM-Priority-'
        , l_only_update = True
        )
    , jira_sync.Sync_Attribute_To_Remote
        ( local_name    = 'key'
        , remote_name   = 'SupplierErrorNumber'
        )
    # FIXME: Does this have a representation in the main problem?
    , jira_sync.Sync_Attribute_To_Remote
        ( local_name     = 'fixVersions.name'
        , remote_name    = 'SupplierVersionOk'
        , join_multilink = True
        )
# FIXME: Maybe we want to transmit a data, is this the expected delivery?
#    , jira_sync.Sync_Attribute_To_Remote
#        ( local_name     = 'FIXME'
#        , remote_name    = 'SupplierResponse.DueDate'
#        )
    , jira_sync.Sync_Attribute_Files (l_only_update = True)
    , kpmwssync.Sync_Attribute_KPM_Message
        ( prefix        = 'TO AUDI:'
        , l_only_update = True
        )
    )

