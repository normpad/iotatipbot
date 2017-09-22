import re
from bot_api import api
fake_seed = 'A'*81

tip_string = re.compile('(\w*) has tipped (\w*) ([0-9]+) iota',re.I)
withdraw_string = re.compile('(\w*) withdrew (\w*)',re.I)
deposit_string = re.compile('(\w*) was assigned to address (\w*)',re.I)
deposit_complete_string = re.compile('(\w*) deposited ([0-9]+) iota',re.I)
tips = 0
withdraws = 0
deposits = 0
completed_deposits = 0
tip_average = 0
tip_max = 0
bot_api = api(fake_seed)

with open('transactionLogs.log','r') as f:
    for line in f:
        match = tip_string.search(line)
        if match:
            tips = tips + 1    
            tip_average = tip_average + int(match.group(3))
            if int(match.group(3)) > tip_max:
                tip_max = int(match.group(3))
        match = withdraw_string.search(line)
        if match:
            withdraws = withdraws + 1
        match = deposit_string.search(line)
        if match:
            deposits = deposits + 1
        match = deposit_complete_string.search(line)
        if match:
            completed_deposits = completed_deposits + 1

tip_average = int(tip_average/tips)
tip_average_value = bot_api.get_iota_value(tip_average)
tip_max_value = bot_api.get_iota_value(tip_max)
completed_deposit_ratio = int((completed_deposits / deposits)*100)
print('Total tips: {0}'.format(tips))
print('Biggest tip: {0}(${1})'.format(tip_max,tip_max_value))
print('Average tip: {0}(${1})'.format(tip_average,tip_average_value))
print('Total withdraws: {0}'.format(withdraws))
print('Total deposits requests: {0}'.format(deposits))
print('Total completed deposits: {0}'.format(completed_deposits))
print('Completed deposit ratio: {0}%'.format(completed_deposit_ratio))
