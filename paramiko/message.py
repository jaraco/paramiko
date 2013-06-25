# Copyright (C) 2003-2007  Robey Pointer <robeypointer@gmail.com>
#
# This file is part of paramiko.
#
# Paramiko is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# Paramiko is distrubuted in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Paramiko; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA.

"""
Implementation of an SSH2 "message".
"""

import struct
import cStringIO

from paramiko import util


class Message (object):
    """
    An SSH2 I{Message} is a stream of bytes that encodes some combination of
    strings, integers, bools, and infinite-precision integers (known in python
    as I{long}s).  This class builds or breaks down such a byte stream.
    
    Normally you don't need to deal with anything this low-level, but it's
    exposed for people implementing custom extensions, or features that
    paramiko doesn't support yet.
    """

    def __init__(self, content=None):
        """
        Create a new SSH2 Message.

        @param content: the byte stream to use as the Message content (passed
            in only when decomposing a Message).
        @type content: string
        """
        if content != None:
            self.packet = cStringIO.StringIO(content)
        else:
            self.packet = cStringIO.StringIO()

    def __str__(self):
        """
        Return the byte stream content of this Message, as a string.

        @return: the contents of this Message.
        @rtype: string
        """
        return self.packet.getvalue()

    def __repr__(self):
        """
        Returns a string representation of this object, for debugging.

        @rtype: string
        """
        return 'paramiko.Message(' + repr(self.packet.getvalue()) + ')'

    def rewind(self):
        """
        Rewind the message to the beginning as if no items had been parsed
        out of it yet.
        """
        self.packet.seek(0)

    def get_remainder(self):
        """
        Return the bytes of this Message that haven't already been parsed and
        returned.

        @return: a string of the bytes not parsed yet.
        @rtype: string
        """
        position = self.packet.tell()
        remainder = self.packet.read()
        self.packet.seek(position)
        return remainder

    def get_so_far(self):
        """
        Returns the bytes of this Message that have been parsed and returned.
        The string passed into a Message's constructor can be regenerated by
        concatenating C{get_so_far} and L{get_remainder}.

        @return: a string of the bytes parsed so far.
        @rtype: string
        """
        position = self.packet.tell()
        self.rewind()
        return self.packet.read(position)

    def get_bytes(self, n):
        """
        Return the next C{n} bytes of the Message, without decomposing into
        an int, string, etc.  Just the raw bytes are returned.

        @return: a string of the next C{n} bytes of the Message, or a string
            of C{n} zero bytes, if there aren't C{n} bytes remaining.
        @rtype: string
        """
        b = self.packet.read(n)
        max_pad_size = 1<<20  # Limit padding to 1 MB
        if len(b) < n and n < max_pad_size:
            return b + '\x00' * (n - len(b))
        return b

    def get_byte(self):
        """
        Return the next byte of the Message, without decomposing it.  This
        is equivalent to L{get_bytes(1)<get_bytes>}.

        @return: the next byte of the Message, or C{'\000'} if there aren't
            any bytes remaining.
        @rtype: string
        """
        return self.get_bytes(1)

    def get_boolean(self):
        """
        Fetch a boolean from the stream.

        @return: C{True} or C{False} (from the Message).
        @rtype: bool
        """
        b = self.get_bytes(1)
        return b != '\x00'

    def get_int(self):
        """
        Fetch an int from the stream.

        @return: a 32-bit unsigned integer.
        @rtype: int
        """
        return struct.unpack('>I', self.get_bytes(4))[0]

    def get_int64(self):
        """
        Fetch a 64-bit int from the stream.

        @return: a 64-bit unsigned integer.
        @rtype: long
        """
        return struct.unpack('>Q', self.get_bytes(8))[0]

    def get_mpint(self):
        """
        Fetch a long int (mpint) from the stream.

        @return: an arbitrary-length integer.
        @rtype: long
        """
        return util.inflate_long(self.get_string())

    def get_string(self):
        """
        Fetch a string from the stream.  This could be a byte string and may
        contain unprintable characters.  (It's not unheard of for a string to
        contain another byte-stream Message.)

        @return: a string.
        @rtype: string
        """
        return self.get_bytes(self.get_int())

    def get_list(self):
        """
        Fetch a list of strings from the stream.  These are trivially encoded
        as comma-separated values in a string.

        @return: a list of strings.
        @rtype: list of strings
        """
        return self.get_string().split(',')

    def add_bytes(self, b):
        """
        Write bytes to the stream, without any formatting.
        
        @param b: bytes to add
        @type b: str
        """
        self.packet.write(b)
        return self

    def add_byte(self, b):
        """
        Write a single byte to the stream, without any formatting.
        
        @param b: byte to add
        @type b: str
        """
        self.packet.write(b)
        return self

    def add_boolean(self, b):
        """
        Add a boolean value to the stream.
        
        @param b: boolean value to add
        @type b: bool
        """
        if b:
            self.add_byte('\x01')
        else:
            self.add_byte('\x00')
        return self
            
    def add_int(self, n):
        """
        Add an integer to the stream.
        
        @param n: integer to add
        @type n: int
        """
        self.packet.write(struct.pack('>I', n))
        return self

    def add_int64(self, n):
        """
        Add a 64-bit int to the stream.

        @param n: long int to add
        @type n: long
        """
        self.packet.write(struct.pack('>Q', n))
        return self

    def add_mpint(self, z):
        """
        Add a long int to the stream, encoded as an infinite-precision
        integer.  This method only works on positive numbers.
        
        @param z: long int to add
        @type z: long
        """
        self.add_string(util.deflate_long(z))
        return self

    def add_string(self, s):
        """
        Add a string to the stream.
        
        @param s: string to add
        @type s: str
        """
        self.add_int(len(s))
        self.packet.write(s)
        return self

    def add_list(self, l):
        """
        Add a list of strings to the stream.  They are encoded identically to
        a single string of values separated by commas.  (Yes, really, that's
        how SSH2 does it.)
        
        @param l: list of strings to add
        @type l: list(str)
        """
        self.add_string(','.join(l))
        return self
        
    def _add(self, i):
        if type(i) is str:
            return self.add_string(i)
        elif type(i) is int:
            return self.add_int(i)
        elif type(i) is long:
            if i > 0xffffffff:
                return self.add_mpint(i)
            else:
                return self.add_int(i)
        elif type(i) is bool:
            return self.add_boolean(i)
        elif type(i) is list:
            return self.add_list(i)
        else:
            raise Exception('Unknown type')

    def add(self, *seq):
        """
        Add a sequence of items to the stream.  The values are encoded based
        on their type: str, int, bool, list, or long.
        
        @param seq: the sequence of items
        @type seq: sequence
        
        @bug: longs are encoded non-deterministically.  Don't use this method.
        """
        for item in seq:
            self._add(item)
