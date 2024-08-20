from roll_no_letter_generator import get_letter_list_series, get_letter_list
import pandas as pd
import time
from pathlib import Path

def get_roll_no_list(letter):
    roll_no_list = []
    for i in range(1, 1000):
        if i < 10:
            roll_no_list.append(f"{letter}00{i}")

        elif i in range(10, 100):
            roll_no_list.append(f"{letter}0{i}")
        elif i in range(100, 1000):
            roll_no_list.append(f"{letter}{i}")
        else:
            print("Range limit exceeded")
    return roll_no_list

def split_roll_no_list(roll_no_list, max_async_requests):
    roll_no_list_split = []
    split_number = len(roll_no_list)//max_async_requests
    for i in range(0, int(split_number)):
        start = i*max_async_requests
        end = start + max_async_requests
        roll_no_list_split.append(roll_no_list[start:end])
        if len(roll_no_list) - end < max_async_requests:
            roll_no_list_split.append(roll_no_list[end:len(roll_no_list)])
    return roll_no_list_split

def get_roll_no_list_from_file(file, col_header, max_async_requests):
    df = pd.read_excel(file, engine= 'openpyxl')
    roll_no_list = df[col_header].dropna().to_list()
    roll_no_list_split = split_roll_no_list(roll_no_list, max_async_requests)
    return roll_no_list_split

def generate_roll_no_list(start_series, end_series, max_async_requests):
    letter_list = get_letter_list(start_series, end_series)
    print(letter_list)
    df = pd.DataFrame(columns=["roll_no"])
    for letter in letter_list:
        ll = get_roll_no_list(letter)
        for roll_no in ll:
            df.loc[len(df.index), "roll_no"] = roll_no
    roll_no_list = df["roll_no"].to_list()
    split_ll = split_roll_no_list(roll_no_list, max_async_requests)
    return split_ll



