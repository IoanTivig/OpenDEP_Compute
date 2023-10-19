import time
import pyvisa
class keysight_33250a():

    def __init__(self, pyvisa_instr):
        self.k33250a = pyvisa_instr  # this is the pyvisa instrument

    def get_all_scpi_list(self):
        result_list = []
        for scpi_list in [self.output_cmd_list, self.pulse_cmd_list, self.am_cmd_list, self.fm_cmd_list,
                          self.fsk_cmd_list, self.sweep_cmd_list, self.burst_cmd_list, self.arb_cmd_list,
                          self.sys_cmd_list, self.phase_cmd_list]:
            for command in scpi_list:
                time.sleep(0.1)
                # print(command.format("?"))
                result = (self.k33250a.query(command.format("?"))).rstrip('\r\n')
                result = " " + result
                result_list.append(command.format(result))
                # print(command.format(result))
        return result_list

    def get_unique_scpi_list(self):
        unique_scpi_list = []
        inst_settings_list = self.get_all_scpi_list()
        for setting in inst_settings_list:
            if (setting not in self.settings_por_scpi_list):
                unique_scpi_list.append(setting)
        return unique_scpi_list

    # value is {0}, string that contains function, frequency, amplitude and offset
    apply_cmd_list = ["APPLy{0}"]

    # value is {0}
    output_cmd_list = ["FUNCtion{0}", "FREQuency{0}",
                       "VOLTage{0}", "VOLTage:OFFSet{0}", "VOLTage:HIGH{0}", "VOLTage:LOW{0}", "VOLTage:UNIT{0}",
                       "FUNCtion:SQUare:DCYCle{0}", "FUNCtion:RAMP:SYMMetry{0}",
                       "OUTPut{0}", "OUTPut:LOAD{0}", "OUTPut:POLarity{0}", "OUTPut:SYNC{0}"]

    pulse_cmd_list = ["PULSe:PERiod{0}", "PULSe:WIDTh{0}", "PULSe:TRANsition{0}"]

    am_cmd_list = ["AM:INTernal:FUNCtion{0}", "AM:INTernal:FREQuency{0}", "AM:DEPTh{0}", "AM:SOURce{0}", "AM:STATe{0}"]

    fm_cmd_list = ["FM:INTernal:FUNCtion{0}", "FM:INTernal:FREQuency{0}", "FM:DEViation{0}", "FM:SOURce{0}", "FM:STATe{0}"]

    fsk_cmd_list = ["FSKey:FREQuency{0}", "FSKey:INTernal:RATE{0}", "FSKey:SOURce{0}", "FSKey:STATe{0}"]

    sweep_cmd_list = ["FREQuency:STARt{0}", "FREQuency:STOP{0}", "FREQuency:CENTer{0}", "FREQuency:SPAN{0}",
                      "SWEep:SPACing{0}", "TRIGger:SOURce{0}", "TRIGger:SLOPe{0}", "TRIGger:DELay{0}",
                      "OUTPut:TRIGger:SLOPe{0}", "OUTPut:TRIGger{0}", "MARKer:FREQuency{0}", "MARKer{0}"]

    burst_cmd_list = ["BURSt:MODE{0}", "BURSt:NCYCles{0}", "BURSt:INTernal:PERiod{0}", "BURSt:PHASe{0}",
                      "BURSt:STATe{0}", "UNIT:ANGLe{0}", "BURSt:GATE:POLarity{0}"]

    arb_cmd_list = ["FORMat:BORDer{0}", "FUNCtion:USER{0}", "DATA:ATTRibute:AVERage{0}", "DATA:ATTRibute:CFACtor{0}",
                    "DATA:ATTRibute:POINts{0}", "DATA:ATTRibute:PTPeak{0}"]

    sys_cmd_list = ["DISPlay{0}", "SYSTem:BEEPer:STATe{0}"]

    phase_cmd_list = ["PHASe{0}", "PHASe:UNLock:ERRor:STATe{0}", "UNIT:ANGLe{0}"]

    settings_por_scpi_list = [ 'FUNCtion SIN',
                               'FREQuency +1.0000000000000E+03',
                               'VOLTage +1.0000000000000E-01',
                               'VOLTage:OFFSet +0.0000000000000E+00',
                               'VOLTage:HIGH +5.0000000000000E-02',
                               'VOLTage:LOW -5.0000000000000E-02',
                               'VOLTage:UNIT VPP',
                               'FUNCtion:SQUare:DCYCle +5.0000000000000E+01',
                               'FUNCtion:RAMP:SYMMetry +1.0000000000000E+02',
                               'OUTPut 0',
                               'OUTPut:LOAD +5.0000000000000E+01',
                               'OUTPut:POLarity NORM',
                               'OUTPut:SYNC 1',
                               'PULSe:PERiod +1.0000000000000E-03',
                               'PULSe:WIDTh +1.0000000000000E-04',
                               'PULSe:TRANsition +5.0000000000000E-09',
                               'AM:INTernal:FUNCtion SIN',
                               'AM:INTernal:FREQuency +1.0000000000000E+02',
                               'AM:DEPTh +1.0000000000000E+02',
                               'AM:SOURce INT',
                               'AM:STATe 0',
                               'FM:INTernal:FUNCtion SIN',
                               'FM:INTernal:FREQuency +1.0000000000000E+01',
                               'FM:DEViation +1.0000000000000E+02',
                               'FM:SOURce INT',
                               'FM:STATe 0',
                               'FSKey:FREQuency +1.0000000000000E+02',
                               'FSKey:INTernal:RATE +1.0000000000000E+01',
                               'FSKey:SOURce INT',
                               'FSKey:STATe 0',
                               'FREQuency:STARt +1.0000000000000E+02',
                               'FREQuency:STOP +1.0000000000000E+03',
                               'FREQuency:CENTer +5.5000000000000E+02',
                               'FREQuency:SPAN +9.0000000000000E+02',
                               'SWEep:SPACing LIN',
                               'TRIGger:SOURce IMM',
                               'TRIGger:SLOPe POS',
                               'TRIGger:DELay +0.0000000000000E+00',
                               'OUTPut:TRIGger:SLOPe POS',
                               'OUTPut:TRIGger 0',
                               'MARKer:FREQuency +5.0000000000000E+02',
                               'MARKer 0',
                               'BURSt:MODE TRIG',
                               'BURSt:NCYCles +1.0000000000000E+00',
                               'BURSt:INTernal:PERiod +1.0000000000000E-02',
                               'BURSt:PHASe +0.0000000000000E+00',
                               'BURSt:STATe 0',
                               'UNIT:ANGLe DEG',
                               'BURSt:GATE:POLarity NORM',
                               'FORMat:BORDer NORM',
                               'FUNCtion:USER EXP_RISE',
                               'DATA:ATTRibute:AVERage +6.7156300000000E-01',
                               'DATA:ATTRibute:CFACtor +2.1119900000000E+00',
                               'DATA:ATTRibute:POINts +4096',
                               'DATA:ATTRibute:PTPeak +1.0000000000000E+00',
                               'DISPlay 1',
                               'SYSTem:BEEPer:STATe 1',
                               'PHASe +0.0000000000000E+00',
                               'PHASe:UNLock:ERRor:STATe 0',
                               'UNIT:ANGLe DEG' ]


rm = pyvisa.ResourceManager()
print(rm.list_resources())
arb = keysight_33250a(rm.open_resource(rm.list_resources()[2]))

time.sleep(2)
print(arb.get_unique_scpi_list())