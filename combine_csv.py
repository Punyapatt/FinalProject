import pandas as pd
rename = {}
list_csv = []

# Get all csv file for drop column 'portLOCAL' and change columns name.
for i in range(10):
    df = pd.read_csv('csv/portstat_' + str(i+1) + '.csv', index_col=0)
    df.drop('portLOCAL', inplace=True, axis=1)
    for dp in df:
        rename[dp] = str(i+1)+'_'+dp
       
    df.rename(columns = rename, inplace = True)
    list_csv.append(df)
    rename = {}

# Get flowstat.csv for change columns name and replace NaN values with zeros.   
flow_stat = pd.read_csv('csv/flowstat.csv', index_col=0)
flow_stat = flow_stat.fillna(0)

for i in flow_stat:
    rename[i] = 'Host_'+i[-1]
flow_stat.rename(columns = rename, inplace = True)

# Merge dataframe
list_csv.append(flow_stat)
dataFrame = pd.concat(list_csv, axis=1)
dataFrame.to_csv('combine_csv.csv')