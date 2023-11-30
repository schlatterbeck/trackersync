#!/usr/bin/python
# Copyright (C) 2021-23 Dr. Ralf Schlatterbeck Open Source Consulting.
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

""" Example configuration for KPM Sync with Jira """

from trackersync import jira_sync
from trackersync import kpmwssync

KPM_USERNAME   = 'user'
KPM_SITE       = 'https://ws-gateway-cert.volkswagenag.com'
KPM_WS         = KPM_SITE + '/PP/QM/GroupProblemManagementService/V3'
KPM_CERTPATH   = '/etc/trackersync/kpm_certificate.pem'
KPM_KEYPATH    = '/etc/trackersync/kpm_certificate.key'
# Instead of KPM_CERTPATH and KPM_KEYPATH you can define a pkcs12
# certificat bundle with KPM_PKCS12_PATH and optionally
# KPM_PKCS12_PASSWORD, the KPM_CERTPATH and KPM_KEYPATH are ignored in
# that case. You need requests-pkcs12 installed for this to work, see
# README.rst for details.
KPM_WSDL        = '/etc/trackersync/kpm.wsdl'
KPM_OU          = 'KPM-TEST' # OrganisationalUnit
KPM_PLANT       = 'Z$'
LOCAL_URL       = 'https://jira.example.com/rest/api/2'
LOCAL_USERNAME  = 'localuser'
LOCAL_PASSWORD  = 'localsecret'
LOCAL_TRACKER   = 'jira'
# These are defaults when setting up a hosted jira at atlassian.net
# Adjust for your project
LOCAL_PROJECT   = 'KAN'
LOCAL_ISSUETYPE = 'Task'

KPM_ATTRIBUTES = \
    ( jira_sync.Sync_Attribute_Check
        ( local_name   = 'status.name'
        , remote_name  = None
        , invert       = True
        , update       = False
        , value        = 'Closed' # or 'Done' or whatever you closed status is
        )
    # The following apply only when considering creation of a remote (KPM)
    # issue, this is selected with the 'only_create' flag.

#    # "External Ticket" field in our test system is customfield_10034
#    # Sync only local issues that do not have an External Ticket set.
#    # This checks for non-empty value and inverts it. So we stop on
#    # empty value. A better variant is below.
#    , jira_sync.Sync_Attribute_Check
#        ( local_name   = 'customfield_10034'
#        , only_create  = True
#        , remote_name  = None
#        , update       = False
#        , invert       = True
#        )
    # "External Ticket" field in our test system is customfield_10034
    # Sync (and create remote issue) only for local issues that have the
    # External Ticket set to 'sync'.
    # The idea here is that the issue is edited until everything is fine
    # and only then set the "External Ticket" field to 'sync'. This
    # avoids that the sync runs in the middle of editing the issue and
    # creates the remote issue with lots of missing values. Note that in
    # KPM currently update after creation is not possible, we have to
    # get it right the first time.
    , jira_sync.Sync_Attribute_Check
        ( local_name   = 'customfield_10034'
        , only_create  = True
        , remote_name  = None
        , update       = False
        , invert       = True
        , value        = 'sync'
        )
    # We create remote issues only if our status is 'Created'
    , jira_sync.Sync_Attribute_Check
        ( local_name   = 'status.name'
        , only_create  = True
        , remote_name  = None
        , update       = False
        , value        = 'Created'
        )
    # We create remote issues only if they have a 'Description'
    , jira_sync.Sync_Attribute_Check
        ( local_name   = 'description'
        , only_create  = True
        , remote_name  = None
        , update       = False
        )

    # This check applies to *all* issues: Sync only when the
    # EngineeringStatus of the remote (KPM) issue is '2'.
    , jira_sync.Sync_Attribute_Check_Remote
        ( local_name   = None
        , remote_name  = 'EngineeringStatus'
        , value        = '2'
        )
    # Hard-coded Attributes for issue creation
    # You should carefully go through these and apply the default values
    # from your project. Note that if there are several parts involved,
    # you probably want to have a 'Project' or 'Part-Number' attribute
    # in your Jira and for each of the attributes below have a mapping
    # from the Jira Project/Part-Number to the respective value in KPM.
    , jira_sync.Sync_Attribute_To_Remote_Default
        ( local_name   = None
        , only_create  = True
        , remote_name  = 'Creator.Address.OrganisationalUnit'
        , l_default    = 'KPM-TEST'
        )
    , jira_sync.Sync_Attribute_To_Remote_Default
        ( local_name   = None
        , only_create  = True
        , remote_name  = 'Creator.Address.Plant'
        , l_default    = 'Z$'
        )
    # we assign to coordinator, different from our mailbox!
    , jira_sync.Sync_Attribute_To_Remote_Default
        ( local_name   = None
        , only_create  = True
        , remote_name  = 'Coordinator.Contractor.Address.OrganisationalUnit'
        , l_default    = 'KPMTEST'
        )
    , jira_sync.Sync_Attribute_To_Remote_Default
        ( local_name   = None
        , only_create  = True
        , remote_name  = 'Coordinator.Contractor.Address.Plant'
        , l_default    = 'Z$'
        )
    , jira_sync.Sync_Attribute_To_Remote_Default
        ( local_name   = None
        , only_create  = True
        , remote_name  = 'StartOfProductionDate'
        , l_default    = '2023-01-01'
        )
    , jira_sync.Sync_Attribute_To_Remote_Default
        ( local_name   = None
        , only_create  = True
        , remote_name  = 'ForemostTestPart.PartNumber.PreNumber'
        , l_default    = '00'
        )
    , jira_sync.Sync_Attribute_To_Remote_Default
        ( local_name   = None
        , only_create  = True
        , remote_name  = 'ForemostTestPart.PartNumber.MiddleGroup'
        , l_default    = '00'
        )
    , jira_sync.Sync_Attribute_To_Remote_Default
        ( local_name   = None
        , only_create  = True
        , remote_name  = 'ForemostTestPart.PartNumber.EndNumber'
        , l_default    = '01'
        )
    , jira_sync.Sync_Attribute_To_Remote_Default
        ( local_name   = None
        , only_create  = True
        , remote_name  = 'ForemostTestPart.PartNumber.Index'
        , l_default    = ''
        )
    , jira_sync.Sync_Attribute_To_Remote_Default
        ( local_name   = None
        , only_create  = True
        , remote_name  = 'ForemostTestPart.Software'
        , l_default    = 'S1'
        )
    , jira_sync.Sync_Attribute_To_Remote_Default
        ( local_name   = None
        , only_create  = True
        , remote_name  = 'ForemostTestPart.Hardware'
        , l_default    = 'H1'
        )
    , jira_sync.Sync_Attribute_To_Remote_Default
        ( local_name   = None
        , only_create  = True
        , remote_name  = 'ForemostGroupProject.Brand'
        , l_default    = 'AU'
        )
    , jira_sync.Sync_Attribute_To_Remote_Default
        ( local_name   = None
        , only_create  = True
        , remote_name  = 'ForemostGroupProject.Project'
        , l_default    = '123'
        )
    , jira_sync.Sync_Attribute_To_Remote_Default
        ( local_name   = None
        , only_create  = True
        , remote_name  = 'Origin.MainProcess'
        , l_default    = 'PEA'
        )
    , jira_sync.Sync_Attribute_To_Remote_Default
        ( local_name   = None
        , only_create  = True
        , remote_name  = 'Origin.Phase'
        , l_default    = 'ALLG'
        )
    , jira_sync.Sync_Attribute_To_Remote_Default
        ( local_name   = None
        , only_create  = True
        , remote_name  = 'Origin.PhaseAddition'
        , l_default    = 'AUDI'
        )
    , jira_sync.Sync_Attribute_To_Remote_Default
        ( local_name   = None
        , only_create  = True
        , remote_name  = 'Origin.SubProcess'
        , l_default    = 'AU'
        )
    , jira_sync.Sync_Attribute_To_Remote_Default
        ( local_name   = None
        , only_create  = True
        , remote_name  = 'Workflow'
        , l_default    = '42'
        )
    , jira_sync.Sync_Attribute_To_Remote_Default
        ( local_name   = None
        , only_create  = True
        , remote_name  = 'Visibility'
        , l_default    = '0'
        )
    # The Description is mandatory on remote issue creation
    , jira_sync.Sync_Attribute_To_Remote
        ( local_name   = 'description'
        , remote_name  = 'Description'
        , only_create  = True
        )
    , jira_sync.Sync_Attribute_To_Local_Multilink_Default
        ( local_name    = 'components.name'
        , remote_name   = None
        , r_default     = 'default component'
        , l_only_create = True
        )
    , jira_sync.Sync_Attribute_To_Local_Default
        ( local_name   = 'project.key'
        , remote_name  = None
        , r_default    = LOCAL_PROJECT
        )
    # It might make sense here to use your own type like
    # 'Customer Defect' just for the sync with KPM.
    , jira_sync.Sync_Attribute_To_Local_Default
        ( local_name   = 'issuetype.name'
        , remote_name  = None
        , r_default    = LOCAL_ISSUETYPE
        )
    , jira_sync.Sync_Attribute_To_Local_Default
        ( local_name   = 'security.name'
        , remote_name  = None
        , r_default    = 'Project Insider'
        )
    # "External Ticket" field in Jira, e.g. customfield_10034
    , jira_sync.Sync_Attribute_To_Local
        ( local_name   = 'customfield_10034'
        , remote_name  = 'ProblemNumber'
        , local_prefix = 'KPM-'
        , after_create = True
        )
    , jira_sync.Sync_Attribute_To_Local
        ( local_name   = 'summary'
        , remote_name  = 'ShortText'
        , r_default    = '?'
        )
    # On remote issue creation we must provide the ShortText
    , jira_sync.Sync_Attribute_To_Remote
        ( local_name   = 'summary'
        , remote_name  = 'ShortText'
        , only_create  = True
        )
    , jira_sync.Sync_Attribute_To_Local_Multistring
        ( local_name    = 'labels'
        , remote_name   = 'EngineeringStatus'
        , prefix        = 'KPM-FB-Status-'
        , l_only_update = True
        )
    # You probably want to add a default version that you're mostly
    # working on anyway.
    , jira_sync.Sync_Attribute_To_Local_Multilink_Default
        ( local_name    = 'versions.name'
        , remote_name   = 'ForemostTestPart.Software'
        , r_default     = 'defaultversion'
        , use_r_default = True
        , l_only_update = True
        )
    , jira_sync.Sync_Attribute_To_Local_Concatenate
        ( local_name      = 'description'
        , short_delimiter = ' '
        , delimiter       = '\n\n'
        , field_prefix    = '*'
        , field_postfix   = ':*\n'
        , remote_names    =
          [ 'Description'
          , 'Analysis'
          , 'Rating'
          , 'ForemostTestPart.Software'
          , 'ForemostTestPart.Hardware'
          , 'ForemostGroupProject.Brand'
          , 'ForemostGroupProject.Project'
          , 'ForemostTestPart.PartNumber.PreNumber'
          , 'ForemostTestPart.PartNumber.MiddleGroup'
          , 'ForemostTestPart.PartNumber.EndNumber'
          , 'ForemostTestPart.PartNumber.Index'
          , 'Origin.MainProcess'
          , 'Origin.SubProcess'
          , 'Origin.Phase'
          , 'Origin.PhaseAddition'
          , 'Repeatable'
          , 'Frequency'
          , 'Keyword'
          , 'SollVerbundRelease.Major'
          , 'SollVerbundRelease.Minor'
          , 'SollVerbundRelease.Extend'
          , 'StartOfProductionDate'
          , 'Creator.PersonalContractor.UserName'
          , 'ProblemSolver.Contractor.PersonalContractor.UserName'
          ]
        # Mapping a name to 'None' will not produce a headline and will
        # use the short_delimiter (default: space)
        , name_map =
          { 'ForemostTestPart.Software'              : 'Affects SW version'
          , 'ForemostTestPart.Hardware'              : 'Affects HW version'
          , 'ForemostTestPart.PartNumber.PreNumber'  : 'Part-no'
          , 'ForemostTestPart.PartNumber.MiddleGroup': None
          , 'ForemostTestPart.PartNumber.EndNumber'  : None
          , 'ForemostTestPart.PartNumber.Index'      : None
          , 'ForemostGroupProject.Brand'             : 'Group Project'
          , 'ForemostGroupProject.Project'           : None
          , 'Origin.MainProcess'                     : 'Origin'
          , 'Origin.SubProcess'                      : None
          , 'Origin.Phase'                           : None
          , 'Origin.PhaseAddition'                   : None
          , 'Creator.PersonalContractor.UserName'    : 'Creator'
          , 'StartOfProductionDate'                  : 'Start of production'
          , 'SollVerbundRelease.Major'               : 'Soll Verbund Release'
          , 'SollVerbundRelease.Minor'               : None
          , 'SollVerbundRelease.Extend'              : None
          , 'ProblemSolver.Contractor.PersonalContractor.UserName' :
            'Problem responsible'
          }
        , content_map =
          { 'Frequency' :
            { 'XF' : 'Intermittent'
            , 'XG' : 'Always'
            , 'XE' : 'Only once'
            }
          , 'Repeatable' :
            { 'XH' : 'yes'
            , 'XI' : 'no'
            }
          }
        )
    # "Release Note" field in Jira, some customfield_10036
    # Note that the l_only_update setting is needed only if the field
    # is not writeable during creation
    , jira_sync.Sync_Attribute_To_Local_Default
        ( local_name    = 'customfield_10036'
        , remote_name   = None
        , r_default     = 'Under Investigation'
        , l_only_update = True
        )
    # "Release Note" field in Jira, e.g. customfield_10036
    , jira_sync.Sync_Attribute_To_Remote
        ( local_name    = 'customfield_10036'
        , remote_name   = 'SupplierResponse'
        , only_assigned = True
        , only_update   = True
        )
    # On some trackers the priority field may be writeable only during
    # creation of the Jira issue. In that case you want to make the
    # sync type here jira_sync.Sync_Attribute_To_Local_Default.
    , jira_sync.Sync_Attribute_To_Local
        ( local_name   = 'priority.name'
        , remote_name  = 'Rating'
        , r_default    = 'Minor'
        , l_default    = 'DB'
        , only_update  = True
        # The following should be mapped according to the states of your
        # Jira tracker
        , imap =
            { '1'  : 'Highest'   # A1
            , '2'  : 'High'      # A
            , '3'  : 'High'      # A
            , '4'  : 'Medium'    # B
            , '5'  : 'Medium'    # B
            , '6'  : 'Low'       # C
            , '7'  : 'Low'       # C
            , '8'  : 'Lowest'    # D
            , '9'  : 'Lowest'    # D
            , '10' : 'Lowest'    # D
            }
        )
    # Same attribute for remote issue creation (flag only_create)
    , jira_sync.Sync_Attribute_To_Remote
        ( local_name   = 'priority.name'
        , remote_name  = 'Rating'
        , r_default    = 'Minor'
        , l_default    = 'DB'
        , only_create  = True
        , imap =
            { '1'  : 'Highest'     # A1 - must be highest
            , '2'  : 'High'        # A
            , '3'  : 'High'        # A
            , '4'  : 'Medium'      # B
            , '5'  : 'Medium'      # B
            , '6'  : 'Low'         # C
            , '7'  : 'Low'         # C
            , '8'  : 'Lowest'      # D
            , '9'  : 'Lowest'      # D
            , '10' : 'Lowest'      # D
            }
        )
    # "Repeatable" field in Jira e.g. customfield_16401
    , jira_sync.Sync_Attribute_To_Local_Default
        ( local_name   = 'customfield_16401.value'
        , remote_name  = 'Repeatable'
        , r_default    = 'yes'
        , l_default    = 'XH'
        , imap =
            { 'XH' : 'yes'
            , 'XI' : 'no'
            }
        )
    # Same attribute for remote issue creation (flag only_create)
    , jira_sync.Sync_Attribute_To_Remote
        ( local_name   = 'customfield_16401.value'
        , remote_name  = 'Repeatable'
        , r_default    = 'yes'
        , l_default    = 'XH'
        , only_create  = True
        , imap =
            { 'XH' : 'yes'
            , 'XI' : 'no'
            }
        )
    # "Frequency" field in Jira e.g. customfield_16400
    , jira_sync.Sync_Attribute_To_Local_Default
        ( local_name   = 'customfield_16400.value'
        , remote_name  = 'Frequency'
        , r_default    = 'Always'
        , l_default    = 'XG'
        , imap =
            { 'XF' : 'Intermittent'
            , 'XG' : 'Always'
            , 'XE' : 'Only once'
            }
        )
    # Same attribute for remote issue creation (flag only_create)
    , jira_sync.Sync_Attribute_To_Remote
        ( local_name   = 'customfield_16400.value'
        , remote_name  = 'Frequency'
        , r_default    = 'Always'
        , l_default    = 'XG'
        , only_create  = True
        , imap =
            { 'XF' : 'Intermittent'
            , 'XG' : 'Always'
            , 'XE' : 'Only once'
            }
        )
    # This is *mandatory*, a SupplierStatus is required by KPM!
    # So you will need to take the time to provide a mapping of local
    # statuses to KPM SupplierStatus. This is only an example.
    # And some projects will require you to sync two-way, see below for
    # and example configuration that you can enable *instead* of this
    # one.
    , jira_sync.Sync_Attribute_To_Remote
        ( local_name   = 'status.name'
        , remote_name  = 'SupplierStatus'
        , map =
            { 'Analyzing'                  : '1'
            , 'Deciding'                   : '1'
            , 'Suspended'                  : '0'
            , 'Open'                       : '0'
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
#    If you need to synchronize SupplierStatus two way between KPM and
#    Jira then enable the following *instead* of the config entry above.
#    Note that this usually needs mappings in both direction: There are
#    two processes that change the SupplierStatus in KPM: If an issue is
#    in the status that signals completion to KPM ('Waiting for
#    Customer' in this example), the issue may be re-opened in KPM. In
#    that case a '-' is sent by KPM (which you normally would never have
#    as something you are mapping local stati *to*). The second case is
#    that KPM rejects an issue (e.g. assigns it to another supplier), in
#    that case KPM is sending '6'.
#    , jira_sync.Sync_Attribute_Two_Way
#        ( local_name   = 'status.name'
#        , remote_name  = 'SupplierStatus'
#        , map =
#            { 'Created'                    : '0'
#            , 'Open'                       : '1'
#            , 'Analyzed'                   : '2'
#            , 'Pending'                    : '3'
#            , 'Under Test'                 : '4'
#            , 'Waiting for Customer'       : '5'
#            , 'Closed'                     : '5'
#            , 'Reject'                     : '6'
#            }
#        # Inverse map (remote to local attribute)
#        , imap =
#            { '0': 'Created'
#            , '1': 'Open'
#            , '2': 'Analyzed'
#            , '3': 'Pending'
#            , '4': 'Under Test'
#            , '5': 'Waiting for Customer'
#            , '6': 'Reject'
#            , '-': 'Open'
#            }
#        )
    , jira_sync.Sync_Attribute_To_Local_Multistring
        ( local_name    = 'labels'
        , remote_name   = 'Rating'
        , prefix        = 'KPM-Priority-'
        , l_only_update = True
        , imap =
            { '1'  : 'A1'
            , '2'  : 'A'
            , '3'  : 'A'
            , '4'  : 'B'
            , '5'  : 'B'
            , '6'  : 'C'
            , '7'  : 'C'
            , '8'  : 'D'
            , '9'  : 'D'
            , '10' : 'D'
            }
        )
    , jira_sync.Sync_Attribute_To_Remote
        ( local_name    = 'key'
        , remote_name   = 'SupplierErrorNumber'
        , only_assigned = True
        )
    # Same attribute for remote issue creation (flag only_create)
    # Note that this needs to be NewSupplierErrorNumber
    # This is a different attribute in KPM and is optional in KPM
    , jira_sync.Sync_Attribute_To_Remote
        ( local_name    = 'key'
        , remote_name   = 'NewSupplierErrorNumber'
        , only_create   = True
        )
    , jira_sync.Sync_Attribute_To_Remote
        ( local_name     = 'fixVersions.name'
        , remote_name    = 'SupplierVersionOk'
        , join_multilink = True
        , only_assigned  = True
        )
    , jira_sync.Sync_Attribute_Files
        ( l_only_update = True
        , only_update   = True
        )
    , kpmwssync.Sync_Attribute_KPM_Message
        ( prefix        = 'TO AUDI:'
        , l_only_update = True
        )
    , kpmwssync.Sync_Attribute_KPM_Message
        ( local_prefix     = 'Supplier Question: '
        , prefix           = 'Question to AUDI:'
        , kpm_process_step = 'Rückfrage'
        , l_only_update    = True
        , only_update      = True
        )
    , kpmwssync.Sync_Attribute_KPM_Message
        ( local_prefix     = 'Answer to Question: '
        , kpm_process_step = 'Antwort auf TV, RF, WK, FK, WA'
        , l_only_update    = True
        , only_update      = True
        )
    , kpmwssync.Sync_Attribute_KPM_Message
        ( local_prefix     = 'Info to Supplier: '
        , kpm_process_step = 'Information an Lieferanten'
        , l_only_update    = True
        , only_update      = True
        )
    )
