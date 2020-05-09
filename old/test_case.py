'''
version 1.0.0 in Aceinna
testing case for MTLT
ID should be 0x80
@author: cek
'''

import os
import time
import csv
from mtlt import can_mtlt
from csv_sheet import my_csv

# create the csv file to record the testing result
file_name = 'result.csv'
file = my_csv(os.path.join(os.getcwd(), file_name))  

# initial CAN_MTLT instance, restart unit and starting to receive and decoding messages
time.sleep(1)
mtlt = can_mtlt(src=0x80)

print('1. Default Interface Setup')

# request value at first before set other configurations
id_msg              = mtlt.get_id()
source_address      = mtlt.get_source_address()[0] # get the device ID from feedback ID message
addr_claim_msg      = mtlt.addressclaim.get()
packet_type         = mtlt.get_packet_type()
lpf_rate, lpf_acc   = mtlt.get_lpf()
orient              = mtlt.get_orientation()
fw_str              = '0x' + mtlt.get_fw_version()
packet_rate, odr_idx = mtlt.get_packet_rate()
hw_bit_msg          = mtlt.get_hw_status()
sw_bit_msg          = mtlt.get_sw_status()
status_msg          = mtlt.get_sensor_status()

unit_behavior       = mtlt.get_unit_behavior()


file.write(['Default Interface Setup',                                                          ''])
file.write(['Verify that default CAN baud rate setting is 250kb/s',                             "0x{0}".format(id_msg['payload'].upper())])
file.write(['Verify that CAN2.0 electrical interface is compliant to  J1939 protocol standard', "0x{0}".format(id_msg['payload'].upper())])
file.write(['Verify that default CAN address is 0x80',                                          "0x{0:X}".format(source_address)])
file.write(['Verify address claiming capability',                                               "0x{0}".format(addr_claim_msg['payload'].upper())])
file.write([['Verify that new address is stored to EEPROM',                                     'manually'],
        ['Verify that CAN address can be changed by RS232 interface',                           'manually'],
        ['Verify that CAN address is saved permanently when saved by RS232 interface',          'manually'],
        ['Verify that default CAN termination can be enabled through RS232',                    'manually'],
        ['Verify that default CAN termination setting is stored permanently',                   'manually']
        ])

# Interface Configuration Checks
file.write(['',                                                                                 ''])
file.write(['Interface Configuration Checks',                                                   ''])
file.write([['Verify that all the baud rates mentioned in the UM are supported',                'manually'], 
        ['Verify Auto Baud is working',                                                         'manually']])

# Verify Defaults
file.write(['Verify Defaults',                                                                  ''])
file.write(['Verify that default Packet Rate Divider  value is 100Hz',                          packet_rate])
file.write(['Verify that default Data Packet Type is 0x07',                                     '0x{0:02X}'.format(packet_type)])
file.write(['Verify that default Digital Filter Value for Rate Sensor is 25Hz',                 lpf_rate])
file.write(['Verify that default Digital Filter Value for Acceleration Sensor is 5Hz',          lpf_acc])
file.write(['Verify that default Orientation value is 0x0000',                                  '0x{0:04X}'.format(orient)])
file.write(['Verify that default Unit behavior value is 0x02',                                  '0x{0:02X}'.format(unit_behavior)])
file.write(['Verify that default Firmware Version is as expected',                              fw_str])
file.write(['Verify that UUT ID is as expected',                                                "0x{0}".format(id_msg['payload'].upper())])

print('2. Response Verification')
# measure all packets can be enabled
mtlt.set_pkt_type(31) # open all packets
slope_exist, rate_exist, acc_exist, angle_ssi_exist, hr_acc_exist = mtlt.decode_pke_type_num(mtlt.measure_pkt_type())
mtlt.set_pkt_type(packet_type) # back to original status, disable some packets
time.sleep(1)

# Set commands
lpf_list_ok    = mtlt.set_lpf_list()
print('first get value',lpf_rate, packet_rate, packet_type, orient, unit_behavior)
reset_alg_feedback_ok = mtlt.reset_algorithm()
set_lpf_ok = mtlt.set_lpf_filter(5)
set_odr_ok = mtlt.set_odr(5)
set_pkt_type_ok = mtlt.set_pkt_type(0x0F)
set_ori_ok = mtlt.set_orientation(0)
set_bhr_ok = mtlt.set_unit_behavior(enabel_bit=0,disable_bit=1)

back_lpf_ok, back_odr_ok, back_pkt_type_ok, back_ori_ok, back_bhr_ok = mtlt.without_sc_pwr_cycle(
                                                                            to_lpf_rate = 5, to_odr = 5, 
                                                                            to_pkt_type = 0x0F, to_ori = 0x0009, 
                                                                            to_behavior = 2)
if all([back_lpf_ok, back_odr_ok, back_pkt_type_ok, back_ori_ok, back_bhr_ok]) == True:
    backall_ok_pwr_cycle       = True
else:
    print("not all configurations back to original value:", back_lpf_ok, back_odr_ok, back_pkt_type_ok, back_ori_ok, back_bhr_ok)
    backall_ok_pwr_cycle       = False

configuration_save_feedback = mtlt.save_configuration()

input('begin to testing ps1:')

mtlt.set_bank_ps1(0x55, 0x00, 0x00, 0x00)       # disable other PS
set_ps1_ok     = True if mtlt.get_packet_type() == False else False
time.sleep(1)
if mtlt.back_plant_default() == False:
    print('restore unit failed')
time.sleep(1)


# Response Verification------Get Commands
file.write([['Response Verification',                                                                ''], 
        ['Get Commands']])
file.write(['Verify that Get command response for Firmware Version is as expected in the UM',        fw_str])
file.write(['Verify that Get command response for Rate of Periodic Data Packets PGN is as expected', packet_rate])
file.write(['Verify that Get command response for Enable Periodic Data Packets PGN is as expected',  set_odr_ok])
file.write(['Verify that Get command response for Active Digital Filters PGN is as expected',        'lpf_rate:{0} lpf_acc:{1}'.format(lpf_rate, lpf_acc)])
file.write(['Verify that Get command response for Current Unit Orientation PGN is as expected',      '0x{0:04X}'.format(orient)])
file.write(['Verify that Get command response for ECU ID PGN is as expected',                        "0x{0}".format(id_msg['payload'].upper())])
file.write(['Verify that Get command response for HW BIT PGN is as expected',                        "0x{0}".format(hw_bit_msg['payload'].upper())])
file.write(['Verify that Get command response for SW BIT PGN is as expected',                        "0x{0}".format(sw_bit_msg['payload'].upper())])
file.write(['Verify that Get command response for Status PGN is as expected',                        "0x{0}".format(status_msg['payload'].upper())])
file.write(['Verify that Get command response for Unit Behaviour PGN is as expected',                '0x{0:02X}'.format(unit_behavior)])
file.write(['Set Commands'])
file.write(['Verify that Set Command response for Configuration Save is as expected',                configuration_save_feedback])
file.write(['Verify that Set Command response for Algorithm Reset is as expected',                   reset_alg_feedback_ok])
file.write(['Verify that Set Command response for Packet Rate Divider is as expected',               set_odr_ok])
file.write(['Verify that Set Command response for Data Packet Type is as expected',                  set_pkt_type_ok])
file.write(['Verify that Set Command response for Digital Filter is as expected',                    set_lpf_ok])
file.write(['Verify that Set Command response for Orientation Save is as expected',                  set_ori_ok])
file.write(['Verify that Set Command response for Unit Behavior is as expected',                     set_bhr_ok])
file.write(['Verify that Set Command response for Bank of PS Number is as expected',                 set_ps1_ok])
file.write(['Data Packets'])
file.write(['Verify that SS1 data packet format is as expected',                                     angle_ssi_exist])
file.write(['Verify that SS2 data packet format is as expected',                                     slope_exist])
file.write(['Verify that Angular Rate data packet format is as expected',                            rate_exist])
file.write(['Verify that Acceleration Sensor data packet format is as expected',                     acc_exist])
file.write(['Verify that HA Acceleration Sensor data packet format is as expected',                  hr_acc_exist])


        # check the configurations saved permanently after power cycle
input('3. configuration verification after saved')

save_lpf_ok, save_odr_ok, save_pkt_type_ok, save_ori_ok, save_bhr_ok = mtlt.with_sc_pwr_cycle(
                                                                            to_lpf_rate = 5, to_odr = 5, 
                                                                            to_pkt_type = 0x0F, to_ori = 0x0009, 
                                                                            to_behavior = 2)
if all([save_lpf_ok, save_odr_ok, save_pkt_type_ok, save_ori_ok, save_bhr_ok]) == True:
    saveall_ok_pwr_cycle       = True
else:
    print("not all cmd saved:",save_lpf_ok, save_odr_ok, save_pkt_type_ok, save_ori_ok, save_bhr_ok)
    saveall_ok_pwr_cycle       = False

input('try confi list starting')
mtlt.set_pkt_type(packet_type)

# try configuration list, confirm all setting valid by measurment.
input('try odr list')
odr_list_valid      = mtlt.try_odr_list(actual_measure=True)
print('odr list valid:', odr_list_valid)
input('try pkt type list')
pkt_type_list_valid = mtlt.try_pkt_type_list(actual_measure=True)
print('pkt_type_list_valid', pkt_type_list_valid)
input('try ori list')
ori_list_valid      = mtlt.try_orientation_list()
print('ori_list_valid', pkt_type_list_valid)
input('try unit behavior list')
unit_bhr_list_valid = mtlt.try_unit_bhr_list()
print('unit_bhr_list_valid', unit_bhr_list_valid)
input('try ps0/1 list')
bank_list_valid     = mtlt.try_bank_ps0_list() & mtlt.try_bank_ps1_list()
print('bank_list_valid', bank_list_valid)




# Measure value
# odr_mea         = mtlt.measure_odr()





file.write(['Configuration Verification'])
file.write(['Verify that UUT configuration is saved permanently for each configuration field in CAN bus when Configuration Save PGN is sent', saveall_ok_pwr_cycle])
file.write(['Verify that change in Configuration values does not retain after UUT restart',                                                   backall_ok_pwr_cycle])
file.write(['Verify that Packet Rate Divider can be configured to each value mentioned in the UM and the output rate corresponds to the value set', odr_list_valid])
file.write(['Verify that Packet type can be configured to each value mentioned in the UM and the output type corresponds to the value set',   pkt_type_list_valid])
file.write(['Verify that each value of the Low pass cutoff frequency for Rate Sensor mentioned in the UM can be set',         lpf_list_ok])
file.write(['Verify that each value of the Low pass cutoff frequency for Acceleration Sensor mentioned in the UM can be set', lpf_list_ok])
file.write(['Verify that each Orientation value of the UUT can be set',                                                       ori_list_valid])
file.write(['Verify that each setting for Unit Behavior can be set to UUT',                                                   unit_bhr_list_valid])
file.write(['Verify that Bank PS number can be changed',                                                                      unit_bhr_list_valid])
file.write(['Verify that none of the output data packets are empty in 100Hz long term read (1M data packets)',                bank_list_valid])

file.write(['Auto Baudrate Detection Verification',                                                                           ''])
file.write(['PreConditions',                                                                                                  ''])
file.write(['UUT sync to the bus upon power up.',                                                                             ''])
file.write(['Automatic UUT resync to new baudrate. UUT always powered UP',                                                    ''])
file.write(['UUT shall not sync to the other units which send messages with standard (not extended) identifiers',             ''])
file.write(['UUT with different baudrates coexist on the same CAN bus. ',                                                     ''])
file.write(['Test without reference unit on the bus',                                                                         ''])
file.write(['',                                                                                                               ''])







print('testing end.')
os._exit(0)





if __name__ == "__main__":
    pass

