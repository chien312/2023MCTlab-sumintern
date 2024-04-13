# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import pandas as pd

output_dir = "dv2_layers"
inpute_file =  "dv2_layers.csv"
song_name = "dv2"

df = pd.read_csv(inpute_file)

instrument_dict = {
"flute1":["flute", "flute1"], 
"flute2":["flute", "flute2"],  
"oboe1":["oboe", "oboe1"], 
"oboe2":["oboe", "oboe2"], 
"clarinet1":["clarinet", "clarinet1"], 
"clarinet2":["clari net", "clarinet2"], 
"bassoon1":["bassoon", "bassoon1"], 
"bassoon2":["bassoon", "bassoon2"], 
"horn1":["horn12", "horn1"], 
"horn2":["horn12", "horn2"],
"horn3":["horn34", "horn3"], 
"horn4":["horn34", "horn4"], 
"trumpet1":["trumpet", "trumpet1"], 
"trumpet2":["trumpet", "trumpet2"], 
"trombone1":["trombone12", "trombone1"], 
"trombone2":["trombone12", "trombone2"], 
"trombone3":["trombone3"], 
"timpani":["timpani"], 
"cymbal":["cymbal"],
"triangle":["triangle"],
"violin1":["violin1"], 
"violin2":["violin2"], 
"viola":["viola"], 
"violoncello":["violoncello"], 
"doublebass" :["doublebass"]
}

def check_if_defined(inst_name):
    for name_list in instrument_dict.values():
        if inst_name in name_list: return True
    else: return False
    
for row in range(df.shape[0]):
    if not check_if_defined(df['instrument'][row]):
        raise Exception(f'In row {row}: ', df['instrument'][row], ' is not defined in the instrument_dict')

for instru in instrument_dict.keys():
    instrument_df = df.loc[df["instrument"] .isin(instrument_dict[instru]) ]
    instrument_df = instrument_df.sort_values(by=['onset'])
    instrument_df = instrument_df[['onset', 'offset', 'role']]
    if instrument_df.shape[0]:
        instrument_df.to_csv(f"{output_dir}/{song_name}_layers_{instru}.csv",index=False)
