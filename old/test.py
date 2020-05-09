import os
import xlwings as xw
from excel_sheet import my_excel

test_80 = my_excel()
a98 = test_80.get_value('A98')
a98 = test_80.get_value('A98:A100')
test_80.write('I99', ['99999', '8888', '7777'])
test_80.write('I100', [99, 88, 77])
test_80.write('I102', [99, 88, 77],to_col=True)
test_80.write('I110', [[99, 88, 77], [99, 88, 77], [99, 88, 77]])
test_80.write('I120', [[99, 88, 77], [99, 88, 77], [99, 88, 77]], to_col=True)

print(1)

del test_80
pass