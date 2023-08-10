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

import sys
from setuptools import setup
sys.path.insert (1, '.')
from trackersync import __version__

with open ('README.rst') as f:
    description = f.read ()

license     = 'MIT License'

setup \
    ( name             = "trackersync"
    , version          = __version__
    , description      = "Issue Tracker Synchronisation Tool"
    , long_description = description
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
    , project_urls     = \
        { 'Homepage':    "https://github.com/schlatterbeck/trackersync"
        , 'Homepage2':   "https://sourceforge.net/projects/trackersync/"
        , "Bug Tracker": "https://github.com/schlatterbeck/trackersync/issues"
        }
    , classifiers      = \
        [ 'Development Status :: 5 - Production/Stable'
        , 'License :: OSI Approved :: ' + license
        , 'Operating System :: OS Independent'
        , 'Programming Language :: Python'
        , 'Intended Audience :: Developers'
        ]
    )
