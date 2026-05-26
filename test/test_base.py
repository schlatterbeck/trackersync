#!/usr/bin/python3
# Copyright (C) 2026 Dr. Ralf Schlatterbeck Open Source Consulting.
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

import pytest
from trackersync.jira_sync import ADF_Node

adf_example = \
  { "description": {
      "type": "doc",
      "version": 1,
      "content": [
        {
          "type": "paragraph",
          "content": [
            {
              "type": "text",
              "text": "A normal paragraph"
            }
          ],
          "attrs": {
            "localId": "aaaaaaaaaaaa"
          }
        },
        {
          "type": "paragraph",
          "attrs": {
            "localId": "aaaaaaaaaaaa"
          }
        },
        {
          "type": "paragraph",
          "attrs": {
            "localId": "aaaaaaaaaaaa"
          }
        },
        {
          "type": "paragraph",
          "content": [
            {
              "type": "text",
              "text": "Some more text followed by a hard break"
            },
            {
              "type": "hardBreak"
            },
            {
              "type": "text",
              "text": "Some more text at end of paragraph"
            }
          ],
          "attrs": {
            "localId": "ffffffffffff"
          }
        },
        {
          "type": "paragraph",
          "attrs": {
            "localId": "ffffffffffff"
          }
        },
        {
          "type": "bulletList",
          "content": [
            {
              "type": "listItem",
              "content": [
                {
                  "type": "paragraph",
                  "content": [
                    {
                      "type": "text",
                      "text": "Hello world"
                    }
                  ]
                }
              ]
            },
            {
              "type": "listItem",
              "content": [
                {
                  "type": "paragraph",
                  "content": [
                    {
                      "type": "text",
                      "text": "Second item"
                    },
                    {
                      "type": "hardBreak"
                    },
                    {
                      "type": "text",
                      "text": "2nd line of second item"
                    },
                  ]
                }
              ]
            },
            {
              "type": "orderedList",
              "attrs": {
                "order": 3
              },
              "content": [
                {
                  "type": "listItem",
                  "content": [
                    {
                      "type": "paragraph",
                      "content": [
                        {
                          "type": "text",
                          "text": "Third inner item"
                        }
                      ]
                    }
                  ]
                },
                {
                  "type": "listItem",
                  "content": [
                    {
                      "type": "paragraph",
                      "content": [
                        {
                          "type": "text",
                          "text": "Fourth inner item"
                        }
                      ]
                    }
                  ]
                },
                {
                  "type": "listItem",
                  "content": [
                    {
                      "type": "paragraph",
                      "content": [
                        {
                          "type": "text",
                          "text": "Fifth inner item"
                        }
                      ]
                    }
                  ]
                }
              ]
            },
            {
              "type": "listItem",
              "content": [
                {
                  "type": "paragraph",
                  "content": [
                    {
                      "type": "text",
                      "text": "Fourth item"
                    }
                  ]
                },
                {
                  "type": "paragraph",
                  "content": [
                    {
                      "type": "text",
                      "text": "Consisting of tree paragraphs"
                    }
                  ]
                },
                {
                  "type": "paragraph",
                  "content": [
                    {
                      "type": "text",
                      "text": "This is the third one"
                    }
                  ]
                }
              ]
            },
            {
              "type": "listItem",
              "content": [
                {
                  "type": "paragraph",
                  "content": [
                    {
                      "type": "text",
                      "text": "Fifth item, a sub list"
                    }
                  ]
                },
                {
                  "type": "bulletList",
                  "content": [
                    {
                      "type": "listItem",
                      "content": [
                        {
                          "type": "paragraph",
                          "content": [
                            {
                              "type": "text",
                              "text": "inner item"
                            }
                          ]
                        }
                      ]
                    },
                    {
                      "type": "listItem",
                      "content": [
                        {
                          "type": "paragraph",
                          "content": [
                            {
                              "type": "text",
                              "text": "inner item"
                            }
                          ]
                        }
                      ]
                    },
                    {
                      "type": "listItem",
                      "content": [
                        {
                          "type": "paragraph",
                          "content": [
                            {
                              "type": "text",
                              "text": "inner item "
                            },
                            {
                              "type": "date",
                              "attrs": { "timestamp": "1582152559" }
                            }
                          ]
                        }
                      ]
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  }

adf_txt = """
A normal paragraph


Some more text followed by a hard break
Some more text at end of paragraph

- Hello world
- Second item
  2nd line of second item
- 3. Third inner item
  4. Fourth inner item
  5. Fifth inner item
- Fourth item
  Consisting of tree paragraphs
  This is the third one
- Fifth item, a sub list
  - inner item
  - inner item
  - inner item 2020-02-19T23:49:19
""" [1:]

class Test_Case:

    def test_adf (self):
        adf = ADF_Node (adf_example ['description'])
        txt = adf.serialize ()
        assert txt == adf_txt
    # end def test_adf

# end class Test_Case
