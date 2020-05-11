'''
CAN testing script
v1.0.0 20200509
'''

import os
import sys
import time
import json
from excel_sheet import my_csv
from device import aceinna_device
from driver import aceinna_driver
from test_case import aceinna_test_case

def main(debug_main = False):
    with open('can_attribute.json') as json_data:
        can_attribute = json.load(json_data)
    
    # input('0')
    main_driver = aceinna_driver(debug_mode = debug_main)
    dev_nodes = main_driver.get_can_nodes()
    
    # input('1')
    device_list = []
    for i in dev_nodes:
        ad = aceinna_device(i, attribute_json = can_attribute,debug_mode = debug_main)
        main_driver.register_dev(dev_src = i, instance_dev = ad) # regist each device to driver
        ad.add_driver(main_driver)
        ad.update_sn()
        device_list.append(ad) # add each device instance to device_list
    if debug_main: eval('print(k, i)', {'k':sys._getframe().f_code.co_name,'i':len(device_list)})
    # input('2')
    # test_file = my_csv('result.csv')
    for i in device_list:
        print('start testing device_src:{0} device_sn:{1}'.format(hex(i.src), hex(i.sn_can)))
        test_file = my_csv(os.path.join(os.getcwd(), 'data','result_{0:#X}_{1:#X}.csv'.format(i.src, i.sn_can)))
        main_test = aceinna_test_case(test_file, debug_mode = debug_main)
        main_test.set_test_dev(i, fwnum=0x1301070000)  # need to be updated for each testing ----------input: 1
        # input('22')
        # main_test.run_test_case(test_item='5.9.6')
        main_test.run_test_case()
    print('testing finished', time.time())
    
    return True

if __name__ == "__main__":
    input('will start main()')
    try:
        print(time.time())
        main(debug_main = False)
    except Exception as e:
        print(e)
  
    