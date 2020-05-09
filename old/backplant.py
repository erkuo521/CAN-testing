import os
import time
import csv
from mtlt import can_mtlt
from csv_sheet import my_csv



# initial CAN_MTLT instance, restart unit and starting to receive and decoding messages
mtlt0 = can_mtlt()

while True:
    time.sleep(0.1)
    print(mtlt0.get_packet_type())
input('get type')
# print(1)

# # mtlt0.with_sc_pwr_cycle()
# print(2)
mtlt0.back_plant_default()

# time.sleep(1)
# mtlt0.try_bank_ps0_list()
# print(2)
# mtlt0.try_bank_ps1_list()
# print(mtlt0.try_orientation_list())
os._exit(0)
