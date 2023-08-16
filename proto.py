verified_dates= [8, 16, 23, 38, 46, 53, 68, 76, 83, 98, 106, 113, 128, 136, 143]
i = 31

idx = None

verified_dates.append(i)
verified_dates = sorted(verified_dates)

idx = verified_dates.index(i)
# for v_idx in verified_dates:
#     if i == 1:
#         idx = verified_dates[0]        
#         break
#     elif v_idx < i:
#         idx = v_idx



print(verified_dates[idx - 1])