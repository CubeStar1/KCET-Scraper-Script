def get_letter_list(startchar, endchar):
    letter_list = []
    start_ascii = ord(startchar)
    end_ascii = ord(endchar)
    if start_ascii > end_ascii:
        (start_ascii, end_ascii) = (end_ascii, start_ascii)


    while start_ascii <= end_ascii:
        if start_ascii == ord("I") or start_ascii == ord("O"):
            start_ascii += 1
            continue



        #print(chr(start_ascii))
        start = ord('A')

        while start <= ord('Z'):
            if start == ord("I") or start == ord("O"):
                start += 1
                continue
            letter_list.append(f"{chr(start_ascii)}{chr(start)}")
            #print(f"{chr(start_ascii)}{chr(start)}")
            start += 1
        start_ascii += 1
    return letter_list
def get_letter_list_series(series, start, end):
    letter_list_series = []
    series_ascii = ord(series)
    start_ascii = ord(start)
    end_ascii = ord(end)
    if start_ascii > end_ascii:
        (start_ascii, end_ascii) = (end_ascii, start_ascii)
    while start_ascii <= end_ascii:
        if start_ascii == ord("I") or start_ascii == ord("O"):
            start_ascii += 1
            continue
        letter_list_series.append(f"{chr(series_ascii)}{chr(start_ascii)}")
        start_ascii += 1
    return letter_list_series




