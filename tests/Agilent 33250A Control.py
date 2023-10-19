#!/usr/bin/env python

# Author: Martin Lints, martin.lints@ioc.ee
# Year: 2019 (originally 2017 for python2)

# Wrapper over pyvisa for remote control of Agilent 33250A
# mainly for binary upload of data
# commands constructed according to Agilent 33250A manual
# see the manual for additional commands

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

#####################################################################

import pyvisa as visa
import time
import struct
from numpy import floor, log10


class Agilent(object):
    """
    Class for communicating with Agilent Arbitrary Waveform Generator 33250A

    Setup the AWG I/O with: RS-232, 57.6K baud, parity None/8Bits, handshake DTR

    Initialize with
    Agilent(dev=u'ASRL/dev/ttyUSB0::INSTR', br=57600)
    where dev is the device (here using Linux notation and ttyUSB0)
    br is baudrate

    Methods (decimal integer values from -2047 to +2047)
    ------------
    Agilent(dev = u'ASRL/dev/ttyUSB0::INSTR', br = 57600) : initialize and connect

    upload_binary(arr) : use this to upload array in binary format (faster, better, N len)
                         uploads the data to VOLATILE slot
    save_volatile(arbname) : saves the contents of VOLATILE into arbname (with error check)
    activate_arb(arbname) : activates user defined ARBibrary fun. to output (no error check)
    catalog_contents()    : list the current contents of user arbitrary functions catalog
    delete_arb(arbname)   : obvious, with error checking

    burst(ncyc=1) : example of how to implement a simple burst output using commands

    close() : close the connection
    write(message)
    read() : outputs returned text or times out




    upload_array(arr): 64k only, slow version, do not use
    """

    def __init__(self, dev=u'ASRL6::INSTR', br=9600, t_o=30):
        """
        start on dev/ttyUSB0 (modify code to change)
        br: baudrate (=57600)
        t_o : timeout
        """
        self.rm = visa.ResourceManager()
        print('========================')
        self.rm.list_resources()
        print(self.rm.list_resources())
        print('========================')
        self.ag = self.rm.open_resource(dev)
        print('========================')
        self.ag.baud_rate = br
        self.ag.set_visa_attribute(visa.constants.VI_ATTR_ASRL_FLOW_CNTRL,
                                   visa.constants.VI_ASRL_FLOW_DTR_DSR)
        self.ag.timeout = t_o * 1000
        self.ag.write('*IDN?')
        print(self.ag.read())

    def upload_array(self, arr):
        """
        upload array of data to VOLATILE memory of Agilent

        right now only accepts array of 64000 elements
        Slow version, do not use. Use upload_binary instead

        not useless, useful as a (bad) example
        """
        self.ag.write_raw('DATA:DAC VOLATILE')
        # pause for 1 ms like manual requires
        time.sleep(1e-2)
        for i in range(1600):
            print("doing {}th of 64000".format(i * 40))
            ctstr1 = ', '.join(map(str, arr[i * 40:(i + 1) * 40] / 2))
            # self.ag.write_raw(u', {}'.format(ctstr1))
            self.ag.write_raw(', {}'.format(ctstr1))
            time.sleep(0.1)

        # self.ag.write_raw(u'\n')
        self.ag.write_raw('\n')

    def upload_binary(self, arr):
        """binary upload to VOLATILE:
         also only accepts array of 64000 elements
        """
        # calculate the number of decimals for 2x datalen (2byte words)
        Nbytes = len(arr) * 2
        # if arr.len is N, then in the data command "#X(2*N)"
        # where X is number of decimals of (2*N)
        X = int(floor(log10(Nbytes))) + 1
        cmdstr = "#" + str(X) + str(int(Nbytes))

        # upload command
        self.ag.write("form:bord swap")
        binarry = b"".join([struct.pack("<h", val) for val in arr])  # pack in 2byte words
        self.ag.write_raw(b'data:dac volatile, ' + cmdstr.encode())  # 6 cmd decimals,128k num
        time.sleep(0.5)
        self.ag.write_raw(binarry)  # python3: already bytes
        self.ag.write_raw(b'\n')
        time.sleep(2)

    def save_volatile(self, arbname):
        """
        At the moment, saves to "MYARB" and selects it
        First looks if we have a free memory slot
        """
        # do we have a free memory slot?
        self.ag.write('DATA:NVOLatile:FREE?')
        rval = self.read()  # returns '+0\n' in case of full
        if rval[1] == '0':
            self.write('DATA:NVOLATILE:CATALOG?')
            catalogContents = self.read()

            # can still go if the arbname is in catalog
            if arbname.upper() in catalogContents:
                print('overwriting previous {}'.format(arbname))
                self.ag.write('DATA:COPY {}, VOLATILE'.format(arbname))

            # no go
            print("User-defined function catalog full, please delete some")
            print("Current functions:")
            print(catalogContents)
            return
        else:
            #  Copy the arbitrary waveform to non-volatile memory, using DATA:COPY
            self.ag.write('DATA:COPY {}, VOLATILE'.format(arbname))

    def activate_arb(self, arbname):
        #  Select the arbitrary waveform to output FUNC:USER
        # (user-defined as opposed to internal functions)
        self.ag.write('FUNC:USER {}'.format(arbname))

    def catalog_contents(self):
        """
        prints the catalog of user-defined functions
        """
        self.write('DATA:NVOLATILE:CATALOG?')
        catalogContents = self.read()
        print("User function catalog holds: ")
        print(catalogContents)

    def delete_arb(self, arbname):
        """
        delete the saved arbitrary waveform of name "ARBNAME" from catalog
        freeing up space
        """
        # check if we have it:
        self.write('DATA:NVOLATILE:CATALOG?')
        catalogContents = self.read()
        if arbname.upper() not in catalogContents:
            print("Catalog held: ")
            print(catalogContents)
            raise RuntimeError('Selected arbitrary name {} not in catalog:'.format(arbname))

        # check if we are not currently outputting it
        # 1) have we selected a user function?
        self.write('FUNCTION?')
        state = self.read()
        if state == 'USER\n':
            # are we using the arbname function
            self.write('FUNCTION:USER?')
            funname = self.read()
            if funname == arbname.upper() + '\n':
                # we have selected the function that we are trying to delete
                # NO-GO
                raise RuntimeError("{} is currently selected, cannot delete".format(arbname))

        # OK, we can delete
        self.write('DATA:DELETE {}'.format(arbname))

    def burst(self, ncyc=1):
        """
        Example of a method for running the code by burst:
        We select burst mode with relevant arguments
        setup the trigger source, enable output and trigger the burst
        """
        self.ag.write('OUTP OFF')
        self.ag.write('BURS:MODE TRIG')
        self.ag.write('BURS:INT:PER 1')  # set burst period (interval for int. trig 1 us to 50sec
        self.ag.write('BURS:PHAS 0')
        self.ag.write('TRIG:SOUR BUS')
        self.ag.write('BURS:STAT ON')
        self.ag.write('OUTP ON')
        self.ag.write('*TRG')

    def close(self):
        """ duh """
        self.ag.close()

    def write(self, txt):
        """
        write commands in text mode
        """
        self.ag.write(txt)

    def read(self):
        """Read the returned data"""
        return self.ag.read()


if __name__ == "__main__":
    import numpy as np
    from pylab import *

    wg = Agilent()

    wg.write('OUTP ON')

    wg.close()
