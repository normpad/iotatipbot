import re
from bot_api import api
fake_seed = 'A'*81

tip_string = re.compile('(\w*) has tipped (\w*) ([0-9]+) iota',re.I)
tips = 0
tip_average = 0
bot_api = api(fake_seed)

with open('transactionLogs.log','r') as f:
    for line in f:
        match = tip_string.search(line)
        if match:
            tips = tips + 1    
            tip_average = tip_average + int(match.group(3))

tip_average = int(tip_average/tips)
tip_average_value = bot_api.get_iota_value(tip_average)
print('Total tips: {0}'.format(tips))
print('Average tip: {0}(${1})'.format(tip_average,tip_average_value))
