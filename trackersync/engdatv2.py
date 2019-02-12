#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__       import unicode_literals
from __future__       import print_function
from rsclib.autosuper import autosuper

""" This implements enough EDIFACT to generate and parse ENGDAT messages
    Note that this is ENGDAT V2, V3 would use XML.
"""

# Example messages from the standard
# VDA-Empfehlung 4951 P 1 Version 2.3, Oktober 2005
msg1 = \
    ( "UNA:+.? '"

      'UNB'
      '+UNOC:1'
      '+O0013006000F2--AG:OD:F2ABT1MEIER'
      '+O0013005466F3--AG:OD:F3ABT6MÜLLER'
      '+950129:1310'
      '+444'
      "'"

      'UNH'
      '+210'
      '+ENGDAT:001::OD'
      "'"

      'MID'
      '+950129131005F2HBG'
      '+950128:1830'
      '+XYZ-GHHD'
      "'"

      'SDE'
      '+F2:Firma 2 AG:Postfach:20150 Hamburg:::195634'
      '+DE+ED0590021'
      '+Abt. ABT-1??:Herr Meier:?+49-40-123-0:38793:46355528746'
      ':?+49-40-123-34555:6667788:hemeier@f2.de'
      '+Übermittlungs GmbH:Postfach 4020:20160 Hamburg:::U2599_245'
      '+DE'
      '+Abt. UE-1:Frau Meder:?+49-40-907-0:363:463555247'
      ':?+49-40-907-400:66677999:kmeder@f2.de'
      "'"

      'RDE'
      '+F3:Firma 3 AG:Postfach:70180 Stuttgart 1:::4712'
      '+DE+He071511'
      'Abt. ABT-6:Herr Müller:0711-45-0:36554:4446578839:?+49-0711-45-36666'
      ':55566773:lmueller@f3.de'
      'Data-Transfer Gesellschaft:Münchner Straße 100:70020 Stuttgart:::222999'
      '+DE'
      '+UET-3:Herr Weller:?+49-711-6786-0:31:4446578839'
      ':?+49-711-566780:555997744:nweller@dtg.de'
      "'"

      'DAN'
      '+310:Angebot'
      '+XYZ00033'
      '+950121:1410'
      "'"

      'FTX'
      '+Angebot auf Ihre Anfrage vom:10.12. des Jahres. Zeichnungen'
      ':sind vertraulich zu behandeln.'
      "'"

      'EFC'
      '+002:EINSPRITZANLAGE.IGS'
      '+IGS:IGES:5.2'
      '+646:US ASCII 7BIT'
      '+CATIA RS6000:V4.1.3:CATIGE'
      '+TOD:Angebot'
      '+Abt. K-1'
      '+3D-Flächenmodell und Drawing'
      '+Keine'
      "'"

      'FTX'
      '+Die Toleranzvorgaben für:Flächenqualitäten sind'
      ':unbedingt einzuhalten.'
      "'"

      'FTX'
      '+Die Größe des Modells:beträgt 15 Megabyte'
      "'"

      'DSD'
      '+'
      '+1'
      '+11-38 D 000341'
      '+A0'
      '+Einspritzanlage'
      '+dispositionsfrei:5:950118'
      "'"

      'FTX'
      '+Radien unter 3 mm sind nicht:als Flächen beschrieben'
      "'"

      'LOF'
      '+003:CATIA.LAY (11-38 D)'
      '+LAY:Layer-Konventionen'
      "'"

      'SEC'
      '+38AXB10:AXX0A:XYZ-GHHD'
      "'"

      'EFC'
      '+003:CATIA.LAY (11-38 D)'
      '+:Text'
      '+646:US ASCII 7BIT'
      '+Text-Editor'
      '+TOD:Angebot'
      '+Abt. K-1'
      '+Layer-Konventionen'
      '+Keine'
      "'"

      'FTX'
      '+Layerkonventionen sind:unbedingt einzuhalten'
      "'"

      'SEC'
      '+38AXB10:AXX0A:XYZ-GHHD'
      "'"

      'TOT'
      '+3:PCE'
      "'"

      'UNT'
      '+18'
      '+210'
      "'"

      'UNZ'
      '+1'
      '+444'
      "'"
    ).encode ('latin-1')


msg2 = \
    ( 'UNB'
      '+UNOC:1'
      '+O0013005400ABC-AG:OD'
      '+O0013005430XYZ-AG:OD:UVWMÜLLER'
      '+950227:1354'
      '+445'
      "'"

      'UNH'
      '+215'
      '+ENGDAT:001::OD'
      "'"

      'MID'
      '+950227135401ABKLN'
      '+950227'
      "'"

      'SDE'
      '+:ABC AG:Hahn Straße 10:50039 KÖln'
      '+ABCAG'
      '+'
      '+Abt. DEF:Herr Maier:0211-88-0:3345'
      '+ABC AG'
      '+'
      '+Abt. UEB::3369'
      "'"

      'RDE'
      '+:XYZ AG:Postfach 888777:80277 München'
      '+XYZAG '
      '+'
      '+Abt. UVW:Herr Müller:089-4567:4499'
      "'"
      
      'EFC'
      '+2:992647001.exp'
      '+ NAT:CATIA export WS-Format V4 ISO8859-1:4.2.2'
      '+885'
      '+CATIA RS6000:V4.2.2:CATEXP PROJECT-A '
      '+:Einbauuntersuchung'
      '+'
      '+3D-Flächenmodell'
      "'"

      'FTX'
      '+Kombi-Instrument für E-XY'
      "'"

      'TOT'
      '+2'
      "'"

      'UNT'
      '+8'
      '+215'
      "'"

      'UNZ'
      '+1'
      '+445'
      "'"
    ).encode ('latin-1')


class UNA (autosuper) :
    """
        An EDIFACT message can start with an una segment.
        This defines the markup characters in use.
        The una segment contains 6 characters:
        - Component data separator (default ':')
        - Data element separator (default '+')
        - Decimal mark (default ',') later versions specify both '.' and
          ', can be used
        - release character (for quoting, similar to \ quoting)
          (default: '?')
        - reserved, must be space
        - segment terminator, (default: "'")
    """

    segment_name = 'UNA'

    def __init__ (self, bytes = b"UNA:+.? '") :
        self.from_bytes (bytes)
        self.length = 9
    # end def __init__

    @property
    def component_sep (self) :
        return self.una [0].encode ('ASCII')
    # end def component_sep

    @property
    def element_sep (self) :
        return self.una [1].encode ('ASCII')
    # end def element_sep

    @property
    def release_char (self) :
        return self.una [3].encode ('ASCII')
    # end def release_char

    @property
    def segment_terminator (self) :
        return self.una [-1].encode ('ASCII')
    # end def segment_terminator

    def from_bytes (self, bytes) :
        assert bytes.startswith (b'UNA')
        self.una = bytes [3:].decode ('ASCII')
    # end def from_bytes

    def to_bytes (self) :
        return ('UNA' + self.una).encode ('ASCII')
    # end def to_bytes

    def __length__ (self) :
        return self.length
    # end def __length__

    def __str__ (self) :
        return 'UNA' + self.una
    # end def __str__
    __unicode__ = __str__

# end class UNA

# default una
una = UNA ()

class _Part_Iter (autosuper) :

    def iterparts (self, bytes, delimiter) :
        """ Iterate over parts delimited with delimiter taking
            una.release_char into account
            Test iterparts:
        >>> e = Edifact_Element (una = una)
        >>> tuple (e.iterparts (b'Abt. ABT-1??????:Herr Meier', b':'))
        (b'Abt. ABT-1??????', b'Herr Meier')
        >>> tuple (e.iterparts (b'Abt. ABT-1????:Herr Meier', b':'))
        (b'Abt. ABT-1????', b'Herr Meier')
        >>> tuple (e.iterparts (b'Abt. ABT-1??:Herr Meier', b':'))
        (b'Abt. ABT-1??', b'Herr Meier')
        >>> tuple (e.iterparts (b'Abt. ABT-1:Herr Meier', b':'))
        (b'Abt. ABT-1', b'Herr Meier')
        >>> tuple (e.iterparts (b'Abt. ABT-1?:Herr Meier', b':'))
        (b'Abt. ABT-1?:Herr Meier',)
        >>> tuple (e.iterparts (b'DE+ED0590021', b'+'))
        (b'DE', b'ED0590021')
        >>> tuple (e.iterparts (b':?+49-40:6667788:hemeier@f2.de+bla', b'+'))
        (b':?+49-40:6667788:hemeier@f2.de', b'bla')
        """
        l    = len (bytes)
        offs = 0
        esc  = self.una.release_char
        while offs < l :
            try :
                # Initialize to start at offs
                # Further searches start at found position +1
                eidx = offs - 2
                idx  = offs - 1
                while (idx - eidx) % 2 :
                    idx = bytes.index (delimiter, idx + 1)
                    eidx = idx
                    while eidx > 0 and bytes [eidx-1:eidx] == esc :
                        eidx -= 1
                yield bytes [offs:idx]
                offs = idx + 1
            except ValueError :
                yield bytes [offs:]
                break
    # end def iterparts

# end class _Part_Iter

class Edifact_Message (_Part_Iter) :
    """
        An EDIFACT message can start with an una segment.
        This defines the markup characters in use.
        Segments are terminated with the segment terminator
        We get the current una in effect as a parameter.
    >>> m = Edifact_Message (bytes = msg1)
    >>> m.to_bytes () == msg1
    True
    >>> m = Edifact_Message (bytes = msg2)
    >>> m.to_bytes () == msg2
    True
    """

    def __init__ (self, una = una, bytes = None, *segments) :
        self.una = una
        self.encoding = 'latin-1'
        if bytes :
            self.from_bytes (bytes)
        else :
            self.segments = segments
    # end def __init__

    def from_bytes (self, bytes) :
        self.segments = []
        offs = 0
        if bytes.startswith (b'UNA') :
            self.una = UNA (bytes [:9])
            offs = 9
            self.segments.append (self.una)
        else :
            self.una = una
        t = self.una.segment_terminator
        for b in self.iterparts (bytes [offs:], t) :
            name = b [:3].decode ('ASCII')
            cls  = Edifact_Segment
            e    = self.encoding
            if name in globals () :
                cls = globals () [name]
            self.segments.append \
                (cls (bytes = b + t, una = self.una, encoding = e))
    # end def from_bytes

    def to_bytes (self) :
        s = b''.join (p.to_bytes () for p in self.segments)
        return s
    # end def to_bytes

    def __str__ (self) :
        r = []
        for s in self.segments :
            r.append (str (s))
        return '\n'.join (r)
    # end def __str__
    __unicode__ = __str__

# end class Edifact_Message

class Edifact_Element (_Part_Iter) :
    """ An edifact data element (elements are delimited by the data
        element separator, usually '+')
    """

    def __init__ (self, encoding = 'latin-1', una = una, bytes = None) :
        self.encoding   = encoding
        self.una        = una
        self.components = []
        if bytes :
            self.from_bytes (bytes)
    # end def __init__

    def append (self, component_text) :
        """ Append component_text to self.components
        """
        self.components.append (component_text)
    # end def append

    def from_bytes (self, bytes) :
        offs = 0
        t    = self.una.component_sep
        for b in self.iterparts (bytes [offs:], t) :
            self.append (self.unquote (b).decode (self.encoding))
    # end def from_bytes

    def to_bytes (self) :
        comps = []
        for c in self.components :
            comps.append (self.quote (c.encode (self.encoding)))
        return self.una.component_sep.join (comps)
    # end def to_bytes

    def quote (self, bytes) :
        """ Add quoting (with release_char)
        >>> x = Edifact_Element (una = una)
        >>> x.quote (b"+49-40-123-0?'")
        b"?+49-40-123-0???'"
        """
        # The release_char must be first, otherwise release chars are
        # multiplied
        special = \
            ( self.una.release_char
            , self.una.component_sep
            , self.una.element_sep
            , self.una.segment_terminator
            )
        for k in special :
            bytes = bytes.replace (k, self.una.release_char + k)
        return bytes
    # end def quote

    def unquote (self, bytes) :
        """ Remove quoting (with release_char)
        >>> x = Edifact_Element (una = una)
        >>> x.unquote (b'?+49-40-123-0')
        b'+49-40-123-0'
        >>> x.unquote (b'Abt. ABT-1??')
        b'Abt. ABT-1?'
        >>> x.unquote (b"?+49-40-123-0???'")
        b"+49-40-123-0?'"
        """
        r    = []
        offs = 0
        idx = bytes.find (self.una.release_char, offs)
        while idx >= 0 :
            r.append (bytes [offs:idx])
            r.append (bytes [idx+1:idx+2])
            offs = idx + 2
            idx  = bytes.find (self.una.release_char, offs)
        r.append (bytes [offs:])
        return b''.join (r)
    # end def unquote

    def __str__ (self) :
        r = []
        for c in self.components :
            r.append (c)
        return '\n'.join (r)
    # end def __str__
    __unicode__ = __str__

# end class Edifact_Element

class Edifact_Segment (_Part_Iter) :
    """ Implements an EDIFACT segment used in ENGDAT V2
        A segment is prefixed with the (3-letter) record name and
        terminated by the current segment terminator.
    """

    def __init__ (self, encoding = 'latin1', bytes = None, una = una) :
        self.encoding = encoding
        self.una      = una
        self.elements = []
        if bytes is not None :
            self.from_bytes (bytes)
        self.__super.__init__ ()
    # end def __init__

    @property
    def segment_class_name (self) :
        return self.__class__.__name__
    # end def segment_class_name

    def to_bytes (self) :
        s = [self.segment_name.encode (self.encoding)]
        for element in self.elements :
            s.append (element.to_bytes ())
        s = self.una.element_sep.join (s)
        self.length = len (s) + 1
        return s + self.una.segment_terminator
    # end def to_bytes

    def from_bytes (self, bytes) :
        self.length = len (bytes)
        self.segment_name = bytes [:3].decode (self.encoding)
        assert self.length == 3 or bytes [3:4] == self.una.element_sep
        assert bytes [-1:] == self.una.segment_terminator
        offs = 4
        t = self.una.element_sep
        e = self.encoding
        for b in self.iterparts (bytes [offs:-1], t) :
            self.elements.append (Edifact_Element (encoding = e, bytes = b))
    # end def from_bytes

    def __length__ (self) :
        return self.length
    # end def __length__

    def __str__ (self) :
        r = []
        r.append (self.segment_name)
        for e in self.elements :
            r.append (str (e))
        return '\n'.join (r)
    # end def __str__
    __unicode__ = __str__

# end class Edifact_Segment

class UNB (Edifact_Segment) :
    pass
    # FIXME: put encoding into creating class

#    serialisation = dict \
#        { 'Syntax-Identification' :
#          ( 'syntax'
#          , 'version'
#          )
#        , 'Absender der Uebertragung'
#          ( 'sender'
#          , 'sender_q'
#          )
#        , 'Empfaenger der Uebertragung'
#          ( 'receiver'
#          , 'receiver_q'
#          )
#        }
#
#    def __init__ \
#        ( self
#        , bytes = None
#        , sender     = ''
#        , receiver   = ''
#        , sender_q   = 'OD'
#        , receiver_q = 'OD'
#        , syntax     = 'UNOC'
#        , version    = '1'
#        ) :
#        self.sender     = sender
#        self.receiver   = receiver
#        self.sender_q   = sender_q
#        self.receiver_q = receiver_q
#        self.syntax     = syntax
#        self.version    = version
#        self.__super.__init__ (bytes)
#    # end def __init__

# end class UNB

if __name__ == '__main__' :
    m = Edifact_Message (bytes = msg1)
    #print (len (m.segments))
    #print (m)
    #for k in m.segments :
    #    print (repr (k.to_bytes ()))

    #print (msg1)
    #print (m.to_bytes ())

    assert m.to_bytes () == msg1
    m = Edifact_Message (bytes = msg2)
    assert m.to_bytes () == msg2
