'''
version 1.1.0 in Aceinna
mtlt products(MTLT305D and 300RI included now) CAN Bus read and send message module
Requires PI3B and CAN_HAT(shopping link: https://m.tb.cn/h.eRtgNe2)
with H/L of CAN_HAT connected with H/L from sensor side
follow http://www.waveshare.net/wiki/RS485_CAN_HAT 
or follow blog at http://skpang.co.uk/blog/archives/1220
only store the angle, acc, rate to can_data.txt
running in hardbyte-python-can foler, downloaded from https://bitbucket.org/hardbyte/python-can/get/4085cffd2519.zip
@author: cek
'''

import os
import sys
import can
import time
import struct
import threading
import subprocess

from queue import Queue #only python3 supported now


#j1939 with extended id
class can_mtlt: 
    def __init__(self, chn = 'can0', bus_type = 'socketcan_ctypes', src = None):   
        if os.sys.platform.startswith('lin'):    
            os.system('sudo /sbin/ip link set can0 up type can bitrate 250000')  # run this command first with correct baud rate
        else:
            print('not linux system, pls running on linux system')
        self.can0 = can.interface.Bus(channel = chn, bustype = bus_type)  # socketcan_native
        self.f = open(os.path.join(os.getcwd(),'can_receive_data.txt'), 'w+')

        self.pdu_dict = {}   
        self.source_address = []
        self.working_sa = None 
        self.record = False
        self.to_file= False
        
        # define all receiveed msg and data pkt msg queue
        self.msg_queue = Queue(1000)  
        self.slopedata = Queue(1000)
        self.acceldata = Queue(1000)
        self.ratedate = Queue(1000)   
        self.addressclaim = Queue(1000)
        self.angle_ssi = Queue(1000)
        self.hr_acc = Queue(1000)
        self.unknow = Queue(1000)

        # define get/set msg feedback msg queue, use 1 firstly, 
        # if need to store more msg need to adjust
        self.fw_version_msg_queue = Queue(1)
        self.id_msg_queue = Queue(1)
        self.hw_bit_msg_queue = Queue(1)
        self.sw_bit_msg_queue = Queue(1)
        self.sensor_status_msg_queue = Queue(1) 
        self.packet_type_msg_queue = Queue(1)
        self.packet_rate_msg_queue = Queue(1)
        self.lpf_msg_queue = Queue(1)
        self.ori_msg_queue = Queue(1)
        self.behavior_msg_queue = Queue(1)
        self.save_confi_msg_queue = Queue(1)
        self.reset_algo_msg_queue = Queue(1)       

        # trigger 2 threads, detect working units and assign one as working_sa
        # you can use set_working_sa
        self.thread_put = threading.Thread(target=self.put_msg)
        self.thread_read = threading.Thread(target=self.parse_msg)         
        self.start_record()
        self.get_source_address()
        if src != None:
            self.working_sa = src
        else:
            if self.set_working_sa() == False:
                print('no working SA detected.')

    def set_working_sa(self, sa_index = 0):    
        '''
        select working unit in units detected.
        '''    
        if ((sa_index + 1) <= len(self.source_address)):
            self.working_sa = self.source_address[sa_index]
            self.empty_data_pkt()
            return True
        else:
            return False
        
    def calc_slope(self,msg):   
        '''
        unit: degree
        '''
        pitch_uint = msg.data[0] + 256 * msg.data[1] +  65536 * msg.data[2]
        roll_uint = msg.data[3] + 256 * msg.data[4] +  65536 * msg.data[5]
        pitch = pitch_uint * (1/32768) - 250.0
        roll = roll_uint * (1/32768) - 250.0
        # put parsed data to queue
        if self.slopedata.qsize() == 1000:
            self.slopedata.queue.clear()
        self.slopedata.put('Time: {2:18.6f} Roll: {0:6.2f} Pitch: {1:6.2f}'.format(roll,pitch,msg.timestamp))
        
    def calc_accel(self,msg):   
        '''
        unit: g
        '''    
        ax_ay_az = struct.unpack('<HHHH', msg.data)
        ax = ax_ay_az[0] * (0.01) - 320.0
        ay = ax_ay_az[1] * (0.01) - 320.0
        az = ax_ay_az[2] * (0.01) - 320.0      
        # put parsed data to queue
        if self.acceldata.qsize() == 1000:
            self.acceldata.queue.clear()
        # print('input acc decodeing data', az)
        self.acceldata.put('Time: {3:18.6f} AX  : {0:6.2f} AY   : {1:6.2f} AZ: {2:6.2f}'.format(ax,ay,az,msg.timestamp))
    def calc_rate(self,msg):     
        '''
        unit: deg/s
        '''   
        wx_wy_wz = struct.unpack('<HHHH', msg.data)
        wx = wx_wy_wz[0] * (1/128.0) - 250.0
        wy = wx_wy_wz[1] * (1/128.0) - 250.0
        wz = wx_wy_wz[2] * (1/128.0) - 250.0      

        # put parsed data to queue
        if self.ratedate.qsize() == 1000:
            self.ratedate.queue.clear()
        self.ratedate.put('Time: {3:18.6f} WX  : {0:6.2f} WY   : {1:6.2f} WZ: {2:6.2f}'.format(wx,wy,wz,msg.timestamp))             
    def start_record(self):  
        self.record = True   
        self.thread_put.start()
        self.thread_read.start() 

    def stop_record(self):
        self.record = False 
     
    def parse_msg(self):    
        while (self.record):
            if (self.msg_queue.not_empty):
                msg_read = self.msg_queue.get()
            else:
                msg_read = self.can0.recv()
            self.get_pdu_list(msg = msg_read)   

            if self.pdu_dict['src'] == self.working_sa or self.working_sa == None:                
                if self.pdu_dict["pgn"] == 61481:
                    self.calc_slope(msg_read)
                elif self.pdu_dict["pgn"] == 61482:                
                    self.calc_rate(msg_read)                    
                elif self.pdu_dict["pgn"] == 61485:                
                    self.calc_accel(msg_read)                    
                elif self.pdu_dict["pgn"] == 61183:                            
                    self.addressclaim.put(self.pdu_dict.copy())                                
                elif self.pdu_dict["pgn"] == 65242:
                    self.fw_version_msg_queue.put(self.pdu_dict.copy())                
                elif self.pdu_dict["pgn"] == 64965:
                    self.id_msg_queue.put(self.pdu_dict.copy())                
                elif self.pdu_dict["pgn"] == 65362:
                    self.hw_bit_msg_queue.put(self.pdu_dict.copy())               
                elif self.pdu_dict["pgn"] == 65363:
                    self.sw_bit_msg_queue.put(self.pdu_dict.copy())                
                elif self.pdu_dict["pgn"] == 65364:
                    self.sensor_status_msg_queue.put(self.pdu_dict.copy())
                elif self.pdu_dict["pgn"] == 65365:
                    self.packet_rate_msg_queue.put(self.pdu_dict.copy())
                elif self.pdu_dict["pgn"] == 65366:
                    print('input pkt type msg:')
                    self.packet_type_msg_queue.put(self.pdu_dict.copy())
                elif self.pdu_dict["pgn"] == 65367:
                    self.lpf_msg_queue.put(self.pdu_dict.copy())
                elif self.pdu_dict["pgn"] == 65368:
                    self.ori_msg_queue.put(self.pdu_dict.copy())         
                elif self.pdu_dict["pgn"] == 65369:
                    self.behavior_msg_queue.put(self.pdu_dict.copy())   
                elif self.pdu_dict["pgn"] == 65361:
                    self.save_confi_msg_queue.put(self.pdu_dict.copy())      
                elif self.pdu_dict["pgn"] == 65360:
                    self.reset_algo_msg_queue.put(self.pdu_dict.copy())    
                elif self.pdu_dict["pgn"] == 61459:
                    self.angle_ssi.put(self.pdu_dict.copy()) 
                elif self.pdu_dict["pgn"] == 65388:
                    self.hr_acc.put(self.pdu_dict.copy()) 
                else:
                    # print(msg_read, "\n")   
                    self.unknow.put(self.pdu_dict.copy())
                       
    def put_msg(self):
        while (self.record):           
            msg_save = self.can0.recv()
            if self.to_file == True:
                msg_temp = self.get_pdu_list(msg=msg_save)
                self.f.write(str(msg_temp['time_stamp']) + '-' + str(msg_temp['pgn']) + ':' + str(msg_temp['payload']).upper() + '\n')
                if msg_temp['payload'] == 0:
                    self.f.write('00000------------------------------------------------------------------------------00000')
                os.fsync(self.f)
            self.msg_queue.put(msg_save)

    def send_msg(self, id_int, data_list):  # id_int = 0x18FF5500, data_list =[128, 1, 0, 0, 0, 0, 0, 0] set ODR is 100hz
        send_msg = can.Message(arbitration_id=id_int, data=data_list, extended_id=True)
        cmd = 'sudo /sbin/ip -details link show can0'
        res = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        feedback = res.stdout.read().decode('utf-8')
        # print(feedback)
        if 'BUS-OFF' not in feedback:
            self.can0.send(send_msg)
        else:
            print('bus-off now')
            cmd = 'sudo /sbin/ip link set can0 type can restart-ms 100'
            res = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
            return False

    def get_source_address(self):
        '''
        based on address claiming msg to detect how many units detected.
        '''
        time.sleep(2)
        # print('address queue size', self.addressclaim.qsize())
        while self.addressclaim.qsize() != 0:
            add_claim = self.addressclaim.get()
            new_sa = add_claim['src']
            # print('new sa', new_sa)
            if new_sa not in self.source_address:
                # print('new sa', new_sa, add_claim)
                self.source_address.append(add_claim['src'])
        return self.source_address

    def empty_data_pkt(self):
        self.slopedata.queue.clear()
        self.ratedate.queue.clear() 
        self.acceldata.queue.clear()
        self.angle_ssi.queue.clear()
        self.hr_acc.queue.clear()
        self.unknow.queue.clear()
        return True

    def measure_pkt_type(self):
        record_status = self.record
        if record_status == False:
            self.start_record()
        odr_idx = self.get_packet_rate()[1]
        self.set_odr(1)
        slope_exist, acc_exist, rate_exist, angle_ssi_exist, hr_acc_exist = 0, 0, 0, 0, 0
        if self.empty_data_pkt():            
            time.sleep(1) # wait 1s to receive packets again
            slope_exist       = 1 if self.slopedata.qsize() > 0 else 0
            rate_exist        = 2 if self.ratedate.qsize() > 0 else 0
            acc_exist         = 4 if self.acceldata.qsize() > 0 else 0
            angle_ssi_exist   = 8 if self.angle_ssi.qsize() > 0 else 0
            hr_acc_exist      = 16 if self.hr_acc.qsize() > 0 else 0  
        self.set_odr(odr_idx)
        if record_status == False:
            self.stop_record()      
        return sum([slope_exist, rate_exist, acc_exist, angle_ssi_exist, hr_acc_exist])

    def measure_odr(self):
        '''
        open the recording and set right packet type 
        measure 5s, calc the received msg
        ''' 
        record_status = self.record
        if record_status == False:
            self.start_record()

        type_old = self.get_packet_type()
        self.set_pkt_type(7) 

        print("measuring ODR by SSI2 message in 5s, pls wait:")
        self.slopedata.queue.clear() 
        start_time = time.time()
        while time.time() - start_time < 5.0:
            time.sleep(0.1)
        odr = self.slopedata.qsize()/5 
        self.set_pkt_type(type_old)
        if record_status == False:
            self.stop_record()
        # print('finished, ODR is {0} hz'.format(odr))
        return odr        

    def get_fw_version(self, ext_id = 0x18EAFF00, pf = 254, ps = 218): 
        self.fw_version_msg_queue.queue.clear() 
        data = [self.working_sa, pf, ps]             

        try_times = 5
        while try_times > 0:
            self.send_msg(ext_id, data)
            try_times -= 1
            time.sleep(0.4)
            if self.fw_version_msg_queue.qsize():
                payload = self.fw_version_msg_queue.get()['payload']
                fw_str = '.'.join([payload[:2], payload[2:4], payload[4:6], payload[6:8], payload[8:10]])
                return fw_str 
        return False                       
    def get_id(self, ext_id = 0x18EAFF01, pf = 253, ps = 197):
        self.id_msg_queue.queue.clear() 
        # print('work sa',self.working_sa)
        data = [self.working_sa, pf, ps]         

        try_times = 5
        while try_times > 0:
            self.send_msg(ext_id,data)
            try_times -= 1
            time.sleep(0.4)
            if self.id_msg_queue.qsize():
                return self.id_msg_queue.get()  
        return False   
               
    def get_hw_status(self, ext_id = 0x18EAFF02, pf = 255, ps = 82):   
        self.hw_bit_msg_queue.queue.clear()      
        data = [self.working_sa, pf, ps]    
        
        try_times = 5
        while try_times > 0:
            self.send_msg(ext_id,data)
            try_times -= 1
            time.sleep(0.4)
            if self.hw_bit_msg_queue.qsize():
                return self.hw_bit_msg_queue.get()  
        return False 

    def get_sw_status(self, ext_id = 0x18EAFF03, pf = 255, ps = 83):  
        self.sw_bit_msg_queue.queue.clear()       
        data = [self.working_sa, pf, ps]           

        try_times = 5
        while try_times > 0:
            self.send_msg(ext_id,data) 
            try_times -= 1
            time.sleep(0.4)
            if self.sw_bit_msg_queue.qsize():
                return self.sw_bit_msg_queue.get()  
        return False 

    def get_sensor_status(self, ext_id = 0x18EAFF04, pf = 255, ps = 84):  
        self.sensor_status_msg_queue.queue.clear()       
        data = [self.working_sa, pf, ps]    

        try_times = 5
        while try_times > 0:
            self.send_msg(ext_id, data)  
            try_times -= 1
            time.sleep(0.4)
            if self.sensor_status_msg_queue.qsize():
                return self.sensor_status_msg_queue.get()  
        return False 

    def get_packet_rate(self, ext_id = 0x18EAFF05, pf = 255, ps = 85):
        self.packet_rate_msg_queue.queue.clear()
        data = [self.working_sa, pf, ps]    
        
        try_times = 5
        while try_times > 0:
            self.send_msg(ext_id,data) 
            try_times -= 1
            time.sleep(0.4)
            if self.packet_rate_msg_queue.qsize():
                rate_index = int(self.packet_rate_msg_queue.get()['payload'][-2:], 16)
                rate = 100/rate_index if rate_index != 0 else 0
                return rate, rate_index
        return False, False

    def get_packet_type(self, ext_id = 0x18EAFF06, pf = 255, ps = 86):
        self.packet_type_msg_queue.queue.clear()  
        data = [self.working_sa, pf, ps]   

        try_times = 5
        while try_times > 0: 
            self.send_msg(ext_id,data)
            try_times -= 1
            time.sleep(0.4)
            print('try times in pkt type get', try_times)
            if self.packet_type_msg_queue.qsize():
                pack_type = self.packet_type_msg_queue.get()
                return int(pack_type['payload'][-2:], 16) & 0x1F
            
        return False
    
    def decode_pke_type_num(self, pkt_num):
        slope_exist       = True if ((pkt_num >> (1-1)) & 1) == 1 else False
        rate_exist        = True if ((pkt_num >> (2-1)) & 1) == 1 else False
        acc_exist         = True if ((pkt_num >> (3-1)) & 1) == 1 else False
        angle_ssi_exist   = True if ((pkt_num >> (4-1)) & 1) == 1 else False
        hr_acc_exist      = True if ((pkt_num >> (5-1)) & 1) == 1 else False
        return slope_exist, rate_exist, acc_exist, angle_ssi_exist, hr_acc_exist

    def get_lpf(self, ext_id = 0x18EAFF07, pf = 255, ps = 87):
        self.lpf_msg_queue.queue.clear()
        data = [self.working_sa, pf, ps]                

        try_times = 5
        while try_times > 0:
            self.send_msg(ext_id,data) 
            try_times -= 1
            time.sleep(0.4)
            if self.lpf_msg_queue.qsize():
                packet = self.lpf_msg_queue.get()
                lpf_rate = int(packet['payload'][-4:-2], 16)
                lpf_acc = int(packet['payload'][-2:], 16)
                return lpf_rate, lpf_acc
        return False, False

    def get_orientation(self, ext_id = 0x18EAFF08, pf = 255, ps = 88):
        self.ori_msg_queue.queue.clear()
        data = [self.working_sa, pf, ps]    
        
        try_times = 5
        while try_times > 0:
            self.send_msg(ext_id,data) 
            try_times -= 1
            time.sleep(0.4)
            if self.ori_msg_queue.qsize():
                return int(self.ori_msg_queue.get()['payload'][-4:], 16)
        return False

    def get_unit_behavior(self, ext_id = 0x18EAFF09, pf = 255, ps = 89):
        self.behavior_msg_queue.queue.clear()
        data = [self.working_sa, pf, ps]             

        try_times = 5        
        while try_times > 0:
            self.send_msg(ext_id,data)
            # print('get bhr,try times:',try_times)
            try_times -= 1
            time.sleep(0.4)
            if self.behavior_msg_queue.qsize():
                return int(self.behavior_msg_queue.get()['payload'][-2:], 16) & 0x3F
        return False

    def decode_behavior_num(self, behavior_num):
        over_range       = ((behavior_num >> (1-1)) & 1)
        dyna_motion      = ((behavior_num >> (2-1)) & 1)
        uncorr_rate      = ((behavior_num >> (3-1)) & 1)
        swap_rateXY      = ((behavior_num >> (4-1)) & 1)
        autobaud_dete    = ((behavior_num >> (5-1)) & 1)
        can_term_resistor= ((behavior_num >> (6-1)) & 1)
        return over_range, dyna_motion, uncorr_rate, swap_rateXY, autobaud_dete, can_term_resistor

    def save_configuration(self, request_bit = 0, ext_id = 0x18FF5100): # if request_bit = 2, will save firstly and then restart/power cycel unit, pls caution
        self.save_confi_msg_queue.queue.clear()   
        data = [request_bit, self.working_sa]       

        try_times = 5
        while try_times > 0:
            self.send_msg(ext_id,data)
            try_times -= 1
            time.sleep(0.4)
            if self.save_confi_msg_queue.qsize():
                feedback = self.save_confi_msg_queue.get()['payload']
                fb_type = int(feedback[:2], 16)
                fb_result = int(feedback[-2:], 16)                
                return True if fb_type == 1 and fb_result == 1 else False
        return False

    def power_rst(self, requestbit = 2, extid = 0x18FF5100):
        self.save_configuration(request_bit=requestbit, ext_id=extid) # it will make unit save and restart, pls caution
                
    def reset_algorithm(self, ext_id = 0x18FF5000):
        self.reset_algo_msg_queue.queue.clear()
        data = [0, self.working_sa]        

        try_times = 5        
        while try_times > 0:
            self.send_msg(ext_id, data) 
            try_times -= 1
            time.sleep(0.4)
            if self.reset_algo_msg_queue.qsize():
                feedback = self.reset_algo_msg_queue.get()['payload']
                fb_type = int(feedback[:2], 16)
                fb_result = int(feedback[-2:], 16)
                return True if fb_type == 1 and fb_result == 1 else False
                
        return False
        
    def set_odr(self, odr_index = 0x1, ext_id = 0x18FF5500):
        data = [self.working_sa, odr_index]  
        rate = 100/odr_index if odr_index != 0 else 0 
        print('set odr: {0} hz'.format(rate)) 
        self.send_msg(ext_id, data) 
        rate_get, odr_idx_get = self.get_packet_rate()  #get the current packet rate configuration 
        if odr_idx_get == odr_index: 
            return True
        else:
            print('set odr {0}hz failed'.format(rate))
            return False
    
    def try_odr_list(self, actual_measure = False):
        # check all odr configuration list is valid by measure or not
        original_odr_idx      = self.get_packet_rate()[1]
        odr_list          = [0, 1, 2, 4, 5, 10, 20, 25, 50] # [0, 1, 2, 4, 5, 10, 20, 25, 50]
        odr_set_ok        = True
        for value in odr_list:
            if self.set_odr(value) == False:
                odr_set_ok = False
                print("can not change odr index to {0}".format(value))
            if actual_measure == True:
                pkt_rate = 100/value if value != 0 else 0
                pass_delta    = 20 if value < 4 else 1
                odr_mea = self.measure_odr()
                if abs(odr_mea - pkt_rate) > pass_delta:
                    odr_set_ok = False   
                    print('set odr:{0}hz, actual:{1}hz, seting invalid actually.'.format(pkt_rate, odr_mea))                 

        self.set_odr(original_odr_idx)
        return odr_set_ok
         
    def set_pkt_type(self, type_int = 0x7, ext_id = 0x18FF5600):
        data = [self.working_sa, type_int]    
        print('pkt type', data)
        self.send_msg(ext_id, data)  
        type_get = self.get_packet_type() # get current configuration to compare with requested value
        print('type_get', type_get)
        input('wait')
        if type_get == type_int:
            return True
        else: 
            print('set packet type failed.set:{0} get:{1}'.format(type_int, type_get))
            return False 

    def try_pkt_type_list(self, actual_measure = False):
        # check all lpf configuration list is valid
        original_type = self.get_packet_type()
        type_list          = [0, 1, 2, 4, 3, 7, 8, 0xB, 0xF, 0xE, 0x13, 0x16, 0x17, 0x1B, 0x1C, 0x1E, 0x1F] 
        type_set_ok        = True
        for value in type_list:
            if self.set_pkt_type(value) == False:
                type_set_ok = False
                print('cannot set pkt_type value to: {0}'.format(value))
            if actual_measure == True:
                # pkt_rate = 100/value if value != 0 else 0
                # pass_delta    = 20 if value < 4 else 1
                pkt_type_mea = self.measure_pkt_type()
                if pkt_type_mea != value:
                    type_set_ok = False   
                    print('set packet type value:{0}, actual:{1}hz, seting invalid actually.'.format(value, pkt_type_mea))           
        self.set_pkt_type(original_type)  
        return type_set_ok  

         
    def set_lpf_filter(self, rate_int = 25, acc_int=5, ext_id = 0x18FF5700):
        data = [self.working_sa, rate_int, acc_int]    
        print("set lpf_rate:{0}hz lpf_acc:{1}hz".format(rate_int, acc_int))
        self.send_msg(ext_id, data)
        rate_get, acc_get = self.get_lpf() # get current configuration to compare with requested value
        if rate_get == rate_int and acc_get == acc_int:
            return True
        else: 
            print('set lpf filter failed.')
            return False 

    def set_lpf_list(self):
        # check all lpf configuration list is valid
        original_rate, original_acc = self.get_lpf()
        lpf_list          = [0, 2, 5, 10, 20, 25, 40, 50] 
        lpf_set_ok        = True
        for value in lpf_list:
            if self.set_lpf_filter(value, value) == False:
                lpf_set_ok = False
                print('set lpf_rate and acc:{0} {1} failed'.format(value, value))
        self.set_lpf_filter(original_rate, original_acc)  
        return lpf_set_ok       
        
    def set_orientation(self,value_int = 0x0000, ext_id = 0x18FF5800):
        value_msb = 0xFF00 & value_int #get the msb value of certain number
        value_msb = value_msb >> 8
        value_lsb = 0x00FF & value_int
        print('set orientation {0:#06X}'.format(value_int))
        data = [self.working_sa, value_msb, value_lsb]
        self.send_msg(ext_id, data)
        ori_get = self.get_orientation() # get current configuration to compare with requested value
        if ori_get == value_int:
            return True
        else: 
            print('set orientation failed.')
            return False  

    def try_orientation_list(self):
        # check some orientation configuration items is valid
        origianl_orient            = self.get_orientation()
        ori_list          = [0x0000, 0x0009, 0x0023, 0x002A, 0x0041, 0x0048, 0x0062, 0x006B, 
                            0x0085, 0x008C, 0x0092, 0x009B, 0x00C4, 0x00CD, 0x00D3, 0x00DA, 0x0111, 
                            0x0118, 0x0124, 0x012D, 0x0150, 0x0159, 0x0165, 0x016C] 
        while input('Please place the unit horizontally to let program detect orientation configuraitons, is it horizontal placement, y/n ? ') != 'y':
            pass      
        ori_set_ok        = True
        for idx,value in enumerate(ori_list):
            if self.set_orientation(value) == False:
                ori_set_ok = False
            print(self.acceldata.get(), "--",self.acceldata.get()[-6:])
        self.set_orientation(origianl_orient)

        return ori_set_ok

    def set_unit_behavior(self, enabel_bit = 2, disable_bit = 0, new_address = None, ext_id = 0x18FF5900):        
        original_behavior = self.get_unit_behavior()
        # target_behavior = ((original_behavior | enabel_bit) ^ disable_bit) # calc the target based on original/enable/disenabel bits
        target_behavior = (original_behavior | enabel_bit) & (~disable_bit)
        if new_address == None:
            data = [self.working_sa, enabel_bit, disable_bit, self.working_sa]
        else:
            data = [self.working_sa, enabel_bit, disable_bit, new_address]
        # print('send bhr reques:')
        self.send_msg(ext_id,data)
        time.sleep(1)
        behavior_get = self.get_unit_behavior()
        if behavior_get == target_behavior:
            return True
        else: 
            print(original_behavior, target_behavior,behavior_get)
            print('set unit behavior failed.')
            return False 
    
    def try_unit_bhr_list(self, actual_measure = False):
        # check some behavior configuration items is set
        enable_list       = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20]
        disable_list      = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20]

        bhr_set_ok        = True
        for value in enable_list:
            if self.set_unit_behavior(enabel_bit=value) == False:
                bhr_set_ok = False
                print('set unit behavior enale value:{0} failure, get_value status is:{1}:'.format(value, self.get_unit_behavior()))
        for value in disable_list:
            if self.set_unit_behavior(disable_bit=value) == False:
                bhr_set_ok = False
                print('set unit behavior disable value:{0} failure, get_value status is:{1}:'.format(value, self.get_unit_behavior()))
        
        return bhr_set_ok

    def set_bank_ps0(self, algo_rst = 0x50, hw_bit = 0x52, sw_bit = 0x53, status_bit = 0x54, hr_acc = 0x6C, ext_id = 0x18FFF000):
        data = [algo_rst, 0, hw_bit, sw_bit, status_bit, hr_acc]
        self.send_msg(ext_id, data)
        set_ps0_ok = True
        if algo_rst != 0x50 and (self.reset_algorithm() != False):
            set_ps0_ok = False
        if hw_bit != 0x52 and (self.get_hw_status() != False):
            set_ps0_ok = False
        if sw_bit != 0x53 and (self.get_sw_status() != False):
            set_ps0_ok = False
        if status_bit != 0x54 and (self.get_sensor_status() != False):
            set_ps0_ok = False
        print('set_ps0_ok before hr acc', set_ps0_ok)
        if hr_acc != 0x6C:
            type_old = self.get_packet_type()
            self.set_pkt_type(0x1F)
            self.empty_data_pkt()            
            # try_times = 100
            time.sleep(1)
            # hr_acc_avi = False
            if self.decode_pke_type_num(self.measure_pkt_type())[4] == True:
                set_ps0_ok = False
            # while try_times and (hr_acc_avi == False):
            #     if self.unknow.get()['pgn'] == (0xff * 256 + hr_acc):
            #         hr_acc_avi = True
            #     try_times -= 1
            # if hr_acc_avi != True:
            #     return False
            self.set_pkt_type(type_old)
        print('set_ps0_ok after hr acc', set_ps0_ok)
        return set_ps0_ok 

    def try_bank_ps0_list(self):
        ps0_set_ok = False
        if self.set_bank_ps0(algo_rst=0x60, hw_bit=0x92, sw_bit=0x93, status_bit=0x94, hr_acc=0x95) == True:
            ps0_set_ok = True
            print('ps0_set_ok', ps0_set_ok)
        else:
            print('try bank ps0 list, failed.')
        
        return ps0_set_ok

    def set_bank_ps1(self,pkt_rate = 0x55, pkt_type = 0x56, dig_filter = 0x57, ori_request = 0x58, ext_id = 0x18FFF100):
        data = [pkt_rate, pkt_type, dig_filter, ori_request]
        self.send_msg(ext_id, data)        
        if pkt_rate != 0x55 and (self.get_packet_rate()[0] != False):
            return False
        if pkt_type != 0x56 and (self.get_packet_type() != False):
            return False
        if dig_filter != 0x57 and (self.get_lpf()[0] != False):
            return False
        if ori_request != 0x58 and (self.get_orientation() != False):
            return False
        time.sleep(0.5)
        return True 

    def try_bank_ps1_list(self):
        ps1_set_ok = False
        if self.set_bank_ps1(pkt_rate = 0x85, pkt_type = 0x86, dig_filter = 0x87, ori_request = 0x88) == True:
            ps1_set_ok = True
            print('ps1_set_ok',ps1_set_ok)
        else:
            print('try bank ps0 list, failed.')
        
        return ps1_set_ok

    def rst_ps0(self, ext_id = 0x18FFF000):
        data = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]        
        self.send_msg(ext_id, data)
        self.save_configuration()
        self.power_rst()      
        return True 
    
    def rst_ps1(self, ext_id = 0x18FFF100):
        data = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]        
        self.send_msg(ext_id, data)
        self.save_configuration()
        self.power_rst()      
        return True 

    def without_sc_pwr_cycle(self, to_lpf_rate = 5, to_odr = 5, to_pkt_type = 0x0F, to_ori = 0x0009, to_behavior = 2):
        self.set_lpf_filter(to_lpf_rate)
        self.set_odr(to_odr)
        self.set_pkt_type(to_pkt_type)
        self.set_orientation(to_ori)
        self.set_unit_behavior(enabel_bit=0,disable_bit=1)
        while input('need to reset power(!!!strong recommend let unit keep power off > 3s !!!), is it finished, y/n ? ') != 'y':
            pass
        time.sleep(1)
        # check the configurations saved or not
        back_lpf_ok                 = True if self.get_lpf()[0] == 25 else False
        back_odr_ok                 = True if self.get_packet_rate()[1] == 1 else False
        back_pkt_type_ok            = True if self.get_packet_type() == 7 else False
        back_ori_ok                 = True if self.get_orientation() == 0 else False
        back_behavior_ok            = True if self.get_unit_behavior() == 2 else False
                
        return back_lpf_ok, back_odr_ok, back_pkt_type_ok, back_ori_ok, back_behavior_ok

    def with_sc_pwr_cycle(self, to_lpf_rate = 5, to_odr = 5, to_pkt_type = 0x0F, to_ori = 0x0009, to_behavior = 2):
        self.set_lpf_filter(to_lpf_rate)
        self.set_odr(to_odr)
        print('set pkt type')
        self.set_pkt_type(to_pkt_type)
        print('set ori')
        self.set_orientation(to_ori)
        self.set_unit_behavior(enabel_bit=0,disable_bit=1)
        self.save_configuration() # restart the unit
        while input('need to reset power(!!!strong recommend let unit keep power off > 3s !!!), is it finished, y/n ? ') != 'y':
            pass
        time.sleep(1)
        # check the configurations saved or not
        print('check after power reset.')
        save_lpf_ok                 = True if self.get_lpf()[0] == to_lpf_rate else False
        save_odr_ok                 = True if self.get_packet_rate()[1] == to_odr else False
        save_pkt_type_ok            = True if self.get_packet_type() == to_pkt_type else False
        save_ori_ok                 = True if self.get_orientation() == to_ori else False
        save_behavior_ok            = True if self.get_unit_behavior() == to_behavior else False
        print('try to get again')
        print(self.get_packet_type())
        print('try finished.')
                
        return save_lpf_ok, save_odr_ok, save_pkt_type_ok, save_ori_ok, save_behavior_ok
        
    def get_pdu_list(self, msg = None, msg_dict = None):         
        if msg == None:
            msg = self.can0.recv()
        msg_list = list(str(msg).split(" "))     # the list include: time, id, priority, DLC, data0,data1,...,data7
        msg_list = [x for x in msg_list if x != '']       # delete the empty items      
        self.pdu_dict["time_stamp"] = float(msg_list[0])
        self.pdu_dict["id"] = int(msg_list[1],16)
        self.pdu_dict["extended_id"] = msg.id_type
        self.pdu_dict["priority"] = int(msg_list[2],2)
        self.pdu_dict["src"] = 0x000000FF & int(msg_list[1],16)
        self.pdu_dict["dlc"] = int(msg_list[3],10)
        self.pdu_dict["pgn"] = (0x00FFFF00 & int(msg_list[1],16)) >> 8
        self.pdu_dict["payload"] = ''.join(msg_list[4:])        
        msg_dict = self.pdu_dict   
        return msg_dict    

    def back_plant_default(self): # back to default confi and power cycle        
        self.set_orientation()
        time.sleep(0.4)
        self.set_pkt_type()
        time.sleep(0.4)
        self.set_lpf_filter()
        self.set_odr()
        self.set_unit_behavior()
        self.set_bank_ps0()
        self.set_bank_ps1()
        self.save_configuration(0)
        print('rst ps0')
        self.rst_ps0()
        time.sleep(1)
        self.rst_ps1()
        time.sleep(1)
        self.power_rst()       
        return True           

if __name__ == "__main__":
    my_can = can_mtlt()    

    # get messages 
    gf = my_can.get_fw_version()    
    gi = my_can.get_id()    
    gh = my_can.get_hw_status()
    gsw = my_can.get_sw_status()
    gss = my_can.get_sensor_status()    
    #set messages
    # my_can.save_configuration()
    # my_can.reset_algorithm()
    my_can.set_odr(1)
    # my.set_pkt_type(7)
    # my_can.set_lpf_filter(25,5)
    # my_can.set_orientation(9)
    my_can.start_record() #start put msgs to queue and parse the msgs

    # time.sleep(0.5)


    # with open('can_data.txt', 'w') as f:  # empty the can_data.txt if it exist
    #     pass

    # while True:
    #     slope_data,accel_data,rate_data = my_can.slopedata.get(),my_can.acceldata.get(),my_can.ratedate.get()  
    #     print('{0}\n{1}\n{2}'.format(slope_data,accel_data,rate_data))
    #     with open('can_data.txt', 'a') as f:  
    #         f.write(slope_data + '\n' + accel_data + '\n' + rate_data + '\n')
    #     if not my_can.addressclaim.empty():
    #         addressclaim = my_can.addressclaim.get()
    #         print(addressclaim)
    #         with open('can_data.txt', 'a') as f:  
    #             f.write(addressclaim + '\n')

   

    



    



      

