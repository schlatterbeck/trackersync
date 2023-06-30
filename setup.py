#!/usr/bin/python3
# Copyright (C) 2015-23 Dr. Ralf Schlatterbeck Open Source Consulting.
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

from setuptools import setup
try:
    from trackersync.Version import VERSION
except:
    VERSION = None

description = []
with open ('README.rst') as f:
    for line in f:
        description.append (line)

license     = 'MIT License'
baseurl     = 'http://downloads.sourceforge.net'
download    = '/'.join ((baseurl, 'project/trackersync/trackersync'))

setup \
    ( name             = "trackersync"
    , version          = VERSION
    , description      = "Issue Tracker Synchronisation Tool"
    , long_description = ''.join (description)
    , license          = license
    , author           = "Ralf Schlatterbeck"
    , author_email     = "rsc@runtux.com"
    , packages         = ['trackersync']
    , platforms        = 'Any'
    , python_requires  = '>=3.7'
    , entry_points       = dict
        ( console_scripts =
            [ 'jirasync=trackersync.jirasync:main'
            , 'kpmwssync=trackersync.kpmwssync:main'
            , 'kpmwstest=trackersync.kpmwssync:wstest'
            , 'pfiffsync=trackersync.pfiffsync:main'
            ]
        )
    , url              = "http://trackersync.sourceforge.net/"
    , download_url     = \
        "%(download)s/%(VERSION)s/trackersync-%(VERSION)s.tar.gz" % locals ()
    , classifiers      = \
        [ 'Development Status :: 5 - Production/Stable'
        , 'License :: OSI Approved :: ' + license
        , 'Operating System :: OS Independent'
        , 'Programming Language :: Python'
        , 'Intended Audience :: Developers'
        ]
    )
