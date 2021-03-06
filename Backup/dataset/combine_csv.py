import pandas as pd
import numpy as np
rename = {}
list_csv = []
file_name = 'csv_random_amplitude_2'
# Get all csv file for drop column 'portLOCAL' and change columns name.

for i in range(5):
    df = pd.read_csv(file_name + '/portstat_' + str(i+1) + '.csv', index_col=None)
    df.where(df < 20000000, 20000000, inplace=True) # replacing values greater than a number in DataFrame
    df.replace(0, 480, inplace=True) # Change 0 to 480
    for dp in df:
        rename[dp] = str(i+1)+'_'+dp
    df.rename(columns = rename, inplace = True)
    # df = df.reset_index()
    list_csv.append(df)
    rename = {}

# Get flowstat.csv for change columns name and replace NaN values with zeros.   
# flow_stat = pd.read_csv(file_name + '/flowstat.csv', index_col=None)

# for i in flow_stat:
#     rename[i] = 'Host_'+i[-1]
# flow_stat.rename(columns = rename, inplace = True)

# Merge dataframe
# list_csv.append(flow_stat)
dataFrame = pd.concat(list_csv, axis=1)
dataFrame = dataFrame.fillna(0)
dataFrame.to_csv(file_name + '_combine' + '.csv')
# print(dataFrame.columns)

