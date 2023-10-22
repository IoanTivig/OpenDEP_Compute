import pyvisa as visa
import zeroconf
import serial
from pyvisa.constants import Parity, StopBits


class FunctionGenerator:
    rm = visa.ResourceManager()
    instrument = None
    instrument_id = None

    print(rm.list_resources())

    def get_all_instruments(self):
        return self.rm.list_resources()

    def connect_instrument(self, instrument_id='ASRL6::INSTR'):
        self.instrument_id = instrument_id
        if instrument_id in self.get_all_instruments():
            self.instrument = self.rm.open_resource(
                instrument_id,
                baud_rate=9600, data_bits=8,
                parity=Parity.none)

            identification = self.instrument.query("*IDN?")
            print("Instrument ID:", identification)
        else:
            print('Instrument not connected')

    def set_frequency(self, value):
        if self.instrument_id in self.get_all_instruments():
            self.instrument.write('FREQ ' + str(int(value)))
        else:
            print('Instrument not connected')

    def get_frequency(self):
        if self.instrument_id in self.get_all_instruments():
            return self.instrument.query('FREQ?')
        else:
            print('Instrument not connected')

    def set_voltage(self, value):
        if self.instrument_id in self.get_all_instruments():
            self.instrument.write('VOLT ' + str(value))
        else:
            print('Instrument not connected')

    def get_voltage(self):
        if self.instrument_id in self.get_all_instruments():
            return self.instrument.query('VOLT?')
        else:
            print('Instrument not connected')

    def start_output(self):
        if self.instrument_id in self.get_all_instruments():
            self.instrument.write('OUTP ON')
        else:
            print('Instrument not connected')

    def stop_output(self):
        if self.instrument_id in self.get_all_instruments():
            self.instrument.write('OUTP OFF')
        else:
            print('Instrument not connected')

    def set_sinusoidal(self):
        if self.instrument_id in self.get_all_instruments():
            self.instrument.write('FUNC SIN')
        else:
            print('Instrument not connected')

if __name__ == "__main__":
    generator = FunctionGenerator()
    generator.connect_instrument('ASRL6::INSTR')
    generator.set_frequency(1234)