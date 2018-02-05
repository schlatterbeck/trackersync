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
from __future__ import absolute_import

""" Example configuration for KPM Sync with Jira """

from trackersync import jira_sync

KPM_USERNAME   = 'user'
KPM_PASSWORD   = 'secret'
KPM_ADDRESS    = '21 KPM-TEST'
KPM_LANGUAGE   = 'german'
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
    # "External Ticket" field in Jira
    , jira_sync.Sync_Attribute_To_Local
        ( local_name   = 'customfield_13000'
        , remote_name  = 'Nummer'
        )
    , jira_sync.Sync_Attribute_To_Local
        ( local_name   = 'summary'
        , remote_name  = 'Kurztext'
        , r_default    = '?'
        )
    , jira_sync.Sync_Attribute_To_Local_Multistring
        ( local_name   = 'labels'
        , remote_name  = 'Status'
        , prefix       = 'KPM-Status-'
        )
    , jira_sync.Sync_Attribute_To_Local_Multilink_Default
        ( local_name    = 'versions.id'
        , remote_name   = 'Softwarestand (verurs.)'
        , r_default     = 'defaultversion'
        , use_r_default = True
        )
    , jira_sync.Sync_Attribute_To_Local_Concatenate
        ( local_name   = 'description'
        , remote_names =
          [ 'Analyse'
          , 'Problembeschreibung'
          , 'Softwarestand (verurs.)'
          , 'Problemlösungsverantwortlicher Benutzer'
          ]
        )
    # "Release Note" field in Jira
    , jira_sync.Sync_Attribute_To_Remote
        ( local_name   = 'customfield_12009'
        , remote_name  = 'Lieferantenaussage'
        )
#    , jira_sync.Sync_Attribute_To_Local_Concatenate
#        ( local_name   = 'environment'
#        , remote_names =
#          [ 'Reproduzierbar'
#          , 'Fehlerhäufigkeit'
#          , 'Hardwarestand'
#          ]
#        )
    # priority can currently only be set during creation
    , jira_sync.Sync_Attribute_To_Local_Default
        ( local_name   = 'priority.name'
        , remote_name  = 'Bewertung'
        , r_default    = 'Minor'
        , l_default    = 'DB'
        , only_update  = True
        , imap = dict
            ( A1 = 'Showstopper'
            , A  = 'Showstopper'
            , B  = 'Major'
            , C  = 'Minor'
            , D  = 'Minor'
            , DB = 'Minor'
            , DV = 'Minor'
            )
        )
    , jira_sync.Sync_Attribute_To_Remote
        ( local_name   = 'status.name'
        , remote_name  = 'L-Status [Code]'
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
    , jira_sync.Sync_Attribute_To_Remote
        ( local_name   = 'key'
        , remote_name  = 'L-Fehlernummer'
        )
    , jira_sync.Sync_Attribute_To_Remote
        ( local_name     = 'fixVersions.name'
        , remote_name    = 'L-System-IO'
        , join_multilink = True
        )
    )

